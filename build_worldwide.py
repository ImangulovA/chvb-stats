#!/usr/bin/env python3
"""Build worldwide national championship statistics from cached API data."""

import json
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUT_DIR = Path(__file__).parent / "worldwide"
WORLDWIDE_DATA = DATA_DIR / "worldwide_results.json"
CLASSIFICATION = DATA_DIR / "tournament_classification.json"

CHST_FLAG_ID = 50
RATING = "https://rating.chgk.info"
FOOTER_AUTHOR = 'Сделано <a href="mailto:imangulovamal@gmail.com" style="color:var(--accent)">Амалем Имангуловым</a>'

COUNTRY_SLUGS = {
    "Азербайджан": "azerbaijan", "Армения": "armenia", "Беларусь": "belarus",
    "Болгария": "bulgaria", "Великобритания": "uk", "Германия": "germany",
    "Грузия": "georgia", "Израиль": "israel", "Казахстан": "kazakhstan",
    "Канада": "canada", "Кыргызстан": "kyrgyzstan", "Латвия": "latvia",
    "Литва": "lithuania", "Молдова": "moldova", "Нидерланды": "netherlands",
    "Россия": "russia", "США": "usa", "Туркменистан": "turkmenistan",
    "Турция": "turkey", "Узбекистан": "uzbekistan", "Украина": "ukraine",
    "Финляндия": "finland", "Франция": "france", "Чехия": "czechia",
    "Швеция": "sweden", "Эстония": "estonia", "Куба": "cuba",
    "Бельгия": "belgium", "Италия": "italy",
}

COUNTRY_FLAGS = {
    "Азербайджан": "🇦🇿", "Армения": "🇦🇲", "Беларусь": "🇧🇾",
    "Болгария": "🇧🇬", "Великобритания": "🇬🇧", "Германия": "🇩🇪",
    "Грузия": "🇬🇪", "Израиль": "🇮🇱", "Казахстан": "🇰🇿",
    "Канада": "🇨🇦", "Кыргызстан": "🇰🇬", "Латвия": "🇱🇻",
    "Литва": "🇱🇹", "Молдова": "🇲🇩", "Нидерланды": "🇳🇱",
    "Россия": "🇷🇺", "США": "🇺🇸", "Туркменистан": "🇹🇲",
    "Турция": "🇹🇷", "Узбекистан": "🇺🇿", "Украина": "🇺🇦",
    "Финляндия": "🇫🇮", "Франция": "🇫🇷", "Чехия": "🇨🇿",
    "Швеция": "🇸🇪", "Эстония": "🇪🇪", "Куба": "🇨🇺",
    "Бельгия": "🇧🇪", "Италия": "🇮🇹",
}


def in_country_zachet(result, town_ids, all_results):
    team = result["team"]
    flags = result.get("flags", [])
    flag_ids = {f["id"] for f in flags}
    has_chst_flags = any(
        CHST_FLAG_ID in {f["id"] for f in r.get("flags", [])}
        for r in all_results
    )
    if has_chst_flags:
        return CHST_FLAG_ID in flag_ids
    town = team.get("town") or {}
    return town.get("id", 0) in town_ids


