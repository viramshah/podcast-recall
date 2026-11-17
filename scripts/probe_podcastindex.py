"""U2 probe: find out how the Podcast Index episode endpoints really behave.

The U2 spec says paging, sort order and field formats are unverified, so this throwaway script
asks the real API and records what it finds. Nothing here is product code.

Usage (from the repo root):
    source ~/.podcast-recall/podcastindex.env
    uv run python scripts/probe_podcastindex.py

Prints a short report and writes data/podcastindex_probe.json (public podcast data only, no
credentials). About 25 API calls.
"""

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://api.podcastindex.org/api/1.0"
PAUSE_S = 0.4
OUT = Path("data/podcastindex_probe.json")
DAY = 86400

# (name, feed URL, [(label, text that appears in the episode title)])
FEEDS = [
    (
        "Lenny's Podcast",
        "https://api.substack.com/feed/podcast/10845.rss",
        [("newer seed episode", "lab team"), ("older seed episode", "enterprise deals")],
    ),
    (
        "Startup Ideas Podcast (Greg Isenberg)",
        "https://rss2.flightcast.com/ordbkg8yojpehffas7vr7qpc.xml",
        [
            ("newer seed episode", "too good at marketing"),
            ("older seed episode", "Building AI agents that actually work"),
        ],
    ),
    (
        "Figuring Out (Raj Shamani)",
        "https://anchor.fm/s/f5347ab0/podcast/rss",
        [
            ("newer seed episode", "Communication Makes People Ignore"),
            ("older seed episode", "Diet Expert"),
        ],
    ),
]


def iso(ts) -> str | None:
    if isinstance(ts, int | float) and ts > 0:
        return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return None


