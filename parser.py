import hashlib
import html
import json
import os
import re
import tempfile
import time
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
    "https://forum1848.de/veranstaltungen/",
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

    # Beinhäuser, Mumien, Grüfte & Sakralbauten (Deutschland & Österreich)
    "https://stpetridom.de/der-dom/besucher-info/bleikeller/",
    "https://www.stadt-oppenheim.de/",
    "https://www.muenster-doberan.de/",
    "https://www.pfarrei-chammuenster.de/",
    "https://www.koelner-dom.de/aktuelles",
    "https://www.st-michaelis.de/veranstaltungen-am-michel",
    "https://www.kaisergruft.com/",
    "https://www.hallstatt.net/",
    "https://www.magdeburgerdom.de/",
    "https://www.naumburger-dom.de/",
    "https://www.katharinen-kirche-oppenheim.de/",
    "https://www.abtei-waldsassen.de/",
    "https://www.dom-speyer.de/",
    "https://www.wuerzburger-dom.de/",

    # NRW & Überregional Deutschland: Archäologie, Sepulkralmuseum & Sakralbauten
    "https://www.duesseldorf.de/stadtgruen/friedhoefe/veranstaltungen",
    "https://www.stiftsmuseum-xanten.de/",
    "https://www.ruhrmuseum.de/veranstaltungen/",
    "https://www.muenster.de/friedhoefe/veranstaltungen.html",
    "https://www.duesseldorf.de/stadtmuseum/veranstaltungen",
    "https://www.rem-mannheim.de/ausstellungen/veranstaltungen/",
    "https://www.archaeologie-online.de/termine/",
    "https://www.archaeologie-bayern.de/de/termine/",
    "https://www.landesmuseum-vorgeschichte.de/veranstaltungen/familiennachmittage",
    "https://www.leiza.de/aktuelles",
    "https://www.lwl-landesmuseum-herne.de/de/veranstaltungen/",
    "https://www.archaeologisches-museum-frankfurt.de/",
    "https://www.landesmuseum-trier.de/",
    "https://schloss-gottorf.de/",

    # Überregional Deutschland: Friedhofskultur & Vereine
    "https://www.sepulkralmuseum.de/veranstaltungen/",
    "https://paul-benndorf-gesellschaft.de/fuehrungen.html",
    "https://eliasfriedhof.de/category/veranstaltungen/",
    "http://www.friedhofskultur-halle.de/terminefuehrungen/",
    "https://www.friedhof-hamburg.de/besucher/veranstaltungen/",
    "https://www.ohlsdorf-derpark.de/termine-ohlsdorf/",
    "https://www.stattreisen-muenchen.de/fuehrungen/der-alte-sudliche-friedhof",
    "https://www.florian-scheungraber.de/termine/",
    "https://theatergemeinde-koeln.org/Kulturkompass/werk/25725/M04/stadtfuhrungen-koln/fuehrung-uber-melaten",
    "https://www.friedhofsverwalter.de/fachveranstaltung-der-arbeitsgemeinschaft-friedhof-und-denkmal-e-v/",
    "https://aufdasleben.de/event/",
    "https://www.totentanz-online.de/veranstaltungen.php"

# --- ÖSTERREICH: Grüfte, Katakomben, Beinhäuser & Friedhofskultur ---
    "https://www.stephansdom.at/visit_tours_catacombs.php",           # Katakomben Stephansdom Wien
    "https://www.petersfriedhof.at/",                                 # Petersfriedhof & Katakomben Salzburg
    "https://www.stift-admont.at/museum/",                            # Stift Admont (Museum & Tod-Thematik)
    "https://www.innsbruck.gv.at/kultur/friedhoefe/veranstaltungen",   # Stadtfriedhöfe Innsbruck
    "https://www.stadt-salzburg.at/friedhoefe/veranstaltungen",       # Kommunalfriedhof Salzburg

    # --- SCHWEIZ: Friedhofsforum, Beinhäuser & Sakralbauten ---
    "https://www.stadt-zuerich.ch/gued/de/index/friedhoefe/friedhofforum/veranstaltungen.html", # Friedhof Forum Zürich
    "https://www.stadtgaertnerei.bs.ch/friedhoefe/veranstaltungen.html",                       # Friedhof Hörnli & Wolfgottesacker Basel
    "https://www.bernermuenster.ch/de/kalender",                                                # Berner Münster (Krypta & Totentanz)
    "https://www.stiftsbezirk.ch/de/veranstaltungen",                                           # Stiftsbezirk St. Gallen (Stiftsbibliothek & Reliquien)
    "https://www.museum-aargau.ch/schloss-lenzburg/event-kalender",                            # Schloss Lenzburg (Ritterkultur & Grabfunde)

    # --- DEUTSCHLAND: Bayern & Baden-Württemberg ---
    "https://www.alter-friedhof-freiburg.de/",                        # Alter Friedhof Freiburg i. Br.
    "https://www.freiburger-muenster.de/kalender",                    # Freiburger Münster (Krypta & Grabdenkmäler)
    "https://www.karlsruhe.de/freizeit-und-sport/friedhoefe/veranstaltungen", # Hauptfriedhof Karlsruhe
    "https://www.domberg-bamberg.de/veranstaltungen",                 # Bamberger Dom (Kaisergrab Heinrich II.)
    "https://www.augsburg.de/umwelt/umweltthemen/friedhoefe/termine", # Alter Ostfriedhof & Hauptfriedhof Augsburg
    "https://www.passauer-dom.de/",                                   # Passauer Dom & Bischofsgruft

    # --- DEUTSCHLAND: Hessen, Rheinland-Pfalz & Saarland ---
    "https://www.frankfurter-hauptfriedhof.de/termine.htm",            # Hauptfriedhof Frankfurt a. M. (Verein)
    "https://www.mainzer-dom.de/aktuelles/termine/",                  # Mainzer Dom (Bischofsgrüfte & Denkmäler)
    "https://www.darmstadt.de/leben-in-darmstadt/umwelt/friedhoefe/veranstaltungen", # Waldfriedhof & Alter Friedhof Darmstadt
    "https://www.saarbruecken.de/leben_in_saarbruecken/planen_bauen_wohnen/friedhoefe/veranstaltungen", # Hauptfriedhof Saarbrücken

    # --- DEUTSCHLAND: Sachsen, Thüringen & Sachsen-Anhalt ---
    "https://www.erfurter-dom.de/",                                   # Erfurter Dom (Mariendom Krypta)
    "https://www.augustinerkloster.de/veranstaltungen/",             # Evangelisches Augustinerkloster Erfurt
    "https://www.dresden.de/de/leben/umwelt/stadtgruen/friedhoefe/veranstaltungen.php", # Städtische Friedhöfe Dresden
    "https://www.chemnitz.de/chemnitz/de/unsere-stadt/friedhoefe/veranstaltungen.html", # Städtische Friedhöfe Chemnitz
    "https://www.stiftskirche-quedlinburg.de/",                       # Stiftskirche Quedlinburg (Krypta & Domschatz)

    # --- DEUTSCHLAND: Norddeutschland ---
    "https://www.st-marien-luebeck.de/kalender",                      # St. Marien zu Lübeck (Totentanz-Kapelle)
    "https://www.braunschweig.de/leben/umwelt_naturschutz/stadtgruen/friedhoefe/veranstaltungen.php", # Hauptfriedhof Braunschweig
    "https://www.kiel.de/de/umwelt_verkehr/friedhoefe/veranstaltungen.php" # Städtische Friedhöfe Kiel


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