def compute_country_stats(country_data, main_tournament_ids):
    tournaments_raw = country_data["tournaments"]
    town_ids = set(country_data.get("town_ids", []))

    player_names = {}
    player_wins_overall = defaultdict(list)
    player_wins_country = defaultdict(list)
    player_podiums_overall = defaultdict(list)
    player_podiums_country = defaultdict(list)
    player_participations = defaultdict(list)
    player_years = defaultdict(set)

    team_wins_overall = defaultdict(list)
    team_wins_country = defaultdict(list)
    team_participations = defaultdict(list)
    team_name_to_id = {}
    team_years = defaultdict(set)

    tournaments_summary = []

    sorted_tids = sorted(
        [t for t in main_tournament_ids if str(t) in tournaments_raw],
        key=lambda t: tournaments_raw[str(t)]["info"].get("dateStart", ""),
    )

    for tid in sorted_tids:
        td = tournaments_raw[str(tid)]
        info = td["info"]
        results = td["results"]
        if not results:
            continue

        year = info["dateStart"][:4]
        qd = info.get("questionQty")
        q_total = sum(qd.values()) if isinstance(qd, dict) else 0
        results.sort(key=lambda x: float(x.get("position") or 999))
        country_results = [r for r in results if in_country_zachet(r, town_ids, results)]

        overall_winner = results[0]["team"]["name"] if results else "?"
        country_winner = country_results[0]["team"]["name"] if country_results else "?"
        overall_winner_score = results[0].get("questionsTotal") or 0
        country_winner_score = country_results[0].get("questionsTotal") or 0 if country_results else 0
        country_winner_overall_pos = float(country_results[0].get("position") or 0) if country_results else 0

        tournaments_summary.append({
            "id": tid, "year": year, "name": info["name"],
            "teams_total": len(results), "teams_country": len(country_results),
            "questions": q_total,
            "overall_winner": overall_winner, "overall_winner_score": overall_winner_score,
            "country_winner": country_winner, "country_winner_score": country_winner_score,
            "country_winner_overall_pos": country_winner_overall_pos,
            "results": [],
        })

        for r in results:
            team = r["team"]
            town = (team.get("town") or {}).get("name", "?")
            pos = r.get("position") or 999
            total = r.get("questionsTotal") or 0
            is_country = in_country_zachet(r, town_ids, results)
            tournaments_summary[-1]["results"].append({
                "pos": pos, "team": team["name"], "team_id": team["id"],
                "town": town, "total": total, "is_country": is_country,
            })
            team_participations[team["name"]].append(year)
            team_name_to_id[team["name"]] = team["id"]
            team_years[team["name"]].add(year)
            for member in r.get("teamMembers", []):
                pid = member["player"]["id"]
                pname = f'{member["player"]["name"]} {member["player"]["surname"]}'
                player_names[pid] = pname
                player_participations[pid].append({"year": year, "team": team["name"], "pos": pos})
                player_years[pid].add(year)

        for r in results:
            if float(r.get("position") or 999) == 1:
                team_wins_overall[r["team"]["name"]].append(year)
                for m in r.get("teamMembers", []):
                    player_wins_overall[m["player"]["id"]].append((year, r["team"]["name"]))
        for r in results:
            if float(r.get("position") or 999) <= 3:
                for m in r.get("teamMembers", []):
                    player_podiums_overall[m["player"]["id"]].append(
                        (year, r["team"]["name"], float(r.get("position") or 999)))
        if country_results:
            best_pos = float(country_results[0].get("position") or 999)
            for r in country_results:
                if float(r.get("position") or 999) == best_pos:
                    team_wins_country[r["team"]["name"]].append(year)
                    for m in r.get("teamMembers", []):
                        player_wins_country[m["player"]["id"]].append((year, r["team"]["name"]))
            for i, r in enumerate(country_results[:3], 1):
                for m in r.get("teamMembers", []):
                    player_podiums_country[m["player"]["id"]].append((year, r["team"]["name"], i))

    # Iron men: players who played ALL championships
    valid_years = [t["year"] for t in tournaments_summary]
    iron_men = []
    if len(valid_years) >= 5:
        valid_set = set(valid_years)
        for pid, parts in player_participations.items():
            played = set(p["year"] for p in parts)
            if played >= valid_set:
                iron_men.append({"id": pid, "name": player_names.get(pid, "?"), "count": len(valid_years)})

    return {
        "player_names": player_names,
        "player_wins_overall": player_wins_overall,
        "player_wins_country": player_wins_country,
        "player_podiums_overall": player_podiums_overall,
        "player_podiums_country": player_podiums_country,
        "player_participations": player_participations,
        "player_years": {pid: sorted(yrs) for pid, yrs in player_years.items()},
        "team_wins_overall": team_wins_overall,
        "team_wins_country": team_wins_country,
        "team_participations": team_participations,
        "team_name_to_id": team_name_to_id,
        "team_years": {t: sorted(yrs) for t, yrs in team_years.items()},
        "tournaments": tournaments_summary,
        "iron_men": iron_men,
    }


def compute_cross_country_stats(worldwide, classification):
    player_names = {}
    player_countries = defaultdict(set)
    player_country_years = defaultdict(lambda: defaultdict(list))
    player_country_medals = defaultdict(lambda: defaultdict(list))

    for cid_str, cdata in worldwide.items():
        cname = cdata["country"]["name"]
        main_ids = classification.get(cid_str, {}).get("main", [])
        town_ids = set(cdata.get("town_ids", []))
        tournaments = cdata["tournaments"]

        for tid in main_ids:
            td = tournaments.get(str(tid))
            if not td or not td["results"]:
                continue
            year = td["info"]["dateStart"][:4]
            results = td["results"]
            results.sort(key=lambda x: float(x.get("position") or 999))

            country_results = [r for r in results if in_country_zachet(r, town_ids, results)]

            for r in results:
                for m in r.get("teamMembers", []):
                    pid = m["player"]["id"]
                    pname = f'{m["player"]["name"]} {m["player"]["surname"]}'
                    player_names[pid] = pname
                    player_countries[pid].add(cname)
                    player_country_years[pid][cname].append(year)

            for i, r in enumerate(country_results[:3], 1):
                for m in r.get("teamMembers", []):
                    pid = m["player"]["id"]
                    player_country_medals[pid][cname].append((year, i))

    # Most countries played
    most_countries = sorted(player_countries.items(), key=lambda x: (-len(x[1]), player_names.get(x[0], "")))

    # Multi-country medalists
    multi_medalists = [
        (pid, countries) for pid, countries in player_country_medals.items()
        if len(countries) >= 2
    ]
    multi_medalists.sort(key=lambda x: (-len(x[1]), -sum(len(m) for m in x[1].values())))

    return {
        "player_names": player_names,
        "player_countries": dict(player_countries),
        "player_country_years": {p: dict(c) for p, c in player_country_years.items()},
        "player_country_medals": {p: dict(c) for p, c in player_country_medals.items()},
        "most_countries": most_countries,
        "multi_medalists": multi_medalists,
    }


# ─── CSS ───

