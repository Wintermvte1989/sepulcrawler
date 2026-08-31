import os
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
    "https://domspatzen.de/veranstaltungen/",

    # --- Landeshauptstadt Stuttgart & Baden-Württemberg ---
    "https://www.freiburger-muenster.de/",

    # --- Landeshauptstadt Düsseldorf & NRW ---
    "https://www.duesseldorf.de/stadtgruen/freizeit/fuehrungen1",
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
    "https://www.stephansdom.at/",
    "https://www.stift-stpeter.at/de/kloster/index.asp?dat=Friedhof-Katakomben",
    "https://www.stiftadmont.at/",
    "https://www.hallstatt.net/",
    "https://kulturzueri.ch/db/veranstalter/veranstalter-profile/friedhof-forum/",
    "https://www.stadtgaertnerei.bs.ch/friedhoefe/veranstaltungen.html",
    "https://www.stiftsbezirk.ch/de/veranstaltungen",
    "https://www.museum-aargau.ch/schloss-lenzburg/event-kalender",
    "https://www.silent-green.net/programm/",
    "https://www.bestattungsmuseum.at/",
    "https://www.bestattungwien.at/veranstaltungen",

    # --- Medizin- und koerpergeschichtliche Sammlungen ---
    "https://bmm-charite.de/ausstellungen",

    # --- Berlin & Brandenburg Ergänzungen ---
    "https://berlin.volksbund.de/aktuell/termine",
    "https://www.efeu-ev.com/",
    "https://www.zwoelf-apostel-berlin.de/alle-termine-der-zwolf-apostel-kirchengemeinde-und-der-kirchhofe",
    "https://forum1848.de/veranstaltungen/",
    "https://www.garnisonfriedhof-berlin.de/",
    "https://www.berlinerdom.de/termine/",
    "https://www.bornstedter-friedhof.de/bornstedter-friedhof/historische-graeber/fuehrungen/termine-fuer-fuehrungen/",
    "https://www.friedhof-in-potsdam.de/allgemeines/aktuelles",
    "https://www.stift-neuzelle.de/",
    "https://bjoern-schulz-stiftung.de/akademie/",
    "https://tickets.jmberlin.de/events/",
    "https://www.zitadelle-berlin.de/en/education/events/",

    # --- Deutschland übrige ---
    "https://landesmuseum-bonn.lvr.de/",
    "https://www.alm-bw.de/",
    "https://roemisch-germanisches-museum.de/",
    "https://www.frauenkirche-dresden.de/kalender/",
    "https://www.florian-scheungraber.de/termine/",
    "https://www.leipzig-im.de/index.php?auswahl=Veranstaltungen&section=home",
    "https://www.stadtgeschichtliches-museum-leipzig.de/ausstellungen/aktuelle-ausstellungen/",

    # --- Tschechien, Österreich, Schweiz ---
    "https://praha-vysehrad.cz/en/",
    "https://www.friedhoefewien.at/veranstaltungen",
    "https://www.friedhoefewien.at/friedhofsfuehrungen",
    "https://www.stadtluzern.ch/dienstleistungeninformation/159",
    # --- Ergaenzt am 26.08.2026, gezielt fuer die Luecken Sueden und AT/CH ---
    # Alle Adressen stammen aus Suchergebnissen mit sichtbaren Terminangaben,
    # keine abgeleiteten Pfade.

    # Kapuzinergruft Wien. Die .com-Domain ist im Lauf zweimal in ein Timeout
    # gelaufen; .at ist die betriebene Domain mit datierten Fuehrungen.

    # Friedhof Forum Zuerich. Die Uebersichtsseite ist JS-gerendert und
    # deaktiviert; diese Unterseite listet die Rundgaenge mit Datum im HTML.
    "https://www.stadt-zuerich.ch/friedhofforum/de/veranstaltungen/oeffentliche-rundgaenge-altes-krematorium.html",

    # Frauenstadtrundgang Zuerich, Ortsseite Friedhof Sihlfeld. Der Pfad
    # "/locations/" ist das Muster von "The Events Calendar" - dort greift
    # womoeglich die ICS-Erkennung aus feeds.py.

    # Friedhofsverwalter*innentagung des Museums fuer Sepulkralkultur.
    "https://www.sepulkralmuseum.de/fortbildung/friedhofsverwalterinnentagung-2026/",
    # --- Baden-Wuerttemberg (bisher gar nicht vertreten) ---
    # Karlsruhe hat eine eigene Friedhofsdomain; die zuvor eingetragene
    # Adresse unter karlsruhe.de lief in einen 404.
    "https://www.friedhof-karlsruhe.de/programm/fuehrungen-und-angebote.html",
    "https://www.friedhof-karlsruhe.de/home/aktuelle-termine/",
    "https://www.heidelberg.de/HD/Rathaus/bergfriedhof_+fuehrungen+und+spaziergaenge.html",

    # --- Oesterreich ausserhalb Wiens ---
    "https://www.barbarafriedhof.at/service-info/aktuelles/rueckblick/kulturgeschichtliche-friedhofsfuehrungen-2026",
    "https://www.linzag.at/portal/de/privatkunden/trauer/veranstaltungen",
    "https://www.kulturfuchs.at/friedhof/",
    # --- Themenportale mit eigenem Veranstaltungskalender ---
    # Aggregatoren: sie sammeln Termine ueber viele Veranstalter hinweg und
    # sind damit ergiebiger als eine einzelne Einrichtung.
    "https://trauergestalt.de/events/",
    "https://trauertaskforce.de/trauerwoche/",
    "https://blauerfalter.de/termine",

    # --- Medizin- und Koerpergeschichte ---
    # Deutsches Medizinhistorisches Museum Ingolstadt, Jahresausstellung 2026
    # "ALLES MUSS RAUS! Koerperliche Hinterlassenschaften".
    "https://www.dmm-ingolstadt.de/",
    # --- NRW: bisher fehlten Dortmund, Wuppertal, Bochum, Duisburg ---
    "https://www.fvwuppertal.de/angebote-veranstaltungen/angebote/veranstaltungen.html",
    "https://www.dortmund.de/rathaus/verwaltung/friedhoefe-dortmund/",

    # --- Nuernberg: eigener Verein fuer Epitaphienkultur, die Epitaphien der
    # Friedhoefe St. Johannis und St. Rochus sind immaterielles Kulturerbe ---
    "https://epitaphienkultur.de/veranstaltungen.html",
    "https://buergerverein-sankt-johannis.de/termine/",
    # --- Foerdervereine mit eigener Domain ---
    # Das Sepulkralmuseum listet ueber 30 solcher Vereine; sie sind die
    # ergiebigste Quellenart, weil sie eigene Terminseiten pflegen, waehrend
    # die Friedhofsverwaltungen der Grossstaedte im Stadtportal haengen.
    "https://www.historische-friedhoefe-osnabrueck.de/",
    "https://alterfriedhofschwerin.de/",
    # Mainzer Hauptfriedhof - Vorbild fuer den Pere-Lachaise in Paris,
    # Platz 3 der schoensten Friedhoefe Deutschlands.
    # --- Weitere Foerdervereine (Runde 2 der Beiratsliste) ---
    # Bonn, Platz 4 der schoensten Friedhoefe: Fuehrungen von Maerz bis
    # Oktober an JEDEM Samstag und Sonntag - entsprechend viele Termine.
    "https://www.alterfriedhofbonn.de/fuehrungen",
    "https://www.alter-friedhof-freiburg.de/aktuelles-veranstaltungen/",
    # --- ChurchDesk-Widget des Kirchlichen Friedhofsverbands Berlin ---
    # kkbs.de laedt seine Termine per iframe von widget.churchdesk.com nach.
    # Die Widget-Adresse selbst rendert SERVERSEITIG - der Umweg loest das
    # JS-Problem ohne Browser-Engine. 333 ist die Organisations-ID des
    # Verbands, evkd9VIgfKDV die Widget-Instanz, die Zahl dahinter die Seite
    # (je 5 Termine). Deshalb mehrere Seiten eintragen.
    "https://widget.churchdesk.com/w/333/event/evkd9VIgfKDV/0/1355280/-/-/-/-/-/or/list?frameId=evkd9VIgfKDV-1",
    "https://widget.churchdesk.com/w/333/event/evkd9VIgfKDV/1/1355280/-/-/-/-/-/or/list?frameId=evkd9VIgfKDV-1",
    "https://widget.churchdesk.com/w/333/event/evkd9VIgfKDV/2/1355280/-/-/-/-/-/or/list?frameId=evkd9VIgfKDV-1",
    # --- Am 27.08.2026 im Testcrawler geprueft und uebernommen ---
    # Grieneisen (AHORN-Gruppe, Berlin): 9268 Zeichen, ~35 Fundstellen,
    # 14 Events ohne eine einzige Verwerfung. Deckt Berliner Friedhoefe ab,
    # die sonst nirgends vorkommen: Waldfriedhof Zehlendorf und Heerstrasse,
    # Kuenstlerfriedhof Schoeneberg III, Luisenkirchhof III sowie die
    # Hohenzollerngruft unter dem Berliner Dom.
    "https://www.grieneisen.de/aktuelles",
    # Friedhof Forum Zuerich, Ausstellungen: 2419 Zeichen, ~4 Fundstellen.
    # Anders als die Schwesterseite /veranstaltungen.html NICHT JS-gerendert.
    "https://www.stadt-zuerich.ch/friedhofforum/de/ausstellungen.html",
    # --- Am 27.08.2026 im Testcrawler geprueft und uebernommen ---
    # Braunschweig: eigene Domain der Friedhofsverwaltung. Die zuvor
    # eingetragene Adresse unter braunschweig.de gab 404.
    "https://www.friedhofsverwaltung-braunschweig.de/termine",
    # Volksbund-Landesverbaende. Gleiches CMS und gleicher Pfad wie das
    # bereits laufende berlin.volksbund.de. Inhalt: Fuehrungen ueber
    # Kriegsgraeberstaetten, Volkstrauertag, Gedenkveranstaltungen.
    "https://saarland.volksbund.de/aktuell/termine",
    "https://bayern.volksbund.de/aktuell/termine",
    "https://hessen.volksbund.de/aktuell/termine",
    "https://niedersachsen.volksbund.de/aktuell/termine",
    # --- Volksbund-Landesverbaende, Runde 2 (Testlauf 27.08.2026) ---
    # Mit Terminen zum Zeitpunkt des Tests:
    "https://nrw.volksbund.de/aktuell/termine",
    "https://baden-wuerttemberg.volksbund.de/aktuell/termine",
    "https://rheinland-pfalz.volksbund.de/aktuell/termine",
    "https://sachsen.volksbund.de/aktuell/termine",
    "https://mecklenburg-vorpommern.volksbund.de/aktuell/termine",
    #
    # Diese sechs meldeten "Keine Termine gefunden" (162 Zeichen). Die
    # Landesverbaende und Seiten EXISTIEREN - sie haben nur gerade nichts
    # anstehen. Sie bleiben deshalb in der Liste: Der Laengenfilter sortiert
    # sie ohne API-Request aus, und sobald ein Termin erscheint, liefern sie
    # von selbst. "Zu kurz" heisst hier nicht "kaputt".
    "https://thueringen.volksbund.de/aktuell/termine",
    "https://brandenburg.volksbund.de/aktuell/termine",
    "https://sachsen-anhalt.volksbund.de/aktuell/termine",
    "https://hamburg.volksbund.de/aktuell/termine",
    "https://bremen.volksbund.de/aktuell/termine",
    "https://schleswig-holstein.volksbund.de/aktuell/termine",
    # Traegerverein der Dresdner Friedhoefe Johannis, Trinitatis und Neuer
    # Annenfriedhof. Im Testlauf vom 31.08.2026: die Feed-Erkennung fand
    # /veranstaltungen/?ical=1 von selbst - 23 Termine, keine Verwerfung,
    # kein API-Request.
    "https://johannisfriedhof-dresden.de/",
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
    # --- ergaenzt nach dem Lauf vom 25.08.2026 ---
    "https://www.evangelisch-stulrich.de/protestantischer-friedhof": "keine Termine auf der Seite",
    "https://www.vhs-augsburg.de/programm/gesellschaft/augsburg-stadtfuehrungen-und-fahrten/fuehrungen": "keine Termine im HTML",
    "https://www.landesmuseum-stuttgart.de/veranstaltungen/": "38 Zeichen, JS-gerendert",
    "https://www.karlsruhe.de/freizeit-und-sport/friedhoefe": "404 (25.08.2026)",
    "https://www.duesseldorf.de/stadtmuseum/veranstaltungen": "110 Zeichen, JS-gerendert",
    "https://www.umweltbetrieb-bremen.de/friedhoefe/fuehrungen-und-veranstaltungen-11442": "16 Zeichen, JS-gerendert",
    "https://www.bernermuenster.ch/": "230 Zeichen, JS-gerendert",
    "http://www.wienfuehrungen.com/morbide-fuehrungen.html": "Katalog ohne Termine; Terminseite verweist auf PDF von 2011",
    "https://www.josephinum.ac.at/veranstaltungen/": "keine Termine im HTML",
    "https://denkmaltag.berlin.de/": "145 Zeichen, JS-gerendert",
    "https://www.kkbs.de/veranstaltungen/veranstaltungen-auf-friedhofen": "Termine per ChurchDesk-Widget, kein HTML",
    "https://stpetri-stmarien.de/": "DNS unbekannt (25.08.2026)",
    "https://www.berlin.de/museum-pankow/aktuelles/veranstaltungen/": "300 Zeichen, JS-gerendert",
    "https://www.villa-oppenheim-berlin.de/": "147 Zeichen, JS-gerendert",
    "https://www.dhm.de/programm/veranstaltungskalender/": "232 Zeichen, JS-gerendert",
    "https://jmaugsburg.de/fuehrungen/": "keine Termine im HTML",
    "https://www.brnenskepodzemi.cz/": "0 Zeichen, vollstaendig JS-gerendert",
    "https://www.michaelerkirche.at/": "0 Zeichen, vollstaendig JS-gerendert",
    "https://www.bern.ch/politik-und-verwaltung/stadtverwaltung/tvs/stadtgrun-bern/friedhofe/friedhofkultur": "404 (25.08.2026)",
    "https://www.vssg.ch/de/arbeitsgruppen/friedhoefe-alles/tag-des-friedhofs.html": "404 (25.08.2026)",
    # --- ergaenzt nach dem Lauf vom 26.08.2026 ---
    "https://www.kaisergruft.com/": "Timeout in zwei Laeufen (26.08.2026)",
    "https://www.kaisergruft.at/site/de/home/familienfuehrungen": "Timeout, Domain vom Runner nicht erreichbar",
    "https://www.kaisergruft.com/fuehrungen": "Timeout, Domain vom Runner nicht erreichbar",
    "https://frauenstadtrundgangzuerich.ch/locations/friedhof-sihlfeld-a-aemtlerstrasse-151-haupteingang/": "243 Zeichen, JS-gerendert",
    "https://kunstundreisen.com/friedhoffuhrungen-in-stuttgart/": "Leistungsbeschreibung ohne Termine",
    "https://bv-trauerbegleitung.de/veranstaltungskalender/": "Kalender JS-gerendert, keine Termine im HTML",
    # --- ergaenzt nach dem Lauf vom 27.08.2026 ---
    "https://st-johannisfriedhof-nuernberg.de/fuehrungen/": "0 Zeichen, vollstaendig JS-gerendert",
    "https://stiftung-historische-friedhoefe.de/fuhrungen-und-veranstaltungen/": "HTTP 503 in zwei Laeufen",
    "https://www.fof-ohlsdorf.de/": "HTTP 403 - Bot-Sperre (26.08.2026)",
    "http://www.nekropolis-moguntia.de/info.html": "HTTP 404 - Seite existiert nicht mehr",
    "https://alterfriedhofbonn.de/": "Startseite ohne Termine; /fuehrungen liefert 13 Fundstellen",
    "https://www.friedhof-mannheim.de/graeber/foerderkreis/": "Vereinsseite ohne Termine",
    # --- Testcrawler 27.08.2026 ---
    "https://zuercher-museen.ch/museen/friedhof-forum-museum-ueber-leben-und-tod": "180 Zeichen, JS-gerendert",
    # --- Testcrawler 27.08.2026 ---
    "https://friedhoefe.saarbruecken.de/": "Startseite ohne Termine (Grabarten, Urnenwaende)",
    "https://nordrhein-westfalen.volksbund.de/aktuell/termine": "Subdomain existiert nicht - andere Schreibweise pruefen",
    "https://westfalen.volksbund.de/aktuell/termine": "Subdomain existiert nicht; nrw.volksbund.de deckt NRW ab",
    # --- Testcrawler 31.08.2026 ---
    "https://www.anima-et-mors.de/termine/": "HTTP 403, Cloudflare-Sperre - Termin steht in MANUAL_EVENTS",
    "https://www.anima-et-mors.de/": "HTTP 403, Cloudflare-Sperre - Termin steht in MANUAL_EVENTS",
    # --- Geprueft und bewusst NICHT aufgenommen (31.08.2026) ---
    # Alle listen "Anima et Mors" korrekt, sind aber allgemeine Stadt- oder
    # Ticketportale: unser Thema ist dort ein Bruchteil des Bestands. Sie
    # aufzunehmen waere der Oppenheim-Fehler - viele Requests, fast alles
    # vom Themenfilter verworfen.
    "https://prinz.de/dresden/events/": "allgemeines Stadtportal, Thema ist Randerscheinung",
    "https://veranstaltungen.meinestadt.de/dresden/": "allgemeines Stadtportal",
    "https://www.eventim.de/": "Ticketportal, kein thematischer Bezug",
    "https://www.ticketonline.de/": "Ticketportal, kein thematischer Bezug",
    # --- Testcrawler 31.08.2026: Umwege um die Cloudflare-Sperre ---
    # Beide gescheitert. Damit bleibt MANUAL_EVENTS der Weg fuer Termine
    # dieser Veranstalterin - eine automatische Quelle gibt es nicht.
    "https://anima-pluma.de/": "TLS-Handshake schlaegt fehl, trotz tolerantem SSL-Kontext",
    "https://www.eventim-light.com/de/a/69662e7995a245200db2f1f0": "0 Zeichen, vollstaendig JS-gerendert (SPA)",
}

