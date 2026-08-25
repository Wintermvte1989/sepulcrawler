import hashlib
import html
import json
import os
import re
import ssl
import tempfile
import time
import difflib
import httpx
import urllib3
from collections import Counter, defaultdict
from datetime import datetime, date
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URLS = [
    # --- Aktionstage, Festtage & Lange Nächte ---
    "https://www.tag-des-offenen-denkmals.de/",
    "https://www.lange-nacht-der-museen.de/",
    "https://www.meinkiez-meinfriedhof.berlin.de/tag-des-friedhofs",

    # --- Landeshauptstadt Berlin & Brandenburg ---
    "https://www.meinkiez-meinfriedhof.berlin.de/veranstaltungen",
    "https://jewish-cemetery-weissensee.org/entdecken/fuehrungen/",
    "https://www.invalidenfriedhof-berlin.de/",
    "https://www.evfbs.de/",
    "https://marienkirche-berlin.de/",
    "https://www.hedwigs-kathedrale.de/",
    "https://www.suedwestkirchhof.de/veranstaltungen.html",
    "https://www.spsg.de/aktuelles/veranstaltungen",
    "https://kriegsgraeberstaetten.volksbund.de/friedhof/halbe",
    "https://www.potsdam-museum.de/de/veranstaltungen",
    "https://www.potsdam.de/veranstaltungskalender",
    "https://stadtmuseum.stadt-brandenburg.de/stadtmuseum/termine",
    "https://www.museum-eberswalde.de/angebote/kalender",
    "https://www.brandenburg-preussen-museum.de/besuch-planen/veranstaltungen.html",

    # --- Landeshauptstadt München & Bayern ---
    "https://www.stadtmuseum.de/programm",
    "https://www.stattreisen-muenchen.de/fuehrungen/der-alte-sudliche-friedhof",
    "https://www.archaeologie-bayern.de/de/termine/",
    "https://www.pfarrei-chammuenster.de/",
    "https://bamberger-dom.de/gotteshaus/besucherpastoral/Veranstaltungen/index.html",
    "https://www.bamberger-dommusik.de/",
    "https://www.bistum-passau.de/dom-kultur/dom-st-stephan-passau",
    "https://www.dom-wuerzburg.de/",
    "https://www.evangelisch-stulrich.de/protestantischer-friedhof",
    "https://www.vhs-augsburg.de/programm/gesellschaft/augsburg-stadtfuehrungen-und-fahrten/fuehrungen",
    "https://domspatzen.de/veranstaltungen/",

    # --- Landeshauptstadt Stuttgart & Baden-Württemberg ---
    "https://www.landesmuseum-stuttgart.de/veranstaltungen/",
    "https://www.freiburger-muenster.de/",
    "https://www.karlsruhe.de/freizeit-und-sport/friedhoefe",

    # --- Landeshauptstadt Düsseldorf & NRW ---
    "https://www.duesseldorf.de/stadtgruen/freizeit/fuehrungen1",
    "https://www.duesseldorf.de/stadtmuseum/veranstaltungen",
    "https://www.stadt-muenster.de/gruen/friedhoefe",
    "https://www.zentralfriedhof-muenster.de/",
    "https://www.stiftsmuseum-xanten.de/",
    "https://www.ruhrmuseum.de/veranstaltungen/",
    "https://www.lwl-landesmuseum-herne.de/de/veranstaltungen/",
    "https://theatergemeinde-koeln.org/Kulturkompass/werk/25725/M04/stadtfuhrungen-koln/fuehrung-uber-melaten",
    "https://www.koelner-dom.de/aktuelles",
    "https://www.bonn.de/veranstaltungskalender/",

    # --- Landeshauptstadt Dresden & Sachsen ---
    "https://striesener-friedhof-dresden.de/vorschau-veranstaltungen/",
    "https://www.kreuzkirche-dresden.de/kalender/",
    "https://www.dhmd.de/ausstellungen/",
    "https://www.chemnitz.de/chemnitz/de/unsere-stadt/friedhoefe/veranstaltungen.html",
    "https://www.stadtgeschichtliches-museum-leipzig.de/besuch/veranstaltungen/",
    "https://paul-benndorf-gesellschaft.de/fuehrungen.html",

    # --- Landeshauptstadt Hannover & Niedersachsen ---
    "https://stpetridom.de/der-dom/besucher-info/bleikeller/",

    # --- Landeshauptstadt Wiesbaden & Hessen ---
    "https://www.krfrm.de/venue/hauptfriedhof-frankfurt-am-main/",
    "https://www.frankfurter-stadtevents.de/Themen/Friedhfe-Parks/Hauptfriedhof-Frankfurt-Grber-erzhlen-Geschichte_20010010/",
    "https://www.archaeologisches-museum-frankfurt.de/",
    "https://www.sepulkralmuseum.de/veranstaltungen/",

    # --- Landeshauptstadt Mainz & Rheinland-Pfalz ---
    "https://www.dommuseum-mainz.de/programm/kalender/aktuelle-termine-kalender/",
    "https://www.mainz.de/freizeit-und-sport/feste-und-veranstaltungen/veranstaltungskalender.php",
    "https://www.stadt-oppenheim.de/",
    "https://www.dom-zu-speyer.de/",
    "https://www.landesmuseum-trier.de/",

    # --- Landeshauptstadt Magdeburg & Sachsen-Anhalt ---
    "https://www.magdeburg.de/Start/Kultur-Sport/Veranstaltungskalender",
    "https://www.magdeburgerdom.de/",
    "https://www.naumburger-dom.de/",
    "https://www.landesmuseum-vorgeschichte.de/veranstaltungen/familiennachmittage",
    "http://www.friedhofskultur-halle.de/terminefuehrungen/",

    # --- Landeshauptstadt Erfurt & Thüringen ---
    "https://www.erfurt.de/ef/de/erleben/veranstaltungen/kalender/index.html",
    "https://www.dom-erfurt.de/",
    "https://www.augustinerkloster.de/veranstaltungen/",
    "https://eliasfriedhof.de/termine/",

    # --- Stadtstaaten Hamburg & Bremen ---
    "https://www.friedhof-hamburg.de/besucher/veranstaltungen/",
    "https://www.ohlsdorf-derpark.de/termine-ohlsdorf/",
    "https://www.shmh.de/veranstaltungen/",
    "https://www.st-michaelis.de/veranstaltungen-am-michel",
    "https://www.umweltbetrieb-bremen.de/friedhoefe/fuehrungen-und-veranstaltungen-11442",

    # --- Landeshauptstadt Schwerin & Mecklenburg-Vorpommern ---
    "https://www.schwerin.de/kultur-tourismus/veranstaltungen/veranstaltungskalender/",
    "https://www.muenster-doberan.de/",

    # --- Landeshauptstadt Kiel & Schleswig-Holstein ---
    "https://www.kiel.de/de/umwelt_verkehr/friedhoefe/",
    "https://www.st-marien-luebeck.de/",
    "https://schloss-gottorf.de/",

    # --- Landeshauptstadt Saarbrücken (Saarland) ---

    # --- Staatliche Museen, Forschung & Vereine (Überregional) ---
    "https://www.smb.museum/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/aegyptisches-museum-und-papyrussammlung/veranstaltungen/",
    "https://www.smb.museum/museen-einrichtungen/museum-fuer-vor-und-fruehgeschichte/veranstaltungen/",
    "https://www.humboldtforum.org/de/programm/",
    "https://www.jmberlin.de/",
    "https://www.ahorn-gruppe.de/",
    "https://www.sarggeschichten.de/",
    "https://www.ricam-hospiz.de/events/",
    "https://www.leiza.de/aktuelles",
    "https://www.archaeologie-online.de/nachrichten/",
    "https://www.friedhofsverwalter.de/fachveranstaltung-der-arbeitsgemeinschaft-friedhof-und-denkmal-e-v/",
    "https://aufdasleben.de/event/",
    "https://www.totentanz-online.de/veranstaltungen.php",
    "https://home.benecke.com/",

    # --- Tschechien & Österreich & Schweiz ---
    "https://www.sedlec.info/",
    "https://www.jewishmuseum.cz/en/info/visit/",
    "https://www.nm.cz/en/program/events",
    "https://www.kaisergruft.com/",
    "https://www.stephansdom.at/",
    "https://www.stift-stpeter.at/de/kloster/index.asp?dat=Friedhof-Katakomben",
    "https://www.stiftadmont.at/",
    "https://www.hallstatt.net/",
    "https://kulturzueri.ch/db/veranstalter/veranstalter-profile/friedhof-forum/",
    "https://www.stadtgaertnerei.bs.ch/friedhoefe/veranstaltungen.html",
    "https://www.bernermuenster.ch/",
    "https://www.stiftsbezirk.ch/de/veranstaltungen",
    "https://www.museum-aargau.ch/schloss-lenzburg/event-kalender",
    # --- Sepulkralkultur im engeren Sinn: Krematorien, Bestattungsmuseen ---
    # silent green: ehemaliges Krematorium Wedding (1912-2002), heute
    # Kulturquartier mit eigener Ausstellung zur Feuerbestattung.
    "https://www.silent-green.net/programm/",
    "https://www.bestattungsmuseum.at/",
    "https://www.bestattungwien.at/veranstaltungen",
    "http://www.wienfuehrungen.com/morbide-fuehrungen.html",

    # --- Medizin- und koerpergeschichtliche Sammlungen ---
    # Anatomie, Praeparate, Moulagen - thematisch nah an Tod und Koerper.
    "https://bmm-charite.de/ausstellungen",
    "https://www.josephinum.ac.at/veranstaltungen/",

    # --- Berlin & Brandenburg (aus der ersten Liste zurueckgeholt) ---
    "https://denkmaltag.berlin.de/",
    "https://www.kkbs.de/veranstaltungen/veranstaltungen-auf-friedhofen",
    "https://berlin.volksbund.de/aktuell/termine",
    "https://www.stiftung-historische-friedhoefe.de/",
    "https://www.efeu-ev.com/",
    "https://www.zwoelf-apostel-berlin.de/alle-termine-der-zwolf-apostel-kirchengemeinde-und-der-kirchhofe",
    "https://forum1848.de/veranstaltungen/",
    "https://www.garnisonfriedhof-berlin.de/",
    "https://stpetri-stmarien.de/",
    "https://www.berlinerdom.de/termine/",
    "https://www.bornstedter-friedhof.de/bornstedter-friedhof/historische-graeber/fuehrungen/termine-fuer-fuehrungen/",
    "https://www.friedhof-in-potsdam.de/allgemeines/aktuelles",
    "https://www.stift-neuzelle.de/",
    "https://bjoern-schulz-stiftung.de/akademie/",
    "https://tickets.jmberlin.de/events/",
    "https://www.berlin.de/museum-pankow/aktuelles/veranstaltungen/",
    "https://www.villa-oppenheim-berlin.de/",
    "https://www.zitadelle-berlin.de/en/education/events/",
    "https://www.dhm.de/programm/veranstaltungskalender/",

    # --- Deutschland uebrige (aus der ersten Liste zurueckgeholt) ---
    "https://landesmuseum-bonn.lvr.de/",
    "https://www.alm-bw.de/",
    "https://roemisch-germanisches-museum.de/",
    "https://www.frauenkirche-dresden.de/kalender/",
    "https://www.florian-scheungraber.de/termine/",

    # --- Leipzig: serverseitig gerenderte Kalender ---
    "https://www.leipzig-im.de/index.php?auswahl=Veranstaltungen&section=home",
    "https://www.stadtgeschichtliches-museum-leipzig.de/ausstellungen/aktuelle-ausstellungen/",

    # --- Augsburg: Traeger mit Friedhofsfuehrungen ---
    "https://jmaugsburg.de/fuehrungen/",

    # --- Tschechien (aus der ersten Liste zurueckgeholt) ---
    "https://www.brnenskepodzemi.cz/",
    "https://praha-vysehrad.cz/en/",

    # --- Oesterreich (aus der ersten Liste zurueckgeholt) ---
    "https://www.michaelerkirche.at/",
    "https://www.friedhoefewien.at/veranstaltungen",
    "https://www.friedhoefewien.at/friedhofsfuehrungen",

    # --- Schweiz: Friedhofskultur ---
    "https://www.bern.ch/politik-und-verwaltung/stadtverwaltung/tvs/stadtgrun-bern/friedhofe/friedhofskultur",
    "https://www.stadtluzern.ch/dienstleistungeninformation/159",
    "https://www.vssg.ch/de/arbeitsgruppen/friedhoefe-alles/tag-des-friedhofs.html",
]

