#!/usr/bin/env python3
"""Fetch national championship data for all countries from rating.chgk.info API."""

import urllib.request
import urllib.parse
import json
import time
from pathlib import Path

API = "https://api.rating.chgk.net"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Country name -> genitive form for searching "Чемпионат {genitive}"
# The API does substring search, so we use the genitive stem
COUNTRY_SEARCH = {
    2: "Австралии",
    3: "Азербайджана",
    4: "Армении",
    5: "Беларуси",
    6: "Бельгии",
    7: "Болгарии",
    8: "Великобритании",
    9: "Германии",
    10: "Грузии",
    11: "Израиля",
    12: "Италии",
    13: "Казахстана",
    14: "Канады",
    15: "Кубы",
    16: "Кыргызстана",
    17: "Латвии",
    18: "Литвы",
    19: "Молдовы",
    20: "Нидерландов",
    21: "России",
    22: "США",
    23: "Туркменистана",
    24: "Турции",
    25: "Узбекистана",
    26: "Украины",
    27: "Финляндии",
    28: "Франции",
    29: "Чехии",
    30: "Швеции",
    31: "Эстонии",
}


def api_get(path):
    url = f"{API}{path}"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def search_tournaments(country_genitive):
    params = urllib.parse.urlencode({
        "itemsPerPage": 100,
        "name": f"Чемпионат {country_genitive}",
    })
    url = f"{API}/tournaments?{params}"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_country_towns(country_id):
    """Get all towns for a country."""
    params = urllib.parse.urlencode({"country": country_id, "itemsPerPage": 500})
    url = f"{API}/towns?{params}"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_all():
    # Step 1: Get country list
    countries = api_get("/countries")
    print(f"Found {len(countries)} countries\n")

    all_data = {}

    for country in countries:
        cid = country["id"]
        cname = country["name"]
        genitive = COUNTRY_SEARCH.get(cid)

        if not genitive:
            print(f"SKIP {cname} (id={cid}) -- no genitive form mapped")
            continue

        print(f"\n{'='*60}")
        print(f"Country: {cname} (id={cid})")
        print(f"{'='*60}")

        # Step 2: Find championship tournaments
        tournaments = search_tournaments(genitive)

        # Filter: only exact national championships (not city/region championships)
        # Keep tournaments whose name is exactly "Чемпионат {genitive}" or has
        # a roman numeral prefix, or "Открытый Чемпионат {genitive}"
        target = f"Чемпионат {genitive}"
        filtered = []
        for t in tournaments:
            name = t["name"].strip()
            # Accept: "Чемпионат X", "N Чемпионат X", "Открытый чемпионат X",
            #         "N Открытый Чемпионат X по ..."
            name_lower = name.lower()
            target_lower = target.lower()
            if target_lower in name_lower:
                # Reject if it's a sub-championship (city/region within country)
                # e.g., "Чемпионат Украины. Первая лига" -- keep
                # e.g., "Чемпионат Россия по бла" -- keep
                # But skip things like "Чемпионат Москвы" when searching for Russia
                filtered.append(t)

        # Sort by date
        filtered.sort(key=lambda x: x.get("dateStart", ""))

        if not filtered:
            print(f"  No championship tournaments found")
            continue

        print(f"  Found {len(filtered)} championship tournaments")

        # Step 3: Get towns for this country (for zachet determination)
        towns = get_country_towns(cid)
        town_ids = {t["id"] for t in towns}
        print(f"  {len(towns)} towns in country")
        time.sleep(0.2)

        # Step 4: Fetch results for each tournament
        tournament_data = {}
        for t in filtered:
            tid = t["id"]
            print(f"  Fetching {tid}: {t['name']} ({t['dateStart'][:10]})...", end=" ", flush=True)
            try:
                results = api_get(f"/tournaments/{tid}/results?includeTeamMembers=1&includeTeamFlags=1")
                tournament_data[str(tid)] = {
                    "info": t,
                    "results": results,
                }
                print(f"{len(results)} teams")
            except Exception as e:
                print(f"ERROR: {e}")
            time.sleep(0.3)

        all_data[str(cid)] = {
            "country": country,
            "genitive": genitive,
            "towns": towns,
            "town_ids": list(town_ids),
            "tournaments": tournament_data,
        }

    # Save all data
    out = DATA_DIR / "worldwide_results.json"
    out.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n\nSaved to {out} ({out.stat().st_size:,} bytes)")

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for cid_str, cdata in sorted(all_data.items(), key=lambda x: x[1]["country"]["name"]):
        cname = cdata["country"]["name"]
        n_tournaments = len(cdata["tournaments"])
        print(f"  {cname:25s} {n_tournaments:3d} championships")


if __name__ == "__main__":
    fetch_all()