DB_FILE = os.environ.get("SEPULKRAL_DB_FILE", "events_db.json")
HTML_OUTPUT_FILE = "index.html"

# Diagnosedatei: alle thematisch verworfenen Events mit vollem Kontext.
# Bewusst NICHT im Repository - wird im Workflow als Artefakt hochgeladen.
# ---------------------------------------------------------------- Kandidaten
#
# Zweigleisiger Betrieb: Neue Quellen kommen ZUERST hier hinein, nicht in
# TARGET_URLS. Der Testcrawler (test_run.py) crawlt nur diese Liste und
# schreibt in eigene Dateien. Der Hauptlauf und die veroeffentlichte
# index.html bleiben davon unberuehrt.
#
# Ablauf:
#   1. Neue Adresse hier eintragen
#   2. test_run.py laufen lassen (lokal oder ueber den Workflow
#      "Sepulkral Crawler TEST")
#   3. test_events_db.json ansehen: kommen brauchbare Termine?
#   4. Wenn ja: Adresse nach TARGET_URLS verschieben und hier entfernen
#      Wenn nein: mit Begruendung nach DISABLED_URLS
# ---------------------------------------------------------------- Handpflege
#
# Termine von Seiten, die der Crawler nicht erreicht - etwa hinter einer
# Cloudflare-Sperre. Sie laufen durch dieselbe Verarbeitung wie alle
# anderen: Datumspruefung, Themenfilter, Deduplizierung.
#
# Bewusst sparsam halten. Abgelaufene Eintraege werden vom Crawler NICHT
# still weiterverarbeitet: main.py prueft beim Start das Datum, ueberspringt
# vorbeigelaufene Eintraege und weist im Log und in der Zusammenfassung
# darauf hin, dass sie hier geloescht werden koennen. Der Crawler kann
# config.py nicht selbst umschreiben - das bleibt ein Handgriff, aber man
# muss nicht daran denken.
MANUAL_EVENTS: list[dict] = [
    {
        "title": "ANIMA ET MORS \u2013 Kleinmesse \u00fcber Leben und Tod",
        "date_start": "2026-10-31",
        "date_end": None,
        "location": "Trinitatisfriedhof, Fiedlerstra\u00dfe 1, 01307 Dresden",
        "description": (
            "Dresdens erste Kleinmesse zu den Themen selbstbestimmtes Leben, "
            "selbstbestimmtes Sterben und LebensWert, mit Ausstellern, "
            "Vortr\u00e4gen, Lesungen und Mitmachangeboten. 10-18 Uhr."
        ),
        "url": "https://www.anima-et-mors.de/",
    },
]