def call(path: str, **params) -> dict:
    """One signed GET. Returns {status, body, seconds} and never raises on API errors."""
    key = os.environ.get("PODCASTINDEX_KEY")
    secret = os.environ.get("PODCASTINDEX_SECRET")
    if not key or not secret:
        raise SystemExit("Set PODCASTINDEX_KEY and PODCASTINDEX_SECRET first.")
    stamp = str(int(time.time()))
    request = urllib.request.Request(
        f"{BASE}{path}?{urllib.parse.urlencode(params)}",
        headers={
            "User-Agent": "podcast-recall-probe/0.0.1",
            "X-Auth-Key": key,
            "X-Auth-Date": stamp,
            "Authorization": hashlib.sha1((key + secret + stamp).encode()).hexdigest(),
        },
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = {"status": response.status, "body": json.load(response)}
    except urllib.error.HTTPError as exc:
        result = {"status": exc.code, "body": None, "error": exc.read(300).decode("utf-8", "replace")}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        result = {"status": 0, "body": None, "error": type(exc).__name__}
    result["seconds"] = round(time.time() - started, 2)
    time.sleep(PAUSE_S)
    return result


def items_of(result: dict) -> list[dict]:
    items = (result.get("body") or {}).get("items")
    return items if isinstance(items, list) else []


def brief(episode: dict) -> dict:
    return {
        "title": episode.get("title"),
        "guid": episode.get("guid"),
        "datePublished": episode.get("datePublished"),
        "published_iso": iso(episode.get("datePublished")),
        "duration": episode.get("duration"),
        "enclosureUrl": episode.get("enclosureUrl"),
        "enclosureType": episode.get("enclosureType"),
        "episodeType": episode.get("episodeType"),
    }


def dates_of(items: list[dict]) -> list[int]:
    return [e["datePublished"] for e in items if isinstance(e.get("datePublished"), int)]


def order_of(items: list[dict]) -> str:
    dates = dates_of(items)
    if len(dates) < 2:
        return "not enough items"
    if dates == sorted(dates, reverse=True):
        return "newest first"
    if dates == sorted(dates):
        return "oldest first"
    return "mixed"


def span_of(items: list[dict]) -> dict:
    dates = dates_of(items)
    if not dates:
        return {"count": len(items)}
    return {
        "count": len(items),
        "newest": iso(max(dates)),
        "oldest": iso(min(dates)),
        "order": order_of(items),
    }


def duration_stats(items: list[dict]) -> dict:
    values = [e.get("duration") for e in items]
    numeric = [v for v in values if isinstance(v, int | float)]
    return {
        "types": dict(Counter(type(v).__name__ for v in values)),
        "zero_or_missing": sum(1 for v in values if not v),
        "min_seconds": min(numeric) if numeric else None,
        "max_seconds": max(numeric) if numeric else None,
        "samples": values[:3],
    }


def transcript_stats(items: list[dict]) -> dict:
    """Do publishers offer their own transcripts? (Podcast Index exposes them if so.)"""
    with_url = [e for e in items if e.get("transcriptUrl")]
    with_list = [e for e in items if e.get("transcripts")]
    return {
        "episodes": len(items),
        "with_transcriptUrl": len(with_url),
        "with_transcripts_list": len(with_list),
        "sample_transcriptUrl": with_url[0].get("transcriptUrl") if with_url else None,
        "sample_transcripts": with_list[0].get("transcripts") if with_list else None,
        "feedDead_values": sorted({str(e.get("feedDead")) for e in items}),
        "feedDuplicateOf_values": sorted({str(e.get("feedDuplicateOf")) for e in items}),
    }


def show_around(feed_id: str, date: str, days: int) -> None:
    """List the episodes of a feed published within `days` of `date` (YYYY-MM-DD)."""
    target = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
    items = items_of(call("/episodes/byfeedid", id=feed_id, max=1000))
    window = [e for e in items if abs(e.get("datePublished", 0) - target) <= days * DAY]
    print(f"Feed {feed_id}: {len(items)} episodes in total, {len(window)} within {days} days of {date}")
    for e in window:
        print(f"  {iso(e.get('datePublished'))}  {e.get('duration')} s  {e.get('title')}")


def probe_feed(name: str, url: str, needles: list[tuple[str, str]]) -> dict:
    report: dict = {"name": name, "feed_url": url}

    found = call("/podcasts/byfeedurl", url=url)
    feed = (found.get("body") or {}).get("feed") or {}
    report["byfeedurl"] = {"status": found["status"], "error": found.get("error")}
    report["feed"] = {
        k: feed.get(k) for k in ("id", "title", "episodeCount", "lastUpdateTime", "language")
    }
    feed_id = feed.get("id")
    if not feed_id:
        report["problem"] = "feed not found in Podcast Index"
        return report

    small = call("/episodes/byfeedid", id=feed_id, max=5)
    small_items = items_of(small)
    report["byfeedid_max5"] = {
        "status": small["status"],
        "seconds": small["seconds"],
        **span_of(small_items),
        "fields": sorted(small_items[0].keys()) if small_items else [],
        "first_three": [brief(e) for e in small_items[:3]],
    }

    by_url = call("/episodes/byfeedurl", url=url, max=5)
    by_url_items = items_of(by_url)
    report["byfeedurl_max5"] = {
        "status": by_url["status"],
        "same_guids_as_byfeedid": [e.get("guid") for e in by_url_items]
        == [e.get("guid") for e in small_items],
    }

    full = call("/episodes/byfeedid", id=feed_id, max=1000)
    full_items = items_of(full)
    report["byfeedid_max1000"] = {
        "status": full["status"],
        "seconds": full["seconds"],
        "matches_feed_episodeCount": len(full_items) == feed.get("episodeCount"),
        **span_of(full_items),
        "duplicate_guids": len(full_items) - len({e.get("guid") for e in full_items}),
    }
    report["durations"] = duration_stats(full_items)
    report["transcripts"] = transcript_stats(full_items)

    huge = call("/episodes/byfeedid", id=feed_id, max=5000)
    report["byfeedid_max5000"] = {
        "status": huge["status"],
        "count": len(items_of(huge)),
        "error": huge.get("error"),
    }

    newest = max(dates_of(full_items), default=0)
    if newest:
        since_ts = newest - 60 * DAY
        since = call("/episodes/byfeedid", id=feed_id, max=1000, since=since_ts)
        since_items = items_of(since)
        expected = sum(1 for e in full_items if e.get("datePublished", 0) > since_ts)
        report["since_60_days_before_newest"] = {
            "status": since["status"],
            "since": iso(since_ts),
            "returned": len(since_items),
            "expected_if_filtering_newer_only": expected,
            **span_of(since_items),
        }
        before_ts = newest - 30 * DAY
        before = call("/episodes/byfeedid", id=feed_id, max=1000, before=before_ts)
        before_items = items_of(before)
        report["before_30_days_before_newest"] = {
            "status": before["status"],
            "before": iso(before_ts),
            "returned": len(before_items),
            "all_older_than_before": all(
                e.get("datePublished", 0) < before_ts for e in before_items
            ),
            "looks_supported": 0 < len(before_items) < len(full_items),
        }

    report["needles"] = []
    for label, text in needles:
        hits = [
            (i, e) for i, e in enumerate(full_items) if text.lower() in (e.get("title") or "").lower()
        ]
        report["needles"].append(
            {
                "label": label,
                "text": text,
                "found": bool(hits),
                "position_in_max1000_list": hits[0][0] if hits else None,
                "episode": brief(hits[0][1]) if hits else None,
            }
        )
    return report


def print_summary(report: dict) -> None:
    print(f"\n== {report['name']} ==")
    if report.get("problem"):
        print(f"  PROBLEM: {report['problem']} (byfeedurl status {report['byfeedurl']['status']})")
        return
    feed = report["feed"]
    print(f"  feed id {feed['id']}, '{feed['title']}', episodeCount {feed['episodeCount']}, "
          f"language {feed['language']}")
    small = report["byfeedid_max5"]
    print(f"  max=5: {small['count']} items, {small.get('order')}, newest {small.get('newest')}")
    full = report["byfeedid_max1000"]
    print(f"  max=1000: {full['count']} items ({full.get('order')}), newest {full.get('newest')}, "
          f"oldest {full.get('oldest')}, matches episodeCount: {full['matches_feed_episodeCount']}")
    print(f"  max=5000: status {report['byfeedid_max5000']['status']}, "
          f"{report['byfeedid_max5000']['count']} items")
    print(f"  byfeedurl gives the same episodes as byfeedid: "
          f"{report['byfeedurl_max5']['same_guids_as_byfeedid']}")
    d = report["durations"]
    print(f"  durations: types {d['types']}, zero/missing {d['zero_or_missing']}, "
          f"min {d['min_seconds']}, max {d['max_seconds']}, samples {d['samples']}")
    t = report["transcripts"]
    print(f"  publisher transcripts: {t['with_transcriptUrl']} of {t['episodes']} episodes have "
          f"transcriptUrl, {t['with_transcripts_list']} have a transcripts list, "
          f"sample {t['sample_transcriptUrl']}")
    if "since_60_days_before_newest" in report:
        s = report["since_60_days_before_newest"]
        print(f"  since={s['since']}: returned {s['returned']} (newer-only would be "
              f"{s['expected_if_filtering_newer_only']}), order {s.get('order')}")
        b = report["before_30_days_before_newest"]
        print(f"  before=...: status {b['status']}, returned {b['returned']}, "
              f"looks supported: {b['looks_supported']}")
    for needle in report["needles"]:
        if needle["found"]:
            ep = needle["episode"]
            print(f"  {needle['label']}: found at position {needle['position_in_max1000_list']}, "
                  f"'{ep['title']}', {ep['published_iso']}, duration {ep['duration']}")
        else:
            print(f"  {needle['label']}: NOT FOUND in the max=1000 list ('{needle['text']}')")


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe the Podcast Index episode endpoints.")
    parser.add_argument(
        "--around", nargs="+", metavar="ARG",
        help="FEED_ID DATE [DAYS]: list episodes near a date, for example 4458228 2026-03-17 7",
    )
    args = parser.parse_args()
    if args.around:
        show_around(args.around[0], args.around[1], int(args.around[2]) if len(args.around) > 2 else 7)
        return
    reports = []
    for name, url, needles in FEEDS:
        report = probe_feed(name, url, needles)
        print_summary(report)
        reports.append(report)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"probed_at": iso(time.time()), "feeds": reports}, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
