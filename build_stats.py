#!/usr/bin/env python3
"""Build ChVB (Чемпионат Великобритании) statistics HTML from cached API data."""

import json
from collections import defaultdict
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "chvb_results.json"
OUTPUT_PATH = Path(__file__).parent / "chvb_stats.html"

UK_TOWN_IDS = {178, 1686, 1736, 1737, 1760, 1767, 1770, 1806, 1917, 1924, 2281}
TOURNAMENT_IDS = [333, 444, 619, 1821, 2091, 2347, 2823, 3214, 3797, 4255, 4856, 5448, 6114, 7805, 9038, 10237, 11919, 13612]

CHST_FLAG_ID = 50  # "Зачёт чемпионата страны"

# 2026: flags not yet set in API; manual overrides
VNE_ZACHETA = {
    13612: {79988},  # Совет в Финчлях -- вне зачёта
}
V_ZACHETE = {
    13612: {98778},  # Tulip Grove Defenders -- в зачёте ЧВБ (город "сборная", но играли в зачёт)
}


def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)


def get_town_id(team):
    town = team.get("town") or {}
    return town.get("id", 0)


def get_town_name(team):
    town = team.get("town") or {}
    return town.get("name", "?")


def is_uk(team):
    return get_town_id(team) in UK_TOWN_IDS


def in_chvb_zachet(result, tournament_id):
    """Determine if a team is in ЧВБ standings for this tournament.

    Priority:
    1. Manual overrides (VNE_ZACHETA) -- known вне зачёта teams
    2. ЧСт flag (id=50) in API -- authoritative when present
    3. Fallback to UK town filter -- for older tournaments without flags
    """
    team_id = result["team"]["id"]
    flags = result.get("flags", [])
    flag_ids = {f["id"] for f in flags}

    if tournament_id in VNE_ZACHETA and team_id in VNE_ZACHETA[tournament_id]:
        return False
    if tournament_id in V_ZACHETE and team_id in V_ZACHETE[tournament_id]:
        return True

    all_flags_in_tournament = any(CHST_FLAG_ID in {f["id"] for f in r.get("flags", [])}
                                   for r in _current_results)
    if all_flags_in_tournament:
        return CHST_FLAG_ID in flag_ids

    return is_uk(result["team"])


_current_results = []


def compute_stats(data):
    player_names = {}
    player_wins_overall = defaultdict(list)
    player_wins_uk = defaultdict(list)
    player_podiums_overall = defaultdict(list)
    player_podiums_uk = defaultdict(list)
    player_participations = defaultdict(list)

    team_wins_overall = defaultdict(list)
    team_wins_uk = defaultdict(list)
    team_participations = defaultdict(list)

    tournaments_summary = []

    for tid in TOURNAMENT_IDS:
        td = data[str(tid)]
        info = td["info"]
        results = td["results"]
        year = info["dateStart"][:4]
        qd = info.get("questionQty")
        q_total = sum(qd.values()) if isinstance(qd, dict) else 0

        results.sort(key=lambda x: float(x.get("position") or 999))

        global _current_results
        _current_results = results

        chvb_results = [r for r in results if in_chvb_zachet(r, tid)]

        overall_winner = results[0]["team"]["name"] if results else "?"
        chvb_winner = chvb_results[0]["team"]["name"] if chvb_results else "?"
        overall_winner_score = results[0].get("questionsTotal") or 0
        chvb_winner_score = chvb_results[0].get("questionsTotal") or 0
        chvb_winner_overall_pos = float(chvb_results[0].get("position") or 0) if chvb_results else 0

        tournaments_summary.append({
            "id": tid,
            "year": year,
            "name": info["name"],
            "teams_total": len(results),
            "teams_uk": len(chvb_results),
            "questions": q_total,
            "overall_winner": overall_winner,
            "overall_winner_score": overall_winner_score,
            "uk_winner": chvb_winner,
            "uk_winner_score": chvb_winner_score,
            "uk_winner_overall_pos": chvb_winner_overall_pos,
            "results": [],
        })

        for r in results:
            team = r["team"]
            town_name = get_town_name(team)
            pos = r.get("position") or 999
            total = r.get("questionsTotal") or 0
            in_zachet = in_chvb_zachet(r, tid)

            tournaments_summary[-1]["results"].append({
                "pos": pos,
                "team": team["name"],
                "town": town_name,
                "total": total,
                "is_uk": in_zachet,
            })

            team_participations[team["name"]].append(year)

            for member in r.get("teamMembers", []):
                pid = member["player"]["id"]
                pname = f'{member["player"]["name"]} {member["player"]["surname"]}'
                player_names[pid] = pname
                player_participations[pid].append({"year": year, "team": team["name"], "pos": pos})

        # Overall winner players
        for r in results:
            if float(r.get("position") or 999) == 1:
                team_wins_overall[r["team"]["name"]].append(year)
                for m in r.get("teamMembers", []):
                    player_wins_overall[m["player"]["id"]].append((year, r["team"]["name"]))

        # Overall podium
        for r in results:
            if float(r.get("position") or 999) <= 3:
                for m in r.get("teamMembers", []):
                    player_podiums_overall[m["player"]["id"]].append((year, r["team"]["name"], float(r.get("position") or 999)))

        # ЧВБ winner / podium
        if chvb_results:
            best_pos = float(chvb_results[0].get("position") or 999)
            for r in chvb_results:
                if float(r.get("position") or 999) == best_pos:
                    team_wins_uk[r["team"]["name"]].append(year)
                    for m in r.get("teamMembers", []):
                        player_wins_uk[m["player"]["id"]].append((year, r["team"]["name"]))
            for i, r in enumerate(chvb_results[:3], 1):
                for m in r.get("teamMembers", []):
                    player_podiums_uk[m["player"]["id"]].append((year, r["team"]["name"], i))

    return {
        "player_names": player_names,
        "player_wins_overall": player_wins_overall,
        "player_wins_uk": player_wins_uk,
        "player_podiums_overall": player_podiums_overall,
        "player_podiums_uk": player_podiums_uk,
        "player_participations": player_participations,
        "team_wins_overall": team_wins_overall,
        "team_wins_uk": team_wins_uk,
        "team_participations": team_participations,
        "tournaments": tournaments_summary,
    }