# Am 24.08.2026 fehlgeschlagen und deshalb deaktiviert. Die korrekten
# Adressen sind nicht verifiziert - vor dem Wiedereinhaengen im Browser
# pruefen und dann oben eintragen.
DISABLED_URLS = {
    "https://www.aachen.de/DE/stadt_buerger/politik_verwaltung/pressemitteilungen/veranstaltungen.html": "404",
    "https://www.braunschweig.de/leben/umwelt_naturschutz/stadtgruen/friedhoefe/": "404",
    "https://www.darmstadt.de/leben-in-darmstadt/umwelt/friedhoefe": "404",
    "https://www.dresden.de/de/kultur/veranstaltungen/veranstaltungskalender.php": "404",
    "https://www.hannover.de/Kultur-Freizeit/Event-Highlights/Veranstaltungskalender": "404",
    "https://www.innsbruck.gv.at/leben/friedhoefe": "404",
    "https://www.kiel.de/de/kultur_freizeit/veranstaltungskalender/": "404",
    "https://www.nuernberg.de/internet/stadtportal/veranstaltungskalender.html": "404",
    "https://www.saarbruecken.de/kultur/veranstaltungskalender": "404",
    "https://www.saarbruecken.de/leben_in_saarbruecken/planen_bauen_wohnen/friedhoefe": "404",
    "https://www.stadt-salzburg.at/friedhoefe": "404",
    "https://www.stadtmuseum-dresden.de/veranstaltungen": "404",
    "https://www.stuttgart.de/leben/meta/veranstaltungskalender.php": "404",
    "https://www.ulmer-muenster.de/kultur-veranstaltungen": "404",
    "https://www.wiesbaden.de/kultur/veranstaltungskalender/index.php": "404",
    "https://www.worms.de/neu-de/kultur-und-tourismus/veranstaltungskalender/": "404",
    "https://friedhofsfreunde.blogspot.com/": "Bot-Sperre (429 ueber Google)",
    "https://www.katharinenkirche-oppenheim.de/": "DNS unbekannt",
    "https://www.welterbe-quedlinburg.de/": "DNS unbekannt",
}

DB_FILE = "events_db.json"
HTML_OUTPUT_FILE = "index.html"

BATCH_SIZE = 8          # nicht erhoehen - Output-Limit der API beachten
TEXT_LIMIT = 12000      # Zeichen pro Seite, die an die API gehen
MIN_TEXT_LENGTH = 1500  # darunter: vermutlich JS-gerenderte Seite ohne Inhalt
STALE_AFTER_DAYS = 10   # ab hier "nicht mehr bestaetigt" im HTML
API_ATTEMPTS = 3        # Achtung: jeder Versuch zaehlt gegen das RPD-Limit
FETCH_ATTEMPTS = 3      # Wiederholungen beim Laden einer Webseite (kostenlos)
API_PAUSE_SECONDS = 0.5 # Pause zwischen API-Requests (RPM-Limit: 1000)

