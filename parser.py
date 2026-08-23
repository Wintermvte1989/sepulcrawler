import hashlib
import json
import os
import httpx
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Liste der zu überwachenden Webseiten
TARGET_URLS = [
    # --- Berlin: Friedhöfe & Friedhofsverbände ---
    "https://www.meinkiez-meinfriedhof.berlin.de/veranstaltungen",  # Sammelseite ev. Friedhöfe Berlin
    "https://www.kkbs.de/veranstaltungen/veranstaltungen-auf-friedhofen",  # Ev. Kirchenkreis Berlin Stadtmitte
    "https://www.suedwestkirchhof.de/veranstaltungen.html",  # Südwestkirchhof Stahnsdorf
    "https://berlin.volksbund.de/aktuell/termine",  # Führungen Historische-/Waldfriedhöfe Berlin

    # --- Berlin: Museen (Geschichte, Archäologie, Kultur) ---
    "https://www.smb.museum/veranstaltungen/",  # Staatliche Museen zu Berlin (u.a. Ägypt. Museum/Totenkult)
    "https://www.berlin.museum/programm",  # Stadtmuseum Berlin (Nikolaikirche, Biedermeier, Stadtgeschichte)
    "https://www.dhm.de/programm/veranstaltungskalender/",  # Deutsches Historisches Museum Berlin

    # --- Überregional / DACH ---
    "https://www.sepulkralmuseum.de/veranstaltungen/",  # Museum für Sepulkralkultur Kassel
    "https://www.friedhof-hamburg.de/besucher/veranstaltungen/",  # Parkfriedhof Ohlsdorf Hamburg
    "https://www.ohlsdorf-derpark.de/termine-ohlsdorf/"
]

DB_FILE = "seen_events.json"
HTML_OUTPUT_FILE = "neue_events.html"

class Event(BaseModel):
    title: str = Field(description="Titel der Veranstaltung")
    date_start: str = Field(description="Startdatum im Format YYYY-MM-DD")
    location: str = Field(description="Ort oder Institution der Veranstaltung")
    description: str = Field(description="Kurze Zusammenfassung in 1-2 Sätzen")
    url: str = Field(description="Direkter Link zur Veranstaltung oder Quell-URL")

class EventList(BaseModel):
    events: list[Event]

def load_seen_events() -> set:
    """Lädt bekannte Event-IDs aus der JSON-Datei."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_events(seen_ids: set):
    """Speichert bekannte Event-IDs in der JSON-Datei."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_ids), f, ensure_ascii=False, indent=2)

def generate_event_id(event: dict) -> str:
    """Erzeugt eine eindeutige ID aus Titel und Datum."""
    raw = f"{event['title']}_{event['date_start']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def save_events_to_html(new_events: list[dict]):
    """Speichert neu gefundene Events als gestaltete HTML-Tabelle."""
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
        f.write('</div>\n')

def fetch_page_text(url: str) -> str:
    """Holt die Webseite und bereinigt den HTML-Code."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=15.0)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup(["script", "style", "nav", "footer"]):
        script.decompose()
        
    return soup.get_text(separator=" ", strip=True)

def extract_events_with_gemini(raw_text: str, source_url: str) -> list[dict]:
    """Extrahierte Events über die Gemini API im JSON-Format."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    prompt = f"""
    Analysiere folgenden Text einer Webseite auf Veranstaltungen im Bereich Sepulkralkultur, 
    Friedhofsführungen, Bestattungswesen, Totenkult, Gedenkkultur, Grabkunst oder historische Ausstellungen zum Thema Tod/Sterben. 
    Extrahiere alle zukünftigen Events, die zu diesen Themen passen. Quell-URL: {source_url}
    
    Webseiten-Text:
    {raw_text[:15000]}
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
    seen_ids = load_seen_events()
    all_new_events = []
    
    for url in TARGET_URLS:
        print(f"\nLade Webseite: {url}...")
        try:
            page_text = fetch_page_text(url)
            print("Analysiere Daten mit Gemini API...")
            events = extract_events_with_gemini(page_text, url)
            
            site_new_events = 0
            for event in events:
                event_id = generate_event_id(event)
                if event_id not in seen_ids:
                    all_new_events.append(event)
                    seen_ids.add(event_id)
                    site_new_events += 1
            print(f"-> {site_new_events} neue(s) Event(s) auf dieser Seite gefunden.")
            
        except Exception as e:
            print(f"Fehler beim Verarbeiten von {url}: {e}")

    if all_new_events:
        save_seen_events(seen_ids)
        save_events_to_html(all_new_events)
        print(f"\nInsgesamt {len(all_new_events)} neue Events in '{HTML_OUTPUT_FILE}' gespeichert.")
    else:
        print("\nKeine neuen Events auf den überwachten Seiten gefunden.")