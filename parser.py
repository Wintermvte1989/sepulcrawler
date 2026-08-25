import hashlib
import html
import json
import os
import re
import tempfile
import time
import difflib
import httpx
import urllib3
from collections import Counter
from datetime import datetime, date
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URLS = [
    # Aktionstage, Festtage & Lange Nächte
    "https://www.tag-des-offenen-denkmals.de/",
    "https://www.lange-nacht-der-museen.de/",
    "https://www.meinkiez-meinfriedhof.berlin.de/tag-des-friedhofs",

    # Berlin: Friedhöfe, Verbände & Grüfte
    "https://www.meinkiez-meinfriedhof.berlin.de/veranstaltungen",
    "https://jewish-cemetery-weissensee.org/entdecken/fuehrungen/",
    "https://www.invalidenfriedhof-berlin.de/",
    "https://www.evfbs.de/",
    "https://marienkirche-berlin.de/",
    "https://www.hedwigs-kathedrale.de/",

    # Brandenburg & Preußische Schlösser/Krypten
    "https://www.suedwestkirchhof.de/veranstaltungen.html",
    "https://www.spsg.de/aktuelles/veranstaltungen",
    "https://kriegsgraeberstaetten.volksbund.de/friedhof/halbe",

    # Berlin & Brandenburg: Bestattungskultur, Hospize & Private
    "https://www.ahorn-gruppe.de/",
    "https://www.sarggeschichten.de/",
    "https://www.ricam-hospiz.de/events/",

    # Berlin & Sachsen: Staatliche & Regionalmuseen
    "https://www.smb.museum/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/aegyptisches-museum-und-papyrussammlung/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/museum-fuer-vor-und-fruehgeschichte/veranstaltungen/",
    "https://www.stadtmuseum.de/programm",
    "https://www.humboldtforum.org/de/programm/",
    "https://www.jmberlin.de/",
    "https://www.dhmd.de/ausstellungen/",

    # Brandenburg: Stadtmuseen & Regionalgeschichte
    "https://www.potsdam-museum.de/de/veranstaltungen",
    "https://stadtmuseum.stadt-brandenburg.de/stadtmuseum/termine",
    "https://www.museum-eberswalde.de/angebote/kalender",
    "https://www.brandenburg-preussen-museum.de/besuch-planen/veranstaltungen.html",

    # Prag & Tschechien: Beinhäuser, Jüdischer Friedhof & Museen
    "https://www.sedlec.info/",
    "https://www.jewishmuseum.cz/en/info/visit/",
    "https://www.nm.cz/en/program/events",

    # Beinhäuser, Mumien, Grüfte & Sakralbauten
    "https://stpetridom.de/der-dom/besucher-info/bleikeller/",
    "https://www.stadt-oppenheim.de/",
    "https://www.katharinenkirche-oppenheim.de/",
    "https://www.muenster-doberan.de/",
    "https://www.pfarrei-chammuenster.de/",
    "https://www.koelner-dom.de/aktuelles",
    "https://www.st-michaelis.de/veranstaltungen-am-michel",
    "https://www.hallstatt.net/",
    "https://www.magdeburgerdom.de/",
    "https://www.naumburger-dom.de/",
    "https://www.kaisergruft.com/",
    "https://www.stephansdom.at/",
    "https://www.stift-stpeter.at/de/kloster/index.asp?dat=Friedhof-Katakomben",
    "https://www.stiftadmont.at/",
    "https://bamberger-dom.de/gotteshaus/besucherpastoral/Veranstaltungen/index.html",
    "https://www.bamberger-dommusik.de/",
    "https://www.bistum-passau.de/dom-kultur/dom-st-stephan-passau",
    "https://www.dom-erfurt.de/",
    "https://www.dom-zu-speyer.de/",
    "https://www.dom-wuerzburg.de/",
    "https://www.dommuseum-mainz.de/programm/kalender/aktuelle-termine-kalender/",
    "https://www.freiburger-muenster.de/",
    "https://www.st-marien-luebeck.de/",
    "https://www.welterbe-quedlinburg.de/",

    # NRW & Überregional Deutschland: Archäologie & Friedhöfe
    "https://www.duesseldorf.de/stadtgruen/freizeit/fuehrungen1",
    "https://www.stadt-muenster.de/gruen/friedhoefe",
    "https://www.zentralfriedhof-muenster.de/",
    "https://www.stiftsmuseum-xanten.de/",
    "https://www.ruhrmuseum.de/veranstaltungen/",
    "https://www.archaeologie-bayern.de/de/termine/",
    "https://www.landesmuseum-vorgeschichte.de/veranstaltungen/familiennachmittage",
    "https://www.leiza.de/aktuelles",
    "https://www.lwl-landesmuseum-herne.de/de/veranstaltungen/",
    "https://www.archaeologisches-museum-frankfurt.de/",
    "https://www.landesmuseum-trier.de/",
    "https://schloss-gottorf.de/",
    "https://www.archaeologie-online.de/nachrichten/",

    # Überregional Deutschland: Friedhofskultur, Vereine & Vorträge
    "https://www.sepulkralmuseum.de/veranstaltungen/",
    "https://paul-benndorf-gesellschaft.de/fuehrungen.html",
    "https://eliasfriedhof.de/termine/",
    "http://www.friedhofskultur-halle.de/terminefuehrungen/",
    "https://www.friedhof-hamburg.de/besucher/veranstaltungen/",
    "https://www.ohlsdorf-derpark.de/termine-ohlsdorf/",
    "https://www.stattreisen-muenchen.de/fuehrungen/der-alte-sudliche-friedhof",
    "https://www.florian-scheungraber.de/termine/",
    "https://theatergemeinde-koeln.org/Kulturkompass/werk/25725/M04/stadtfuhrungen-koln/fuehrung-uber-melaten",
    "https://www.friedhofsverwalter.de/fachveranstaltung-der-arbeitsgemeinschaft-friedhof-und-denkmal-e-v/",
    "https://aufdasleben.de/event/",
    "https://www.totentanz-online.de/veranstaltungen.php",
    "https://home.benecke.com/",
    "https://www.krfrm.de/venue/hauptfriedhof-frankfurt-am-main/",
    "https://www.frankfurter-stadtevents.de/Themen/Friedhfe-Parks/Hauptfriedhof-Frankfurt-Grber-erzhlen-Geschichte_20010010/",

    # Nischen-Blogs
    "https://friedhofsfreunde.blogspot.com/",

    # Schweiz & Regionalverwaltung Friedhöfe
    "https://www.stadt-zuerich.ch/friedhofforum/de/veranstaltungen.html",
    "https://www.stadtgaertnerei.bs.ch/friedhoefe/veranstaltungen.html",
    "https://www.bernermuenster.ch/",
    "https://www.stiftsbezirk.ch/de/veranstaltungen",
    "https://www.museum-aargau.ch/schloss-lenzburg/event-kalender",
    "https://www.innsbruck.gv.at/leben/friedhoefe",
    "https://www.stadt-salzburg.at/friedhoefe",
    "https://www.karlsruhe.de/freizeit-und-sport/friedhoefe",
    "https://www.augsburg.de/umwelt/umweltthemen/friedhoefe",
    "https://www.darmstadt.de/leben-in-darmstadt/umwelt/friedhoefe",
    "https://www.saarbruecken.de/leben_in_saarbruecken/planen_bauen_wohnen/friedhoefe",
    "https://striesener-friedhof-dresden.de/vorschau-veranstaltungen/",
    "https://www.braunschweig.de/leben/umwelt_naturschutz/stadtgruen/friedhoefe/",
    "https://www.kiel.de/de/umwelt_verkehr/friedhoefe/",
    "https://www.augustinerkloster.de/veranstaltungen/",
    "https://www.chemnitz.de/chemnitz/de/unsere-stadt/friedhoefe/veranstaltungen.html"
]

