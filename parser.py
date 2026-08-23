import hashlib
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

# Deaktiviert SSL-Warnungen für ältere Vereins-Webseiten
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URLS = [
    # Berlin: Friedhöfe & Verbände
    "https://www.meinkiez-meinfriedhof.berlin.de/veranstaltungen",
    "https://www.kkbs.de/veranstaltungen/veranstaltungen-auf-friedhofen",
    "https://www.suedwestkirchhof.de/veranstaltungen.html",
    "https://berlin.volksbund.de/aktuell/termine",
    "https://www.stiftung-historische-friedhoefe.de/",
    "https://www.efeuev.de/",
    "https://www.zwoelf-apostel-berlin.de/friedhoefe",
    "https://www.invalidenfriedhof-berlin.de/",
    "https://www.evfbs.de/",
    "https://www.friedhof-der-maerzgefallenen.de/",
    "https://www.garnisonfriedhof-berlin.de/",

    # Berlin: Bestattungskultur & Private
    "https://www.ahorn-gruppe.de/",
    "https://www.sarggeschichten.de/",

    # Berlin: Museen & Archäologie
    "https://www.smb.museum/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/aegyptisches-museum-und-papyrussammlung/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/museum-fuer-vor-und-fruehgeschichte/veranstaltungen/",
    "https://www.stadtmuseum.de/programm",
    "https://www.dhm.de/programm/veranstaltungskalender/",
    "https://www.humboldtforum.org/de/programm/",
    "https://www.jmberlin.de/programm",

    # Überregional / DACH
    "https://www.sepulkralmuseum.de/veranstaltungen/",
    "https://www.friedhof-hamburg.de/besucher/veranstaltungen/",
    "https://www.ohlsdorf-derpark.de/termine-ohlsdorf/",
    "https://www.bestattungsmuseum.at/",
    "https://www.friedhoefewien.at/veranstaltungen"
]

DB_FILE = "seen_events.json"
HTML_OUTPUT_FILE = "index.html"
BATCH_SIZE = 5  # Bündelt 5 Webseiten pro Gemini-API-Anfrage

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
    date_str = date_str.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    match = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return date_str

def load_seen_events() -> set:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_events(seen_ids: set):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_ids), f, ensure_ascii=False, indent=2)

def generate_event_id(event: dict) -> str:
    raw = f"{event['title']}_{event['date_start']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def save_events_to_html(new_events: list[dict]):
    timestamp = datetime.now().strftime("%d.%m.%Y um %H:%M Uhr")
    file_exists = os.path.exists(HTML_OUTPUT_FILE)
    
    with open(HTML_OUTPUT_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Sepulkralkultur Event-Feed</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f8; color: #333; margin: 20px; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .run-block { background: white; border-radius: 8px; padding: 20px; margin-bottom: 25px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .timestamp { font-size: 0.9em; color: #7f8c8d; font-weight: bold; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { background-color: #2c3e50; color: white; text-align: left; padding: 10px; font-size: 0.9em; }
        td { padding: 12px 10px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 0.95em; }
        tr:hover { background-color: #f8f9fa; }
        .date-badge { background-color: #3498db; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; whitespace: nowrap; }
        .location { font-weight: bold; color: #34495e; }
        a.btn { display: inline-block; background-color: #27ae60; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; }
        a.btn:hover { background-color: #219150; }
    </style>
</head>
<body>
    <h1>Sepulkralkultur & Friedhofskultur - Event-Feed</h1>
""")

        f.write(f'<div class="run-block">\n')
        f.write(f'  <div class="timestamp">Suchlauf vom {timestamp} ({len(new_events)} neue Funde)</div>\n')
        
        if new_events:
            f.write('  <table>\n')
            f.write('    <thead><tr><th>Datum</th><th>Titel</th><th>Ort</th><th>Beschreibung</th><th>Aktion</th></tr></thead>\n')
            f.write('    <tbody>\n')
            
            for event in new_events:
                f.write('      <tr>\n')
                f.write(f'        <td><span class="date-badge">{event["date_start"]}</span></td>\n')
                f.write(f'        <td><strong>{event["title"]}</strong></td>\n')
                f.write(f'        <td class="location">{event["location"]}</td>\n')
                f.write(f'        <td>{event["description"]}</td>\n')
                f.write(f'        <td><a href="{event["url"]}" target="_blank" class="btn">Link öffnen</a></td>\n')
                f.write('      </tr>\n')
                
            f.write('    </tbody>\n')
            f.write('  </table>\n')
        else:
            f.write('  <p>Keine neuen Termine bei diesem Durchlauf gefunden.</p>\n')
            
        f.write('</div>\n')

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
    
    result = json.loads(response.text)
    return result.get("events", [])

if __name__ == "__main__":
    today_str = datetime.now().strftime("%Y-%m-%d")
    seen_ids = load_seen_events()
    all_new_events = []
    
    # 1. Alle Webseiten lokal abrufen
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

    # 2. In 5er-Paketen an Gemini senden
    print(f"\n--- Phase 2: KI-Analyse in {BATCH_SIZE}er-Paketen ---")
    for i in range(0, len(fetched_pages), BATCH_SIZE):
        batch = fetched_pages[i:i + BATCH_SIZE]
        print(f"\nSende Paket {i//BATCH_SIZE + 1} ({len(batch)} Seiten) an Gemini API...")
        
        try:
            events = extract_events_batch(batch, today_str)
            batch_new = 0
            for event in events:
                event["date_start"] = normalize_date(event.get("date_start", ""))
                if event["date_start"] < today_str:
                    continue
                
                event_id = generate_event_id(event)
                if event_id not in seen_ids:
                    all_new_events.append(event)
                    seen_ids.add(event_id)
                    batch_new += 1
            print(f"-> {batch_new} neue(s) Event(s) in diesem Paket gefunden.")
        except Exception as e:
            print(f"Fehler bei API-Anfrage für Paket {i//BATCH_SIZE + 1}: {e}")
        
        time.sleep(4)

    save_seen_events(seen_ids)
    save_events_to_html(all_new_events)
    print(f"\nInsgesamt {len(all_new_events)} neue Events in '{HTML_OUTPUT_FILE}' geschrieben.")