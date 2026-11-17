"""Week 0 step 0.8 helper: check which shows in the seed list have an RSS feed.

Usage:
    source ~/.podcast-recall/podcastindex.env
    uv run python scripts/seed_check.py [data/seed_episodes.csv]

For each unique show in the CSV, prints the top Podcast Index matches with feed
URLs. You then fill in the `has_rss` column (y/n) by hand: a match whose title
looks like the show you listen to means yes. No match means n (video-only).
"""

import csv
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.podcastindex.org/api/1.0"


def search(term: str) -> list[dict]:
    key = os.environ.get("PODCASTINDEX_KEY")
    secret = os.environ.get("PODCASTINDEX_SECRET")
    if not key or not secret:
        raise SystemExit("set PODCASTINDEX_KEY and PODCASTINDEX_SECRET first")
    ts = str(int(time.time()))
    req = urllib.request.Request(
        f"{BASE}/search/byterm?{urllib.parse.urlencode({'q': term, 'max': 3})}",
        headers={
            "User-Agent": "podcast-recall/0.0.1",
            "X-Auth-Key": key,
            "X-Auth-Date": ts,
            "Authorization": hashlib.sha1((key + secret + ts).encode()).hexdigest(),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp).get("feeds", [])


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/seed_episodes.csv")
    if not path.exists():
        raise SystemExit(f"{path} not found")
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    shows = sorted({r["show"].strip() for r in rows if r.get("show", "").strip()})
    print(f"{len(rows)} episodes, {len(shows)} shows\n")
    for show in shows:
        count = sum(1 for r in rows if r["show"].strip() == show)
        feeds = search(show)
        print(f"{show}  ({count} episodes)")
        if not feeds:
            print("  no feed found -> has_rss = n (video-only?)")
        for fd in feeds:
            print(f"  - {fd['title']}  |  {fd['url']}")
        print()


if __name__ == "__main__":
    main()