# Verdichtung langer Seiten: Fenster um jede gefundene Datumsangabe.
# Ein Termineintrag (Datum + Titel + Ort + Kurztext) passt meist in ~600 Zeichen.
SNIPPET_BEFORE = 200
SNIPPET_AFTER = 400

# Obergrenze fuer die geschaetzte Zahl Events pro Request. Die Antwort der API
# ist auf ~8000 Output-Tokens begrenzt, ein Event kostet ~100 - darueber bricht
# das JSON ab und der Request ist verloren. Bewusst mit Reserve gesetzt.
MAX_EVENTS_PER_BATCH = 55

# Obergrenze der Fundstellen, die aus EINER Seite mitgenommen werden.
# Ohne diese Grenze kann eine dichte Kalenderseite das Output-Limit allein
# reissen - und die Paketierung kann sie dann nicht mehr abfangen, weil eine
# Seite nicht teilbar ist. Grosse Kalender liefern ihre restlichen Termine
# in den Folgelaeufen nach; der Bestand in events_db.json waechst dabei.
#
# Hoeher = mehr Termine pro Lauf, aber weniger Seiten pro Paket und damit
# mehr Requests. Gemessen mit 144 Quellen:
#   18 / TEXT_LIMIT  9000 -> 33 Requests
#   25 / TEXT_LIMIT 12000 -> 36 Requests   <- aktuell
#   35 / TEXT_LIMIT 16000 -> 44 Requests
MAX_HITS_PER_PAGE = 25

# Harte Obergrenze der Pakete pro Lauf. Der bezahlte Tarif erlaubt 50
# Requests pro Lauf; die Differenz ist Reserve fuer Retries (jeder
# Wiederholungsversuch in call_with_retry zaehlt als eigener Request).
MAX_REQUESTS_PER_RUN = 40

BERLIN = ZoneInfo("Europe/Berlin")

# Erkennt deutsche und ISO-Datumsangaben. Auch Kurzformen ohne Jahr
# ("Sa, 12.09.") und abgekuerzte Monatsnamen ("12. Sept."), weil viele
# Terminlisten das Jahr weglassen - sonst werden gueltige Seiten verworfen.
DATE_PATTERN = re.compile(
    r"\b\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}\b"          # 12.09.2026
    r"|\b\d{1,2}\.\s*\d{1,2}\.(?!\d)"                   # 12.09.
    r"|\b\d{1,2}\.?\s*(Jan|Feb|M\u00e4r|Mrz|Apr|Mai|Jun|Jul|Aug|"
    r"Sep|Sept|Okt|Nov|Dez)[a-z\u00e4\u00f6\u00fc]*\.?"     # 12. Sept. / 12. September
    r"|\b\d{4}-\d{2}-\d{2}\b"                           # 2026-09-12
    r"|\b(Mo|Di|Mi|Do|Fr|Sa|So)\.?,\s*\d{1,2}\."          # Sa, 12.
    , re.IGNORECASE,
)

MONTH_MAP = {
    "jan": 1, "januar": 1,
    "feb": 2, "februar": 2,
    "mär": 3, "mrz": 3, "märz": 3, "maerz": 3,
    "apr": 4, "april": 4,
    "mai": 5,
    "jun": 6, "juni": 6,
    "jul": 7, "juli": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dez": 12, "dezember": 12,
}

# Nur echte Funktionswoerter. Veranstaltungsarten ("Fuehrung", "Vortrag")
# gehoeren NICHT hierher - sie unterscheiden Termine voneinander und werden
# unten ueber EVENT_TYPES ausgewertet.
STOP_WORDS = {
    "über", "durch", "nach", "beim", "eines", "einer", "einen", "einem",
    "mit", "und", "oder", "für", "vom", "auf", "dem", "den", "der", "die",
    "das", "des", "aus", "zum", "zur", "von", "im", "in", "am", "an", "bei",
    "sowie", "wird", "wie", "als", "auch", "sich", "ist", "sind", "uhr",
}

# Veranstaltungsart. Zwei Termine unterschiedlicher Art am selben Tag und Ort
# sind verschiedene Veranstaltungen, auch wenn die Titel einander aehneln.
#
# Reihenfolge ist Pruefreihenfolge - der erste Treffer gewinnt. Wichtig:
#  - "film" vor "fuehrung": "Filmvorfuehrung" ist ein Film.
#  - "gottesdienst" vor "lesung": "Andacht mit Verlesung" ist eine Andacht,
#    sonst greift das "lesung" in "Verlesung".
#  - "fuehrung" vor "aktionstag": "Fuehrungen am Museumstag" ist eine Fuehrung.
#  - "workshop" vor "gottesdienst": ein "Redner-Workshop: Trauerfeiern"
#    ist eine Fortbildung, keine Trauerfeier.
#  - "aktionstag" zuletzt: faengt nur, was kein eigenes Format nennt.
EVENT_TYPES = (
    ("film", ("filmvorführung", "filmvorfuehrung", "filmabend", "kino", "film")),
    ("ausstellung", ("ausstellung", "vernissage", "finissage")),
    ("workshop", ("workshop", "seminar", "fortbildung", "modellier",
                  "ausbildung", "kurs")),
    ("gottesdienst", ("gottesdienst", "messfeier", "trauerfeier", "gedenkfeier",
                      "gedenkveranstaltung", "kranzniederlegung", "gedenken",
                      "andacht", "requiem", "messe")),
    ("konzert", ("konzert", "musik", "chor", "orgel")),
    ("lesung", ("lesung", "buchvorstellung")),
    ("vortrag", ("vortrag", "referat", "podium", "diskussion", "kolloquium",
                 "symposium", "tagung")),
    ("begleitung", ("sterbebegleitung", "trauerbegleitung", "trauercafé",
                    "trauercafe", "letzte hilfe", "hospiz", "austausch",
                    "gesprächstisch", "gespraechstisch")),
    ("fuehrung", ("führung", "fuehrung", "rundgang", "spaziergang", "rundfahrt",
                  "busrundfahrt", "fahrradtour", "exkursion", "tour")),
    ("aktionstag", ("tag des friedhofs", "tag des offenen denkmals",
                    "tag des denkmals", "museumsnacht", "lange nacht",
                    "museumstag", "aktionstag", "aktionswoche", "sommerfest")),
)

# Substring-Suche erst ab dieser Laenge, sonst exakter Wortvergleich.
# Verhindert Treffer wie "kurs" in "Diskurs" oder "tour" in "Kontour".
_TYPE_MIN_SUBSTRING = 6

# Bewusst konservativ: ein uebersehenes Duplikat ist sichtbar und harmlos,
# eine falsche Zusammenfuehrung loescht ein echtes Event.
TITLE_RATIO_THRESHOLD = 0.88
TOKEN_JACCARD_THRESHOLD = 0.60

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


class TruncatedResponseError(Exception):
    """Antwort der API war kein gueltiges JSON - meist abgeschnitten wegen Output-Limit."""


class Event(BaseModel):
    source_id: int = Field(description="Nummer der QUELLE, aus der dieses Event stammt")
    title: str = Field(description="Titel der Veranstaltung")
    date_start: str = Field(description="Startdatum im Format YYYY-MM-DD")
    date_end: str | None = Field(
        default=None,
        description="Enddatum YYYY-MM-DD, nur bei mehrtaegigen Veranstaltungen, sonst null",
    )
    location: str = Field(description="Ort oder Institution der Veranstaltung")
    description: str = Field(description="Kurze Zusammenfassung in 1-2 Saetzen")


class EventList(BaseModel):
    events: list[Event]


# ---------------------------------------------------------------- Datum & Text-Normalisierung

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
        month_num = MONTH_MAP.get(month_str)
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
    return words - STOP_WORDS