CSS = """\
:root {
  --bg: #0a0e1a; --card: #151d30; --card-border: #1e2a45;
  --text: #e0e6f0; --text-muted: #8892a8; --accent: #1877F2;
  --gold: #f59e0b; --silver: #94a3b8; --bronze: #cd7f32;
  --green: #02e2ac; --red: #ef4444; --purple: #a855f7; --country-badge: #1877F2;
}
[data-theme="light"] {
  --bg: #f0f2f5; --card: #ffffff; --card-border: #dde1e6;
  --text: #1c1e21; --text-muted: #65676b; --accent: #1877F2;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
header { background: linear-gradient(135deg, #0a1628 0%, #162544 100%); padding: 40px 20px; text-align: center; border-bottom: 3px solid var(--accent); }
[data-theme="light"] header { background: linear-gradient(135deg, #e8f0fe 0%, #d2e3fc 100%); }
header h1 { font-size: 2em; margin-bottom: 8px; }
header h1 span { color: var(--accent); }
header p { color: var(--text-muted); font-size: 1.1em; }
.theme-toggle { position: fixed; top: 16px; right: 16px; z-index: 100; background: var(--card); border: 1px solid var(--card-border); color: var(--text); padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 14px; }
nav { position: sticky; top: 0; z-index: 50; background: var(--card); border-bottom: 1px solid var(--card-border); padding: 10px 20px; display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
nav a { color: var(--text-muted); text-decoration: none; padding: 6px 14px; border-radius: 16px; font-size: 13px; transition: all 0.2s; }
nav a:hover, nav a.active { background: var(--accent); color: #fff; }
.card { background: var(--card); border: 1px solid var(--card-border); border-radius: 12px; padding: 24px; margin-bottom: 20px; }
.card h2 { font-size: 1.3em; margin-bottom: 16px; color: var(--accent); }
.card h3 { font-size: 1.1em; margin: 16px 0 8px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat-box { background: var(--bg); border-radius: 8px; padding: 16px; text-align: center; }
.stat-box .num { font-size: 2em; font-weight: 700; color: var(--accent); }
.stat-box .label { font-size: 0.85em; color: var(--text-muted); }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--card-border); color: var(--text-muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 6px 10px; border-bottom: 1px solid var(--card-border); }
tr:hover { background: rgba(24,119,242,0.05); }
tr.hidden { display: none; }
.pos { font-weight: 700; width: 40px; text-align: center; }
.score { text-align: right; font-weight: 600; }
.country-badge { display: inline-block; background: var(--country-badge); color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 8px; margin-left: 4px; }
.team-name { font-weight: 500; }
.town { color: var(--text-muted); font-size: 13px; }
.year-tag { display: inline-block; background: var(--bg); padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 1px; }
.bar-row { display: flex; align-items: center; margin: 4px 0; gap: 8px; }
.bar-row.hidden { display: none; }
.bar-label { min-width: 180px; font-size: 13px; text-align: right; }
.bar-track { flex: 1; height: 24px; background: var(--bg); border-radius: 4px; overflow: hidden; position: relative; }
.bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
.bar-value { font-size: 12px; min-width: 30px; font-weight: 600; }
section { scroll-margin-top: 60px; }
section h2 { padding: 20px 0 10px; font-size: 1.4em; }
.entity-link { color: var(--text); text-decoration: none; border-bottom: 1px dotted var(--text-muted); }
.entity-link:hover { color: var(--accent); border-color: var(--accent); }
.year-filter { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 14px; }
.yfp { padding: 4px 10px; border-radius: 12px; cursor: pointer; background: var(--bg); color: var(--text-muted); font-size: 12px; border: 1px solid var(--card-border); transition: all 0.15s; }
.yfp:hover { border-color: var(--accent); color: var(--accent); }
.yfp.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.mode-toggle { display: flex; gap: 0; margin-bottom: 16px; justify-content: center; }
.mode-btn { padding: 8px 20px; border: 1px solid var(--card-border); background: var(--bg); color: var(--text-muted); cursor: pointer; font-size: 13px; transition: all 0.2s; }
.mode-btn:first-child { border-radius: 8px 0 0 8px; }
.mode-btn:last-child { border-radius: 0 8px 8px 0; }
.mode-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
[data-mode="overall"] .country-only { display: none; }
[data-mode="country"] .overall-only { display: none; }
.country-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.country-card { background: var(--card); border: 1px solid var(--card-border); border-radius: 12px; padding: 20px; transition: transform 0.15s, border-color 0.15s; text-decoration: none; color: var(--text); display: block; }
.country-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.country-card .flag { font-size: 2em; }
.country-card .name { font-size: 1.2em; font-weight: 600; margin: 8px 0 4px; }
.country-card .meta { color: var(--text-muted); font-size: 13px; }
.country-card .mini-stats { display: flex; gap: 16px; margin-top: 12px; }
.country-card .mini-stat { text-align: center; }
.country-card .mini-stat .n { font-size: 1.4em; font-weight: 700; color: var(--accent); }
.country-card .mini-stat .l { font-size: 11px; color: var(--text-muted); }
.iron-badge { display: inline-block; background: var(--green); color: #000; font-size: 11px; padding: 2px 8px; border-radius: 8px; font-weight: 600; }
.map-container { background: var(--card); border: 1px solid var(--card-border); border-radius: 12px; padding: 20px; margin-bottom: 20px; overflow: hidden; }
.map-container svg { width: 100%; height: auto; display: block; }
.map-country { cursor: pointer; transition: opacity 0.2s, filter 0.2s; stroke: var(--bg); stroke-width: 0.5; }
.map-country:hover { opacity: 1 !important; filter: brightness(1.3); }
.map-bg { fill: var(--card-border); opacity: 0.25; stroke: none; }
.map-flag { pointer-events: none; font-size: 14px; dominant-baseline: central; text-anchor: middle; }
footer a { color: var(--accent); }
@media (max-width: 600px) { .bar-label { min-width: 120px; font-size: 12px; } header h1 { font-size: 1.4em; } .stats-grid { grid-template-columns: repeat(2, 1fr); } .country-grid { grid-template-columns: 1fr; } }
"""