CANDIDATE_URLS: list[str] = [
    # Hier kommen neue Adressen zum Ausprobieren hinein, zum Beispiel:
    # "https://www.beispiel-friedhof.de/veranstaltungen/",
]






# Eigene Dateien fuer den Testlauf. Sie tauchen NICHT im Workflow-Commit auf
# und ueberschreiben damit nie den echten Bestand.
TEST_DB_FILE = "test_events_db.json"
TEST_HTML_FILE = "test_index.html"
TEST_REJECTED_FILE = "test_verworfen.json"


# ---------------------------------------------------------------- Testmodus
#
# Ein voller Lauf kostet ~30 API-Requests. Zum Ausprobieren einer Aenderung
# ist das zu teuer, deshalb zwei Schalter ueber Umgebungsvariablen - kein
# eigener Branch noetig, derselbe Code laeuft lokal wie in Actions.
#
#   SEPULKRAL_TEST_URLS   Kommaliste von Suchbegriffen. Es werden nur die
#                         TARGET_URLS gecrawlt, die einen davon enthalten.
#   SEPULKRAL_DRY_RUN     "1" = kein einziger API-Request. Phase 1 laeuft
#                         vollstaendig (Abruf, Feeds, Verdichtung,
#                         Paketbildung), Phase 2 zeigt nur, was gesendet
#                         WUERDE. Kostet nichts.
#   SEPULKRAL_DB_FILE     Andere Datenbankdatei, damit ein Test den echten
#                         Bestand nicht anfasst.
#
# Beispiele (PowerShell):
#   $env:SEPULKRAL_DRY_RUN = "1"; python main.py
#   $env:SEPULKRAL_TEST_URLS = "eliasfriedhof,karlsruhe"; python main.py
#   Remove-Item Env:SEPULKRAL_TEST_URLS      # Testmodus wieder aus