def event_type(title: str) -> str | None:
    """Grobe Kategorie der Veranstaltungsart, oder None wenn nicht erkennbar.

    Deutsche Veranstaltungstitel sind Komposita: "Sonntagsfuehrung",
    "Kurator*innenfuehrung", "Busrundfahrten", "Gedenkmessfeier". Ein exakter
    Wortvergleich findet davon nichts, deshalb Substring-Suche fuer lange
    Stichworte und exakter Vergleich fuer kurze.
    """
    text = clean_text_for_comparison(title)
    if not text:
        return None
    words = set(re.findall(r"\b\w{3,}\b", text))

    for name, keywords in EVENT_TYPES:
        for keyword in keywords:
            if len(keyword) >= _TYPE_MIN_SUBSTRING or " " in keyword:
                if keyword in text:
                    return name
            elif keyword in words:
                return name
    return None


def event_host(event: dict) -> str:
    return urlparse(str(event.get("url") or "")).netloc.lower()


def _locations_compatible(ev1: dict, ev2: dict) -> bool:
    """Verschiedene Orte schliessen ein Duplikat aus. Eine fehlende
    Ortsangabe gilt als vereinbar - fehlende Information darf nicht trennen."""
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
    uebereinstimmen. Im Zweifel getrennt lassen."""
    # 1. Datum muss identisch sein.
    if ev1.get("date_start") != ev2.get("date_start"):
        return False

    # 2. Verschiedene Quell-Domains trennen. Dasselbe Event auf zwei Seiten
    #    ist moeglich, aber selten - ein sichtbares Duplikat ist billiger
    #    als ein geloeschtes Event.
    host1, host2 = event_host(ev1), event_host(ev2)
    if host1 and host2 and host1 != host2:
        return False

    # 3. Verschiedene Orte trennen. Wichtig bei Dachseiten, die Termine
    #    mehrerer Friedhoefe unter einer Domain listen (z. B. Verbaende).
    if not _locations_compatible(ev1, ev2):
        return False

    title1 = clean_text_for_comparison(ev1.get("title", ""))
    title2 = clean_text_for_comparison(ev2.get("title", ""))
    if not title1 or not title2:
        return False

    # 4. Identischer normalisierter Titel: Duplikat.
    if title1 == title2:
        return True

    # 5. Unscharfer Fall - nur bei hoher Aehnlichkeit UND gleicher
    #    Veranstaltungsart UND ueberwiegend gleichen Inhaltswoertern.
    if not _types_compatible(ev1, ev2):
        return False

    ratio = difflib.SequenceMatcher(None, title1, title2).ratio()
    if ratio < TITLE_RATIO_THRESHOLD:
        return False

    tok1 = extract_tokens(ev1.get("title", ""))
    tok2 = extract_tokens(ev2.get("title", ""))
    return _jaccard(tok1, tok2) >= TOKEN_JACCARD_THRESHOLD


def generate_event_id(event: dict) -> str:
    """Host gehoert in die ID: sonst kollidieren gleichnamige Termine
    verschiedener Institutionen am selben Tag."""
    title = clean_text_for_comparison(event.get("title", ""))
    raw = f"{title}|{event.get('date_start', '')}|{event_host(event)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def merge_into(target: dict, source: dict) -> None:
    """Fuehrt source in target zusammen - nur ergaenzend. Vorhandene Werte
    werden hoechstens durch laengere, informativere ersetzt."""
    # Laenge am normalisierten Text messen: sonst gewinnt die Variante mit
    # Doppelleerzeichen und Komma am Ende, obwohl sie keinen Inhalt mehr hat.
    # Bei Gleichstand bleibt der Bestand - er wurde zuerst gesehen.
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


# ---------------------------------------------------------------- Datenbank & Deduplizierung

def load_events_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events_db(db: dict):
    directory = os.path.dirname(os.path.abspath(DB_FILE)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, DB_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def deduplicate_db(db: dict) -> dict:
    """Gruppiert nach Datum und vergleicht nur innerhalb der Gruppe - Events
    an verschiedenen Tagen koennen nie Duplikate sein."""
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
    """Sucht im Bestand einen Eintrag, der dasselbe Event bezeichnet."""
    for key, existing in db.items():
        if are_events_duplicate(event, existing):
            return key
    return None


# ---------------------------------------------------------------- Auswahl

def is_worth_sending(url: str, text: str) -> bool:
    if len(text) < MIN_TEXT_LENGTH:
        print(f"  uebersprungen (nur {len(text)} Zeichen, evtl. JS-gerendert): {url}")
        return False
    if not DATE_PATTERN.search(text):
        print(f"  uebersprungen (kein Datumsmuster gefunden): {url}")
        return False
    return True


# ---------------------------------------------------------------- Abruf

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
}


def make_ssl_context() -> ssl.SSLContext:
    """Toleranter TLS-Kontext. Einige Kirchen- und Vereinsserver bieten nur
    alte Cipher-Suites an und brechen sonst mit HANDSHAKE_FAILURE ab.
    Zertifikatspruefung ist ohnehin aus (nur oeffentliche Seiten, keine
    Credentials), daher kostet die Lockerung hier nichts zusaetzlich."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except (AttributeError, ValueError):
        pass
    for ciphers in ("DEFAULT@SECLEVEL=1", "ALL:@SECLEVEL=1"):
        try:
            ctx.set_ciphers(ciphers)
            break
        except ssl.SSLError:
            continue
    return ctx


def make_http_client() -> httpx.Client:
    """Ein Client fuer alle Anfragen: wiederverwendete Verbindungen,
    getrennte Timeouts fuer Verbindungsaufbau und Antwort."""
    return httpx.Client(
        headers=BROWSER_HEADERS,
        follow_redirects=True,
        verify=make_ssl_context(),
        timeout=httpx.Timeout(connect=15.0, read=40.0, write=15.0, pool=15.0),
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    )


def html_to_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup
    return main.get_text(separator=" ", strip=True)