JS_COMMON = """\
function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}
(function() {
  const s = localStorage.getItem('theme');
  if (s) document.documentElement.setAttribute('data-theme', s);
  document.querySelectorAll('.yfp[data-year="all"]').forEach(b => b.classList.add('active'));
})();
document.querySelectorAll('nav a').forEach(a => {
  a.addEventListener('click', function() {
    document.querySelectorAll('nav a').forEach(x => x.classList.remove('active'));
    this.classList.add('active');
  });
});
function filterYear(btn) {
  const section = btn.dataset.section;
  const year = btn.dataset.year;
  document.querySelectorAll(`.yfp[data-section="${section}"]`).forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll(`.filterable[data-section="${section}"]`).forEach(row => {
    if (year === 'all') { row.classList.remove('hidden'); }
    else { row.classList.toggle('hidden', !row.dataset.years.split(',').includes(year)); }
  });
}
function setMode(mode) {
  document.body.setAttribute('data-mode', mode);
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  localStorage.setItem('viewMode', mode);
}
(function() {
  const m = localStorage.getItem('viewMode') || 'country';
  if (document.querySelector('.mode-btn')) setMode(m);
})();
"""


def medal_icon(pos):
    if pos == 1: return "🥇"
    if pos == 2: return "🥈"
    if pos == 3: return "🥉"
    return ""


def bar_html(val, max_val, color="#1877F2"):
    pct = (val / max_val * 100) if max_val else 0
    return f'<div class="bar" style="width:{pct}%;background:{color}"></div>'


def player_link(pid, name):
    return f'<a href="{RATING}/player/{pid}" target="_blank" class="entity-link">{name}</a>'


def team_link(name, team_id=None, tid_map=None):
    t_id = team_id or (tid_map or {}).get(name)
    if t_id:
        return f'<a href="{RATING}/teams/{t_id}" target="_blank" class="entity-link">{name}</a>'
    return name


def tournament_link(tid, text):
    return f'<a href="{RATING}/tournament/{tid}" target="_blank" class="entity-link">{text}</a>'


def year_filter_pills(section_id, all_years):
    pills = [f'<button class="yfp" data-section="{section_id}" data-year="all" onclick="filterYear(this)">Все</button>']
    for y in all_years:
        pills.append(f'<button class="yfp" data-section="{section_id}" data-year="{y}" onclick="filterYear(this)">{y}</button>')
    return f'<div class="year-filter" id="yf-{section_id}">{"".join(pills)}</div>'


def footer_html(back_link=None):
    parts = []
    if back_link:
        parts.append(f'<a href="{back_link}">← Все страны</a> |')
    parts.append(f'Данные: <a href="{RATING}">rating.chgk.info</a> API |')
    parts.append(FOOTER_AUTHOR)
    return f'<footer style="text-align:center;padding:40px 20px;color:var(--text-muted);font-size:13px">{" ".join(parts)}</footer>'


# ─── SVG MAP ───

COUNTRY_COLORS = {
    "Азербайджан": "#e74c3c", "Армения": "#e67e22", "Беларусь": "#27ae60",
    "Болгария": "#8e44ad", "Великобритания": "#2980b9", "Германия": "#f39c12",
    "Грузия": "#e74c3c", "Израиль": "#3498db", "Казахстан": "#1abc9c",
    "Канада": "#c0392b", "Кыргызстан": "#d35400", "Латвия": "#9b59b6",
    "Литва": "#2ecc71", "Молдова": "#e74c3c", "Россия": "#2c3e50",
    "США": "#2980b9", "Туркменистан": "#16a085", "Турция": "#e74c3c",
    "Узбекистан": "#3498db", "Украина": "#f1c40f", "Финляндия": "#ecf0f1",
    "Чехия": "#e74c3c", "Эстония": "#3498db",
}

