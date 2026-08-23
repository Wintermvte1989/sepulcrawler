import hashlib
import html
import json
import os
import re
import time
import httpx
import urllib3
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URLS = [
    # Aktionstage & Gedenktage
    "https://www.tag-des-offenen-denkmals.de/",
    "https://denkmaltag.berlin.de/",
    "https://www.tag-des-friedhofs.de/",

    # Berlin: Friedhöfe, Verbände & Grüfte
    "https://www.meinkiez-meinfriedhof.berlin.de/veranstaltungen",
    "https://www.kkbs.de/veranstaltungen/veranstaltungen-auf-friedhofen",
    "https://berlin.volksbund.de/aktuell/termine",
    "https://stiftung-historische-friedhoefe.de/fuehrungen_und_veranstaltungen/",
    "https://stiftung-historische-friedhoefe.de/stiftung/veranstaltungen/",
    "https://www.efeu-ev.de/",
    "https://jewish-cemetery-weissensee.org/entdecken/fuehrungen/",
    "https://www.zwoelf-apostel-berlin.de/alle-termine-der-zwolf-apostel-kirchengemeinde-und-der-kirchhofe",
    "https://www.invalidenfriedhof-berlin.de/",
    "https://www.evfbs.de/",
    "https://forum1848.de/veranstaltungen/",
    "https://www.garnisonfriedhof-berlin.de/",
    "https://marienkirche-berlin.de/",
    "https://www.parochialkirche.de/",
    "https://www.hedwigs-kathedrale.de/",
    "https://www.berlinerdom.de/termine/",

    # Brandenburg: Friedhöfe, Klöster & Gedenkstätten
    "https://www.suedwestkirchhof.de/veranstaltungen.html",
    "https://www.bornstedter-friedhof.de/bornstedter-friedhof/historische-graeber/fuehrungen/termine-fuer-fuehrungen/",
    "https://www.potsdam.de/de/friedhoefe-potsdam",
    "https://www.denkmal-halbe.de/termine/",
    "https://www.goerlitz.de/",
    "https://www.stift-neuzelle.de/",

    # Berlin & Brandenburg: Bestattungskultur, Hospize & Private
    "https://www.ahorn-gruppe.de/",
    "https://www.sarggeschichten.de/",
    "https://www.ricam-hospiz.de/events/",
    "https://bjoern-schulz-stiftung.de/akademie/",

    # Berlin: Staatliche & Bezirksmuseen
    "https://www.smb.museum/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/aegyptisches-museum-und-papyrussammlung/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/museum-fuer-vor-und-fruehgeschichte/veranstaltungen/",
    "https://www.stadtmuseum.de/programm",
    "https://www.dhm.de/programm/veranstaltungskalender/",
    "https://www.humboldtforum.org/de/programm/",
    "https://www.jmberlin.de/",
    "https://tickets.jmberlin.de/events/",
    "https://www.berlin.de/museum-pankow/aktuelles/veranstaltungen/",
    "https://www.villa-oppenheim-berlin.de/",
    "https://www.zitadelle-berlin.de/en/education/events/",

    # Brandenburg: Stadtmuseen & Regionalgeschichte
    "https://www.potsdam-museum.de/de/veranstaltungen",
    "https://stadtmuseum.stadt-brandenburg.de/stadtmuseum/termine",
    "https://www.museum-eberswalde.de/angebote/kalender",
    "https://www.brandenburg-preussen-museum.de/besuch-planen/veranstaltungen.html",

    # Prag & Tschechien: Beinhäuser, Jüdischer Friedhof & Museen
    "https://www.sedlec.info/",
    "https://www.brnenske-podzemi.cz/",
    "https://www.jewishmuseum.cz/en/info/visit/",
    "https://www.praha-vysehrad.cz/en/culture-events/",
    "https://www.nm.cz/en/visit-us/events",

    # Beinhäuser, Grüfte & Sakralbauten (Deutschland & Österreich)
    "https://www.stadt-oppenheim.de/",
    "https://www.muenster-doberan.de/",
    "https://www.cham.de/",
    "https://www.frauenkirche-dresden.de/kalender/",
    "https://www.koelner-dom.de/termine/",
    "https://www.st-michaelis.de/veranstaltungen/",
    "https://www.kapuzinergruft.com/",
    "https://www.hallstatt.net/",
    "https://www.magdeburgerdom.de/",
    "https://www.naumburger-dom.de/",
    "https://www.michaelerkirche.at/",

    # Überregional Deutschland: Archäologische Landesmuseen & Fachmuseen
    "https://www.landesmuseum-vorgeschichte.de/ausstellungen/sonderausstellungen.html",
    "https://www.leiza.de/veranstaltungen/",
    "https://www.lwl-landesmuseum-herne.de/de/veranstaltungen/",
    "https://landesmuseum-bonn.lvr.de/de/ausstellungen/ausstellungen_1.html",
    "https://www.archaeologisches-museum-frankfurt.de/de/ausstellungen/sonderausstellungen",
    "https://www.landesmuseum-trier.de/",
    "https://www.alm-bw.de/",
    "https://schloss-gottorf.de/de/ausstellungen",
    "https://roemisch-germanisches-museum.de/",
    "https://www.antike-am-koenigsplatz.de/",

    # Überregional Deutschland: Friedhofskultur & Vereine
    "https://www.sepulkralmuseum.de/veranstaltungen/",
    "https://paul-benndorf-gesellschaft.de/fuehrungen.html",
    "https://eliasfriedhof.de/category/veranstaltungen/",
    "http://www.friedhofskultur-halle.de/terminefuehrungen/",
    "https://www.friedhof-hamburg.de/besucher/veranstaltungen/",
    "https://www.ohlsdorf-derpark.de/termine-ohlsdorf/",
    "https://www.stattreisen-muenchen.de/fuehrungen/der-alte-sudliche-friedhof",
    "https://www.florian-scheungraber.de/termine/",
    "https://theatergemeinde-koeln.org/Kulturkompass/werk/25725/M04/stadtfuhrungen-koln/fuhrung-uber-melaten",
    "https://www.friedhofsverwalter.de/fachveranstaltung-der-arbeitsgemeinschaft-friedhof-und-denkmal-e-v/",
    "https://aufdasleben.de/event/",

    # Schweiz & Österreich
    "https://www.stadt-zuerich.ch/friedhofforum/de/veranstaltungen.html",
    "https://www.bestattungsmuseum.at/besucherinfo/auf-einen-blick",
    "https://www.friedhoefewien.at/veranstaltungen"
]

