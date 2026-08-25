import hashlib
import html
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

    # Themenkriterium statt Ortskriterium - aber bewusst grosszuegig.
    # Eine zu strenge Fassung hat die Filmvorfuehrung "Der muede Tod"
    # verworfen, obwohl der Film genau zum Thema gehoert. Deshalb gilt jetzt:
    # im Zweifel ERFASSEN. Was inhaltlich daneben liegt, faengt zusaetzlich
    # database.is_topically_relevant deterministisch ab.
    prompt = f"""
    Das heutige Datum ist {today_str}.
    Analysiere die folgenden Webseiten-Texte auf Veranstaltungen mit Bezug zu
    Tod, Bestattung, Trauer, Totengedenken und Friedhofskultur.

    GRUNDREGEL: Der Ort allein macht eine Veranstaltung nicht relevant, aber
    er schliesst sie auch nicht aus. Entscheidend ist, ob das THEMA einen
    Bezug hat. Bei Zweifel: ERFASSEN. Ein zu viel erfasstes Event ist
    leichter zu verkraften als ein fehlendes.

    ERFASSEN - inhaltlicher Bezug:
    - Friedhoefe, Grabkunst, Grabmale, Mausoleen, Gruefte, Beinhaeuser,
      Katakomben, Krematorien, Kolumbarien
    - Bestattung, Begraebnis, Beisetzung, Feuerbestattung, Bestattungskultur
    - Trauer, Trauerbegleitung, Trauerreden, Hospiz- und Palliativarbeit,
      Sterbebegleitung, Letzte-Hilfe-Kurse
    - Totengedenken: Volkstrauertag, Ewigkeitssonntag, Totensonntag,
      Allerheiligen, Allerseelen, Gedenkfeiern fuer Verstorbene,
      Kranzniederlegungen, Requien, Gedenkgottesdienste
    - Kulturgeschichte des Todes: Totentanz, Vanitas, Memento mori,
      Vergaenglichkeit, Mumien, Gebeine, Reliquien, Anatomie
    - Grabfunde, Bestattungssitten und Totenkult in Archaeologie,
      Aegyptologie und Anthropologie
    - Erinnerungs- und Gedenkkultur an Opfer von Krieg, Verfolgung und
      Gewalt, Kriegsgraeberstaetten, Mahnmale

    ERFASSEN - auch als Konzert, Film, Lesung, Theater oder Vortrag, wenn
    das WERK oder THEMA um Tod, Trauer oder Vergaenglichkeit kreist.
    Beispiele: eine Vorfuehrung des Films "Der muede Tod", ein Requiem,
    ein Konzert "zum Trost in Trauer", eine Lesung ueber Sterbehilfe,
    ein Vortrag ueber Kannibalismus in der Menschheitsgeschichte,
    eine Theaterfuehrung ueber Wiedergaenger und Totenglauben.

    ERFASSEN - jede Veranstaltung, die AUF einem Friedhof, in einer
    Friedhofskapelle, einem Hospiz, einem Krematorium oder einem
    Bestattungsmuseum stattfindet. Dort ist der Ort das Thema.

    NICHT ERFASSEN - kein inhaltlicher Bezug, nur passender Ort:
    - Orgel- und Chorkonzerte, Vespern, Gottesdienste ohne Totenbezug
    - Kirchen-, Kloster- und Domfuehrungen zur Bau-, Kunst- oder
      Ordensgeschichte
    - allgemeine Museums- und Stadtfuehrungen, Jubilaeumstouren,
      Ausstellungsfuehrungen ohne Themenbezug
    - Archaeologie ohne Grab- oder Totenbezug (Siedlungen, Werkzeuge,
      Felsbilder, Handel)
    - Bastel- und Mitmachangebote fuer Kinder
    - Ausstellungen zu Stadtgeschichte, Architektur, Fotografie, Politik
    - Weinproben, Feste, Museumsnaechte, Wissenschaftsmaerkte, Kabarett
    - Sprachkurse, Yoga, Floh- und Weihnachtsmaerkte
    - reine Oeffnungszeiten, Eintrittspreise, Dauerangebote ohne Termin

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
            # Zweites Netz hinter fetcher.html_to_text: falls doch eine
            # Entity durchkommt, darf sie nicht in die Datenbank gelangen.
            for field in ("title", "location", "description"):
                if isinstance(ev.get(field), str):
                    ev[field] = html.unescape(ev[field]).strip()
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