def classify_error(exc: Exception) -> str:
    """Grobe Fehlerklasse fuer die Auswertung am Ende des Laufs."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout)):
        return "Timeout"
    if isinstance(exc, httpx.ConnectError):
        text = str(exc)
        if "Name or service not known" in text or "nodename nor servname" in text:
            return "DNS unbekannt"
        if "SSL" in text or "HANDSHAKE" in text.upper():
            return "TLS-Handshake"
        return "Verbindung fehlgeschlagen"
    if isinstance(exc, httpx.RemoteProtocolError):
        return "Protokollfehler"
    return type(exc).__name__


# Fehlerklassen, bei denen ein erneuter Versuch sinnvoll ist. Ein 404 oder
# ein DNS-Fehler wiederholt sich dagegen garantiert.
RETRYABLE = (
    httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout,
    httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError,
)


def fetch_page_text(client_http: httpx.Client, url: str) -> str:
    """Laedt genau die angegebene URL. KEIN Fallback auf die Startseite:
    der liefert Inhalte, die nicht zur URL gehoeren, und verbraucht
    Batch-Plaetze fuer Muell.

    Gibt immer den extrahierten Text zurueck (auch einen kurzen) oder wirft
    eine Exception. Ob der Text brauchbar ist, entscheidet is_worth_sending."""
    last_exc: Exception | None = None

    for attempt in range(FETCH_ATTEMPTS):
        try:
            response = client_http.get(url)
            response.raise_for_status()
            return html_to_text(response.text)
        except httpx.HTTPStatusError as exc:
            # Verbindung stand, Server sagt nein. Kein Retry.
            raise exc
        except RETRYABLE as exc:
            last_exc = exc
            if attempt < FETCH_ATTEMPTS - 1:
                wait = 3 * (attempt + 1)
                print(f"  {classify_error(exc)}, Versuch "
                      f"{attempt + 2}/{FETCH_ATTEMPTS} in {wait}s: {url}")
                time.sleep(wait)
        except Exception as exc:
            last_exc = exc
            break

    raise last_exc if last_exc else RuntimeError("Abruf ohne Ergebnis")


# ---------------------------------------------------------------- Verdichtung

def cap_hits(text: str, max_hits: int) -> tuple[str, int]:
    """Schneidet vor der (max_hits+1)-ten Datumsangabe ab.

    Gilt bewusst fuer JEDE Seite, nicht nur fuer lange: eine kompakte
    Terminliste kann auf 6000 Zeichen 80 Termine enthalten und wuerde sonst
    das Output-Limit allein reissen. Der Text der letzten mitgenommenen
    Veranstaltung reicht bis zur naechsten Datumsangabe und bleibt vollstaendig.
    """
    found = list(DATE_PATTERN.finditer(text))
    if len(found) <= max_hits:
        return text, len(found)
    return text[:found[max_hits].start()], max_hits


def condense_text(text: str, limit: int) -> tuple[str, int]:
    """Reduziert eine Seite auf die Textstellen um Datumsangaben herum.

    Stumpfes text[:limit] verschenkt bei grossen Kalendern fast alles: die
    ersten Zeichen sind Navigation und Einleitung, die Terminliste beginnt
    weiter unten. Hier wird stattdessen um jedes Datum ein Fenster gelegt,
    ueberlappende Fenster werden verschmolzen.

    Rueckgabe: (Text fuer die API, Anzahl Datumsangaben darin). Die Anzahl
    dient als Schaetzung, wie viele Events die Seite liefert.
    """
    if len(text) <= limit:
        return cap_hits(text, MAX_HITS_PER_PAGE)

    spans: list[list[int]] = []
    # Hinweis: Bei dichten Terminlisten ueberlappen die Fenster durchgehend und
    # verschmelzen zu einem einzigen Bereich. Das ist gewollt - er beginnt dann
    # genau am ersten Termin, statt bei der Navigation.
    for match in DATE_PATTERN.finditer(text):
        window_start = max(0, match.start() - SNIPPET_BEFORE)
        window_stop = min(len(text), match.end() + SNIPPET_AFTER)
        if spans and window_start <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], window_stop)
        else:
            spans.append([window_start, window_stop])

    if not spans:
        # Kein Datum gefunden - is_worth_sending haette die Seite ohnehin
        # verworfen. Vorne abschneiden als letzter Rueckfall.
        return text[:limit], 0

    separator = " [...] "
    parts: list[str] = []
    used = 0
    hits = 0
    for window_start, window_stop in spans:
        chunk = text[window_start:window_stop]
        if used + len(chunk) + len(separator) > limit:
            break
        parts.append(chunk)
        used += len(chunk) + len(separator)
        hits += len(DATE_PATTERN.findall(chunk))
        if hits >= MAX_HITS_PER_PAGE:
            break

    if not parts:
        # Ein einzelner (verschmolzener) Bereich ist groesser als das Limit.
        # Vom Anfang nehmen: dort stehen die zeitlich naechsten Termine.
        # Weiter entfernte ruecken in spaeteren Laeufen nach vorne.
        result = text[spans[0][0]:spans[0][0] + limit]
    else:
        result = separator.join(parts)

    return cap_hits(result, MAX_HITS_PER_PAGE)


def pack_batches(pages: list[tuple[str, str, int]]) -> list[list[tuple[str, str]]]:
    """Verteilt Seiten auf Pakete, ohne die geschaetzte Event-Obergrenze
    pro Request zu reissen.

    Ohne das landeten eine dichte Kalenderseite und sieben kleine
    Vereinsseiten im gleichen Paket - die grosse dominierte die Antwort und
    riskierte ein abgeschnittenes JSON. First-Fit-Decreasing: dichte Seiten
    zuerst, kleine fuellen die Luecken.
    """
    ordered = sorted(pages, key=lambda page: page[2], reverse=True)
    batches: list[list[tuple[str, str, int]]] = []

    for page in ordered:
        for batch in batches:
            crowded = len(batch) >= BATCH_SIZE
            too_many = sum(p[2] for p in batch) + page[2] > MAX_EVENTS_PER_BATCH
            if not crowded and not too_many:
                batch.append(page)
                break
        else:
            batches.append([page])

    return [[(url, text) for url, text, _ in batch] for batch in batches]


def rotation_key(url: str, period: int) -> int:
    """Stabile, aber pro Lauf wechselnde Reihenfolge einer URL."""
    return int(hashlib.md5(f"{url}|{period}".encode("utf-8")).hexdigest(), 16)


def select_within_budget(
    pages: list[tuple[str, str, int]], period: int, max_requests: int
) -> tuple[list[tuple[str, str, int]], list[tuple[str, str, int]]]:
    """Waehlt Seiten aus, wenn nicht alle ins Request-Budget passen.

    Ein einfaches Abschneiden der letzten Pakete waere unfair: pack_batches
    sortiert nach Dichte, also landeten immer dieselben duennen Quellen hinten
    und kaemen nie zum Zug. Die Auswahl rotiert daher pro Lauf.
    """
    if not pages or len(pack_batches(pages)) <= max_requests:
        return pages, []

    kept: list[tuple[str, str, int]] = []
    for page in sorted(pages, key=lambda pg: rotation_key(pg[0], period)):
        if len(pack_batches(kept + [page])) <= max_requests:
            kept.append(page)

    kept_urls = {url for url, _, _ in kept}
    skipped = [pg for pg in pages if pg[0] not in kept_urls]
    return kept, skipped


# ---------------------------------------------------------------- Extraktion

def extract_events_batch(batch_sources: list[tuple[str, str]], today_str: str) -> list[dict]:
    # Der Text ist bereits verdichtet und auf TEXT_LIMIT begrenzt
    # (siehe condense_text in Phase 1) - hier nicht erneut abschneiden.
    combined_text = ""
    for idx, (url, text) in enumerate(batch_sources, start=1):
        combined_text += (
            f"\n=== QUELLE {idx} ===\n{text}\n=== ENDE QUELLE {idx} ===\n"
        )

    prompt = f"""
    Das heutige Datum ist {today_str}.
    Analysiere die folgenden Webseiten-Texte auf Veranstaltungen im Bereich Sepulkralkultur,
    Friedhofsfuehrungen, Bestattungswesen, Totenkult, Gedenkkultur, Grabkunst oder
    historische Ausstellungen zum Thema Tod/Sterben.

    WICHTIG:
    - Extrahiere AUSSCHLIESSLICH Veranstaltungen, deren Datum am oder nach dem heutigen Datum ({today_str}) liegt.
    - date_start MUSS strikt YYYY-MM-DD sein.
    - date_end nur bei mehrtaegigen Veranstaltungen (Ausstellungen, Aktionstage) setzen, sonst null.
    - Ignoriere alle vergangenen Veranstaltungen strikt.
    - Trage in 'source_id' die Nummer der QUELLE ein, in deren Block das Event stand.
    - MEHRSPRACHIGE TEXTE: Falls der Quelltext auf Englisch, Tschechisch oder einer anderen
      Sprache verfasst ist, uebersetze title, location und description praezise ins Deutsche.

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
    for attempt in range(API_ATTEMPTS):
        try:
            return extract_events_batch(batch_sources, today_str)
        except TruncatedResponseError:
            print("  Antwort abgeschnitten - kein Retry, BATCH_SIZE pruefen")
            return []
        except Exception as e:
            wait = 5 * (2 ** attempt)
            print(f"  Versuch {attempt + 1}/{API_ATTEMPTS} fehlgeschlagen ({e}), warte {wait}s")
            if attempt < API_ATTEMPTS - 1:
                time.sleep(wait)
    print("  endgueltig aufgegeben")
    return []


