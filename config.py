import re
from zoneinfo import ZoneInfo

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
    "https://www.silent-green.net/programm/",
    "https://www.bestattungsmuseum.at/",
    "https://www.bestattungwien.at/veranstaltungen",
    "http://www.wienfuehrungen.com/morbide-fuehrungen.html",

    # --- Medizin- und koerpergeschichtliche Sammlungen ---
    "https://bmm-charite.de/ausstellungen",
    "https://www.josephinum.ac.at/veranstaltungen/",

    # --- Berlin & Brandenburg Ergänzungen ---
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

    # --- Deutschland übrige ---
    "https://landesmuseum-bonn.lvr.de/",
    "https://www.alm-bw.de/",
    "https://roemisch-germanisches-museum.de/",
    "https://www.frauenkirche-dresden.de/kalender/",
    "https://www.florian-scheungraber.de/termine/",
    "https://www.leipzig-im.de/index.php?auswahl=Veranstaltungen&section=home",
    "https://www.stadtgeschichtliches-museum-leipzig.de/ausstellungen/aktuelle-ausstellungen/",
    "https://jmaugsburg.de/fuehrungen/",

    # --- Tschechien, Österreich, Schweiz ---
    "https://www.brnenskepodzemi.cz/",
    "https://praha-vysehrad.cz/en/",
    "https://www.michaelerkirche.at/",
    "https://www.friedhoefewien.at/veranstaltungen",
    "https://www.friedhoefewien.at/friedhofsfuehrungen",
    "https://www.bern.ch/politik-und-verwaltung/stadtverwaltung/tvs/stadtgrun-bern/friedhofe/friedhofkultur",
    "https://www.stadtluzern.ch/dienstleistungeninformation/159",
    "https://www.vssg.ch/de/arbeitsgruppen/friedhoefe-alles/tag-des-friedhofs.html",
]

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

BATCH_SIZE = 8
TEXT_LIMIT = 12000
# Gesenkt von 1500, damit JS-/Kompaktsammlungen nicht rausfliegen. Im
# bezahlten Tarif ist dieser Filter Kostenschutz, nicht mehr Budgetschutz:
# jede durchgelassene Seite belegt einen Batch-Platz und kostet Geld.
# Im Log pruefen, ob die kurzen Seiten tatsaechlich Events liefern
# (Abschnitt "Quellen ohne Ertrag") - sonst wieder anheben.
MIN_TEXT_LENGTH = 350
STALE_AFTER_DAYS = 10
API_ATTEMPTS = 3
FETCH_ATTEMPTS = 3
API_PAUSE_SECONDS = 0.5

SNIPPET_BEFORE = 200
SNIPPET_AFTER = 400

MAX_EVENTS_PER_BATCH = 55
# Obergrenze der Fundstellen aus EINER Seite. Der Wert steuert indirekt die
# Zahl der Requests: dichtere Seiten belegen mehr der MAX_EVENTS_PER_BATCH
# und es passen weniger Seiten pro Paket.
#
# Gemessen mit 144 Quellen und MAX_REQUESTS_PER_RUN = 40:
#   20 -> 33 Pakete, 100 % Abdeckung, 1582 Fundstellen
#   25 -> 34 Pakete, 100 % Abdeckung, 1782 Fundstellen   <- aktuell
#   32 -> 40 Pakete, 100 % Abdeckung, 2062 Fundstellen (kein Puffer)
#   50 -> 54 Pakete,  79 % Abdeckung - Quellen werden verschoben
#
# Wer hoeher gehen will, muss MAX_REQUESTS_PER_RUN mit anheben; das Limit
# von 50 Requests pro Lauf gilt inklusive Retries.
MAX_HITS_PER_PAGE = 25
MAX_REQUESTS_PER_RUN = 40

BERLIN = ZoneInfo("Europe/Berlin")

# Datums-Regex erweitert um ausgeschriebene Monatsnamen
DATE_PATTERN = re.compile(
    r"\b\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}\b"
    r"|\b\d{1,2}\.\s*\d{1,2}\.(?!\d)"
    r"|\b\d{1,2}\.?\s*(Jan|Feb|M\u00e4r|Mrz|Apr|Mai|Jun|Jul|Aug|Sep|Sept|Okt|Nov|Dez|Januar|Februar|M\u00e4rz|April|Juni|Juli|August|September|Oktober|November|Dezember)[a-z\u00e4\u00f6\u00fc]*\.?"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b(Mo|Di|Mi|Do|Fr|Sa|So)\.?,\s*\d{1,2}\."
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

STOP_WORDS = {
    "über", "durch", "nach", "beim", "eines", "einer", "einen", "einem",
    "mit", "und", "oder", "für", "vom", "auf", "dem", "den", "der", "die",
    "das", "des", "aus", "zum", "zur", "von", "im", "in", "am", "an", "bei",
    "sowie", "wird", "wie", "als", "auch", "sich", "ist", "sind", "uhr",
}

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

_TYPE_MIN_SUBSTRING = 6
TITLE_RATIO_THRESHOLD = 0.88
TOKEN_JACCARD_THRESHOLD = 0.60

# Ab dieser Titellaenge gilt "ein Titel steckt im anderen" als Duplikat.
# 12 Zeichen halten generische Titel wie "Fuehrung" (7) draussen.
SUBSTRING_MIN_LENGTH = 12

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