DB_FILE = "events_db.json"
HTML_OUTPUT_FILE = "index.html"

BATCH_SIZE = 8          # nicht erhoehen - Output-Limit der API beachten
TEXT_LIMIT = 9000       # Zeichen pro Seite, die an die API gehen
MIN_TEXT_LENGTH = 1500  # darunter: vermutlich JS-gerenderte Seite ohne Inhalt
STALE_AFTER_DAYS = 10   # ab hier "nicht mehr bestaetigt" im HTML
API_ATTEMPTS = 3

BERLIN = ZoneInfo("Europe/Berlin")

DATE_PATTERN = re.compile(
    r"\b\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}\b"
    r"|\b\d{1,2}\.\s*(Januar|Februar|M\u00e4rz|April|Mai|Juni|Juli|"
    r"August|September|Oktober|November|Dezember)\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)

MONTH_MAP = {
    "jan": 1, "januar": 1,
    "feb": 2, "februar": 2,
    "mär": 3, "mrz": 3, "märz": 3, "maerz": 3,
    "apr": 4, "april": 4,
    "mai": 5,
    "jun": 6, "juni": 6,
    "jul": 7, "juli": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dez": 12, "dezember": 12,
}

STOP_WORDS = {
    "führung", "sonderführung", "ausstellung", "vortrag", "konzert",
    "rundgang", "spaziergang", "lesung", "filmvorführung", "museum",
    "tag", "tage", "über", "durch", "nach", "beim", "eines", "einer",
    "einen", "einem", "mit", "und", "oder", "für", "vom", "auf", "dem",
    "den", "der", "die", "das", "des", "aus", "zum", "zur", "von", "im", "in"
}

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


class TruncatedResponseError(Exception):
    """Antwort der API war kein gueltiges JSON - meist abgeschnitten wegen Output-Limit."""


class Event(BaseModel):
    source_id: int = Field(description="Nummer der QUELLE, aus der dieses Event stammt")
    title: str = Field(description="Titel der Veranstaltung")
    date_start: str = Field(description="Startdatum im Format YYYY-MM-DD")
    date_end: str | None = Field(
        default=None,
        description="Enddatum YYYY-MM-DD, nur bei mehrtaegigen Veranstaltungen, sonst null",
    )
    location: str = Field(description="Ort oder Institution der Veranstaltung")
    description: str = Field(description="Kurze Zusammenfassung in 1-2 Saetzen")


class EventList(BaseModel):
    events: list[Event]


# ---------------------------------------------------------------- Datum & Text-Normalisierung

def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    s = str(date_str).strip().lower()

    match_iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if match_iso:
        y, m, d = map(int, match_iso.groups())
        try:
            return date(y, m, d).isoformat()
        except ValueError:
            pass

    match_num = re.search(r"\b(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})\b", s)
    if match_num:
        d, m, y = map(int, match_num.groups())
        if y < 100:
            y += 2000
        try:
            return date(y, m, d).isoformat()
        except ValueError:
            pass

    match_text = re.search(r"\b(\d{1,2})\.?\s+([a-zäöü]+)\.?\s+(\d{2,4})\b", s)
    if match_text:
        d_str, month_str, y_str = match_text.groups()
        d = int(d_str)
        y = int(y_str)
        if y < 100:
            y += 2000
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            try:
                return date(y, month_num, d).isoformat()
            except ValueError:
                pass

    return None


def clean_text_for_comparison(text: str) -> str:
    if not text:
        return ""
    s = str(text).lower()
    s = re.sub(r'[–—:\,\"`«»„“\(\)\[\]\-\n\r]', ' ', s)
    s = s.replace("'", ' ').replace('"', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def extract_tokens(text: str) -> set[str]:
    if not text:
        return set()
    cleaned = clean_text_for_comparison(text)
    words = set(re.findall(r'\b\w{3,}\b', cleaned))
    return words - STOP_WORDS


def are_events_duplicate(ev1: dict, ev2: dict) -> bool:
    # 1. Startdatum muss exakt übereinstimmen
    if ev1.get("date_start") != ev2.get("date_start"):
        return False

    t1 = clean_text_for_comparison(ev1.get("title", ""))
    t2 = clean_text_for_comparison(ev2.get("title", ""))

    if not t1 or not t2:
        return False

    if t1 == t2:
        return True

    # Ähnlichkeitsvergleich der Titel
    ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
    if ratio >= 0.72:
        return True

    # Token-Analyse von Ort & Titel
    tok1 = extract_tokens(ev1.get("title", ""))
    tok2 = extract_tokens(ev2.get("title", ""))
    loc1 = extract_tokens(ev1.get("location", ""))
    loc2 = extract_tokens(ev2.get("location", ""))

    same_loc = len(loc1 & loc2) > 0 or not loc1 or not loc2

    if same_loc:
        common_tokens = tok1 & tok2
        # Wenn mindestens 2 signifikante Wörter im Titel übereinstimmen
        if len(common_tokens) >= 2:
            return True

        # Substring-Matching bei ausreichend langen Einzellokationen (z.B. Melaten)
        if (t1 in t2 or t2 in t1) and min(len(t1), len(t2)) >= 5:
            return True

        # Auswertung der Beschreibung bei abweichenden Titeln
        desc1 = extract_tokens(ev1.get("description", ""))
        desc2 = extract_tokens(ev2.get("description", ""))
        if len(desc1 & desc2) >= 4:
            return True

    return False


# ---------------------------------------------------------------- Datenbank & Deduplizierung

def load_events_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events_db(db: dict):
    directory = os.path.dirname(os.path.abspath(DB_FILE)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, DB_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def deduplicate_db(db: dict) -> dict:
    events = list(db.values())
    merged_events = []

    for ev in events:
        found_dup = False
        for existing in merged_events:
            if are_events_duplicate(ev, existing):
                existing["first_seen"] = min(existing.get("first_seen", "9999"), ev.get("first_seen", "9999"))
                existing["last_seen"] = max(existing.get("last_seen", ""), ev.get("last_seen", ""))
                
                if len(ev.get("title", "")) > len(existing.get("title", "")):
                    existing["title"] = ev["title"]
                if len(ev.get("description", "")) > len(existing.get("description", "")):
                    existing["description"] = ev["description"]
                if len(ev.get("location", "")) > len(existing.get("location", "")):
                    existing["location"] = ev["location"]
                if not existing.get("date_end") and ev.get("date_end"):
                    existing["date_end"] = ev["date_end"]
                
                found_dup = True
                break
        
        if not found_dup:
            merged_events.append(ev)

    cleaned_db = {}
    for ev in merged_events:
        norm_t = clean_text_for_comparison(ev.get("title", ""))
        raw = f"{norm_t}|{ev.get('date_start', '')}"
        event_id = hashlib.md5(raw.encode("utf-8")).hexdigest()
        cleaned_db[event_id] = ev

    return cleaned_db


# ---------------------------------------------------------------- Auswahl

def is_worth_sending(url: str, text: str) -> bool:
    if len(text) < MIN_TEXT_LENGTH:
        print(f"  uebersprungen (nur {len(text)} Zeichen, evtl. JS-gerendert): {url}")
        return False
    if not DATE_PATTERN.search(text):
        print(f"  uebersprungen (kein Datumsmuster gefunden): {url}")
        return False
    return True


# ---------------------------------------------------------------- Abruf & Fallback

def fetch_page_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    urls_to_try = [url]
    parsed = urlparse(url)
    if parsed.path and parsed.path != "/":
        urls_to_try.append(f"{parsed.scheme}://{parsed.netloc}/")

    last_exception = None
    for current_url in urls_to_try:
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=25.0, verify=False) as client_http:
                response = client_http.get(current_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
                    tag.decompose()

                main = soup.find("main") or soup.find("article") or soup
                text = main.get_text(separator=" ", strip=True)
                if len(text) >= MIN_TEXT_LENGTH or current_url != url:
                    return text
        except httpx.HTTPStatusError as e:
            last_exception = e
            if e.response.status_code == 404:
                print(f"  404 auf {current_url} -> versuche Fallback...")
                continue
        except Exception as e:
            last_exception = e
            break

    raise last_exception if last_exception else Exception("Unbekannter Ladefehler")


# ---------------------------------------------------------------- Extraktion

def extract_events_batch(batch_sources: list[tuple[str, str]], today_str: str) -> list[dict]:
    combined_text = ""
    for idx, (url, text) in enumerate(batch_sources, start=1):
        combined_text += (
            f"\n=== QUELLE {idx} ===\n{text[:TEXT_LIMIT]}\n=== ENDE QUELLE {idx} ===\n"
        )

    prompt = f"""
    Das heutige Datum ist {today_str}.
    Analysiere die folgenden Webseiten-Texte auf Veranstaltungen im Bereich Sepulkralkultur,
    Friedhofsfuehrungen, Bestattungswesen, Totenkult, Gedenkkultur, Grabkunst oder
    historische Ausstellungen zum Thema Tod/Sterben.

    WICHTIG:
    - Extrahiere AUSSCHLIESSLICH Veranstaltungen, deren Datum am oder nach dem heutigen Datum ({today_str}) liegt.
    - date_start MUSS strikt YYYY-MM-DD sein.
    - date_end nur bei mehrtaegigen Veranstaltungen (Ausstellungen, Aktionstage) setzen, sonst null.
    - Ignoriere alle vergangenen Veranstaltungen strikt.
    - Trage in 'source_id' die Nummer der QUELLE ein, in deren Block das Event stand.
    - MEHRSPRACHIGE TEXTE: Falls der Quelltext auf Englisch, Tschechisch oder einer anderen
      Sprache verfasst ist, uebersetze title, location und description praezise ins Deutsche.

    Webseiten-Daten:
    {combined_text}
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EventList,
            temperature=0.1,
        ),
    )

    raw_text = (response.text or "").strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"  JSON-Fehler: {e}")
        print(f"  Antwortlaenge: {len(raw_text)} Zeichen")
        print(f"  Ende der Antwort: ...{raw_text[-200:]}")
        raise TruncatedResponseError(str(e))

    valid = []
    for ev in result.get("events", []):
        sid = ev.pop("source_id", None)
        if isinstance(sid, int) and 1 <= sid <= len(batch_sources):
            ev["url"] = batch_sources[sid - 1][0]
            valid.append(ev)
        else:
            print(f"  verworfen (ungueltige source_id={sid}): {ev.get('title')}")
    return valid


def call_with_retry(batch_sources, today_str) -> list[dict]:
    for attempt in range(API_ATTEMPTS):
        try:
            return extract_events_batch(batch_sources, today_str)
        except TruncatedResponseError:
            print("  Antwort abgeschnitten - kein Retry, BATCH_SIZE pruefen")
            return []
        except Exception as e:
            wait = 5 * (2 ** attempt)
            print(f"  Versuch {attempt + 1}/{API_ATTEMPTS} fehlgeschlagen ({e}), warte {wait}s")
            if attempt < API_ATTEMPTS - 1:
                time.sleep(wait)
    print("  endgueltig aufgegeben")
    return []


# ---------------------------------------------------------------- HTML

def render_html(events: list[dict], today: date):
    timestamp = datetime.now(BERLIN).strftime("%d.%m.%Y um %H:%M Uhr")
    sorted_events = sorted(events, key=lambda x: x.get("date_start", ""))
    today_str = today.isoformat()

    html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sepulkralkultur Event-Feed</title>
    <style>
        :root {{
            --bg-body: #f4f6f8;
            --bg-container: #ffffff;
            --text-main: #333333;
            --text-muted: #7f8c8d;
            --heading-color: #2c3e50;
            --border-color: #ecf0f1;
            --filter-bg: #f8f9fa;
            --filter-border: #e9ecef;
            --tag-bg: #e9ecef;
            --tag-text: #495057;
            --tag-active-bg: #3498db;
            --tag-active-text: #ffffff;
            --th-bg: #2c3e50;
            --th-text: #ffffff;
            --tr-hover: #f8f9fa;
            --location-color: #34495e;
            --btn-bg: #27ae60;
            --btn-hover: #219150;
            --input-border: #ced4da;
            --input-bg: #ffffff;
            --toggle-bg: #e9ecef;
        }}

        [data-theme="dark"] {{
            --bg-body: #121417;
            --bg-container: #1e2227;
            --text-main: #e1e6eb;
            --text-muted: #8b99a8;
            --heading-color: #8fa0b3;
            --border-color: #2d353e;
            --filter-bg: #181b1f;
            --filter-border: #2d353e;
            --tag-bg: #2d353e;
            --tag-text: #c0caf5;
            --tag-active-bg: #3498db;
            --tag-active-text: #ffffff;
            --th-bg: #2a323d;
            --th-text: #e1e6eb;
            --tr-hover: #252a30;
            --location-color: #a0b2c6;
            --btn-bg: #27ae60;
            --btn-hover: #219150;
            --input-border: #3d4652;
            --input-bg: #181b1f;
            --toggle-bg: #2d353e;
        }}

        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 20px; transition: background-color 0.2s, color 0.2s; }}
        
        .header-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--tag-active-bg); padding-bottom: 10px; margin-bottom: 10px; }}
        h1 {{ color: var(--heading-color); margin: 0; font-size: 1.8em; }}
        
        .theme-toggle-btn {{ background: var(--toggle-bg); border: 1px solid var(--filter-border); color: var(--text-main); padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 1em; display: flex; align-items: center; gap: 6px; font-weight: 600; transition: all 0.2s; }}
        .theme-toggle-btn:hover {{ opacity: 0.85; }}

        .container {{ background: var(--bg-container); border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: background-color 0.2s; }}
        .timestamp {{ font-size: 0.85em; color: var(--text-muted); margin-bottom: 20px; }}

        .filter-container {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; align-items: center; background: var(--filter-bg); padding: 15px; border-radius: 6px; border: 1px solid var(--filter-border); }}
        .search-input {{ flex: 1; min-width: 250px; padding: 8px 12px; border: 1px solid var(--input-border); background-color: var(--input-bg); color: var(--text-main); border-radius: 4px; font-size: 0.95em; }}
        .filter-tags {{ display: flex; gap: 5px; flex-wrap: wrap; }}
        .tag-btn {{ background: var(--tag-bg); border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; color: var(--tag-text); font-weight: 600; transition: all 0.2s; }}
        .tag-btn:hover {{ opacity: 0.85; }}
        .tag-btn.active {{ background: var(--tag-active-bg); color: var(--tag-active-text); }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background-color: var(--th-bg); color: var(--th-text); text-align: left; padding: 10px; font-size: 0.9em; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid var(--border-color); vertical-align: top; font-size: 0.95em; }}
        tr:hover {{ background-color: var(--tr-hover); }}
        .date-badge {{ background-color: var(--tag-active-bg); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; white-space: nowrap; }}
        .date-end {{ display: block; margin-top: 4px; font-size: 0.8em; color: var(--text-muted); white-space: nowrap; }}
        .location {{ font-weight: bold; color: var(--location-color); }}
        .badge-new {{ background: #27ae60; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 6px; vertical-align: middle; }}
        .badge-stale {{ background: #f39c12; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 6px; vertical-align: middle; }}
        a.btn {{ display: inline-block; background-color: var(--btn-bg); color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; }}
        a.btn:hover {{ background-color: var(--btn-hover); }}
        .no-results {{ display: none; padding: 20px; text-align: center; color: var(--text-muted); font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-bar">
            <h1>Sepulkralkultur &amp; Friedhofskultur &ndash; Termine</h1>
            <button id="themeToggleBtn" class="theme-toggle-btn" onclick="toggleTheme()">
                <span id="themeIcon">🌙</span> <span id="themeLabel">Dunkel</span>
            </button>
        </div>
        <div class="timestamp">Stand: {timestamp} | Zeige <span id="visibleCount">{len(sorted_events)}</span> von {len(sorted_events)} Events</div>

        <div class="filter-container">
            <input type="text" id="searchInput" class="search-input" placeholder="Events durchsuchen (z. B. Beinhaus, Köln, Leipzig, Stahnsdorf)..." onkeyup="filterEvents()">
            <div class="filter-tags">
                <button class="tag-btn active" data-filter="" onclick="setTagFilter(this)">Alle</button>
                <button class="tag-btn" data-filter="berlin" onclick="setTagFilter(this)">Berlin</button>
                <button class="tag-btn" data-filter="führung|rundgang|spaziergang" onclick="setTagFilter(this)">Führungen</button>
                <button class="tag-btn" data-filter="konzert|musik|kunst|lesung|film" onclick="setTagFilter(this)">Konzerte &amp; Kunst</button>
                <button class="tag-btn" data-filter="ausstellung|vortrag|museum" onclick="setTagFilter(this)">Ausstellungen</button>
                <button class="tag-btn" data-filter="trauer|hospiz|kurs|workshop" onclick="setTagFilter(this)">Trauer &amp; Praxis</button>
            </div>
        </div>

        <div id="noResults" class="no-results">Keine passenden Veranstaltungen f&uuml;r die Suchkriterien gefunden.</div>
"""

    if sorted_events:
        html_content += """
        <table id="eventsTable">
            <thead>
                <tr>
                    <th>Datum</th>
                    <th>Titel</th>
                    <th>Ort</th>
                    <th>Beschreibung</th>
                    <th>Aktion</th>
                </tr>
            </thead>
            <tbody>
"""
        for event in sorted_events:
            date_s = html.escape(event.get("date_start", ""))
            title_s = html.escape(event.get("title", ""))
            loc_s = html.escape(event.get("location", ""))
            desc_s = html.escape(event.get("description", ""))

            raw_url = str(event.get("url") or "")
            url_s = html.escape(raw_url) if raw_url.startswith(("http://", "https://")) else "#"

            end_html = ""
            if event.get("date_end"):
                end_html = f'<span class="date-end">bis {html.escape(event["date_end"])}</span>'

            badges = ""
            if event.get("first_seen") == today_str:
                badges += '<span class="badge-new">neu</span>'
            last_seen = event.get("last_seen")
            if last_seen:
                try:
                    age = (today - date.fromisoformat(last_seen)).days
                    if age > STALE_AFTER_DAYS:
                        badges += f'<span class="badge-stale">seit {age} Tagen nicht best&auml;tigt</span>'
                except ValueError:
                    pass

            html_content += f"""
                <tr>
                    <td><span class="date-badge">{date_s}</span>{end_html}</td>
                    <td><strong>{title_s}</strong>{badges}</td>
                    <td class="location">{loc_s}</td>
                    <td>{desc_s}</td>
                    <td><a href="{url_s}" target="_blank" rel="noopener noreferrer" class="btn">Link &ouml;ffnen</a></td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""
    else:
        html_content += "<p>Derzeit keine bevorstehenden Termine in der Datenbank.</p>"

    html_content += """
    </div>

    <script>
        let currentTagPattern = '';

        function initTheme() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
                document.getElementById('themeIcon').innerText = '☀️';
                document.getElementById('themeLabel').innerText = 'Hell';
            }
        }

        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === 'dark') {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                document.getElementById('themeIcon').innerText = '🌙';
                document.getElementById('themeLabel').innerText = 'Dunkel';
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                document.getElementById('themeIcon').innerText = '☀️';
                document.getElementById('themeLabel').innerText = 'Hell';
            }
        }

        function setTagFilter(btn) {
            document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTagPattern = btn.getAttribute('data-filter').toLowerCase();
            filterEvents();
        }

        function filterEvents() {
            const searchValue = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#eventsTable tbody tr');
            let visibleCount = 0;

            const keywords = currentTagPattern ? currentTagPattern.split('|') : [];

            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                const matchesSearch = text.includes(searchValue);
                
                let matchesTag = true;
                if (keywords.length > 0) {
                    matchesTag = keywords.some(kw => text.includes(kw));
                }

                if (matchesSearch && matchesTag) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });

            document.getElementById('visibleCount').innerText = visibleCount;
            document.getElementById('noResults').style.display = (visibleCount === 0 && rows.length > 0) ? 'block' : 'none';
        }

        initTheme();
    </script>