# ---------------------------------------------------------------- Verschlagwortung

# Region aus dem location-Feld. Reihenfolge in der Liste = Pruefreihenfolge,
# der erste Treffer gewinnt. Stichworte in Kleinschreibung.
REGIONS = (
    ("berlin-brandenburg", (
        "berlin", "stahnsdorf", "potsdam", "brandenburg", "weißensee",
        "weissensee", "liesenstraße", "liesenstrasse", "neukölln", "pankow",
        "hellersdorf", "spandau", "charlottenburg", "kreuzberg", "eberswalde",
        "neuzelle", "halbe",
    )),
    ("nord", (
        "hamburg", "ohlsdorf", "kiel", "bremen", "lübeck", "luebeck",
        "schwerin", "hannover", "braunschweig", "doberan", "gottorf",
        "schleswig", "flensburg", "rostock",
    )),
    ("west", (
        "köln", "koeln", "melaten", "frankfurt", "herne", "bonn",
        "düsseldorf", "duesseldorf", "münster", "muenster", "kassel",
        "xanten", "essen", "aachen", "mainz", "wiesbaden", "darmstadt",
        "trier", "speyer", "worms", "oppenheim", "saarbrücken",
        "saarbruecken", "dortmund", "bochum",
    )),
    ("ost", (
        "leipzig", "dresden", "halle", "erfurt", "magdeburg", "naumburg",
        "chemnitz", "quedlinburg", "striesener", "eliasfriedhof", "görlitz",
        "goerlitz", "weimar", "jena",
    )),
    ("sued", (
        "münchen", "muenchen", "nürnberg", "nuernberg", "regensburg",
        "augsburg", "stuttgart", "ulm", "bamberg", "würzburg", "wuerzburg",
        "passau", "karlsruhe", "freiburg", "chammünster", "chammuenster",
        "bayern", "schwaben",
    )),
    ("ausland", (
        "wien", "salzburg", "innsbruck", "graz", "admont", "hallstatt",
        "basel", "bern", "zürich", "zuerich", "st. gallen", "st.gallen",
        "luzern", "genf", "prag", "praha", "kutná hora", "kutna hora",
        "sedlec", "brno", "brünn", "bruenn", "österreich", "oesterreich",
        "schweiz", "tschechien",
    )),
)

# Anzeigenamen fuer die Filterknoepfe im HTML.
REGION_LABELS = {
    "berlin-brandenburg": "Berlin &amp; Brandenburg",
    "nord": "Norden",
    "west": "Westen",
    "ost": "Osten",
    "sued": "S&uuml;den",
    "ausland": "AT / CH / CZ",
    "online": "Online",
}

TYPE_LABELS = {
    "fuehrung": "F&uuml;hrungen",
    "aktionstag": "Aktionstage",
    "konzert": "Konzerte &amp; Musik",
    "ausstellung": "Ausstellungen",
    "vortrag": "Vortr&auml;ge",
    "lesung": "Lesungen",
    "gottesdienst": "Gedenken",
    "workshop": "Kurse &amp; Workshops",
    "begleitung": "Trauer &amp; Begleitung",
    "film": "Film",
}


def event_region(event: dict) -> str:
    """Grobe geografische Einordnung. 'online' hat Vorrang: eine reine
    Online-Veranstaltung gehoert in keine Ortsliste."""
    location = clean_text_for_comparison(event.get("location"))
    if not location or "online" in location or "bundesweit" in location:
        return "online"
    for name, keywords in REGIONS:
        if any(word in location for word in keywords):
            return name
    return "sonstige"


def event_tags(event: dict) -> list[str]:
    """Tags werden hier vergeben, nicht im Browser gesucht.

    Der frühere Filter suchte Substrings im gerenderten Zeilentext. Das leckt:
    'kunst' fand 'Grabkunst' in Dutzenden Fuehrungsbeschreibungen, 'museum'
    fand 'Museum fuer Sepulkralkultur' und machte jede Kasseler Fuehrung zur
    Ausstellung. Feste Tags im data-Attribut vermeiden das.
    """
    tags = [f"region-{event_region(event)}"]

    kind = event_type(event.get("title", ""))
    if kind is None:
        # Titel ohne Gattungswort - Beschreibung als zweite Chance nutzen.
        kind = event_type(event.get("description", ""))
    tags.append(f"art-{kind}" if kind else "art-sonstige")

    if event.get("date_end"):
        tags.append("laufend")

    return tags


# ---------------------------------------------------------------- HTML

def _filter_buttons(group: str, counts: dict, labels: dict) -> str:
    """Baut die Filterknoepfe einer Gruppe - nur fuer Tags, die es auch gibt.

    Leere Filter sind schlimmer als fehlende: sie sehen aus wie ein Fehler.
    """
    parts = [f'<button class="tag-btn active" data-group="{group}" '
             f'data-value="" onclick="setFilter(this)">Alle</button>']
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for value, count in ordered:
        label = labels.get(value, value.capitalize())
        parts.append(
            f'<button class="tag-btn" data-group="{group}" data-value="{value}" '
            f'onclick="setFilter(this)">{label} <span style="opacity:.6">'
            f'{count}</span></button>'
        )
    return "\n                ".join(parts)


