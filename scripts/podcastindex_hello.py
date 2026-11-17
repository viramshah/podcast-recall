"""Week 0 step 0.6 pass test: search Podcast Index for a show.

Usage:
    export PODCASTINDEX_KEY=... PODCASTINDEX_SECRET=...
    uv run python scripts/podcastindex_hello.py [search term]

Standard library only. Credentials come from environment variables and are
never printed or written to disk.
"""

import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://api.podcastindex.org/api/1.0"


def get(path: str, params: dict) -> dict:
    key = os.environ.get("PODCASTINDEX_KEY")
    secret = os.environ.get("PODCASTINDEX_SECRET")
    if not key or not secret:
        raise SystemExit("set PODCASTINDEX_KEY and PODCASTINDEX_SECRET first")

    ts = str(int(time.time()))
    auth = hashlib.sha1((key + secret + ts).encode()).hexdigest()
    req = urllib.request.Request(
        f"{BASE}{path}?{urllib.parse.urlencode(params)}",
        headers={
            "User-Agent": "podcast-recall/0.0.1",
            "X-Auth-Key": key,
            "X-Auth-Date": ts,
            "Authorization": auth,
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def main() -> None:
    term = sys.argv[1] if len(sys.argv) > 1 else "huberman"
    data = get("/search/byterm", {"q": term, "max": 5})
    feeds = data.get("feeds", [])
    print(f"status: {data.get('status')}  feeds returned: {len(feeds)}")
    for f in feeds:
        print(f"  - {f['title']}  |  {f['url']}")


if __name__ == "__main__":
    main()