</body>
</html>
"""

    with open(HTML_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)


# ---------------------------------------------------------------- Hauptlauf

if __name__ == "__main__":
    today = datetime.now(BERLIN).date()
    today_str = today.isoformat()

    raw_db = load_events_db()
    print(f"Bestand geladen: {len(raw_db)} Roh-Events")

    events_db = deduplicate_db(raw_db)
    print(f"Nach Initial-Deduplizierung: {len(events_db)} eindeutige Events")

    print(f"\n--- Phase 1: Webseiten laden ({len(TARGET_URLS)} Quellen) ---")
    fetched_pages = []
    for url in TARGET_URLS:
        try:
            page_text = fetch_page_text(url)
        except Exception as e:
            print(f"  Fehler beim Laden: {url} - {e}")
            continue

        print(f"  {len(page_text):>6} Zeichen  {url}")
        if is_worth_sending(url, page_text):
            fetched_pages.append((url, page_text))

    print(f"\n{len(fetched_pages)} Seiten gehen an die API "
          f"({(len(fetched_pages) + BATCH_SIZE - 1) // BATCH_SIZE} Requests)")

    print(f"\n--- Phase 2: KI-Analyse in {BATCH_SIZE}er-Paketen ---")
    stats = Counter()
    for i in range(0, len(fetched_pages), BATCH_SIZE):
        batch = fetched_pages[i:i + BATCH_SIZE]
        print(f"\nPaket {i // BATCH_SIZE + 1} ({len(batch)} Seiten)")

        events = call_with_retry(batch, today_str)
        print(f"  {len(events)} Events extrahiert")

        for event in events:
            parsed_start = parse_date(event.get("date_start", ""))
            if parsed_start is None:
                print(f"  verworfen (Datum unlesbar '{event.get('date_start')}'): {event.get('title')}")
                stats["datum_ungueltig"] += 1
                continue
            event["date_start"] = parsed_start
            event["date_end"] = parse_date(event.get("date_end") or "")

            relevant = event["date_end"] or event["date_start"]
            if relevant < today_str:
                stats["vergangen"] += 1
                continue

            found_duplicate_key = None
            for existing_id, existing_ev in events_db.items():
                if are_events_duplicate(event, existing_ev):
                    found_duplicate_key = existing_id
                    break

            if found_duplicate_key:
                existing = events_db[found_duplicate_key]
                existing["first_seen"] = min(existing.get("first_seen", today_str), today_str)
                existing["last_seen"] = today_str
                if len(event.get("title", "")) > len(existing.get("title", "")):
                    existing["title"] = event["title"]
                if len(event.get("description", "")) > len(existing.get("description", "")):
                    existing["description"] = event["description"]
                if len(event.get("location", "")) > len(existing.get("location", "")):
                    existing["location"] = event["location"]
                if not existing.get("date_end") and event.get("date_end"):
                    existing["date_end"] = event["date_end"]
                stats["aktualisiert"] += 1
            else:
                event["first_seen"] = today_str
                event["last_seen"] = today_str
                norm_t = clean_text_for_comparison(event.get("title", ""))
                raw_id = f"{norm_t}|{event.get('date_start', '')}"
                new_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()
                events_db[new_id] = event
                stats["neu"] += 1

        time.sleep(4)

    events_db = deduplicate_db(events_db)
    cleaned_db = {}
    for event_id, event in events_db.items():
        relevant = event.get("date_end") or event.get("date_start", "")
        if relevant >= today_str:
            cleaned_db[event_id] = event
    stats["entfernt"] = len(events_db) - len(cleaned_db)

    save_events_db(cleaned_db)
    render_html(list(cleaned_db.values()), today)

    print("\n--- Zusammenfassung ---")
    print(f"  neu:            {stats['neu']}")
    print(f"  aktualisiert:   {stats['aktualisiert']}")
    print(f"  Datum ungueltig:{stats['datum_ungueltig']}")
    print(f"  vergangen:      {stats['vergangen']}")
    print(f"  DB bereinigt:   {stats['entfernt']} entfernt")
    print(f"\n{len(cleaned_db)} aktive Events in '{HTML_OUTPUT_FILE}' geschrieben.")