def render_html(events: list[dict], today: date):
    timestamp = datetime.now(BERLIN).strftime("%d.%m.%Y um %H:%M Uhr")
    today_str = today.isoformat()

    # Tags einmal vorberechnen und am Event mitfuehren.
    enriched = []
    region_counts: Counter = Counter()
    type_counts: Counter = Counter()
    for event in events:
        tags = event_tags(event)
        region = next(t[len("region-"):] for t in tags if t.startswith("region-"))
        kind = next(t[len("art-"):] for t in tags if t.startswith("art-"))
        region_counts[region] += 1
        type_counts[kind] += 1
        enriched.append((event, tags))

    # Sortierschluessel ist max(Startdatum, heute): eine seit Juli laufende
    # Ausstellung erscheint damit an der Position "heute" und nicht mehr weit
    # oben bei ihrem Startdatum. Wer sie ganz ausblenden will, nutzt den
    # Art-Filter - laufende Formate tragen zusaetzlich das Tag "laufend".
    enriched.sort(key=lambda pair: (
        max(pair[0].get("date_start", ""), today_str),
        pair[0].get("date_start", ""),
    ))

    region_buttons = _filter_buttons("region", region_counts, REGION_LABELS)
    type_buttons = _filter_buttons("art", type_counts, TYPE_LABELS)
    total = len(enriched)

    html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sepulkralkultur Event-Feed</title>
    <style>
        :root {{
            --bg-body: #f4f6f8;
            --bg-container: #ffffff;
            --text-main: #333333;
            --text-muted: #7f8c8d;
            --heading-color: #2c3e50;
            --border-color: #ecf0f1;
            --filter-bg: #f8f9fa;
            --filter-border: #e9ecef;
            --tag-bg: #e9ecef;
            --tag-text: #495057;
            --tag-active-bg: #3498db;
            --tag-active-text: #ffffff;
            --th-bg: #2c3e50;
            --th-text: #ffffff;
            --tr-hover: #f8f9fa;
            --location-color: #34495e;
            --btn-bg: #27ae60;
            --btn-hover: #219150;
            --input-border: #ced4da;
            --input-bg: #ffffff;
            --toggle-bg: #e9ecef;
        }}

        [data-theme="dark"] {{
            --bg-body: #121417;
            --bg-container: #1e2227;
            --text-main: #e1e6eb;
            --text-muted: #8b99a8;
            --heading-color: #8fa0b3;
            --border-color: #2d353e;
            --filter-bg: #181b1f;
            --filter-border: #2d353e;
            --tag-bg: #2d353e;
            --tag-text: #c0caf5;
            --tag-active-bg: #3498db;
            --tag-active-text: #ffffff;
            --th-bg: #2a323d;
            --th-text: #e1e6eb;
            --tr-hover: #252a30;
            --location-color: #a0b2c6;
            --btn-bg: #27ae60;
            --btn-hover: #219150;
            --input-border: #3d4652;
            --input-bg: #181b1f;
            --toggle-bg: #2d353e;
        }}

        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 20px; transition: background-color 0.2s, color 0.2s; }}
        
        .header-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--tag-active-bg); padding-bottom: 10px; margin-bottom: 10px; }}
        h1 {{ color: var(--heading-color); margin: 0; font-size: 1.8em; }}
        
        .theme-toggle-btn {{ background: var(--toggle-bg); border: 1px solid var(--filter-border); color: var(--text-main); padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 1em; display: flex; align-items: center; gap: 6px; font-weight: 600; transition: all 0.2s; }}
        .theme-toggle-btn:hover {{ opacity: 0.85; }}

        .container {{ background: var(--bg-container); border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: background-color 0.2s; }}
        .timestamp {{ font-size: 0.85em; color: var(--text-muted); margin-bottom: 20px; }}

        .filter-container {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; align-items: center; background: var(--filter-bg); padding: 15px; border-radius: 6px; border: 1px solid var(--filter-border); }}
        .search-input {{ flex: 1; min-width: 250px; padding: 8px 12px; border: 1px solid var(--input-border); background-color: var(--input-bg); color: var(--text-main); border-radius: 4px; font-size: 0.95em; }}
        .filter-tags {{ display: flex; gap: 5px; flex-wrap: wrap; }}
        .tag-btn {{ background: var(--tag-bg); border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; color: var(--tag-text); font-weight: 600; transition: all 0.2s; }}
        .tag-btn:hover {{ opacity: 0.85; }}
        .tag-btn.active {{ background: var(--tag-active-bg); color: var(--tag-active-text); }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background-color: var(--th-bg); color: var(--th-text); text-align: left; padding: 10px; font-size: 0.9em; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid var(--border-color); vertical-align: top; font-size: 0.95em; }}
        tr:hover {{ background-color: var(--tr-hover); }}
        .date-badge {{ background-color: var(--tag-active-bg); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; white-space: nowrap; }}
        .date-end {{ display: block; margin-top: 4px; font-size: 0.8em; color: var(--text-muted); white-space: nowrap; }}
        .location {{ font-weight: bold; color: var(--location-color); }}
        .badge-new {{ background: #27ae60; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 6px; vertical-align: middle; }}
        .badge-stale {{ background: #f39c12; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 6px; vertical-align: middle; }}
        a.btn {{ display: inline-block; background-color: var(--btn-bg); color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; }}
        a.btn:hover {{ background-color: var(--btn-hover); }}
        .no-results {{ display: none; padding: 20px; text-align: center; color: var(--text-muted); font-style: italic; }}
    
        .filter-group {{ display: flex; flex-direction: column; gap: 6px; }}
        .filter-group-label {{ font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 700; }}
        .filter-row {{ display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; background: var(--filter-bg); padding: 15px; border-radius: 6px; border: 1px solid var(--filter-border); }}
        .badge-laufend {{ background: #8e44ad; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 6px; vertical-align: middle; }}
        .reset-btn {{ background: none; border: 1px solid var(--input-border); color: var(--text-muted); padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }}
        .reset-btn:hover {{ color: var(--text-main); }}
</style>
</head>
<body>
    <div class="container">
        <div class="header-bar">
            <h1>Sepulkralkultur &amp; Friedhofskultur</h1>
            <button class="theme-toggle-btn" onclick="toggleTheme()">
                <span id="themeIcon">&#127769;</span>
                <span id="themeLabel">Dunkel</span>
            </button>
        </div>
        <div class="timestamp">Stand: {timestamp} &nbsp;|&nbsp;
            <span id="visibleCount">{total}</span> von {total} Terminen</div>

        <div class="filter-row">
            <input type="text" id="searchInput" class="search-input"
                   placeholder="Suchen nach Ort, Titel, Stichwort &hellip;"
                   onkeyup="applyFilters()">

            <div class="filter-group">
                <span class="filter-group-label">Zeitraum</span>
                <div class="filter-tags">
                    <button class="tag-btn active" data-group="zeit" data-value="" onclick="setFilter(this)">Alle</button>
                    <button class="tag-btn" data-group="zeit" data-value="7" onclick="setFilter(this)">N&auml;chste 7 Tage</button>
                    <button class="tag-btn" data-group="zeit" data-value="30" onclick="setFilter(this)">N&auml;chste 30 Tage</button>
                    <button class="tag-btn" data-group="zeit" data-value="90" onclick="setFilter(this)">N&auml;chste 3 Monate</button>
                </div>
            </div>

            <div class="filter-group">
                <span class="filter-group-label">Region</span>
                <div class="filter-tags">
                {region_buttons}
                </div>
            </div>

            <div class="filter-group">
                <span class="filter-group-label">Art</span>
                <div class="filter-tags">
                {type_buttons}
                </div>
            </div>

            <div>
                <button class="reset-btn" onclick="resetFilters()">Filter zur&uuml;cksetzen</button>
            </div>
        </div>

        <div id="noResults" class="no-results">Keine Termine f&uuml;r diese Auswahl.</div>
"""

    if enriched:
        html_content += """
        <table id="eventsTable">
            <thead>
                <tr>
                    <th>Datum</th>
                    <th>Titel</th>
                    <th>Ort</th>
                    <th>Beschreibung</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody>
"""
        for event, tags in enriched:
            date_s = html.escape(event.get("date_start", ""))
            end_raw = event.get("date_end") or ""
            title_s = html.escape(event.get("title", ""))
            loc_s = html.escape(event.get("location", ""))
            desc_s = html.escape(event.get("description", ""))

            # Nur http/https ins href - html.escape verhindert kein javascript:
            raw_url = str(event.get("url") or "")
            url_s = (html.escape(raw_url)
                     if raw_url.startswith(("http://", "https://")) else "#")

            end_html = (f'<span class="date-end">bis {html.escape(end_raw)}</span>'
                        if end_raw else "")

            badges = ""
            if end_raw:
                badges += '<span class="badge-laufend">l&auml;uft</span>'
            if event.get("first_seen") == today_str:
                badges += '<span class="badge-new">neu</span>'
            last_seen = event.get("last_seen")
            if last_seen:
                try:
                    age = (today - date.fromisoformat(last_seen)).days
                    if age > STALE_AFTER_DAYS:
                        badges += ('<span class="badge-stale">seit '
                                   f'{age} Tagen nicht best&auml;tigt</span>')
                except ValueError:
                    pass

            html_content += f"""
                <tr data-tags="{' '.join(tags)}" data-start="{date_s}" data-end="{html.escape(end_raw)}">
                    <td><span class="date-badge">{date_s}</span>{end_html}</td>
                    <td><strong>{title_s}</strong>{badges}</td>
                    <td class="location">{loc_s}</td>
                    <td>{desc_s}</td>
                    <td><a href="{url_s}" target="_blank" rel="noopener noreferrer" class="btn">&ouml;ffnen</a></td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""
    else:
        html_content += "<p>Derzeit keine bevorstehenden Termine in der Datenbank.</p>"

    html_content += """
    </div>

    <script>
        const filters = { zeit: '', region: '', art: '' };

        function initTheme() {
            if (localStorage.getItem('theme') === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
                document.getElementById('themeIcon').innerText = '\\u2600\\ufe0f';
                document.getElementById('themeLabel').innerText = 'Hell';
            }
        }

        function toggleTheme() {
            const dark = document.documentElement.getAttribute('data-theme') === 'dark';
            if (dark) {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                document.getElementById('themeIcon').innerText = '\\ud83c\\udf19';
                document.getElementById('themeLabel').innerText = 'Dunkel';
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                document.getElementById('themeIcon').innerText = '\\u2600\\ufe0f';
                document.getElementById('themeLabel').innerText = 'Hell';
            }
        }

        function setFilter(btn) {
            const group = btn.getAttribute('data-group');
            filters[group] = btn.getAttribute('data-value');
            document.querySelectorAll('.tag-btn[data-group="' + group + '"]')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            applyFilters();
        }

        function resetFilters() {
            Object.keys(filters).forEach(k => filters[k] = '');
            document.querySelectorAll('.tag-btn').forEach(b => {
                b.classList.toggle('active', b.getAttribute('data-value') === '');
            });
            document.getElementById('searchInput').value = '';
            applyFilters();
        }

        // Ein Termin liegt im Zeitfenster, wenn er es ueberlappt. Damit
        // erscheinen laufende Ausstellungen auch in "Naechste 7 Tage", obwohl
        // ihr Startdatum lange zurueckliegt.
        function inWindow(row, days) {
            if (!days) return true;
            const start = row.getAttribute('data-start');
            const end = row.getAttribute('data-end') || start;
            const today = new Date();
            const limit = new Date();
            limit.setDate(limit.getDate() + parseInt(days, 10));
            const iso = d => d.toISOString().slice(0, 10);
            return start <= iso(limit) && end >= iso(today);
        }

        function applyFilters() {
            const term = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#eventsTable tbody tr');
            let visible = 0;

            rows.forEach(row => {
                const tags = row.getAttribute('data-tags');
                const ok =
                    (!term || row.innerText.toLowerCase().includes(term)) &&
                    (!filters.region || tags.includes('region-' + filters.region)) &&
                    (!filters.art || tags.includes('art-' + filters.art)) &&
                    inWindow(row, filters.zeit);
                row.style.display = ok ? '' : 'none';
                if (ok) visible++;
            });

            document.getElementById('visibleCount').innerText = visible;
            document.getElementById('noResults').style.display =
                (visible === 0 && rows.length > 0) ? 'block' : 'none';
        }

        initTheme();
    </script>
</body>
</html>
"""

    with open(HTML_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)


# ---------------------------------------------------------------- Hauptlauf

if __name__ == "__main__":
    today = datetime.now(BERLIN).date()
    today_str = today.isoformat()

    raw_db = load_events_db()
    print(f"Bestand geladen: {len(raw_db)} Roh-Events")

    events_db = deduplicate_db(raw_db)
    print(f"Nach Initial-Deduplizierung: {len(events_db)} eindeutige Events")

    print(f"\n--- Phase 1: Webseiten laden ({len(TARGET_URLS)} Quellen) ---")
    if DISABLED_URLS:
        print(f"    ({len(DISABLED_URLS)} Quellen sind deaktiviert, siehe DISABLED_URLS)")

    fetched_pages = []
    problems: dict[str, list[str]] = defaultdict(list)

    with make_http_client() as client_http:
        for url in TARGET_URLS:
            try:
                page_text = fetch_page_text(client_http, url)
            except Exception as e:
                kind = classify_error(e)
                problems[kind].append(url)
                print(f"  FEHLER  {kind:<24} {url}")
                continue

            if not is_worth_sending(url, page_text):
                # is_worth_sending protokolliert den Grund bereits selbst
                reason = ("zu kurz" if len(page_text) < MIN_TEXT_LENGTH
                          else "kein Datum")
                problems[reason].append(url)
                continue

            condensed, hits = condense_text(page_text, TEXT_LIMIT)
            if len(condensed) < len(page_text):
                print(f"  {len(page_text):>7} -> {len(condensed):>5} Zeichen, "
                      f"~{hits} Fundstellen  {url}")
            else:
                print(f"  {len(page_text):>7} Zeichen, ~{hits} Fundstellen  {url}")
            fetched_pages.append((url, condensed, hits))

    selected, deferred = select_within_budget(
        fetched_pages, today.toordinal(), MAX_REQUESTS_PER_RUN
    )
    batches = pack_batches(selected)

    if deferred:
        print(f"\n  {len(deferred)} Quellen passen nicht ins Request-Budget "
              f"({MAX_REQUESTS_PER_RUN}) und kommen in einem spaeteren Lauf dran:")
        for url, _, _ in deferred:
            problems["auf spaeteren Lauf verschoben"].append(url)
            print(f"    {url}")

    print(f"\n{len(selected)} von {len(fetched_pages)} Seiten gehen an die API "
          f"in {len(batches)} Paketen (Budget: {MAX_REQUESTS_PER_RUN})")

    print("\n--- Phase 2: KI-Analyse ---")
    stats = Counter()
    for number, batch in enumerate(batches, start=1):
        print(f"\nPaket {number}/{len(batches)} ({len(batch)} Seiten, "
              f"{sum(len(t) for _, t in batch)} Zeichen)")

        events = call_with_retry(batch, today_str)
        print(f"  {len(events)} Events extrahiert")

        for event in events:
            parsed_start = parse_date(event.get("date_start", ""))
            if parsed_start is None:
                print(f"  verworfen (Datum unlesbar '{event.get('date_start')}'): {event.get('title')}")
                stats["datum_ungueltig"] += 1
                continue
            event["date_start"] = parsed_start
            event["date_end"] = parse_date(event.get("date_end") or "")

            relevant = event["date_end"] or event["date_start"]
            if relevant < today_str:
                stats["vergangen"] += 1
                continue

            duplicate_key = find_duplicate_key(event, events_db)
            if duplicate_key:
                event["first_seen"] = today_str
                event["last_seen"] = today_str
                merge_into(events_db[duplicate_key], event)
                events_db[duplicate_key]["last_seen"] = today_str
                stats["aktualisiert"] += 1
            else:
                event["first_seen"] = today_str
                event["last_seen"] = today_str
                events_db[generate_event_id(event)] = event
                stats["neu"] += 1

        if number < len(batches):
            time.sleep(API_PAUSE_SECONDS)

    # Zweite Deduplizierung als Sicherheitsnetz: innerhalb EINES Laufs koennen
    # zwei Pakete dasselbe Event liefern (z. B. Dachseite und Einzelfriedhof),
    # ohne dass find_duplicate_key das beim Eintragen schon sehen konnte.
    before_dedup = len(events_db)
    events_db = deduplicate_db(events_db)
    stats["zusammengefuehrt"] = before_dedup - len(events_db)

    cleaned_db = {}
    for event_id, event in events_db.items():
        relevant = event.get("date_end") or event.get("date_start", "")
        if relevant >= today_str:
            cleaned_db[event_id] = event
    stats["entfernt"] = len(events_db) - len(cleaned_db)

    save_events_db(cleaned_db)
    render_html(list(cleaned_db.values()), today)

    print("\n--- Zusammenfassung ---")
    print(f"  neu:            {stats['neu']}")
    print(f"  aktualisiert:   {stats['aktualisiert']}")
    print(f"  Datum ungueltig:{stats['datum_ungueltig']}")
    print(f"  vergangen:      {stats['vergangen']}")
    print(f"  zusammengefuehrt:{stats['zusammengefuehrt']}")
    print(f"  DB bereinigt:   {stats['entfernt']} entfernt")
    print(f"\n{len(cleaned_db)} aktive Events in '{HTML_OUTPUT_FILE}' geschrieben.")

    if problems:
        print("\n--- Quellen ohne Ertrag ---")
        for kind in sorted(problems):
            urls = problems[kind]
            print(f"\n  {kind} ({len(urls)}):")
            for url in urls:
                print(f"    {url}")
        total = sum(len(v) for v in problems.values())
        print(f"\n  {total} von {len(TARGET_URLS)} Quellen haben nichts geliefert.")