TEST_URL_FILTER = [
    part.strip().lower()
    for part in os.environ.get("SEPULKRAL_TEST_URLS", "").split(",")
    if part.strip()
]
DRY_RUN = os.environ.get("SEPULKRAL_DRY_RUN", "") == "1"


def active_target_urls() -> list[str]:
    """Die tatsaechlich zu crawlenden Quellen - im Testmodus nur eine Auswahl."""
    if not TEST_URL_FILTER:
        return TARGET_URLS
    return [u for u in TARGET_URLS
            if any(part in u.lower() for part in TEST_URL_FILTER)]


REJECTED_FILE = "verworfen.json"

# Quellen, bei denen der ICS-Feed SCHLECHTER ist als die HTML-Seite.
# Der Feed von stadt-oppenheim.de ist der komplette Gemeindekalender:
# In zwei Laeufen lieferte er 30 bzw. 30 Termine, davon null brauchbare
# (Stadtrat, Wochenmarkt, Buergersprechstunde, Einkaufsfahrt). Gleichzeitig
# verdraengt er die HTML-Seite, die zuvor ~18 Datumsangaben hatte.
FEED_BLOCKLIST = {
    "www.stadt-oppenheim.de",
}

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
# Simulation (zu pessimistisch, echte Seiten sind duenner):
#   20 -> 33 Pakete | 25 -> 34 | 32 -> 40 | 50 -> 54 Pakete
#
# GEMESSEN im Lauf vom 25.08.2026: bei 25 wurden nur 22 von 40 Paketen
# gebraucht, dabei waren ~22 Seiten am Deckel abgeschnitten - darunter
# suedwestkirchhof.de (6422 -> 2349 Zeichen), friedhof-hamburg.de und
# ohlsdorf-derpark.de. Der Deckel warf also Tiefe weg, ohne dass das
# Budget knapp war.
#
# Mit den echten Seitengroessen nachgerechnet (Simulation liefert 32 Pakete,
# wo real 22 gemessen wurden - sie ueberschaetzt um rund 45 %):
#   25 -> 32 Pakete simuliert  |  30 -> 36  |  35 -> 39  |  45 -> 44 (reisst)
# 35 liegt simuliert noch unter der Grenze, real also mit Reserve.
# Erscheint im Log "Quellen passen nicht ins Request-Budget", auf 30 senken.
#
# Wer hoeher gehen will, muss MAX_REQUESTS_PER_RUN mit anheben; das Limit
# von 50 Requests pro Lauf gilt inklusive Retries.
MAX_HITS_PER_PAGE = 35
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
                    "museumstag", "aktionstag", "aktionswoche", "sommerfest",
                    # Publikumsmessen. Als Komposita, weil das kurze "messe"
                    # in der Kategorie gottesdienst die katholische Messe
                    # meint. "Kleinmesse ueber Leben und Tod" wurde sonst
                    # ueber die Beschreibung zur "Lesung".
                    "kleinmesse", "fachmesse", "publikumsmesse",
                    "informationsmesse", "infomesse", "bestattermesse",
                    "messetag")),
)

