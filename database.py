import difflib
import html as html_mod
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import date
from urllib.parse import urlparse
import config


def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    s = str(date_str).strip().lower()

    match_iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if match_iso:
        y, m, d = map(int, match_iso.groups())
        try:
            return date(y, m, d).isoformat()
        except ValueError:
            pass

    match_num = re.search(r"\b(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})\b", s)
    if match_num:
        d, m, y = map(int, match_num.groups())
        if y < 100:
            y += 2000
        try:
            return date(y, m, d).isoformat()
        except ValueError:
            pass

    match_text = re.search(r"\b(\d{1,2})\.?\s+([a-zäöü]+)\.?\s+(\d{2,4})\b", s)
    if match_text:
        d_str, month_str, y_str = match_text.groups()
        d = int(d_str)
        y = int(y_str)
        if y < 100:
            y += 2000
        month_num = config.MONTH_MAP.get(month_str)
        if month_num:
            try:
                return date(y, month_num, d).isoformat()
            except ValueError:
                pass

    return None


def clean_text_for_comparison(text: str) -> str:
    if not text:
        return ""
    # Entities zuerst aufloesen, sonst gelten "Gr&auml;ber" und "Gräber"
    # als verschiedene Titel und werden nicht zusammengefuehrt.
    s = html_mod.unescape(str(text)).lower()
    s = re.sub(r"[–—:,\"`«»„“'()\[\]\-\n\r/|]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Haeufige deutsche Flexionsendungen. Nur fuer den Vergleich, nie fuer die
# Anzeige: "Sonntagsfuehrung" und "Sonntagsfuehrungen" sollen als dasselbe
# Wort gelten, sonst scheitert der Jaccard-Vergleich an einem Plural-n.
_STEM_SUFFIXES = ("en", "er", "es", "n", "s", "e")


def stem(word: str) -> str:
    """Sehr grobe Endungsreduktion. Nur bei Woertern ab 6 Zeichen, damit
    kurze Woerter nicht zu Stummeln werden."""
    if len(word) < 6:
        return word
    for suffix in _STEM_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def extract_tokens(text: str) -> set[str]:
    if not text:
        return set()
    words = set(re.findall(r"\b\w{3,}\b", clean_text_for_comparison(text)))
    return {stem(w) for w in words - config.STOP_WORDS}


def event_type(title: str) -> str | None:
    text = clean_text_for_comparison(title)
    if not text:
        return None
    words = set(re.findall(r"\b\w{3,}\b", text))

    for name, keywords in config.EVENT_TYPES:
        for keyword in keywords:
            if len(keyword) >= config._TYPE_MIN_SUBSTRING or " " in keyword:
                if keyword in text:
                    return name
            elif keyword in words:
                return name
    return None


def is_topically_relevant(event: dict) -> tuple[bool, str]:
    """Prueft, ob ein Event ueberhaupt zum Thema gehoert.

    Der Prompt allein genuegt nicht: ein Ortskriterium wie "Veranstaltung an
    einem Museum oder einer Kirche" laesst jedes Orgelkonzert, jede
    Stadtfuehrung und jeden Familiennachmittag durch. Hier wird deterministisch
    nachgeprueft.

    Rueckgabe: (relevant, Begruendung) - die Begruendung dient dem Log.
    """
    title = str(event.get("title") or "")
    description = str(event.get("description") or "")
    location = str(event.get("location") or "")

    # 1a. Die QUELLE gehoert durch ihre Art zum Thema. Eine Friedhofs-,
    #     Hospiz- oder Krematoriumsverwaltung veroeffentlicht keine
    #     Fremdtermine - alles dort Gelistete ist relevant.
    #     Notwendig, weil das Modell die Ortsangabe kuerzt: aus
    #     "KapelleDREI, Parkfriedhof Ohlsdorf, Hamburg" wurde "KapelleDREI,
    #     Hamburg", womit die Ortspruefung unten ins Leere lief und vier
    #     Termine des Ohlsdorfer Trauerprogramms verworfen wurden.
    # Domain UND Pfad pruefen: bei "stadt-zuerich.ch/friedhofforum/..." und
    # ".../locations/friedhof-sihlfeld-..." steht das Signal im Pfad, nicht
    # im Hostnamen.
    parsed_url = urlparse(str(event.get("url") or ""))
    source_path = f"{parsed_url.netloc}{parsed_url.path}".lower()
    host_hit = config.VENUE_PATTERN.search(source_path)
    if host_hit:
        return True, f"Quelle: {host_hit.group(0)}"

    # 1b. Ort gehoert schon durch seine Art zum Thema (Friedhofskapelle,
    #     Hospiz, Krematorium ...). Deckt Titel ab, die das Thema verschweigen.
    venue_hit = config.VENUE_PATTERN.search(location)
    if venue_hit:
        return True, f"Ort: {venue_hit.group(0)}"

    # 2. Themenwort in Titel, Beschreibung oder Ortsangabe.
    for field_name, text in (("Titel", title), ("Beschreibung", description),
                             ("Ort", location)):
        hit = config.TOPIC_PATTERN.search(text)
        if hit:
            return True, f"{field_name}: {hit.group(0)}"

    return False, "kein sepulkraler Bezug"


def event_host(event: dict) -> str:
    return urlparse(str(event.get("url") or "")).netloc.lower()


def _sources_compatible(ev1: dict, ev2: dict) -> bool:
    """Regelt, ob zwei Eintraege aus verschiedenen Quellen zusammengefuehrt
    werden duerfen.

    Gleicher Host: unkritisch, dort ist Doppelerfassung der Normalfall.
    Verschiedene Hosts: nur wenn BEIDE Ortsangaben gefuellt sind und sich
    ueberlappen. Ohne diese Bedingung fuehrt eine fehlende Ortsangabe dazu,
    dass "Fuehrung" auf dem Suedwestkirchhof und "Fuehrung" in Weissensee
    am selben Tag verschmelzen - der Ort ist die einzige Absicherung, und
    er kommt vom Modell, ist also nicht garantiert vorhanden.
    """
    host1, host2 = event_host(ev1), event_host(ev2)
    if not host1 or not host2 or host1 == host2:
        return True
    loc1 = extract_tokens(ev1.get("location", ""))
    loc2 = extract_tokens(ev2.get("location", ""))
    return bool(loc1 and loc2 and (loc1 & loc2))


def _locations_compatible(ev1: dict, ev2: dict) -> bool:
    loc1 = extract_tokens(ev1.get("location", ""))
    loc2 = extract_tokens(ev2.get("location", ""))
    if not loc1 or not loc2:
        return True
    return bool(loc1 & loc2)


def _types_compatible(ev1: dict, ev2: dict) -> bool:
    t1 = event_type(ev1.get("title", ""))
    t2 = event_type(ev2.get("title", ""))
    if t1 is None or t2 is None:
        return True
    return t1 == t2


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def are_events_duplicate(ev1: dict, ev2: dict) -> bool:
    """Konservativ: nur zusammenfuehren, wenn mehrere unabhaengige Merkmale
    uebereinstimmen. Ein uebersehenes Duplikat ist sichtbar und harmlos,
    eine falsche Zusammenfuehrung loescht ein echtes Event."""
    # 1. Datum: normalerweise muss der Beginn stimmen. Bei laufenden
    #    Veranstaltungen ist der Beginn aber unzuverlaessig - viele Seiten
    #    zeigen bei einer laufenden Ausstellung den HEUTIGEN Tag als Start
    #    ("laeuft ab ..."). Dadurch entstand pro Crawl ein neuer Eintrag:
    #    "Das Leben ist eine Collage" lag dreimal in der Datenbank, jeweils
    #    mit dem Datum des Laufs und identischem Enddatum. Bei Formaten mit
    #    Enddatum genuegt deshalb ein uebereinstimmendes ENDE.
    start_gleich = ev1.get("date_start") == ev2.get("date_start")
    ende1, ende2 = ev1.get("date_end"), ev2.get("date_end")
    ende_gleich = bool(ende1) and ende1 == ende2
    if not (start_gleich or ende_gleich):
        return False

    # 2. Quellenuebergreifend nur mit belastbarer Ortsangabe.
    if not _sources_compatible(ev1, ev2):
        return False

    # 3. Verschiedene Orte trennen. Wichtig bei Dachseiten, die Termine
    #    mehrerer Friedhoefe unter einer Domain listen.
    if not _locations_compatible(ev1, ev2):
        return False

    title1 = clean_text_for_comparison(ev1.get("title", ""))
    title2 = clean_text_for_comparison(ev2.get("title", ""))
    if not title1 or not title2:
        return False

    # 4. Identischer normalisierter Titel: Duplikat.
    if title1 == title2:
        return True

    # 5. Verschiedene Veranstaltungsart trennt immer.
    if not _types_compatible(ev1, ev2):
        return False

    # 6. Hohe Zeichenaehnlichkeit UND ueberwiegend gleiche Inhaltswoerter.
    ratio = difflib.SequenceMatcher(None, title1, title2).ratio()
    tok1 = extract_tokens(ev1.get("title", ""))
    tok2 = extract_tokens(ev2.get("title", ""))
    if (ratio >= config.TITLE_RATIO_THRESHOLD
            and _jaccard(tok1, tok2) >= config.TOKEN_JACCARD_THRESHOLD):
        return True

    # 7. Ein Titel ist vollstaendig im anderen enthalten. Faengt Faelle wie
    #    "Remembrance Sunday" / "Remembrance Sunday (Erinnerungssonntag)".
    #    Mindestlaenge verhindert, dass ein generischer Titel wie "Fuehrung"
    #    jeden laengeren Titel am selben Ort einsammelt.
    shorter, longer = sorted((title1, title2), key=len)
    if len(shorter) >= config.SUBSTRING_MIN_LENGTH and shorter in longer:
        return True

    return False


def generate_event_id(event: dict) -> str:
    title = clean_text_for_comparison(event.get("title", ""))
    raw = f"{title}|{event.get('date_start', '')}|{event_host(event)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def merge_into(target: dict, source: dict) -> None:
    for key in ("title", "description", "location"):
        new_len = len(clean_text_for_comparison(source.get(key)))
        old_len = len(clean_text_for_comparison(target.get(key)))
        if new_len > old_len:
            target[key] = source[key]
    if not target.get("date_end") and source.get("date_end"):
        target["date_end"] = source["date_end"]
    # Frueheren Beginn behalten: bei laufenden Formaten ist das der Wert,
    # der dem echten Beginn am naechsten kommt.
    if source.get("date_start") and target.get("date_start"):
        target["date_start"] = min(target["date_start"], source["date_start"])
    if source.get("first_seen"):
        target["first_seen"] = min(
            target.get("first_seen") or source["first_seen"], source["first_seen"]
        )
    if source.get("last_seen"):
        target["last_seen"] = max(target.get("last_seen") or "", source["last_seen"])


def load_events_db() -> dict:
    if not os.path.exists(config.DB_FILE):
        return {}
    with open(config.DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events_db(db: dict):
    directory = os.path.dirname(os.path.abspath(config.DB_FILE)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, config.DB_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def normalize_event(event: dict) -> dict:
    """Repariert Anzeigefelder im Bestand.

    Entities wie "Gr&auml;ber" wuerden im HTML als "Gr&amp;auml;ber"
    erscheinen, weil html.escape das Ampersand erneut maskiert. Die Funktion
    ist idempotent und laeuft bei jedem Lauf ueber die ganze Datenbank -
    damit werden auch Altbestaende ohne Extraskript sauber.
    """
    for field in ("title", "location", "description"):
        value = event.get(field)
        if isinstance(value, str):
            event[field] = html_mod.unescape(value).strip()
    return event


def _dedupe_gruppen(gruppen: dict) -> list[dict]:
    """Vergleicht innerhalb jeder Gruppe und fuehrt Duplikate zusammen."""
    behalten: list[dict] = []
    for gruppe in gruppen.values():
        kept: list[dict] = []
        for event in gruppe:
            for existing in kept:
                if are_events_duplicate(event, existing):
                    merge_into(existing, event)
                    break
            else:
                kept.append(event)
        behalten.extend(kept)
    return behalten


def deduplicate_db(db: dict) -> dict:
    """Zwei Durchgaenge, weil zwei verschiedene Datumsfelder tragen koennen.

    Durchgang 1 gruppiert nach Beginn - das faengt Einzeltermine, die von
    mehreren Quellen oder in abweichender Schreibweise gemeldet werden.

    Durchgang 2 gruppiert die Formate MIT Enddatum nach diesem Ende. Das
    ist noetig, weil laufende Ausstellungen bei jedem Crawl einen neuen
    Beginn bekommen und in Durchgang 1 deshalb in verschiedenen Gruppen
    landen.
    """
    nach_beginn = defaultdict(list)
    for event in db.values():
        nach_beginn[normalize_event(event).get("date_start", "")].append(event)
    zwischenstand = _dedupe_gruppen(nach_beginn)

    nach_ende = defaultdict(list)
    ohne_ende: list[dict] = []
    for event in zwischenstand:
        if event.get("date_end"):
            nach_ende[event["date_end"]].append(event)
        else:
            ohne_ende.append(event)
    merged = ohne_ende + _dedupe_gruppen(nach_ende)

    return {generate_event_id(ev): ev for ev in merged}


def find_duplicate_key(event: dict, db: dict) -> str | None:
    for key, existing in db.items():
        if are_events_duplicate(event, existing):
            return key
    return None