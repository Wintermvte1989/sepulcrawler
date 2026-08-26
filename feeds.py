"""Erkennung und Auswertung von ICS-Kalenderfeeds.

Warum das lohnt: Ein ICS-Feed liefert Titel, Datum, Ort und Beschreibung in
getrennten Feldern. Damit entfaellt fuer diese Quelle die KI-Extraktion
komplett - kein API-Request, keine Fehlinterpretation, keine Verdichtung, die
Termine abschneidet.

Bewusst OHNE geratene URLs: die Feed-Adresse wird im HTML der Seite gesucht.
Findet sich keine, bleibt alles beim bisherigen Weg. Damit kostet das Modul
nichts, wenn eine Quelle keinen Feed anbietet.
"""

import html as html_mod
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import config

# Plattformen, die einen Kalenderexport unter einem festen Pfad anbieten.
# Wird nur genutzt, wenn die Seite sich selbst als solche ausweist - nicht
# blind ausprobiert.
GENERATOR_FEEDS = (
    # WordPress "The Events Calendar": Terminliste + "?ical=1"
    ("the events calendar", "?ical=1"),
    ("events calendar", "?ical=1"),
)

MAX_FEED_EVENTS = 60


def find_feed_urls(raw_html: str, page_url: str) -> list[str]:
    """Sucht Kalenderfeeds im HTML. Reihenfolge = Vertrauensreihenfolge."""
    soup = BeautifulSoup(raw_html, "html.parser")
    found: list[str] = []

    def add(candidate: str | None):
        if not candidate:
            return
        absolute = urljoin(page_url, candidate.strip())
        if absolute not in found and absolute.startswith(("http://", "https://")):
            found.append(absolute)

    # 1. Selbstauskunft im Head - der saubere Weg.
    for link in soup.find_all("link", href=True):
        rel = " ".join(link.get("rel") or []).lower()
        mime = (link.get("type") or "").lower()
        if "text/calendar" in mime or (rel and "alternate" in rel and "ical" in mime):
            add(link["href"])

    # 2. Verlinkte .ics-Dateien im Seiteninhalt.
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if href.lower().split("?")[0].endswith(".ics"):
            add(href)

    # 3. Bekannte Plattform anhand des generator-Meta-Tags.
    generator = ""
    meta = soup.find("meta", attrs={"name": "generator"})
    if meta and meta.get("content"):
        generator = meta["content"].lower()
    body_hint = raw_html[:200000].lower()
    for marker, suffix in GENERATOR_FEEDS:
        if marker in generator or f'"{marker}"' in body_hint or "tribe-events" in body_hint:
            separator = "&" if "?" in page_url else ""
            add(page_url + (suffix if not separator else suffix.replace("?", "&")))
            break

    return found


def _unfold(text: str) -> list[str]:
    """RFC 5545: Zeilen, die mit Leerzeichen oder Tab beginnen, setzen die
    vorige fort. Ohne dieses Entfalten reissen lange Titel mitten im Wort."""
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw_line[:1] in (" ", "\t") and lines:
            lines[-1] += raw_line[1:]
        else:
            lines.append(raw_line)
    return lines


def _unescape_value(value: str) -> str:
    value = (value.replace("\\n", " ").replace("\\N", " ")
                  .replace("\\,", ",").replace("\\;", ";")
                  .replace("\\\\", "\\"))
    return re.sub(r"\s+", " ", html_mod.unescape(value)).strip()


def _parse_ics_date(value: str) -> tuple[str | None, bool]:
    """Gibt (ISO-Datum, ist_ganztaegig) zurueck.

    Formate: 20260913 (ganztaegig), 20260913T180000, 20260913T160000Z.
    """
    value = value.strip()
    match = re.match(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})Z?)?$", value)
    if not match:
        return None, False
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        iso = date(year, month, day).isoformat()
    except ValueError:
        return None, False
    return iso, match.group(4) is None


def parse_ics(text: str, source_url: str) -> list[dict]:
    """Zerlegt einen ICS-Text in Event-Dicts im Schema der Datenbank.

    Nicht unterstuetzt: RRULE-Wiederholungen werden nicht aufgeloest, es
    bleibt der erste Termin. Das ist bewusst - eine falsch expandierte
    Serie erzeugt mehr Schaden als ein fehlender Folgetermin.
    """
    if "BEGIN:VEVENT" not in text.upper():
        return []

    events: list[dict] = []
    current: dict[str, str] | None = None

    for line in _unfold(text):
        stripped = line.strip()
        upper = stripped.upper()
        if upper == "BEGIN:VEVENT":
            current = {}
            continue
        if upper == "END:VEVENT":
            if current is not None:
                built = _build_event(current, source_url)
                if built:
                    events.append(built)
            current = None
            continue
        if current is None or ":" not in stripped:
            continue

        name_part, _, value = stripped.partition(":")
        name = name_part.split(";")[0].upper()
        if name in ("SUMMARY", "LOCATION", "DESCRIPTION", "URL",
                    "DTSTART", "DTEND"):
            # Bei DTSTART/DTEND steht die Zeitzone in den Parametern; der
            # Wert selbst genuegt uns, weil nur das Datum interessiert.
            current[name] = value
            if name in ("DTSTART", "DTEND"):
                current[name + "_PARAMS"] = name_part

        if len(events) >= MAX_FEED_EVENTS:
            break

    return events


def _build_event(fields: dict, source_url: str) -> dict | None:
    title = _unescape_value(fields.get("SUMMARY", ""))
    start_raw = fields.get("DTSTART", "")
    start, all_day = _parse_ics_date(start_raw)
    if not title or not start:
        return None

    end = None
    if fields.get("DTEND"):
        end_iso, _ = _parse_ics_date(fields["DTEND"])
        if end_iso:
            # Bei ganztaegigen Terminen ist DTEND exklusiv: ein einzelner Tag
            # hat DTEND = Folgetag. Ohne Korrektur wird jeder Termin
            # faelschlich zweitaegig.
            if all_day:
                end_date = date.fromisoformat(end_iso) - timedelta(days=1)
                end_iso = end_date.isoformat()
            if end_iso > start:
                end = end_iso

    link = _unescape_value(fields.get("URL", "")) or source_url
    if not link.startswith(("http://", "https://")):
        link = source_url

    return {
        "title": title,
        "date_start": start,
        "date_end": end,
        "location": _unescape_value(fields.get("LOCATION", "")),
        "description": _unescape_value(fields.get("DESCRIPTION", ""))[:400],
        "url": link,
    }


def fetch_feed_events(client_http, raw_html: str, page_url: str) -> tuple[list[dict], str | None]:
    """Sucht einen Feed, laedt ihn und gibt die Events zurueck.

    Rueckgabe: (events, benutzte_feed_url). Leere Liste bedeutet: kein Feed
    gefunden oder keine brauchbaren Termine - dann laeuft die Quelle wie
    bisher ueber die KI-Extraktion.
    """
    for feed_url in find_feed_urls(raw_html, page_url)[:2]:
        try:
            response = client_http.get(feed_url)
            response.raise_for_status()
            body = response.text
        except Exception as exc:
            print(f"      Feed nicht abrufbar ({type(exc).__name__}): {feed_url}")
            continue

        # Manche Server liefern bei unbekannten Parametern die HTML-Seite
        # zurueck. Dann ist es kein Feed.
        if "BEGIN:VCALENDAR" not in body.upper():
            continue

        events = parse_ics(body, page_url)
        if events:
            return events, feed_url

    return [], None
