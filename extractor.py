import hashlib
import json
import os
import re
import time
from google import genai
from google.genai import types
import config
from models import EventList, TruncatedResponseError

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def pack_batches(pages: list[tuple[str, str, int]]) -> list[list[tuple[str, str]]]:
    ordered = sorted(pages, key=lambda page: page[2], reverse=True)
    batches: list[list[tuple[str, str, int]]] = []

    for page in ordered:
        for batch in batches:
            crowded = len(batch) >= config.BATCH_SIZE
            too_many = sum(p[2] for p in batch) + page[2] > config.MAX_EVENTS_PER_BATCH
            if not crowded and not too_many:
                batch.append(page)
                break
        else:
            batches.append([page])

    return [[(url, text) for url, text, _ in batch] for batch in batches]


def rotation_key(url: str, period: int) -> int:
    return int(hashlib.md5(f"{url}|{period}".encode("utf-8")).hexdigest(), 16)


def select_within_budget(
    pages: list[tuple[str, str, int]], period: int, max_requests: int
) -> tuple[list[tuple[str, str, int]], list[tuple[str, str, int]]]:
    if not pages or len(pack_batches(pages)) <= max_requests:
        return pages, []

    kept: list[tuple[str, str, int]] = []
    for page in sorted(pages, key=lambda pg: rotation_key(pg[0], period)):
        if len(pack_batches(kept + [page])) <= max_requests:
            kept.append(page)

    kept_urls = {url for url, _, _ in kept}
    skipped = [pg for pg in pages if pg[0] not in kept_urls]
    return kept, skipped


def extract_events_batch(batch_sources: list[tuple[str, str]], today_str: str) -> list[dict]:
    combined_text = ""
    for idx, (url, text) in enumerate(batch_sources, start=1):
        combined_text += (
            f"\n=== QUELLE {idx} ===\n{text}\n=== ENDE QUELLE {idx} ===\n"
        )

    # Prompt gelockert: Erfasst auch Kultur-, Kunst- und Filmveranstaltungen an Friedhöfen, Museen und Kirchen
    prompt = f"""
    Das heutige Datum ist {today_str}.
    Analysiere die folgenden Webseiten-Texte auf Veranstaltungen. 

    Ziel-Veranstaltungen:
    - Friedhofsführungen, Sepulkralkultur, Grabkunst, Bestattungswesen, Gedenkkultur
    - Ausstellungen zu Tod, Sterben, Archäologie, Antike, Geschichte
    - Kulturveranstaltungen (Konzerte, Lesungen, Filmreihen/Kino, Vorträge, Führungen) an Museen, Kirchen, Gedenkstätten oder Friedhöfen

    WICHTIG:
    - Extrahiere AUSSCHLIESSLICH Veranstaltungen, deren Datum am oder nach dem heutigen Datum ({today_str}) liegt.
    - date_start MUSS strikt YYYY-MM-DD sein.
    - date_end nur bei mehrtägigen Veranstaltungen (Ausstellungen, Aktionstage) setzen, sonst null.
    - Ignoriere vergangene Veranstaltungen strikt.
    - Trage in 'source_id' die Nummer der QUELLE ein, in deren Block das Event stand.
    - MEHRSPRACHIGE TEXTE: Falls der Quelltext auf Englisch, Tschechisch oder einer anderen Sprach verfasst ist, übersetze title, location und description präzise ins Deutsche.

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
    for attempt in range(config.API_ATTEMPTS):
        try:
            return extract_events_batch(batch_sources, today_str)
        except TruncatedResponseError:
            print("  Antwort abgeschnitten - kein Retry, BATCH_SIZE pruefen")
            return []
        except Exception as e:
            wait = 5 * (2 ** attempt)
            print(f"  Versuch {attempt + 1}/{config.API_ATTEMPTS} fehlgeschlagen ({e}), warte {wait}s")
            if attempt < config.API_ATTEMPTS - 1:
                time.sleep(wait)
    print("  endgueltig aufgegeben")
    return []