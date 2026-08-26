import html
from urllib.parse import urlparse
from collections import Counter
from datetime import datetime, date
import config
import database


def event_region(event: dict) -> str:
    """Grobe geografische Einordnung.

    Die Ortsangabe kommt vom Modell und nennt die Stadt oft nicht: aus
    "Alter St.-Matthaeus-Friedhof, Berlin" wird "Haupteingang des Alten
    St.-Matthaeus-Friedhofs". Deshalb dient die Quell-Domain als Rueckfall -
    sie ist nicht vom Modell erzeugt und daher verlaesslich.
    """
    location = database.clean_text_for_comparison(event.get("location"))

    # 'online' hat Vorrang: eine reine Online-Veranstaltung gehoert in keine
    # Ortsliste, auch wenn die Domain eine Stadt nennt.
    if not location or "online" in location or "bundesweit" in location:
        return "online"

    for name, keywords in config.REGIONS:
        if any(word in location for word in keywords):
            return name

    # Rueckfall: Stadt aus der Quell-Domain ableiten. Deckt die Berliner
    # Friedhofsseiten ab, deren Ortsangaben ohne Stadtnamen auskommen.
    host = database.clean_text_for_comparison(urlparse(str(event.get("url") or "")).netloc)
    if host:
        for name, keywords in config.REGIONS:
            if any(word in host for word in keywords):
                return name

    return "sonstige"


def event_tags(event: dict) -> list[str]:
    tags = [f"region-{event_region(event)}"]

    kind = database.event_type(event.get("title", ""))
    if kind is None:
        kind = database.event_type(event.get("description", ""))
    tags.append(f"art-{kind}" if kind else "art-sonstige")

    if event.get("date_end"):
        tags.append("laufend")

    return tags


def _filter_buttons(group: str, counts: dict, labels: dict) -> str:
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
    timestamp = datetime.now(config.BERLIN).strftime("%d.%m.%Y um %H:%M Uhr")
    today_str = today.isoformat()

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

    enriched.sort(key=lambda pair: (
        max(pair[0].get("date_start", ""), today_str),
        pair[0].get("date_start", ""),
    ))

    region_buttons = _filter_buttons("region", region_counts, config.REGION_LABELS)
    type_buttons = _filter_buttons("art", type_counts, config.TYPE_LABELS)
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

        .search-input {{ width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid var(--input-border); background-color: var(--input-bg); color: var(--text-main); border-radius: 4px; font-size: 0.95em; }}
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

        @media (max-width: 768px) {{
            body {{ margin: 8px; }}
            .container {{ padding: 12px; }}
            h1 {{ font-size: 1.3em; }}
            .header-bar {{ flex-wrap: wrap; gap: 8px; }}
            .filter-row {{ padding: 10px; gap: 10px; }}

            #eventsTable, #eventsTable tbody, #eventsTable tr, #eventsTable td {{
                display: block;
                width: 100%;
                box-sizing: border-box;
            }}
            #eventsTable thead {{
                display: none;
            }}
            #eventsTable tbody tr {{
                margin-bottom: 12px;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 12px;
                background: var(--filter-bg);
            }}
            #eventsTable td {{
                padding: 3px 0;
                border-bottom: none;
            }}
            #eventsTable td:has(.btn) {{
                margin-top: 6px;
                padding-top: 6px;
                border-top: 1px dashed var(--border-color);
            }}
            a.btn {{
                display: block;
                text-align: center;
                width: 100%;
                box-sizing: border-box;
                padding: 8px 0;
            }}

            /* Beschriftung in der Kartenansicht: ohne Tabellenkopf waeren
               Ort und Beschreibung sonst unbeschriftet untereinander. */
            #eventsTable td[data-label]::before {{
                content: attr(data-label);
                display: block;
                font-size: 0.68em;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: var(--text-muted);
                font-weight: 700;
                margin-bottom: 1px;
            }}
            #eventsTable td[data-label] {{ margin-top: 6px; }}

            /* Filter: eine Zeile pro Gruppe, horizontal wischbar. Umbrechend
               brauchten die Knoepfe ueber 900 px Hoehe, bevor der erste
               Termin sichtbar wurde. */
            .filter-tags {{
                flex-wrap: nowrap;
                overflow-x: auto;
                padding-bottom: 4px;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
            }}
            .filter-tags::-webkit-scrollbar {{ display: none; }}
            .tag-btn {{ white-space: nowrap; flex: 0 0 auto; }}
            .theme-toggle-btn {{ padding: 6px 10px; font-size: 0.85em; }}
        }}
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
                    if age > config.STALE_AFTER_DAYS:
                        badges += ('<span class="badge-stale">seit '
                                   f'{age} Tagen nicht best&auml;tigt</span>')
                except ValueError:
                    pass

            html_content += f"""
                <tr data-tags="{' '.join(tags)}" data-start="{date_s}" data-end="{html.escape(end_raw)}">
                    <td class="cell-plain"><span class="date-badge">{date_s}</span>{end_html}</td>
                    <td class="cell-plain"><strong>{title_s}</strong>{badges}</td>
                    <td class="location" data-label="Ort">{loc_s}</td>
                    <td data-label="Beschreibung">{desc_s}</td>
                    <td class="cell-plain"><a href="{url_s}" target="_blank" rel="noopener noreferrer" class="btn">&ouml;ffnen</a></td>
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

    with open(config.HTML_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)