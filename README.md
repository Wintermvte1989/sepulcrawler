# Sepulkral-Kultur Event Crawler

Automatisierter Python-Crawler zur Erfassung von Veranstaltungen im Bereich Sepulkralkultur, Friedhofsführungen, Bestattungswesen, Totenkult und historische Ausstellungen. Das Skript lädt Zielseiten, filtert irrelevanten Content vor und nutzt die Gemini API zur strukturierten Extraktion von Terminen.

Die Ergebnisse werden atomar in einer Datenbank (`events_db.json`) gespeichert und als statische, durchsuchbare HTML-Seite (`index.html`) aufbereitet.

## Features

* **Semantische KI-Extraktion:** Nutzung von `gemini-3.6-flash` mit Pydantic Structured Outputs (`EventList`) zur präzisen Erkennung von Datumsangaben, Titeln, Orten und Beschreibungen – auch bei mehrsprachigen Quellen (z. B. Tschechisch, Englisch).
* **Ressourcenschonend:** Vorfilterung von JS-gerenderten Seiten (< 1.500 Zeichen) und Datumsmustern via Regex vor API-Aufrufen.
* **Batch-Verarbeitung:** Bündelung von bis zu 8 Webseiten pro API-Request zur Optimierung von Request-Limits und Token-Verbrauch.
* **Netzwerk-Optimierung:** Erzwingen von IPv4-Transport zur Vermeidung von `Errno 101`-Blockaden in Cloud-Umgebungen (z. B. GitHub Actions).
* **Atomare Datenverarbeitung:** Sicherer Schreibprozess der JSON-Datenbank via Temporärdateien gegen Datenverlust bei Abbrüchen.
* **Vollautomatisierter Ablauf:** Tägliche Ausführung via GitHub Actions inkl. automatischer Veröffentlichung und Bereinigung vergangener Events.

## Architektur & Ablauf

1. **Phase 1 (Fetch & Filter):** Lädt den Content aller definierten Ziel-URLs via `httpx` (mit IPv4-Zwang & Custom Header) und extrahiert den Haupttext via `BeautifulSoup`.
2. **Phase 2 (KI-Analyse):** Sendet valide Textblöcke gebündelt an die Gemini API.
3. **Phase 3 (DB-Sync & Cleanup):** Generiert eindeutige MD5-Hashes pro Event, aktualisiert `first_seen`/`last_seen`-Zeitstempel und entfernt abgelaufene Termine.
4. **Phase 4 (Rendering):** Erstellt die interaktive `index.html` inklusive Freitextsuche und Tag-Filtern (Berlin, Brandenburg, Prag, Grüfte/Beinhäuser).

## Tech-Stack

* **Sprache:** Python 3.11+
* **HTTP Client:** `httpx`
* **HTML Parser:** `BeautifulSoup4`
* **LLM Engine:** `google-genai` (`gemini-3.6-flash`)
* **Data Validation:** `pydantic`
* **Automation:** GitHub Actions

## Lokale Einrichtung

### Voraussetzungen

* Python 3.11 oder höher
* Google Gemini API Key (Pay-as-you-go im Google AI Studio aktiviert)

### Installation & Start

1. Repository klonen:
   ```bash
   git clone [https://github.com/Wintermvte1989/sepulkral-crawler.git](https://github.com/Wintermvte1989/sepulkral-crawler.git)
   cd sepulkral-crawler
