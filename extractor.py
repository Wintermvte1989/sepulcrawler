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
    # Der Text ist bereits verdichtet und gekappt (fetcher.condense_text),
    # hier nicht erneut abschneiden.
    combined_text = ""
    for idx, (url, text) in enumerate(batch_sources, start=1):
        combined_text += (
            f"\n=== QUELLE {idx} ===\n{text}\n=== ENDE QUELLE {idx} ===\n"
        )

    # Themenkriterium, nicht Ortskriterium: "Kulturveranstaltung an einem
    # Museum oder einer Kirche" liess jedes Orgelkonzert und jede
    # Stadtfuehrung durch. Zusaetzlich prueft database.is_topically_relevant
    # das Ergebnis deterministisch nach.
    prompt = f"""
    Das heutige Datum ist {today_str}.
    Analysiere die folgenden Webseiten-Texte auf Veranstaltungen zur
    SEPULKRALKULTUR - also zu Tod, Bestattung, Trauer und Totengedenken.

    ENTSCHEIDENDE REGEL: Der Ort allein macht eine Veranstaltung NICHT
    relevant. Ein Konzert in einer Kirche, eine Stadtfuehrung an einem Museum
    oder ein Familiennachmittag im Landesmuseum gehoeren NICHT dazu, nur weil
    sie an einem historischen Ort stattfinden. Entscheidend ist das THEMA.

    ERFASSEN, wenn die Veranstaltung inhaltlich um mindestens eines dieser
    Themen kreist:
    - Friedhoefe, Grabkunst, Grabmale, Mausoleen, Gruefte, Beinhaeuser
    - Bestattung, Begraebnis, Beisetzung, Feuerbestattung, Krematorien
    - Trauer, Trauerbegleitung, Hospiz- und Palliativarbeit, Sterbebegleitung
    - Totengedenken: Volkstrauertag, Ewigkeitssonntag, Allerheiligen,
      Gedenkfeiern fuer Verstorbene, Kranzniederlegungen
    - Kulturgeschichte des Todes: Totentanz, Vanitas, Memento mori,
      Mumien, Gebeine, Vergaenglichkeit in Kunst und Literatur
    - Grabfunde und Bestattungssitten in Archaeologie und Aegyptologie
    - Veranstaltungen, die AUF einem Friedhof, in einer Friedhofskapelle,
      einem Hospiz oder Krematorium stattfinden - dort ist der Ort das Thema

    NICHT ERFASSEN, auch wenn der Ort passend klingt:
    - Orgelkonzerte, Chorkonzerte, Vespern, Gottesdienste ohne Totenbezug
    - Kirchen-, Kloster- und Domfuehrungen zur Bau- oder Ordensgeschichte
    - allgemeine Museums- und Stadtfuehrungen, Jubilaeumstouren
    - Archaeologie ohne Grabbezug (Siedlungen, Werkzeuge, Felsbilder)
    - Familiennachmittage, Bastel- und Mitmachangebote fuer Kinder
    - Theater, Kabarett, Lesungen, Filmreihen ohne Themenbezug
    - Ausstellungen zu Stadtgeschichte, Architektur, Politik, Fotografie
    - Weinproben, Feste, Museumsnaechte, Wissenschaftsmaerkte
    - Sprachkurse, Yoga, Floh- und Weihnachtsmaerkte
    - reine Oeffnungszeiten, Eintrittspreise, Dauerangebote ohne Termin

    Im Zweifel NICHT erfassen. Eine fehlende Veranstaltung ist besser als
    eine thematisch falsche.

    FORMAT:
    - Nur Veranstaltungen am oder nach dem heutigen Datum ({today_str}).
    - date_start strikt YYYY-MM-DD.
    - date_end nur bei mehrtaegigen Veranstaltungen, sonst null.
    - 'source_id': Nummer der QUELLE, in deren Block das Event stand.
    - Fremdsprachige Texte (Englisch, Tschechisch u. a.): title, location
      und description praezise ins Deutsche uebersetzen.

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