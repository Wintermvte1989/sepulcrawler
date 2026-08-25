import difflib
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
    s = str(text).lower()
    s = re.sub(r"[–—:,\"`«»„“'()\[\]\-\n\r/|]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_tokens(text: str) -> set[str]:
    if not text:
        return set()
    words = set(re.findall(r"\b\w{3,}\b", clean_text_for_comparison(text)))
    return words - config.STOP_WORDS


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


def event_host(event: dict) -> str:
    return urlparse(str(event.get("url") or "")).netloc.lower()


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
    if ev1.get("date_start") != ev2.get("date_start"):
        return False

    if not _locations_compatible(ev1, ev2):
        return False

    title1 = clean_text_for_comparison(ev1.get("title", ""))
    title2 = clean_text_for_comparison(ev2.get("title", ""))
    if not title1 or not title2:
        return False

    if title1 == title2:
        return True

    if not _types_compatible(ev1, ev2):
        return False

    ratio = difflib.SequenceMatcher(None, title1, title2).ratio()
    if ratio < config.TITLE_RATIO_THRESHOLD:
        return False

    tok1 = extract_tokens(ev1.get("title", ""))
    tok2 = extract_tokens(ev2.get("title", ""))
    return _jaccard(tok1, tok2) >= config.TOKEN_JACCARD_THRESHOLD


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


def deduplicate_db(db: dict) -> dict:
    by_date = defaultdict(list)
    for event in db.values():
        by_date[event.get("date_start", "")].append(event)

    merged = []
    for group in by_date.values():
        kept = []
        for event in group:
            for existing in kept:
                if are_events_duplicate(event, existing):
                    merge_into(existing, event)
                    break
            else:
                kept.append(event)
        merged.extend(kept)

    return {generate_event_id(ev): ev for ev in merged}


def find_duplicate_key(event: dict, db: dict) -> str | None:
    for key, existing in db.items():
        if are_events_duplicate(event, existing):
            return key
    return None