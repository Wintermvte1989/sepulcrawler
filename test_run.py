"""Testcrawler fuer neue Quellen.

Crawlt AUSSCHLIESSLICH config.CANDIDATE_URLS und schreibt in eigene Dateien:

    test_events_db.json     Termine der Kandidaten
    test_index.html         Vorschau zum Anschauen im Browser
    test_verworfen.json     was der Themenfilter aussortiert hat

Der echte Bestand (events_db.json) und die veroeffentlichte index.html
werden dabei NICHT angefasst. Erst wenn eine Kandidatenquelle brauchbare
Termine liefert, wandert ihre Adresse nach config.TARGET_URLS.

Aufruf:
    python test_run.py

Der Testbestand wird bei jedem Lauf neu aufgebaut, damit man das Ergebnis
einer Quelle unverfaelscht sieht und nicht Reste vom letzten Mal.
"""

import os
import sys

import config


def main() -> int:
    if not config.CANDIDATE_URLS:
        print("config.CANDIDATE_URLS ist leer - nichts zu testen.")
        print("Trage dort die Adressen ein, die du ausprobieren willst.")
        return 0

    # Ausgabeziele umbiegen, BEVOR main importiert wird. database.py und
    # renderer.py lesen die Pfade jeweils ueber config, deshalb genuegt es,
    # die Werte hier zu ersetzen.
    config.DB_FILE = config.TEST_DB_FILE
    config.HTML_OUTPUT_FILE = config.TEST_HTML_FILE
    config.REJECTED_FILE = config.TEST_REJECTED_FILE

    # Frisch anfangen: sonst mischen sich Ergebnisse mehrerer Testlaeufe und
    # man sieht nicht mehr, welche Quelle welchen Termin geliefert hat.
    if os.path.exists(config.TEST_DB_FILE):
        os.remove(config.TEST_DB_FILE)

    import main as crawler

    print("=" * 70)
    print(f"TESTCRAWLER - {len(config.CANDIDATE_URLS)} Kandidatenquelle(n)")
    print(f"  Datenbank: {config.TEST_DB_FILE}")
    print(f"  Vorschau:  {config.TEST_HTML_FILE}")
    print("  Der echte Bestand wird nicht veraendert.")
    print("=" * 70)
    for url in config.CANDIDATE_URLS:
        print(f"  - {url}")

    crawler.run(config.CANDIDATE_URLS)

    print("\n" + "=" * 70)
    print("Naechster Schritt: test_events_db.json bzw. test_index.html ansehen.")
    print("  Brauchbare Termine -> Adresse nach config.TARGET_URLS verschieben")
    print("  Nichts Brauchbares -> nach config.DISABLED_URLS, mit Begruendung")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