# ---------------------------------------------------------------- Datum

def normalize_date(date_str: str) -> str:
    date_str = str(date_str or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    match = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return date_str


def parse_date(date_str: str) -> str | None:
    normalized = normalize_date(date_str)
    try:
        return datetime.strptime(normalized, "%Y-%m-%d").date().isoformat()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------- Datenbank

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


def generate_event_id(event: dict) -> str:
    title = re.sub(r"\s+", " ", str(event.get("title") or "")).strip().lower()
    host = urlparse(event.get("url") or "").netloc
    raw = f"{title}|{event.get('date_start', '')}|{host}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- Auswahl

def is_worth_sending(url: str, text: str) -> bool:
    if len(text) < MIN_TEXT_LENGTH:
        print(f"  uebersprungen (nur {len(text)} Zeichen, evtl. JS-gerendert): {url}")
        return False
    if not DATE_PATTERN.search(text):
        print(f"  uebersprungen (kein Datumsmuster gefunden): {url}")
        return False
    return True


# ---------------------------------------------------------------- Abruf

def fetch_page_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=25.0, verify=False) as client_http:
        response = client_http.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup
    return main.get_text(separator=" ", strip=True)


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
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f8; color: #333; margin: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 10px; }}
        .container {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .timestamp {{ font-size: 0.85em; color: #7f8c8d; margin-bottom: 20px; }}

        .filter-container {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; align-items: center; background: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #e9ecef; }}
        .search-input {{ flex: 1; min-width: 250px; padding: 8px 12px; border: 1px solid #ced4da; border-radius: 4px; font-size: 0.95em; }}
        .filter-tags {{ display: flex; gap: 5px; flex-wrap: wrap; }}
        .tag-btn {{ background: #e9ecef; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; color: #495057; font-weight: 600; transition: all 0.2s; }}
        .tag-btn:hover {{ background: #dee2e6; }}
        .tag-btn.active {{ background: #3498db; color: white; }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background-color: #2c3e50; color: white; text-align: left; padding: 10px; font-size: 0.9em; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 0.95em; }}
        tr:hover {{ background-color: #f8f9fa; }}
        .date-badge {{ background-color: #3498db; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; white-space: nowrap; }}
        .date-end {{ display: block; margin-top: 4px; font-size: 0.8em; color: #7f8c8d; white-space: nowrap; }}
        .location {{ font-weight: bold; color: #34495e; }}
        .badge-new {{ background: #27ae60; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 6px; vertical-align: middle; }}
        .badge-stale {{ background: #f39c12; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 6px; vertical-align: middle; }}
        a.btn {{ display: inline-block; background-color: #27ae60; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; }}
        a.btn:hover {{ background-color: #219150; }}
        .no-results {{ display: none; padding: 20px; text-align: center; color: #7f8c8d; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Sepulkralkultur &amp; Friedhofskultur &ndash; Termine</h1>
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

    events_db = load_events_db()
    print(f"Bestand geladen: {len(events_db)} Events")

    # Phase 1: Webseiten laden und filtern
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

    # Phase 2: KI-Analyse
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

            event_id = generate_event_id(event)
            if event_id in events_db:
                event["first_seen"] = events_db[event_id].get("first_seen", today_str)
                stats["aktualisiert"] += 1
            else:
                event["first_seen"] = today_str
                stats["neu"] += 1
            event["last_seen"] = today_str
            events_db[event_id] = event

        time.sleep(4)

    # Phase 3: Bereinigung vergangener Events
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