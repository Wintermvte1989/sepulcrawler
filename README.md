SEPULCRAWLER - README

BESCHREIBUNG
----------------------------------------------------------------------
Automatisierter Web-Crawler und KI-gestützter Extraktor für
Veranstaltungen im Bereich Sepulkralkultur, Friedhofsführungen,
Bestattungswesen, Gedenkkultur und Grabkunst in Deutschland,
Österreich, der Schweiz und Tschechien.

Das System liest rund 160 vordefinierte Webseiten aus, wertet vorhandene
ICS-Kalenderfeeds direkt aus, verdichtet die übrigen Inhalte auf die
terminrelevanten Textstellen, analysiert diese mittels der Gemini API,
filtert thematisch Fremdes heraus, führt quellübergreifende
Deduplizierungen durch und erzeugt eine statische, responsive Webansicht
(index.html) mit Dunkelmodus und Filtern nach Zeitraum, Region und
Veranstaltungsart.


FUNKTIONSUMFANG
----------------------------------------------------------------------
- ICS-Feed-Erkennung: Bietet eine Quelle einen Kalenderfeed an, wird er
  dem HTML vorgezogen - strukturierte Felder statt Fließtext, und ohne
  API-Request. Die Feed-Adresse wird im HTML der Seite gesucht, nicht
  geraten. Einzeltermin-Exporte werden erkannt und ignoriert.
- Web Scraper: Toleranter HTTP-Client (eigener TLS-Kontext für Server
  mit alten Cipher-Suites, browserähnliche Header, Wiederholungen bei
  Zeitüberschreitung) mit Auswertung eingebetteter JSON-LD-Daten.
- Text-Verdichtung: Statt die ersten n Zeichen zu nehmen, werden
  Textfenster um jede erkannte Datumsangabe gelegt und verschmolzen.
  Bei großen Kalendern besteht der Seitenanfang aus Navigation; die
  Termine stehen weiter unten.
- KI-Extraktion: Strukturierte Event-Erkennung über die Gemini API mit
  automatischer Übersetzung fremdsprachiger Quellen ins Deutsche. Die
  Zuordnung Event -> Quelle erfolgt über eine Nummer, die das Modell
  zurückgibt; die URL setzt der Code selbst.
- Themenfilter: Deterministische Nachprüfung in Python. Ein Ortskriterium
  allein ("Veranstaltung an einer Kirche") ließe jedes Orgelkonzert durch.
  Geprüft werden Themenwörter in Titel, Beschreibung und Ort sowie die
  Art der Quelle.
- Deduplizierung: Vergleich von Datum, Quell-Domain, Ort,
  Veranstaltungsart, Zeichenähnlichkeit des Titels
  (difflib.SequenceMatcher, Ratcliff/Obershelp) und Jaccard-Ähnlichkeit
  der endungsreduzierten Inhaltswörter. Quellübergreifend wird nur
  zusammengeführt, wenn beide Einträge eine überlappende Ortsangabe
  haben. Bewusst konservativ: ein übersehenes Duplikat ist sichtbar und
  harmlos, eine falsche Zusammenführung löscht ein echtes Event.
- Budgetsteuerung: Seiten werden nach geschätzter Ergiebigkeit zu
  Paketen gebündelt, damit die Antwortlänge der API nicht überschritten
  wird. Reicht das Request-Budget nicht, rotiert die Auswahl über die
  Läufe.
- Frontend: Eigenständige HTML-Datei mit serverseitig vergebenen Tags
  (Region, Veranstaltungsart, Zeitraum) und Kartenlayout für Mobilgeräte.
- CI/CD: Ausführung per GitHub Actions, montags und freitags.


ARCHITEKTUR & MODULSTRUKTUR
----------------------------------------------------------------------
sepulcrawler/
├── config.py         # Quellen, Filter, Schwellenwerte - alles Einstellbare
├── models.py         # Pydantic-Datenmodelle & eigene Exceptions
├── fetcher.py        # HTTP-Client, TLS-Kontext, HTML-Parsing, Verdichtung
├── feeds.py          # ICS-Feed-Erkennung und -Auswertung
├── database.py       # JSON-DB, Themenfilter, Hashing, Deduplizierung
├── extractor.py      # Gemini-API, Prompt, Paketbildung
├── renderer.py       # HTML/CSS/JS-Ausgabe (responsiv, Dunkelmodus)
├── main.py           # Orchestrator, run() für beide Einstiegspunkte
├── test_run.py       # Testcrawler für neue Quellen
├── requirements.txt
└── .github/workflows/
    ├── crawler.yml       # Hauptlauf (Cron + manuell)
    └── crawler-test.yml  # Testcrawler (nur manuell, ohne Schreibrechte)


