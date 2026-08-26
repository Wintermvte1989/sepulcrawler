import json
import time
from collections import Counter, defaultdict
from datetime import datetime
import config
import database
import extractor
import feeds
import fetcher
import renderer


def ingest(event, events_db, stats, rejected, today_str, origin):
    """Nimmt ein Event auf - egal ob aus einem ICS-Feed oder aus der
    KI-Extraktion. Datum, Themenfilter und Deduplizierung gelten fuer
    beide Wege gleich."""
    parsed_start = database.parse_date(event.get("date_start", ""))
    if parsed_start is None:
        print(f"  verworfen (Datum unlesbar '{event.get('date_start')}'): {event.get('title')}")
        stats["datum_ungueltig"] += 1
        return
    event["date_start"] = parsed_start
    event["date_end"] = database.parse_date(event.get("date_end") or "")

    relevant = event["date_end"] or event["date_start"]
    if relevant < today_str:
        stats["vergangen"] += 1
        return

    on_topic, reason = database.is_topically_relevant(event)
    if not on_topic:
        print(f"  verworfen (Thema): {str(event.get('title'))[:70]}")
        rejected.append({**event, "_grund": reason, "_herkunft": origin})
        stats["thema_verfehlt"] += 1
        return

    duplicate_key = database.find_duplicate_key(event, events_db)
    event["first_seen"] = today_str
    event["last_seen"] = today_str
    if duplicate_key:
        database.merge_into(events_db[duplicate_key], event)
        events_db[duplicate_key]["last_seen"] = today_str
        stats["aktualisiert"] += 1
    else:
        events_db[database.generate_event_id(event)] = event
        stats["neu"] += 1


