SEPULKRAL EVENT CRAWLER - README

BESCHREIBUNG
----------------------------------------------------------------------
Automatisierter Web-Crawler und KI-gestützter Extraktor für
Veranstaltungen im Bereich Sepulkralkultur, Friedhofsführungen,
Bestattungswesen, Gedenkkultur und Grabkunst in Deutschland,
Österreich, der Schweiz und Tschechien.

Das System liest vordefinierte Webseiten aus, verdichtet die Inhalte,
analysiert diese mittels der Gemini API (Gemini 3.6 Flash), führt
quellübergreifende Deduplizierungen durch und generiert eine statische,
responsive Webansicht (index.html) inklusive Dunkelmodus und
Filterfunktionen.


FUNKTIONSUMFANG
----------------------------------------------------------------------
- Web Scraper: Toleranter HTTP-Client (TLS-Fallbacks, Custom User-Agents)
  zur Extraktion relevanter Textabschnitte.
- Text-Kondensierung: Intelligentes Parsing von Datumsmustern zur
  Reduzierung des Token-Verbrauchs vor der Übertragung an die API.
- KI-Extraktion: Strukturierte Event-Erkennung über die Gemini API
  (gemini-3.6-flash) mit automatischer Übersetzung fremdsprachiger
  Quellen ins Deutsche.
- Deduplizierung & Datenbank: Fuzzy-Matching-Logik (Levenshtein-Distanz
  & Jaccard-Ähnlichkeit) zur quellübergreifenden Zusammenführung
  doppelter Termine in events_db.json.
- Frontend-Generierung: Ausgabe einer eigenständigen HTML-Datei mit
  serverseitig generierten Tag-Filtern (Region, Veranstaltungsart,
  Zeitraum) und responsivem Karten-Layout für Mobilgeräte.
- CI/CD Pipeline: Vollautomatische Ausführung per GitHub Actions
  via Cron-Schedule.


ARCHITEKTUR & MODULSTRUKTUR
----------------------------------------------------------------------
sepulkral-crawler/
├── config.py         # Ziel-URLs, Deaktivierte URLs, Schwellenwerte
├── models.py         # Pydantic-Datenmodelle & Custom Exceptions
├── fetcher.py        # HTTP-Client, SSL-Kontext, HTML-Parsing
├── database.py       # JSON-DB, Hashing & Fuzzy-Deduplizierung
├── extractor.py      # Gemini API-Anbindung & Batch-Optimierung
├── renderer.py       # HTML/CSS/JS-Generierung (Responsive, Dark Mode)
├── main.py           # Haupt-Orchestrator für den Crawler-Ablauf
├── requirements.txt  # Python-Abhängigkeiten
└── .github/
    └── workflows/
        └── crawler.yml # GitHub Actions Workflow


VORAUSSETZUNGEN & INSTALLATION
----------------------------------------------------------------------
Voraussetzungen:
- Python 3.12+
- Gemini API Key von Google AI Studio

Lokale Einrichtung:
1. Repository klonen:
   git clone https://github.com/DEIN-USERNAME/sepulkral-crawler.git
   cd sepulkral-crawler

2. Abhängigkeiten installieren:
   pip install -r requirements.txt

3. API-Schlüssel setzen:
   - Linux/macOS:          export GEMINI_API_KEY="dein-api-key"
   - Windows (PowerShell): $env:GEMINI_API_KEY="dein-api-key"

4. Crawler ausführen:
   python main.py


AUTOMATISIERUNG (GITHUB ACTIONS)
----------------------------------------------------------------------
Der Crawler wird automatisch über die Pipeline .github/workflows/crawler.yml
ausgeführt (montags und freitags per Cron-Job oder manuell via
workflow_dispatch).

Für die Ausführung im Repository muss das GitHub Secret GEMINI_API_KEY
unter Settings > Secrets and variables > Actions hinterlegt sein.
