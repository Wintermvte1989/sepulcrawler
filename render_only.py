"""Erzeugt nur index.html neu - ohne Crawl und ohne API-Request.

Sinn: index.html ist ein Erzeugnis des Crawlers. Aenderungen an
renderer.py (Farben, Schrift, Kopfband, Beschriftungen) wirken deshalb
erst beim naechsten vollen Lauf, und der kostet rund 32 API-Requests.
Dieses Skript liest den vorhandenen Bestand und baut allein die Seite neu.

events_db.json wird dabei NICHT veraendert - nur gelesen.

Aufruf:
    python render_only.py

In GitHub Actions ueber den Workflow "Sepulcrawler Seite neu bauen".
"""

import sys
from datetime import datetime

import config
import database
import renderer


def main() -> int:
    db = database.load_events_db()
    if not db:
        print(f"'{config.DB_FILE}' ist leer oder fehlt - nichts zu rendern.")
        return 1

    today = datetime.now(config.BERLIN).date()
    events = list(db.values())

    renderer.render_html(events, today)
    print(f"{len(events)} Events aus '{config.DB_FILE}' gelesen.")
    print(f"'{config.HTML_OUTPUT_FILE}' neu erzeugt (Stand {today.isoformat()}).")
    print("events_db.json wurde nicht angefasst.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