_TYPE_MIN_SUBSTRING = 6
TITLE_RATIO_THRESHOLD = 0.88
TOKEN_JACCARD_THRESHOLD = 0.60

# Ab dieser Titellaenge gilt "ein Titel steckt im anderen" als Duplikat.
# 12 Zeichen halten generische Titel wie "Fuehrung" (7) draussen.
SUBSTRING_MIN_LENGTH = 12

# ---------------------------------------------------------------- Themenfilter
#
# Zweite Verteidigungslinie hinter dem Prompt. Der Prompt allein reicht nicht:
# ein Ortskriterium ("Veranstaltung an einem Museum oder einer Kirche") laesst
# jedes Orgelkonzert und jede Stadtfuehrung durch. Hier wird geprueft, ob
# Titel, Beschreibung ODER Ort einen echten sepulkralen Bezug haben.
#
# Regel: entweder ein Themenwort (TOPIC_PATTERN) oder ein Ort, der schon
# durch seine Art zum Thema gehoert (VENUE_PATTERN).
#
# Vorsicht bei kurzen Staemmen:
#  - "grab" als Substring trifft "Ausgrabung"/"ausgegraben" - deshalb nur
#    ausgeschriebene Komposita und Wortanfaenge (\b).
#  - "tot" als Wortanfang trifft "total" - deshalb "tote", "toten", "tod".
#  - "gedenk" allein trifft jede Gedenkstaette, auch politische - deshalb nur
#    die konkreten Formen (gedenkfeier, gedenkkultur, totengedenken ...).
TOPIC_PATTERN = re.compile(
    r"""(?:
        friedhof | friedhöf | kirchhof | kirchhöf
      | grabstätte | grabmal | grabkunst | grabstein | grabdenkmal
      | grabanlage | grabkammer | grabschatz | grabschätze | grabes
      | grabfund | grablege | ehrengrab | ehrengräb
      | \bgrab\b | \bgräber | \bgrabe\b | \bgräbern
      | gruft | grüfte | mausoleum | mausoleen | beinhaus | ossuar
      | kolumbarium | urnen | \bsarg | \bsärge | \bsarko
      | bestattung | begräbnis | beisetzung | sepulkral | sepulchral
      | epitaph | krematorium | feuerbestattung | erdbestattung
      | einäscherung
      | trauer | hinterbliebene | kondolenz | beileid
      | sterbebegleitung | sterbende | \bsterben | \bsterbe
      | hospiz | palliativ | \bverstorben | \bverstarb
      | \btod | \btote | \btoten | \btotes | totengedenk | totentanz
      | volkstrauertag | ewigkeitssonntag | totensonntag | allerheiligen
      | allerseelen | requiem | seelenmesse | gedenkkultur
      | gedenkfeier | gedenkveranstaltung | kranzniederlegung
      | mumie | mumien | skelett | gebeine | \bknochen
      | vergänglichkeit | memento\s+mori | vanitas | jenseits
      | nachlass | kriegsgräber | \bgefallenen | mahnmal | ehrenmal
      | holocaust | schoah | \bleichen | aufbahrung | aussegnung
      | totenkult | ruhestätte | ruhestätten | nekropol | katakombe
      # Vorsorge und letzter Wille - eigenes Feld der Bestattungskultur.
      # "testament" bewusst NICHT: das traefe auch "Altes Testament" in
      # jeder Bibelveranstaltung.
      | bestattungsvorsorge | vorsorgeplanung | vorsorgevollmacht
      | patientenverfügung | patientenverfuegung | letztwillig
      | lebensende | letzte\s+hilfe | vermächtnis | vermaechtnis
      | \bgestorben | \bverwaist | \bwaisen | sternenkind
      | totgeburt | fehlgeburt | \bverwitwet
      | hinterlassenschaft | präparat | praeparat | obduktion
      | pathologisch | \bsezier | einbalsamier | moulage
      | sterblichkeit | endlichkeit | abschiednehmen | trauerrede
      | grabrede | urnenhain | friedwald | ruheforst | gedenkstein
      | \bwiedergänger | \breliquie | anatomisch | \banatomie
      | seelenheil | fegefeuer | \bhinrichtung | \bmassengrab
      | \bmassengräber | kannibal | einbalsam | leichnam
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Einzelne Bestattungen. Manche Friedhofsverwaltungen veroeffentlichen ihre
# Belegungsplaene: "Beisetzung Petra Pucelik-Guenther", "Trauerfeier fuer
# Vladimir Afonichev". Das sind keine oeffentlichen Veranstaltungen, und die
# Namen frisch Verstorbener gehoeren nicht in einen bundesweiten
# Kulturkalender - die Verwaltung stellt sie fuer Angehoerige und Trauergaeste
# online, nicht zur Weiterverbreitung.
#
# Erkennungsmerkmal: Der Titel BEGINNT mit der Bestattungsart und es folgt
# ein grossgeschriebener Name. Das trennt sie von Veranstaltungen, die
# dieselben Woerter enthalten:
#   "Redner-Workshop: Zweisprachige Trauerfeiern"          -> bleibt
#   "Gottesdienst und Festakt zur Wiederbeisetzung Ottos"  -> bleibt
#   "Gedenkfeier fuer einsam Verstorbene"                  -> bleibt
PERSONAL_FUNERAL_PATTERN = re.compile(
    r"""^\s*
        # Bestattungsart - Gross-/Kleinschreibung hier egal. Das \b am Ende
        # ist entscheidend: ohne es matcht "Beisetzung" auch in
        # "Beisetzungsformen im Wandel", einem Vortragstitel.
        (?i:(?:urnen|erd|feuer|see|baum)?\s*
            (?:beisetzung | bestattung | trauerfeier | beerdigung |
               trauerandacht | aussegnung))\b
        \s* (?i:f\u00fcr|von)? \s*
        # Personenname: hier MUSS gross geschrieben sein, deshalb steht
        # re.IGNORECASE nicht in den Flags, sondern nur oben in den Gruppen.
        [A-Z\u00c4\u00d6\u00dc][\w\u00e4\u00f6\u00fc\u00df-]+
        \s+ [A-Z\u00c4\u00d6\u00dc]
    """,
    re.VERBOSE,
)

# Orte, die durch ihre Art zum Thema gehoeren. Eine Veranstaltung in einer
# Friedhofskapelle ist relevant, auch wenn der Titel es nicht verraet
# (z. B. "Aufwind - Chor fuer trauernde Menschen" an der KapelleDREI).
VENUE_PATTERN = re.compile(
    r"""(?:
        friedhof | friedhöf | friedhoef | kirchhof | kirchhöf | kirchhoef
      | beinhaus | krematorium | hospiz | kolumbarium
      | gruft | grüfte | gruefte
      | aussegnungshalle | trauerhalle | palliativ | katakombe
      | sepulkralmuseum | bestattungsmuseum | friedhofforum | epitaph
      # Volksbund Deutsche Kriegsgraeberfuersorge - durch seinen Gegenstand
      # einschlaegig, unabhaengig vom einzelnen Titel.
      | volksbund | kriegsgräber | kriegsgraeber
      # "trauer" wirkt vor allem auf Quell-Domains (bv-trauerbegleitung.de,
      # trauergestalt.de, trauertaskforce.de) - solche Anbieter sind durch
      # ihren Gegenstand einschlaegig. In Ortsangaben trifft es
      # "Trauerhalle" und "Trauercafe", was ebenfalls passt.
      | trauer
    )""",
    re.IGNORECASE | re.VERBOSE,
)
# Hinweis: Das Muster wird auch auf URLs angewandt, und dort stehen
# Umlaute transliteriert ("friedhoefe", "gruefte"). Die ASCII-Varianten
# muessen deshalb mit in die Liste.

REGIONS = (
    ("berlin-brandenburg", (
        "berlin", "stahnsdorf", "potsdam", "brandenburg", "weißensee",
        "weissensee", "liesenstraße", "liesenstrasse", "neukölln", "pankow",
        "hellersdorf", "spandau", "charlottenburg", "kreuzberg", "eberswalde",
        "neuzelle", "halbe",
        # Berliner Friedhoefe, deren Ortsangabe die Stadt nicht nennt.
        # "hallesch" steht bewusst VOR dem "halle saale" im Osten: das
        # Hallesche Tor liegt in Kreuzberg, nicht in Sachsen-Anhalt.
        "hallesch", "matthäus", "dorotheenstädtisch", "dreifaltigkeit",
        "heerstraße", "friedrichswerdersch", "invalidenfriedhof",
        "garnisonfriedhof", "südwestkirchhof", "stahnsdorf",
    )),
    ("nord", (
        "hamburg", "ohlsdorf", "kiel", "bremen", "lübeck", "luebeck",
        "schwerin", "hannover", "braunschweig", "doberan", "gottorf",
        "niedersachsen", "holstein", "mecklenburg",
        "schleswig", "flensburg", "rostock",
    )),
    ("west", (
        "köln", "koeln", "melaten", "frankfurt", "herne", "bonn",
        "düsseldorf", "duesseldorf", "münster", "muenster", "kassel",
        "xanten", "essen", "aachen", "mainz", "wiesbaden", "darmstadt",
        "trier", "speyer", "worms", "oppenheim", "saarbrücken",
        "osnabrück", "osnabrueck", "düren", "dueren", "siegen", "paderborn",
        "saarbruecken", "saarland", "nordrhein", "westfalen", "rheinland",
        "nrw", "pfalz",
        "dortmund", "bochum", "wuppertal", "duisburg",
        "oberhausen", "gelsenkirchen", "krefeld", "hagen", "bielefeld",
        "mönchengladbach", "moenchengladbach", "leverkusen", "solingen",
        # Domain nennt die Stadt nicht - Museum fuer Sepulkralkultur, Kassel.
        "sepulkralmuseum",
    )),
    ("ost", (
        # "halle" allein traf "Halleschen Tor" in Berlin - daher mit Zusatz.
        "leipzig", "dresden", "halle saale", "erfurt", "magdeburg", "naumburg",
        "sachsen", "thüringen", "thueringen", "anhalt",
        "chemnitz", "quedlinburg", "striesener", "eliasfriedhof", "görlitz",
        "goerlitz", "weimar", "jena",
    )),
    ("sued", (
        "münchen", "muenchen", "nürnberg", "nuernberg", "regensburg",
        "augsburg", "stuttgart", "ulm", "bamberg", "würzburg", "wuerzburg",
        "passau", "karlsruhe", "freiburg", "chammünster", "chammuenster",
        "bayern", "schwaben", "heidelberg", "tübingen", "tuebingen",
        "ingolstadt", "dmm-ingolstadt", "epitaphienkultur", "greding",
        "fürth", "fuerth", "erlangen",
        "mannheim", "konstanz", "baden",
    )),
    ("ausland", (
        "wien", "salzburg", "innsbruck", "graz", "admont", "hallstatt",
        "basel", "bern", "zürich", "zuerich", "st. gallen", "st.gallen",
        "luzern", "genf", "prag", "praha", "kutná hora", "kutna hora",
        "sedlec", "brno", "brünn", "bruenn", "österreich", "oesterreich",
        "schweiz", "tschechien",
        # Domains ohne Stadtnamen.
        "kaisergruft", "kapuzinergruft", "friedhoefewien", "bestattungwien",
        "linz", "barbarafriedhof", "linzag", "kulturfuchs", "klagenfurt",
        "winterthur", "biel", "chur",
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