DB_FILE = "events_db.json"
HTML_OUTPUT_FILE = "index.html"
BATCH_SIZE = 8

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class Event(BaseModel):
    title: str = Field(description="Titel der Veranstaltung")
    date_start: str = Field(description="Startdatum im Format YYYY-MM-DD")
    location: str = Field(description="Ort oder Institution der Veranstaltung")
    description: str = Field(description="Kurze Zusammenfassung in 1-2 Sätzen")
    url: str = Field(description="Direkter Link zur Veranstaltung oder Quell-URL")

class EventList(BaseModel):
    events: list[Event]

def normalize_date(date_str: str) -> str:
    date_str = str(date_str or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    match = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return date_str

def load_events_db() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_events_db(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def generate_event_id(event: dict) -> str:
    raw = f"{event.get('title', '')}_{event.get('date_start', '')}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def render_html(events: list[dict]):
    timestamp = datetime.now().strftime("%d.%m.%Y um %H:%M Uhr")
    sorted_events = sorted(events, key=lambda x: x.get("date_start", ""))

    html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sepulkralkultur Event-Feed</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f8; color: #333; margin: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .container {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .timestamp {{ font-size: 0.9em; color: #7f8c8d; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background-color: #2c3e50; color: white; text-align: left; padding: 10px; font-size: 0.9em; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 0.95em; }}
        tr:hover {{ background-color: #f8f9fa; }}
        .date-badge {{ background-color: #3498db; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; white-space: nowrap; }}
        .location {{ font-weight: bold; color: #34495e; }}
        a.btn {{ display: inline-block; background-color: #27ae60; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; }}
        a.btn:hover {{ background-color: #219150; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Sepulkralkultur & Friedhofskultur – Aktuelle Termine</h1>
        <div class="timestamp">Stand: {timestamp} | Aktive bevorstehende Events: {len(sorted_events)}</div>
"""

    if sorted_events:
        html_content += """
        <table>
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
            date_s = html.escape(event.get('date_start', ''))
            title_s = html.escape(event.get('title', ''))
            loc_s = html.escape(event.get('location', ''))
            desc_s = html.escape(event.get('description', ''))
            url_s = html.escape(event.get('url', '#'))

            html_content += f"""
                <tr>
                    <td><span class="date-badge">{date_s}</span></td>
                    <td><strong>{title_s}</strong></td>
                    <td class="location">{loc_s}</td>
                    <td>{desc_s}</td>
                    <td><a href="{url_s}" target="_blank" rel="noopener noreferrer" class="btn">Link öffnen</a></td>
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
</body>
</html>
"""

    with open(HTML_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

def fetch_page_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=15.0, verify=False)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup(["script", "style", "nav", "footer"]):
        script.decompose()
        
    return soup.get_text(separator=" ", strip=True)

def extract_events_batch(batch_sources: list[tuple[str, str]], today_str: str) -> list[dict]:
    combined_text = ""
    for url, text in batch_sources:
        combined_text += f"\n--- QUELL-URL: {url} ---\n{text[:6000]}\n"

prompt = f"""
    Das heutige Datum ist {today_str}.
    Analysiere die folgenden Webseiten-Texte auf Veranstaltungen im Bereich Sepulkralkultur, 
    Friedhofsführungen, Bestattungswesen, Totenkult, Gedenkkultur, Grabkunst oder historische Ausstellungen zum Thema Tod/Sterben. 
    
    WICHTIG:
    - Extrahiere AUSSCHLIESSLICH Veranstaltungen, deren Datum (date_start) am oder nach dem heutigen Datum ({today_str}) liegt.
    - Formatierung für date_start MUSS strikt YYYY-MM-DD sein.
    - Ignoriere alle vergangenen Veranstaltungen strikt.
    - Trage in das Feld 'url' jeweils die zugehörige QUELL-URL ein.
    - WICHTIG FÜR MEHRSPRACHIGE TEXTE: Falls der Quelltext auf Englisch, Tschechisch oder einer anderen Sprache verfasst ist, übersetze Titel (title), Ort (location) und Beschreibung (description) präzise ins Deutsche.
    
    Webseiten-Daten:
    {combined_text}
    """

    response = client.models.generate_content(
        model='gemini-3.6-flash',
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
        return result.get("events", [])
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen der API-Antwort: {e}")
        return []

if __name__ == "__main__":
    today_str = datetime.now().strftime("%Y-%m-%d")
    events_db = load_events_db()
    
    # Phase 1: Webseiten laden
    fetched_pages = []
    print("--- Phase 1: Webseiten laden ---")
    for url in TARGET_URLS:
        try:
            page_text = fetch_page_text(url)
            if page_text:
                fetched_pages.append((url, page_text))
                print(f"Erfolgreich geladen: {url}")
        except Exception as e:
            print(f"Fehler beim Laden von {url}: {e}")

    # Phase 2: KI-Analyse
    print(f"\n--- Phase 2: KI-Analyse in {BATCH_SIZE}er-Paketen ---")
    for i in range(0, len(fetched_pages), BATCH_SIZE):
        batch = fetched_pages[i:i + BATCH_SIZE]
        print(f"\nSende Paket {i//BATCH_SIZE + 1} ({len(batch)} Seiten) an Gemini API...")
        
        try:
            events = extract_events_batch(batch, today_str)
            for event in events:
                event["date_start"] = normalize_date(event.get("date_start", ""))
                if event["date_start"] >= today_str:
                    event_id = generate_event_id(event)
                    events_db[event_id] = event
        except Exception as e:
            print(f"Fehler bei API-Anfrage für Paket {i//BATCH_SIZE + 1}: {e}")
        
        time.sleep(4)

    # Phase 3: Bereinigung vergangener Events aus der Datenbank
    cleaned_db = {}
    for event_id, event in events_db.items():
        if event.get("date_start", "") >= today_str:
            cleaned_db[event_id] = event

    # Speichern & HTML neu bauen
    save_events_db(cleaned_db)
    render_html(list(cleaned_db.values()))
    
    print(f"\nVerarbeitung abgeschlossen. {len(cleaned_db)} aktive Zukunfts-Events in '{HTML_OUTPUT_FILE}' geschrieben.")