def build_map_svg(country_summaries):
    """Build an inline SVG world map with real country outlines."""
    from map_data import VIEW_W, VIEW_H, BG_PATHS, COUNTRY_PATHS, COUNTRY_CENTERS

    svg = [f'<svg viewBox="0 0 {VIEW_W} {VIEW_H}" xmlns="http://www.w3.org/2000/svg">']
    svg.append(f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="var(--bg)" rx="8"/>')

    for path in BG_PATHS:
        svg.append(f'<path d="{path}" class="map-bg"/>')

    for cname, cs in country_summaries.items():
        if cname not in COUNTRY_PATHS:
            continue
        slug = COUNTRY_SLUGS.get(cname, cname.lower())
        color = COUNTRY_COLORS.get(cname, "#1877F2")
        flag = COUNTRY_FLAGS.get(cname, "")
        paths = COUNTRY_PATHS[cname]

        svg.append(f'<a href="countries/{slug}.html">')
        for p in paths:
            svg.append(f'  <path d="{p}" class="map-country" fill="{color}" opacity="0.75"/>')
        if cname in COUNTRY_CENTERS:
            cx, cy = COUNTRY_CENTERS[cname]
            svg.append(f'  <text class="map-flag" x="{cx}" y="{cy}">{flag}</text>')
        svg.append('</a>')

    svg.append('</svg>')
    return "\n".join(svg)


# ─── COUNTRY PAGE ───

def build_country_page(stats, country_name, country_genitive, back_link="../index.html"):
    tournaments = stats["tournaments"]
    if not tournaments:
        return None

    pn = stats["player_names"]
    tid_map = stats["team_name_to_id"]
    flag = COUNTRY_FLAGS.get(country_name, "🏴")
    iron_men = stats.get("iron_men", [])

    all_years = sorted(set(t["year"] for t in tournaments))
    first_year = all_years[0] if all_years else "?"
    last_year = all_years[-1] if all_years else "?"

    top_country_winners = sorted(stats["player_wins_country"].items(), key=lambda x: -len(x[1]))
    top_overall_winners = sorted(stats["player_wins_overall"].items(), key=lambda x: -len(x[1]))
    top_country_podiums = sorted(stats["player_podiums_country"].items(),
        key=lambda x: (-len(x[1]), -len(stats["player_wins_country"].get(x[0], []))))
    top_overall_podiums = sorted(stats["player_podiums_overall"].items(),
        key=lambda x: (-len(x[1]), -len(stats["player_wins_overall"].get(x[0], []))))
    top_participations = sorted(stats["player_participations"].items(), key=lambda x: -len(x[1]))
    top_team_wins_country = sorted(stats["team_wins_country"].items(), key=lambda x: -len(x[1]))
    top_team_wins_overall = sorted(stats["team_wins_overall"].items(), key=lambda x: -len(x[1]))
    top_team_parts = sorted(stats["team_participations"].items(), key=lambda x: -len(x[1]))

    def tl(name, t_id=None):
        return team_link(name, t_id, tid_map)

    nav_items = ['<a href="#overview">Обзор</a>', '<a href="#champions">Чемпионы</a>',
                 '<a href="#players">Игроки</a>', '<a href="#teams">Команды</a>',
                 '<a href="#tournaments">Турниры</a>']
    if iron_men:
        nav_items.insert(-1, '<a href="#ironmen">Железные люди</a>')

    h = []
    h.append(f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{flag} Чемпионат {country_genitive} по ЧГК -- Статистика</title>
<style>{CSS}</style>
</head>
<body data-mode="country">
<button class="theme-toggle" onclick="toggleTheme()">🌙 / ☀️</button>
<header>
  <h1>{flag} <span>Чемпионат {country_genitive}</span></h1>
  <p>Статистика {first_year}--{last_year} | <a href="{back_link}" style="color:var(--accent)">← Все страны</a></p>
</header>
<nav>{"".join(nav_items)}</nav>
<div class="container">
<div class="mode-toggle">
  <button class="mode-btn" data-mode="country" onclick="setMode('country')">🏆 Зачёт ЧС</button>
  <button class="mode-btn" data-mode="overall" onclick="setMode('overall')">🌍 Общий зачёт</button>
</div>
""")

    # === OVERVIEW ===
    total_teams = sum(t["teams_total"] for t in tournaments)
    total_players = len(stats["player_participations"])
    max_teams = max(t["teams_total"] for t in tournaments) if tournaments else 0
    max_teams_year = [t["year"] for t in tournaments if t["teams_total"] == max_teams][0] if max_teams else "?"

    h.append(f"""
<section id="overview"><div class="card">
  <h2>Обзор</h2>
  <div class="stats-grid">
    <div class="stat-box"><div class="num">{len(tournaments)}</div><div class="label">турниров</div></div>
    <div class="stat-box"><div class="num">{total_players}</div><div class="label">игроков</div></div>
    <div class="stat-box"><div class="num">{total_teams}</div><div class="label">команд-участий</div></div>
    <div class="stat-box"><div class="num">{max_teams}</div><div class="label">макс. команд ({max_teams_year})</div></div>
  </div>
  <h3>Рост турнира</h3>""")

    max_t = max(t["teams_total"] for t in tournaments) if tournaments else 1
    for t in tournaments:
        pct = t["teams_total"] / max_t * 100
        c_pct = t["teams_country"] / max_t * 100
        h.append(f"""
  <div class="bar-row">
    <div class="bar-label">{tournament_link(t['id'], t['year'])}</div>
    <div class="bar-track">
      <div class="bar" style="width:{pct}%;background:var(--accent);opacity:0.4;position:absolute"></div>
      <div class="bar" style="width:{c_pct}%;background:var(--accent);position:absolute"></div>
    </div>
    <div class="bar-value">{t['teams_total']} ({t['teams_country']} ЧС)</div>
  </div>""")
    h.append("</div></section>")

    # === CHAMPIONS ===
    h.append(f"""
<section id="champions"><div class="card">
  <h2>Чемпионы по годам</h2>
  <table><tr><th>Год</th><th>Чемпион (общий)</th><th>Взято</th><th>Чемпион ЧС</th><th>Взято</th><th>Место</th><th>Команд</th></tr>""")
    for t in tournaments:
        c_pos = t["country_winner_overall_pos"]
        pos_str = str(int(c_pos)) if c_pos == int(c_pos) else str(c_pos)
        same = t["overall_winner"] == t["country_winner"]
        hl = "" if same else ' style="color:var(--gold)"'
        h.append(f"""    <tr>
      <td class="pos">{tournament_link(t['id'], t['year'])}</td>
      <td class="team-name">{tl(t['overall_winner'])}</td>
      <td class="score">{t['overall_winner_score'] or '—'}</td>
      <td class="team-name"{hl}>{tl(t['country_winner'])}</td>
      <td class="score">{t['country_winner_score'] or '—'}</td>
      <td class="pos">{pos_str}</td>
      <td class="pos">{t['teams_total']}</td></tr>""")
    h.append("</table></div></section>")

    # === PLAYERS ===
    h.append(f'<section id="players"><div class="card country-only"><h2>Игроки -- победы (зачёт ЧС)</h2>')
    h.append(year_filter_pills("pw-c", all_years))
    max_w = len(top_country_winners[0][1]) if top_country_winners else 1
    for pid, wins in top_country_winners[:25]:
        if not wins: break
        dyears = ",".join(sorted(set(y for y, _ in wins)))
        h.append(f'<div class="bar-row filterable" data-section="pw-c" data-years="{dyears}"><div class="bar-label">{player_link(pid, pn.get(pid, "?"))}</div><div class="bar-track">{bar_html(len(wins), max_w, "#f59e0b")}</div><div class="bar-value">{len(wins)}</div></div>')
    h.append("</div>")

    h.append(f'<div class="card overall-only"><h2>Игроки -- победы (общий зачёт)</h2>')
    h.append(year_filter_pills("pw-o", all_years))
    max_w = len(top_overall_winners[0][1]) if top_overall_winners else 1
    for pid, wins in top_overall_winners[:25]:
        if not wins: break
        dyears = ",".join(sorted(set(y for y, _ in wins)))
        h.append(f'<div class="bar-row filterable" data-section="pw-o" data-years="{dyears}"><div class="bar-label">{player_link(pid, pn.get(pid, "?"))}</div><div class="bar-track">{bar_html(len(wins), max_w, "#f59e0b")}</div><div class="bar-value">{len(wins)}</div></div>')
    h.append("</div>")

    h.append(f'<div class="card country-only"><h2>Игроки -- подиумы (зачёт ЧС)</h2>')
    h.append(year_filter_pills("pp-c", all_years))
    h.append('<table><thead><tr><th>#</th><th>Игрок</th><th>Подиумов</th><th>Побед</th><th>Детали</th></tr></thead><tbody>')
    for rank, (pid, podiums) in enumerate(top_country_podiums[:30], 1):
        if len(podiums) < 2: break
        wins = len(stats["player_wins_country"].get(pid, []))
        details = " ".join(f'<span class="year-tag">{medal_icon(p)}{y}</span>' for y, t, p in podiums)
        dyears = ",".join(sorted(set(y for y, _, _ in podiums)))
        h.append(f'<tr class="filterable" data-section="pp-c" data-years="{dyears}"><td class="pos">{rank}</td><td class="team-name">{player_link(pid, pn.get(pid, "?"))}</td><td class="score">{len(podiums)}</td><td class="score">{wins}</td><td>{details}</td></tr>')
    h.append("</tbody></table></div>")

    h.append(f'<div class="card overall-only"><h2>Игроки -- подиумы (общий зачёт)</h2>')
    h.append(year_filter_pills("pp-o", all_years))
    h.append('<table><thead><tr><th>#</th><th>Игрок</th><th>Подиумов</th><th>Побед</th><th>Детали</th></tr></thead><tbody>')
    for rank, (pid, podiums) in enumerate(top_overall_podiums[:30], 1):
        if len(podiums) < 2: break
        wins = len(stats["player_wins_overall"].get(pid, []))
        details = " ".join(f'<span class="year-tag">{medal_icon(p)}{y}</span>' for y, t, p in podiums)
        dyears = ",".join(sorted(set(y for y, _, _ in podiums)))
        h.append(f'<tr class="filterable" data-section="pp-o" data-years="{dyears}"><td class="pos">{rank}</td><td class="team-name">{player_link(pid, pn.get(pid, "?"))}</td><td class="score">{len(podiums)}</td><td class="score">{wins}</td><td>{details}</td></tr>')
    h.append("</tbody></table></div>")

    h.append(f'<div class="card"><h2>Игроки -- участия</h2>')
    h.append(year_filter_pills("pt", all_years))
    h.append('<table><thead><tr><th>#</th><th>Игрок</th><th>Турниров</th><th>Годы</th></tr></thead><tbody>')
    min_parts = max(3, len(tournaments) // 4)
    for rank, (pid, parts) in enumerate(top_participations[:30], 1):
        if len(parts) < min_parts: break
        yrs = sorted(set(p["year"] for p in parts))
        yrs_html = " ".join(f'<span class="year-tag">{y}</span>' for y in yrs)
        dyears = ",".join(yrs)
        h.append(f'<tr class="filterable" data-section="pt" data-years="{dyears}"><td class="pos">{rank}</td><td class="team-name">{player_link(pid, pn.get(pid, "?"))}</td><td class="score">{len(parts)}</td><td>{yrs_html}</td></tr>')
    h.append("</tbody></table></div></section>")

    # === IRON MEN ===
    if iron_men:
        h.append(f'<section id="ironmen"><div class="card"><h2>🦾 Железные люди -- все {len(tournaments)} чемпионатов</h2>')
        h.append(f'<p style="color:var(--text-muted);margin-bottom:12px">Игроки, которые участвовали в каждом чемпионате {country_genitive}</p>')
        h.append('<table><thead><tr><th>#</th><th>Игрок</th><th>Турниров</th></tr></thead><tbody>')
        for i, im in enumerate(iron_men, 1):
            h.append(f'<tr><td class="pos">{i}</td><td class="team-name">{player_link(im["id"], im["name"])} <span class="iron-badge">IRON</span></td><td class="score">{im["count"]}</td></tr>')
        h.append("</tbody></table></div></section>")

    # === TEAMS ===
    h.append(f'<section id="teams"><div class="card country-only"><h2>Команды -- победы (зачёт ЧС)</h2>')
    max_tw = len(top_team_wins_country[0][1]) if top_team_wins_country else 1
    for tn, wy in top_team_wins_country[:15]:
        if not wy: break
        h.append(f'<div class="bar-row"><div class="bar-label">{tl(tn)}</div><div class="bar-track">{bar_html(len(wy), max_tw, "#02e2ac")}</div><div class="bar-value">{len(wy)}</div></div>')
    h.append("</div>")

    h.append(f'<div class="card overall-only"><h2>Команды -- победы (общий зачёт)</h2>')
    max_tw = len(top_team_wins_overall[0][1]) if top_team_wins_overall else 1
    for tn, wy in top_team_wins_overall[:15]:
        if not wy: break
        h.append(f'<div class="bar-row"><div class="bar-label">{tl(tn)}</div><div class="bar-track">{bar_html(len(wy), max_tw, "#02e2ac")}</div><div class="bar-value">{len(wy)}</div></div>')
    h.append("</div>")

    h.append(f'<div class="card"><h2>Команды -- участия</h2>')
    h.append(year_filter_pills("tp", all_years))
    h.append('<table><thead><tr><th>#</th><th>Команда</th><th>Турниров</th><th>Годы</th></tr></thead><tbody>')
    for rank, (tn, yrs) in enumerate(top_team_parts[:25], 1):
        if len(yrs) < 3: break
        unique_yrs = sorted(set(yrs))
        yrs_html = " ".join(f'<span class="year-tag">{y}</span>' for y in unique_yrs)
        dyears = ",".join(unique_yrs)
        h.append(f'<tr class="filterable" data-section="tp" data-years="{dyears}"><td class="pos">{rank}</td><td class="team-name">{tl(tn)}</td><td class="score">{len(unique_yrs)}</td><td>{yrs_html}</td></tr>')
    h.append("</tbody></table></div></section>")

    # === TOURNAMENTS ===
    h.append('<section id="tournaments"><div class="card"><h2>Все турниры</h2></div>')
    for t in tournaments:
        results = t["results"]
        h.append(f"""
<div class="card">
  <h3>{tournament_link(t['id'], t['name'] + ' ' + t['year'])}</h3>
  <p style="color:var(--text-muted);font-size:13px">{t['teams_total']} команд | {t['questions']} вопросов</p>
  <table><tr><th>М</th><th>Команда</th><th>Город</th><th>Взято</th></tr>""")
        for r in results:
            pos = r["pos"]
            pos_str = str(int(pos)) if pos == int(pos) else str(pos)
            c_mark = '<span class="country-badge">ЧС</span>' if r["is_country"] else ""
            score = r["total"] if r["total"] else "—"
            md = medal_icon(pos)
            h.append(f'    <tr><td class="pos">{md} {pos_str}</td><td class="team-name">{team_link(r["team"], r.get("team_id"), tid_map)}{c_mark}</td><td class="town">{r["town"]}</td><td class="score">{score}</td></tr>')
        h.append("</table></div>")
    h.append("</section>")

    h.append(f"""
</div>
{footer_html(back_link)}
<script>{JS_COMMON}</script>
</body>
</html>""")

    return "\n".join(h)


# ─── INDEX PAGE ───

def build_index_page(all_country_stats, cross_stats, all_iron_men):
    h = []
    h.append(f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🌍 Чемпионаты стран по ЧГК -- Мировая статистика</title>
<style>{CSS}</style>
</head>
<body>
<button class="theme-toggle" onclick="toggleTheme()">🌙 / ☀️</button>
<header>
  <h1>🌍 <span>Чемпионаты стран</span> по ЧГК</h1>
  <p>Статистика национальных чемпионатов всего мира | rating.chgk.info</p>
</header>
<nav>
  <a href="#map">Карта</a>
  <a href="#overview">Обзор</a>
  <a href="#travelers">Путешественники</a>
  <a href="#multi-medalists">Мультимедалисты</a>
  <a href="#ironmen">Железные люди</a>
  <a href="#countries">Страны</a>
</nav>
<div class="container">
""")

    total_countries = len(all_country_stats)
    total_tournaments = sum(s["n_tournaments"] for s in all_country_stats.values())
    total_players = len(cross_stats["player_names"])
    multi_country_players = sum(1 for c in cross_stats["player_countries"].values() if len(c) >= 2)
    multi_medalists_count = len(cross_stats["multi_medalists"])

    # === MAP ===
    h.append(f'<section id="map"><div class="map-container"><h2>🗺️ Карта чемпионатов</h2>')
    h.append(build_map_svg(all_country_stats))
    h.append('</div></section>')

    # === OVERVIEW ===
    h.append(f"""
<section id="overview"><div class="card">
  <h2>Обзор</h2>
  <div class="stats-grid">
    <div class="stat-box"><div class="num">{total_countries}</div><div class="label">стран</div></div>
    <div class="stat-box"><div class="num">{total_tournaments}</div><div class="label">чемпионатов</div></div>
    <div class="stat-box"><div class="num">{total_players:,}</div><div class="label">уникальных игроков</div></div>
    <div class="stat-box"><div class="num">{multi_country_players}</div><div class="label">играли в 2+ странах</div></div>
    <div class="stat-box"><div class="num">{multi_medalists_count}</div><div class="label">медали 2+ стран</div></div>
    <div class="stat-box"><div class="num">{sum(len(im) for im in all_iron_men.values())}</div><div class="label">железных людей</div></div>
  </div>
</div></section>
""")

    # === TRAVELERS ===
    pn = cross_stats["player_names"]
    h.append('<section id="travelers"><div class="card"><h2>🧳 Путешественники -- наибольшее количество стран</h2>')
    h.append('<table><thead><tr><th>#</th><th>Игрок</th><th>Стран</th><th>Страны</th></tr></thead><tbody>')
    for rank, (pid, countries) in enumerate(cross_stats["most_countries"][:40], 1):
        if len(countries) < 3:
            break
        flags = " ".join(COUNTRY_FLAGS.get(c, "") for c in sorted(countries))
        h.append(f'<tr><td class="pos">{rank}</td><td class="team-name">{player_link(pid, pn.get(pid, "?"))}</td><td class="score">{len(countries)}</td><td>{flags}</td></tr>')
    h.append("</tbody></table></div></section>")

    # === MULTI-MEDALISTS ===
    h.append('<section id="multi-medalists"><div class="card"><h2>🏅 Мультимедалисты -- медали чемпионатов разных стран</h2>')
    h.append('<table><thead><tr><th>#</th><th>Игрок</th><th>Стран</th><th>Медали</th></tr></thead><tbody>')
    for rank, (pid, countries) in enumerate(cross_stats["multi_medalists"][:40], 1):
        details = []
        for cname in sorted(countries.keys()):
            medals = countries[cname]
            g = sum(1 for _, p in medals if p == 1)
            s = sum(1 for _, p in medals if p == 2)
            b = sum(1 for _, p in medals if p == 3)
            flag = COUNTRY_FLAGS.get(cname, "")
            parts = []
            if g: parts.append(f"{g}🥇")
            if s: parts.append(f"{s}🥈")
            if b: parts.append(f"{b}🥉")
            details.append(f'{flag}{"".join(parts)}')
        h.append(f'<tr><td class="pos">{rank}</td><td class="team-name">{player_link(pid, pn.get(pid, "?"))}</td><td class="score">{len(countries)}</td><td>{" ".join(details)}</td></tr>')
    h.append("</tbody></table></div></section>")

    # === IRON MEN ===
    h.append('<section id="ironmen"><div class="card"><h2>🦾 Железные люди мира</h2>')
    h.append('<p style="color:var(--text-muted);margin-bottom:12px">Игроки, которые не пропустили ни одного чемпионата своей страны (мин. 5 чемпионатов)</p>')
    h.append('<table><thead><tr><th>Страна</th><th>Игрок</th><th>Чемпионатов</th></tr></thead><tbody>')
    for cname in sorted(all_iron_men.keys()):
        iron_list = all_iron_men[cname]
        if not iron_list:
            continue
        flag = COUNTRY_FLAGS.get(cname, "")
        slug = COUNTRY_SLUGS.get(cname, "")
        for im in iron_list:
            h.append(f'<tr><td>{flag} <a href="countries/{slug}.html" class="entity-link">{cname}</a></td><td class="team-name">{player_link(im["id"], im["name"])} <span class="iron-badge">IRON</span></td><td class="score">{im["count"]}</td></tr>')
    h.append("</tbody></table></div></section>")

    # === COUNTRIES ===
    h.append('<section id="countries"><h2 style="text-align:center;margin-bottom:16px">Все страны</h2><div class="country-grid">')
    sorted_countries = sorted(all_country_stats.items(), key=lambda x: -x[1]["n_tournaments"])
    for cname, cs in sorted_countries:
        slug = COUNTRY_SLUGS.get(cname, cname.lower())
        flag = COUNTRY_FLAGS.get(cname, "🏴")
        n_iron = len(all_iron_men.get(cname, []))
        iron_html = f'<div class="mini-stat"><div class="n">{n_iron}</div><div class="l">iron men</div></div>' if n_iron else ""
        h.append(f"""
  <a class="country-card" href="countries/{slug}.html">
    <div class="flag">{flag}</div>
    <div class="name">{cname}</div>
    <div class="meta">{cs['year_range']}</div>
    <div class="mini-stats">
      <div class="mini-stat"><div class="n">{cs['n_tournaments']}</div><div class="l">турниров</div></div>
      <div class="mini-stat"><div class="n">{cs['n_players']}</div><div class="l">игроков</div></div>
      <div class="mini-stat"><div class="n">{cs['n_teams']}</div><div class="l">команд</div></div>
      {iron_html}
    </div>
  </a>""")
    h.append("</div></section>")

    h.append(f"""
</div>
{footer_html()}
<script>{JS_COMMON}</script>
</body>
</html>""")
    return "\n".join(h)


# ─── MAIN ───

def main():
    print("Loading data...", flush=True)
    with open(WORLDWIDE_DATA) as f:
        worldwide = json.load(f)
    with open(CLASSIFICATION) as f:
        classification = json.load(f)

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "countries").mkdir(exist_ok=True)

    all_country_summaries = {}
    all_iron_men = {}

    for cid_str, cdata in sorted(worldwide.items(), key=lambda x: x[1]["country"]["name"]):
        cname = cdata["country"]["name"]
        genitive = cdata.get("genitive", cname)
        cls = classification.get(cid_str, {})
        main_ids = cls.get("main", [])

        if not main_ids:
            print(f"  SKIP {cname} -- no main tournaments")
            continue

        print(f"  Processing {cname} ({len(main_ids)} main)...", end=" ", flush=True)
        stats = compute_country_stats(cdata, main_ids)
        if not stats["tournaments"]:
            print("no data")
            continue

        slug = COUNTRY_SLUGS.get(cname, cname.lower())
        html = build_country_page(stats, cname, genitive)
        if html:
            (OUT_DIR / "countries" / f"{slug}.html").write_text(html, encoding="utf-8")
            n_players = len(stats["player_participations"])
            n_teams = len(set(stats["team_participations"].keys()))
            years = [t["year"] for t in stats["tournaments"]]
            all_country_summaries[cname] = {
                "n_tournaments": len(stats["tournaments"]),
                "n_players": n_players,
                "n_teams": n_teams,
                "year_range": f"{min(years)}--{max(years)}" if years else "?",
            }
            all_iron_men[cname] = stats.get("iron_men", [])
            print(f"OK ({len(html):,} bytes, {len(stats.get('iron_men', []))} iron men)")

    print("\nComputing cross-country stats...", flush=True)
    cross_stats = compute_cross_country_stats(worldwide, classification)
    print(f"  {len(cross_stats['most_countries'])} players across countries")
    print(f"  {len(cross_stats['multi_medalists'])} multi-country medalists")

    print("Building index...", flush=True)
    index_html = build_index_page(all_country_summaries, cross_stats, all_iron_men)
    (OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"Index: {len(index_html):,} bytes")
    print(f"Total: {len(all_country_summaries)} country pages + index")


if __name__ == "__main__":
    main()