if __name__ == "__main__":
    today = datetime.now(config.BERLIN).date()
    today_str = today.isoformat()

    rejected: list[dict] = []

    raw_db = database.load_events_db()
    print(f"Bestand geladen: {len(raw_db)} Roh-Events")

    events_db = database.deduplicate_db(raw_db)
    print(f"Nach Initial-Deduplizierung: {len(events_db)} eindeutige Events")

    print(f"\n--- Phase 1: Webseiten laden ({len(config.TARGET_URLS)} Quellen) ---")
    if config.DISABLED_URLS:
        print(f"    ({len(config.DISABLED_URLS)} Quellen sind deaktiviert, siehe DISABLED_URLS)")

    fetched_pages = []
    problems: dict[str, list[str]] = defaultdict(list)

    feed_events: list[dict] = []

    with fetcher.make_http_client() as client_http:
        for url in config.TARGET_URLS:
            try:
                raw_html = fetcher.fetch_page_html(client_http, url)
            except Exception as e:
                kind = fetcher.classify_error(e)
                problems[kind].append(url)
                print(f"  FEHLER  {kind:<24} {url}")
                continue

            # Bietet die Quelle einen ICS-Feed an, ist er dem HTML-Text
            # immer vorzuziehen: strukturierte Felder statt Fliesstext,
            # und die Quelle kostet keinen API-Request.
            found, feed_url = feeds.fetch_feed_events(client_http, raw_html, url)
            if found:
                print(f"  FEED    {len(found):>3} Termine  {feed_url}")
                feed_events.extend(found)
                continue

            page_text = fetcher.html_to_text(raw_html)

            if not fetcher.is_worth_sending(url, page_text):
                reason = ("zu kurz" if len(page_text) < config.MIN_TEXT_LENGTH
                          else "kein Datum")
                problems[reason].append(url)
                continue

            condensed, hits = fetcher.condense_text(page_text, config.TEXT_LIMIT)
            if len(condensed) < len(page_text):
                print(f"  {len(page_text):>7} -> {len(condensed):>5} Zeichen, "
                      f"~{hits} Fundstellen  {url}")
            else:
                print(f"  {len(page_text):>7} Zeichen, ~{hits} Fundstellen  {url}")
            fetched_pages.append((url, condensed, hits))

    selected, deferred = extractor.select_within_budget(
        fetched_pages, today.toordinal(), config.MAX_REQUESTS_PER_RUN
    )
    batches = extractor.pack_batches(selected)

    if deferred:
        print(f"\n  {len(deferred)} Quellen passen nicht ins Request-Budget "
              f"({config.MAX_REQUESTS_PER_RUN}) und kommen in einem spaeteren Lauf dran:")
        for url, _, _ in deferred:
            problems["auf spaeteren Lauf verschoben"].append(url)
            print(f"    {url}")

    print(f"\n{len(selected)} von {len(fetched_pages)} Seiten gehen an die API "
          f"in {len(batches)} Paketen (Budget: {config.MAX_REQUESTS_PER_RUN})")

    stats = Counter()

    if feed_events:
        print(f"\n--- Phase 1b: {len(feed_events)} Termine aus ICS-Feeds "
              f"(ohne API-Request) ---")
        for event in feed_events:
            ingest(event, events_db, stats, rejected, today_str, "feed")
        print(f"  neu {stats['neu']}, aktualisiert {stats['aktualisiert']}, "
              f"Thema verfehlt {stats['thema_verfehlt']}")

    print("\n--- Phase 2: KI-Analyse ---")
    for number, batch in enumerate(batches, start=1):
        print(f"\nPaket {number}/{len(batches)} ({len(batch)} Seiten, "
              f"{sum(len(t) for _, t in batch)} Zeichen)")
        # URLs mitschreiben: ohne sie laesst sich nicht klaeren, warum ein
        # Paket null Events liefert - korrekt gefiltert oder Quelle verpufft.
        for batch_url, batch_text in batch:
            print(f"      {len(batch_text):>6} Z.  {batch_url}")

        events = extractor.call_with_retry(batch, today_str)
        print(f"  {len(events)} Events extrahiert")

        for event in events:
            ingest(event, events_db, stats, rejected, today_str, "api")

        if number < len(batches):
            time.sleep(config.API_PAUSE_SECONDS)

    before_dedup = len(events_db)
    events_db = database.deduplicate_db(events_db)
    stats["zusammengefuehrt"] = before_dedup - len(events_db)

    cleaned_db = {}
    for event_id, event in events_db.items():
        relevant = event.get("date_end") or event.get("date_start", "")
        if relevant >= today_str:
            cleaned_db[event_id] = event
    stats["entfernt"] = len(events_db) - len(cleaned_db)

    database.save_events_db(cleaned_db)
    renderer.render_html(list(cleaned_db.values()), today)

    # Verworfene Events mit vollem Kontext ablegen. Im Actions-Log steht nur
    # der Titel; zum Justieren von TOPIC_PATTERN braucht man Ort und
    # Beschreibung. Die Datei wird als Artefakt hochgeladen, nicht committet.
    with open(config.REJECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(rejected, f, ensure_ascii=False, indent=2)
    print(f"\n{len(rejected)} verworfene Events in "
          f"'{config.REJECTED_FILE}' protokolliert.")

    print("\n--- Zusammenfassung ---")
    print(f"  neu:            {stats['neu']}")
    print(f"  aktualisiert:   {stats['aktualisiert']}")
    print(f"  Datum ungueltig:{stats['datum_ungueltig']}")
    print(f"  vergangen:      {stats['vergangen']}")
    print(f"  Thema verfehlt: {stats['thema_verfehlt']}")
    print(f"  zusammengefuehrt:{stats['zusammengefuehrt']}")
    print(f"  DB bereinigt:   {stats['entfernt']} entfernt")
    print(f"\n{len(cleaned_db)} aktive Events in '{config.HTML_OUTPUT_FILE}' geschrieben.")

    if problems:
        print("\n--- Quellen ohne Ertrag ---")
        for kind in sorted(problems):
            urls = problems[kind]
            print(f"\n  {kind} ({len(urls)}):")
            for url in urls:
                print(f"    {url}")
        total = sum(len(v) for v in problems.values())
        print(f"\n  {total} von {len(config.TARGET_URLS)} Quellen haben nichts geliefert.")