def build_html(stats):
    tournaments = stats["tournaments"]
    pn = stats["player_names"]

    # Top players by UK wins
    top_uk_winners = sorted(stats["player_wins_uk"].items(), key=lambda x: -len(x[1]))
    top_uk_podiums = sorted(stats["player_podiums_uk"].items(), key=lambda x: (-len(x[1]), -len(stats["player_wins_uk"].get(x[0], []))))
    top_overall_winners = sorted(stats["player_wins_overall"].items(), key=lambda x: -len(x[1]))
    top_participations = sorted(stats["player_participations"].items(), key=lambda x: -len(x[1]))

    # Top teams
    top_team_wins_uk = sorted(stats["team_wins_uk"].items(), key=lambda x: -len(x[1]))
    top_team_wins_overall = sorted(stats["team_wins_overall"].items(), key=lambda x: -len(x[1]))
    top_team_parts = sorted(stats["team_participations"].items(), key=lambda x: -len(x[1]))

    years = [t["year"] for t in tournaments]

    def medal(pos):
        if pos == 1: return "🥇"
        if pos == 2: return "🥈"
        if pos == 3: return "🥉"
        return ""

    def bar(val, max_val, color="#1877F2"):
        pct = (val / max_val * 100) if max_val else 0
        return f'<div class="bar" style="width:{pct}%;background:{color}"></div>'

    html = []
    html.append("""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ЧВБ -- Статистика Чемпионатов Великобритании по ЧГК</title>
<style>
:root {
  --bg: #0a0e1a;
  --card: #151d30;
  --card-border: #1e2a45;
  --text: #e0e6f0;
  --text-muted: #8892a8;
  --accent: #1877F2;
  --gold: #f59e0b;
  --silver: #94a3b8;
  --bronze: #cd7f32;
  --green: #02e2ac;
  --red: #ef4444;
  --purple: #a855f7;
  --uk-badge: #1877F2;
}
[data-theme="light"] {
  --bg: #f0f2f5;
  --card: #ffffff;
  --card-border: #dde1e6;
  --text: #1c1e21;
  --text-muted: #65676b;
  --accent: #1877F2;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  padding: 0;
}
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

/* Header */
header {
  background: linear-gradient(135deg, #0a1628 0%, #162544 100%);
  padding: 40px 20px;
  text-align: center;
  border-bottom: 3px solid var(--accent);
}
[data-theme="light"] header {
  background: linear-gradient(135deg, #e8f0fe 0%, #d2e3fc 100%);
}
header h1 { font-size: 2em; margin-bottom: 8px; }
header h1 span { color: var(--accent); }
header p { color: var(--text-muted); font-size: 1.1em; }

/* Theme toggle */
.theme-toggle {
  position: fixed; top: 16px; right: 16px; z-index: 100;
  background: var(--card); border: 1px solid var(--card-border);
  color: var(--text); padding: 8px 14px; border-radius: 20px;
  cursor: pointer; font-size: 14px;
}

/* Nav */
nav {
  position: sticky; top: 0; z-index: 50;
  background: var(--card); border-bottom: 1px solid var(--card-border);
  padding: 10px 20px; display: flex; gap: 8px; flex-wrap: wrap;
  justify-content: center;
}
nav a {
  color: var(--text-muted); text-decoration: none; padding: 6px 14px;
  border-radius: 16px; font-size: 13px; transition: all 0.2s;
}
nav a:hover, nav a.active { background: var(--accent); color: #fff; }

/* Cards */
.card {
  background: var(--card); border: 1px solid var(--card-border);
  border-radius: 12px; padding: 24px; margin-bottom: 20px;
}
.card h2 { font-size: 1.3em; margin-bottom: 16px; color: var(--accent); }
.card h3 { font-size: 1.1em; margin: 16px 0 8px; }

/* Stats grid */
.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 20px;
}
.stat-box {
  background: var(--bg); border-radius: 8px; padding: 16px; text-align: center;
}
.stat-box .num { font-size: 2em; font-weight: 700; color: var(--accent); }
.stat-box .label { font-size: 0.85em; color: var(--text-muted); }

/* Tables */
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--card-border); color: var(--text-muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 6px 10px; border-bottom: 1px solid var(--card-border); }
tr:hover { background: rgba(24,119,242,0.05); }
.pos { font-weight: 700; width: 40px; text-align: center; }
.score { text-align: right; font-weight: 600; }
.uk-badge { display: inline-block; background: var(--uk-badge); color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 8px; margin-left: 4px; }
.team-name { font-weight: 500; }
.town { color: var(--text-muted); font-size: 13px; }
.year-tag { display: inline-block; background: var(--bg); padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 1px; }

/* Bar chart */
.bar-row { display: flex; align-items: center; margin: 4px 0; gap: 8px; }
.bar-label { min-width: 180px; font-size: 13px; text-align: right; }
.bar-track { flex: 1; height: 24px; background: var(--bg); border-radius: 4px; overflow: hidden; position: relative; }
.bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
.bar-value { font-size: 12px; min-width: 30px; font-weight: 600; }

/* Timeline */
.timeline { display: flex; gap: 2px; flex-wrap: wrap; margin: 8px 0; }
.timeline .dot {
  width: 24px; height: 24px; border-radius: 4px; display: flex;
  align-items: center; justify-content: center; font-size: 10px; font-weight: 700;
}
.dot.gold { background: var(--gold); color: #000; }
.dot.silver { background: var(--silver); color: #000; }
.dot.bronze { background: var(--bronze); color: #fff; }
.dot.played { background: var(--card-border); color: var(--text-muted); }
.dot.empty { background: transparent; border: 1px dashed var(--card-border); color: var(--text-muted); }

/* Section */
section { scroll-margin-top: 60px; }
section h2 { padding: 20px 0 10px; font-size: 1.4em; }

/* Tabs */
.tabs { display: flex; gap: 4px; margin-bottom: 16px; }
.tab {
  padding: 6px 16px; border-radius: 8px; cursor: pointer;
  background: var(--bg); color: var(--text-muted); font-size: 13px; border: none;
}
.tab.active { background: var(--accent); color: #fff; }

/* Tournament detail toggle */
.toggle-btn {
  background: none; border: 1px solid var(--card-border); color: var(--text-muted);
  padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; margin-top: 8px;
}
.toggle-btn:hover { border-color: var(--accent); color: var(--accent); }
.details { display: none; margin-top: 12px; }
.details.open { display: block; }

/* Responsive */
@media (max-width: 600px) {
  .bar-label { min-width: 120px; font-size: 12px; }
  header h1 { font-size: 1.4em; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>
<button class="theme-toggle" onclick="toggleTheme()">🌙 / ☀️</button>
""")

    html.append("""
<header>
  <h1>🏆 <span>ЧВБ</span> -- Чемпионат Великобритании по ЧГК</h1>
  <p>Полная статистика 2008--2026 | rating.chgk.info</p>
</header>

<nav>
  <a href="#overview">Обзор</a>
  <a href="#champions">Чемпионы</a>
  <a href="#players">Игроки</a>
  <a href="#teams">Команды</a>
  <a href="#tournaments">Турниры</a>
</nav>
""")

    html.append('<div class="container">')

    # === OVERVIEW ===
    total_teams = sum(t["teams_total"] for t in tournaments)
    total_players = len(stats["player_participations"])
    total_uk = sum(t["teams_uk"] for t in tournaments)
    max_teams = max(t["teams_total"] for t in tournaments)
    max_teams_year = [t["year"] for t in tournaments if t["teams_total"] == max_teams][0]

    html.append(f"""
<section id="overview">
<div class="card">
  <h2>Обзор</h2>
  <div class="stats-grid">
    <div class="stat-box"><div class="num">{len(tournaments)}</div><div class="label">турниров</div></div>
    <div class="stat-box"><div class="num">{total_players}</div><div class="label">игроков</div></div>
    <div class="stat-box"><div class="num">{total_teams}</div><div class="label">команд-участий</div></div>
    <div class="stat-box"><div class="num">{max_teams}</div><div class="label">макс. команд ({max_teams_year})</div></div>
  </div>

  <h3>Рост турнира</h3>
""")

    max_t = max(t["teams_total"] for t in tournaments)
    for t in tournaments:
        pct = t["teams_total"] / max_t * 100
        uk_pct = t["teams_uk"] / max_t * 100
        html.append(f"""
  <div class="bar-row">
    <div class="bar-label">{t['year']}</div>
    <div class="bar-track">
      <div class="bar" style="width:{pct}%;background:var(--accent);opacity:0.4;position:absolute"></div>
      <div class="bar" style="width:{uk_pct}%;background:var(--accent);position:absolute"></div>
    </div>
    <div class="bar-value">{t['teams_total']} ({t['teams_uk']} UK)</div>
  </div>""")

    html.append("</div></section>")

    # === CHAMPIONS ===
    html.append("""
<section id="champions">
<div class="card">
  <h2>Чемпионы по годам</h2>
  <table>
    <tr><th>Год</th><th>Чемпион (общий)</th><th>Взято</th><th>Чемпион UK</th><th>Взято</th><th>Место UK в общем</th><th>Команд</th></tr>
""")
    for t in tournaments:
        uk_pos = t["uk_winner_overall_pos"]
        pos_str = str(int(uk_pos)) if uk_pos == int(uk_pos) else str(uk_pos)
        same = t["overall_winner"] == t["uk_winner"]
        highlight = "" if same else ' style="color:var(--gold)"'
        html.append(f"""    <tr>
      <td class="pos">{t['year']}</td>
      <td class="team-name">{t['overall_winner']}</td>
      <td class="score">{t['overall_winner_score'] or '—'}</td>
      <td class="team-name"{highlight}>{t['uk_winner']}</td>
      <td class="score">{t['uk_winner_score'] or '—'}</td>
      <td class="pos">{pos_str}</td>
      <td class="pos">{t['teams_total']}</td>
    </tr>""")
    html.append("</table></div></section>")

    # === PLAYERS ===
    html.append("""<section id="players"><div class="card"><h2>Игроки -- победы (зачёт UK)</h2>""")

    # Bar chart -- UK wins
    max_wins = len(top_uk_winners[0][1]) if top_uk_winners else 1
    for pid, wins in top_uk_winners[:20]:
        if len(wins) < 1:
            break
        years_html = " ".join(f'<span class="year-tag">{y} <small>({t})</small></span>' for y, t in wins)
        html.append(f"""
  <div class="bar-row">
    <div class="bar-label">{pn[pid]}</div>
    <div class="bar-track">{bar(len(wins), max_wins, '#f59e0b')}</div>
    <div class="bar-value">{len(wins)}</div>
  </div>""")

    html.append("</div>")

    # Podiums UK
    html.append('<div class="card"><h2>Игроки -- подиумы (зачёт UK, топ-3)</h2>')
    html.append("<table><tr><th>#</th><th>Игрок</th><th>Подиумов</th><th>Побед</th><th>Детали</th></tr>")
    for rank, (pid, podiums) in enumerate(top_uk_podiums[:25], 1):
        if len(podiums) < 2:
            break
        wins = len(stats["player_wins_uk"].get(pid, []))
        details = " ".join(f'<span class="year-tag">{medal(p)}{y}</span>' for y, t, p in podiums)
        html.append(f'<tr><td class="pos">{rank}</td><td class="team-name">{pn[pid]}</td><td class="score">{len(podiums)}</td><td class="score">{wins}</td><td>{details}</td></tr>')
    html.append("</table></div>")

    # Most participations
    html.append('<div class="card"><h2>Игроки -- больше всего ЧВБ</h2>')
    html.append("<table><tr><th>#</th><th>Игрок</th><th>Турниров</th><th>Годы</th></tr>")
    for rank, (pid, parts) in enumerate(top_participations[:25], 1):
        if len(parts) < 5:
            break
        yrs = sorted(set(p["year"] for p in parts))
        yrs_html = " ".join(f'<span class="year-tag">{y}</span>' for y in yrs)
        html.append(f'<tr><td class="pos">{rank}</td><td class="team-name">{pn[pid]}</td><td class="score">{len(parts)}</td><td>{yrs_html}</td></tr>')
    html.append("</table></div></section>")

    # === TEAMS ===
    html.append('<section id="teams"><div class="card"><h2>Команды -- победы (зачёт UK)</h2>')
    max_tw = len(top_team_wins_uk[0][1]) if top_team_wins_uk else 1
    for team, wins_years in top_team_wins_uk[:15]:
        if not wins_years:
            break
        yrs = ", ".join(wins_years)
        html.append(f"""
  <div class="bar-row">
    <div class="bar-label">{team}</div>
    <div class="bar-track">{bar(len(wins_years), max_tw, '#02e2ac')}</div>
    <div class="bar-value">{len(wins_years)}</div>
  </div>""")
    html.append("</div>")

    html.append('<div class="card"><h2>Команды -- участия</h2>')
    html.append("<table><tr><th>#</th><th>Команда</th><th>Турниров</th><th>Годы</th></tr>")
    for rank, (team, yrs) in enumerate(top_team_parts[:20], 1):
        if len(yrs) < 3:
            break
        unique_yrs = sorted(set(yrs))
        yrs_html = " ".join(f'<span class="year-tag">{y}</span>' for y in unique_yrs)
        html.append(f'<tr><td class="pos">{rank}</td><td class="team-name">{team}</td><td class="score">{len(unique_yrs)}</td><td>{yrs_html}</td></tr>')
    html.append("</table></div></section>")

    # === TOURNAMENTS ===
    html.append('<section id="tournaments"><div class="card"><h2>Все турниры -- подробные результаты</h2></div>')

    for t in tournaments:
        results = t["results"]
        html.append(f"""
<div class="card">
  <h3>{t['name']} {t['year']}</h3>
  <p style="color:var(--text-muted);font-size:13px">{t['teams_total']} команд | {t['questions']} вопросов | ID {t['id']}</p>
  <table>
    <tr><th>М</th><th>Команда</th><th>Город</th><th>Взято</th><th></th></tr>
""")
        for r in results:
            pos = r["pos"]
            pos_str = str(int(pos)) if pos == int(pos) else str(pos)
            uk_mark = '<span class="uk-badge">UK</span>' if r["is_uk"] else ""
            score = r["total"] if r["total"] else "—"
            md = medal(pos)
            html.append(f'    <tr><td class="pos">{md} {pos_str}</td><td class="team-name">{r["team"]}{uk_mark}</td><td class="town">{r["town"]}</td><td class="score">{score}</td><td></td></tr>')
        html.append("</table></div>")

    html.append("</section>")

    # Footer
    html.append("""
</div>
<footer style="text-align:center;padding:40px 20px;color:var(--text-muted);font-size:13px">
  Данные: <a href="https://rating.chgk.info" style="color:var(--accent)">rating.chgk.info</a> API |
  Собрано автоматически | 2026
</footer>

<script>
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}
(function() {
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
})();

document.querySelectorAll('nav a').forEach(a => {
  a.addEventListener('click', function() {
    document.querySelectorAll('nav a').forEach(x => x.classList.remove('active'));
    this.classList.add('active');
  });
});
</script>
</body>
</html>""")

    return "\n".join(html)


def main():
    data = load_data()
    stats = compute_stats(data)
    html = build_html(stats)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Saved to {OUTPUT_PATH} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