VORAUSSETZUNGEN & INSTALLATION
----------------------------------------------------------------------
Voraussetzungen:
- Python 3.12+
- Gemini API Key von Google AI Studio

Lokale Einrichtung:
1. Repository klonen:
   git clone https://github.com/Wintermvte1989/sepulcrawler.git
   cd sepulcrawler

2. Abhängigkeiten installieren:
   pip install -r requirements.txt

3. API-Schlüssel setzen:
   - Linux/macOS:          export GEMINI_API_KEY="dein-api-key"
   - Windows (PowerShell): $env:GEMINI_API_KEY="dein-api-key"

4. Crawler ausführen:
   python main.py


NEUE QUELLEN AUFNEHMEN
----------------------------------------------------------------------
Ein voller Lauf kostet rund 30 API-Requests. Zum Prüfen einer neuen
Adresse gibt es deshalb einen eigenen Weg, der ein bis zwei kostet:

1. Adresse in config.py unter CANDIDATE_URLS eintragen (nicht in
   TARGET_URLS).
2. python test_run.py
   Der Testcrawler liest ausschließlich die Kandidaten und schreibt in
   test_events_db.json, test_index.html und test_verworfen.json. Der
   echte Bestand bleibt unberührt.
3. Ergebnis ansehen. Brauchbare Termine -> Adresse nach TARGET_URLS
   verschieben. Nichts Brauchbares -> nach DISABLED_URLS, mit Begründung
   und Datum.

Alternativ über GitHub Actions: Workflow "Sepulkral Crawler TEST"
manuell starten, Ergebnis als Artefakt herunterladen.

Was sich bewährt hat: Termine werden meist nicht von Stadtverwaltungen
gepflegt, sondern von Fördervereinen und Friedhofsverwaltungen mit
eigener Domain. Wo eine Stadtportal-Adresse einen 404 liefert, lohnt die
Suche nach einer eigenen Domain (Beispiel: karlsruhe.de/... gab 404,
friedhof-karlsruhe.de liefert seither zuverlässig).


TESTMODUS ÜBER UMGEBUNGSVARIABLEN
----------------------------------------------------------------------
SEPULKRAL_TEST_URLS   Kommaliste von Suchbegriffen; es werden nur
                      passende Quellen gecrawlt.
SEPULKRAL_DRY_RUN     "1" = kein API-Request. Phase 1 läuft vollständig,
                      Phase 2 zeigt nur, was gesendet würde. Kostet
                      nichts.
SEPULKRAL_DB_FILE     Andere Datenbankdatei für Versuche.

Beispiel (PowerShell):
   $env:SEPULKRAL_DRY_RUN = "1"; python main.py
   Remove-Item Env:SEPULKRAL_DRY_RUN

Die Variablen heißen weiterhin SEPULKRAL_*, nicht SEPULCRAWLER_*.


AUTOMATISIERUNG (GITHUB ACTIONS)
----------------------------------------------------------------------
Der Hauptlauf läuft über .github/workflows/crawler.yml montags und
freitags um 08:23 UTC oder manuell via workflow_dispatch. Er committet
events_db.json und index.html zurück ins Repository - aber nur, wenn
sich die Datenbank inhaltlich geändert hat und eine
Plausibilitätsprüfung bestanden wurde (kein Einbruch des Bestands um
mehr als die Hälfte).

Der Testcrawler (crawler-test.yml) läuft nur manuell, hat ausdrücklich
keine Schreibrechte und liefert seine Ergebnisse als Artefakt.

Für beide muss das GitHub Secret GEMINI_API_KEY unter
Settings > Secrets and variables > Actions hinterlegt sein.


HINWEISE ZUM BETRIEB
----------------------------------------------------------------------
- Nicht jede Quelle liefert bei jedem Lauf. "Zu kurz" im Log bedeutet
  oft nur, dass gerade keine Termine anstehen - nicht, dass die Quelle
  kaputt ist. Die Volksbund-Landesverbände zeigen dann eine Seite mit
  "Keine Termine gefunden".
- Der Abschnitt "Quellen ohne Ertrag" am Ende des Logs ist das
  wichtigste Werkzeug zur Pflege der Quellenliste.
- Verworfene Events werden mit vollem Kontext in verworfen.json
  protokolliert und als Artefakt hochgeladen. Wenn dort etwas steht, das
  in den Feed gehört, fehlt ein Wort in TOPIC_PATTERN.
- Auf Windows wird zusätzlich das Paket tzdata benötigt; Linux bringt
  die Zeitzonendaten mit.
