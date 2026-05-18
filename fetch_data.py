#!/usr/bin/env python3
"""Fetch ChVB tournament data from rating.chgk.info API."""

import urllib.request
import json
import time
from pathlib import Path

API = "https://api.rating.chgk.net"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CHVB_IDS = [
    333, 444, 619, 1821, 2091, 2347, 2823, 3214, 3797,
    4255, 4856, 5448, 6114, 7805, 9038, 10237, 11919, 13612,
]


def api_get(path):
    url = f"{API}{path}"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_all():
    data = {}
    for tid in CHVB_IDS:
        print(f"Fetching tournament {tid}...", flush=True)
        info = api_get(f"/tournaments/{tid}")
        results = api_get(f"/tournaments/{tid}/results?includeTeamMembers=1&includeTeamFlags=1")
        data[str(tid)] = {"info": info, "results": results}
        print(f"  {info['name']} ({info['dateStart'][:10]}) -- {len(results)} teams")
        time.sleep(0.3)

    out = DATA_DIR / "chvb_results.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    fetch_all()
