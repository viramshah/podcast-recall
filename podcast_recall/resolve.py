"""The resolver flows: choose a feed per channel, keep a feed's episodes up to date, match
videos to episodes, and handle the PM's confirm and reject decisions.

No printing here. The CLI formats everything. Podcast Index calls go through the client passed in.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from podcast_recall import ids as video_ids_module
from podcast_recall import matcher, resolve_store
from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.models import (
    ChannelNeedingFeed,
    FeedInfo,
    ResolvedVideo,
    ResolveResult,
)
from podcast_recall.podcastindex import MAX_EPISODES, PodcastIndexClient

STATUSES = ("matched", "needs_review", "unmatched", "no_feed")
SEED_CHECK_COLUMNS = [
    "video_id", "youtube_title", "youtube_date", "youtube_duration_s", "status", "method", "score",
    "episode_id", "episode_title", "episode_date", "episode_duration_s", "duration_diff_s",
    "expected", "auto_check", "correct (y/n)",
]


def to_epoch(iso: str | None) -> int | None:
    """YouTube's `2026-11-15T13:00:12Z` as epoch seconds (UTC)."""
    if not iso:
        return None
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp())


# ---------------------------------------------------------------------------- feeds


def find_feed_candidates(
    conn: sqlite3.Connection, client: PodcastIndexClient, channel_id: str, limit: int = 5
) -> list[FeedInfo]:
    title = resolve_store.channel_title(conn, channel_id)
    if title is None:
        raise ConfigError(f"Channel {channel_id} is not in the database. Run `fetch` or `sync` first.")
    return client.search_feeds(title, max_results=10)[:limit]


def set_channel_feed(
    conn: sqlite3.Connection,
    client: PodcastIndexClient | None,
    channel_id: str,
    ref: str,
    now: str,
) -> FeedInfo | None:
    """Record a channel's feed: `none`, a Podcast Index feed ID, or a feed URL."""
    if resolve_store.channel_title(conn, channel_id) is None:
        raise ConfigError(f"Channel {channel_id} is not in the database. Run `fetch` or `sync` first.")
    ref = ref.strip()
    if ref.lower() == "none":
        resolve_store.set_channel_feed(conn, channel_id, None, now)
        return None
    if client is None:
        raise ConfigError("Podcast Index is needed to look up a feed.")
    feed = client.feed_by_id(int(ref)) if ref.isdigit() else client.feed_by_url(ref)
    if feed is None:
        raise ConfigError(f"Podcast Index does not know the feed {ref!r}.")
    resolve_store.upsert_feed(conn, feed)
    resolve_store.set_channel_feed(conn, channel_id, feed.feed_id, now)
    return feed


def channels_needing_feed(conn: sqlite3.Connection, video_ids: Sequence[str]) -> list[ChannelNeedingFeed]:
    rows = resolve_store.videos_by_ids(conn, video_ids)
    by_channel: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows.values():
        if row["status"] == "ok" and row["channel_id"]:
            by_channel[row["channel_id"]].append(row)
    waiting = []
    for channel_id, videos in by_channel.items():
        if resolve_store.get_channel_feed(conn, channel_id) is None:
            title = resolve_store.channel_title(conn, channel_id) or channel_id
            samples = tuple(v["title"] for v in sorted(videos, key=lambda v: v["title"])[:2])
            waiting.append(ChannelNeedingFeed(channel_id, title, len(videos), samples))
    waiting.sort(key=lambda c: c.title.casefold())
    return waiting


def refresh_feed(
    conn: sqlite3.Connection,
    client: PodcastIndexClient,
    feed_id: int,
    now: str,
    *,
    full: bool = False,
) -> tuple[int, bool]:
    """Bring a feed's episodes up to date: one call for everything the first time, then one call
    for episodes newer than the newest one stored. Returns (new episodes, truncated)."""
    newest = None if full else resolve_store.newest_published(conn, feed_id)
    first = newest is None
    episodes = client.episodes(feed_id, since=newest, max_items=MAX_EPISODES)
    new = resolve_store.save_episodes(conn, feed_id, episodes, now)
    truncated = len(episodes) >= MAX_EPISODES if first else None
    resolve_store.update_feed_fetch(conn, feed_id, now, truncated)
    return new, bool(truncated)


# ---------------------------------------------------------------------------- resolving


def _resolved(video_title: str, video_id: str, decision: matcher.Decision, episode_title: str,
              episode_id: int | None, reviewed: bool = False) -> ResolvedVideo:
    best = decision.best
    return ResolvedVideo(
        video_id=video_id,
        video_title=video_title,
        status=decision.status,
        method=decision.method,
        reason=decision.reason,
        episode_id=episode_id,
        episode_title=episode_title,
        score=best.combined if best else None,
        title_score=best.title_score if best else None,
        date_score=best.date_score if best else None,
        duration_score=best.duration_score if best else None,
        duration_diff_s=best.duration_diff_s if best else None,
        margin=decision.margin if best else None,
        reviewed=reviewed,
    )


def resolve_videos(
    conn: sqlite3.Connection,
    client: PodcastIndexClient | None,
    video_ids: Sequence[str],
    now: str,
    *,
    refresh: bool = True,
    full_refresh: bool = False,
) -> ResolveResult:
    """Match each video to an episode of its channel's feed.

    A channel with no feed decision gets no result (it is listed as waiting). A channel set to
    "none" gives `no_feed`. A result the PM reviewed is never overwritten. A Podcast Index
    failure makes the run partial if anything else could be done, and is raised otherwise.
    """
    ids = list(dict.fromkeys(video_ids))
    rows = resolve_store.videos_by_ids(conn, ids)
    calls_before = dict(client.calls) if client else {}
    result = ResolveResult(
        counts=dict.fromkeys(STATUSES, 0), videos=[], waiting=[], unavailable=[],
        missing=[i for i in ids if i not in rows], kept_reviewed=0, feeds_refreshed=[],
        calls={}, warnings=[],
    )
    by_channel: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for video_id in ids:
        row = rows.get(video_id)
        if row is None:
            continue
        if row["status"] != "ok" or not row["channel_id"]:
            result.unavailable.append(video_id)
            continue
        by_channel[row["channel_id"]].append(row)

    by_feed: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for channel_id, videos in by_channel.items():
        choice = resolve_store.get_channel_feed(conn, channel_id)
        if choice is None:
            title = resolve_store.channel_title(conn, channel_id) or channel_id
            samples = tuple(v["title"] for v in sorted(videos, key=lambda v: v["title"])[:2])
            result.waiting.append(ChannelNeedingFeed(channel_id, title, len(videos), samples))
        elif choice["feed_id"] is None:
            for row in videos:
                _record_no_feed(conn, result, row, now)
        else:
            by_feed[choice["feed_id"]].extend(videos)
    result.waiting.sort(key=lambda c: c.title.casefold())

    feed_failures: list[ApiError] = []
    for feed_id, videos in by_feed.items():
        episodes = resolve_store.load_episodes(conn, feed_id)
        if client is not None and (refresh or not episodes):
            try:
                new, truncated = refresh_feed(conn, client, feed_id, now, full=full_refresh)
                result.feeds_refreshed.append((feed_id, new, truncated))
                if truncated:
                    result.warnings.append(
                        f"Feed {feed_id} returned {MAX_EPISODES} episodes, so older ones may be missing."
                    )
                episodes = resolve_store.load_episodes(conn, feed_id)
            except ApiError as exc:
                feed_failures.append(exc)
                result.partial = True
                result.warnings.append(f"Could not refresh feed {feed_id}: {exc}")
        if not episodes:
            result.warnings.append(f"No episodes are stored for feed {feed_id}; its videos were skipped.")
            result.partial = True
            continue
        for row in videos:
            _resolve_one(conn, result, row, episodes, now)

    if client is not None:
        result.calls = {
            k: v - calls_before.get(k, 0) for k, v in client.calls.items() if v - calls_before.get(k, 0)
        }
    nothing_resolved = not result.videos and not result.kept_reviewed
    if feed_failures and nothing_resolved:
        raise feed_failures[0]
    return result


def _record_no_feed(conn, result: ResolveResult, row: sqlite3.Row, now: str) -> None:
    existing = resolve_store.get_match(conn, row["video_id"])
    if existing is not None and existing["reviewed"]:
        result.kept_reviewed += 1
        return
    decision = matcher.Decision("no_feed", "channel_feed_none", "this channel has no podcast feed",
                                None, 0.0, [])
    resolve_store.save_match(conn, row["video_id"], decision, now)
    result.counts["no_feed"] += 1
    result.videos.append(_resolved(row["title"], row["video_id"], decision, "", None))


def _resolve_one(conn, result: ResolveResult, row: sqlite3.Row,
                 episodes: list[matcher.PreparedEpisode], now: str) -> None:
    existing = resolve_store.get_match(conn, row["video_id"])
    if existing is not None and existing["reviewed"]:
        result.kept_reviewed += 1
        return
    video = matcher.VideoFacts(row["title"], to_epoch(row["published_at"]), row["duration_s"])
    decision = matcher.decide(video, episodes)
    resolve_store.save_match(conn, row["video_id"], decision, now)
    result.counts[decision.status] += 1
    best = decision.best
    shown_id = best.episode_id if best and decision.status in ("matched", "needs_review") else None
    result.videos.append(
        _resolved(row["title"], row["video_id"], decision, best.title if best else "", shown_id)
    )


# ---------------------------------------------------------------------------- PM decisions


def confirm_match(conn: sqlite3.Connection, video_id: str, episode_id: int, now: str) -> ResolvedVideo:
    """The PM says this episode is the right one for this video."""
    rows = resolve_store.videos_by_ids(conn, [video_id])
    if video_id not in rows:
        raise ConfigError(f"Video {video_id} is not in the database.")
    episode = resolve_store.get_episode(conn, episode_id)
    if episode is None:
        raise ConfigError(f"Episode {episode_id} is not in the database. Run `resolve run` first.")
    row = rows[video_id]
    prepared = matcher.prepare_episode(
        episode["episode_id"], episode["title"], episode["published"], episode["duration_s"]
    )
    video = matcher.VideoFacts(row["title"], to_epoch(row["published_at"]), row["duration_s"])
    scored = matcher.score_episode(video, matcher.title_words(video.title), prepared)
    decision = matcher.Decision("matched", "confirmed", "confirmed by the PM", scored, 0.0, [scored])
    resolve_store.save_match(conn, video_id, decision, now, reviewed=True, episode_id=episode_id)
    return _resolved(row["title"], video_id, decision, episode["title"], episode_id, reviewed=True)


def reject_match(conn: sqlite3.Connection, video_id: str, now: str) -> ResolvedVideo:
    """The PM says there is no matching episode."""
    rows = resolve_store.videos_by_ids(conn, [video_id])
    if video_id not in rows:
        raise ConfigError(f"Video {video_id} is not in the database.")
    decision = matcher.Decision("unmatched", "rejected", "rejected by the PM", None, 0.0, [])
    resolve_store.save_match(conn, video_id, decision, now, reviewed=True, episode_id=None)
    return _resolved(rows[video_id]["title"], video_id, decision, "", None, reviewed=True)


def list_review_items(conn: sqlite3.Connection, video_ids: Sequence[str]) -> list[dict]:
    items = []
    for row in resolve_store.review_rows(conn, video_ids):
        items.append(
            {
                "video_id": row["video_id"],
                "video_title": row["video_title"],
                "status": row["status"],
                "method": row["method"],
                "reason": row["reason"],
                "score": row["score"],
                "title_score": row["title_score"],
                "date_score": row["date_score"],
                "duration_score": row["duration_score"],
                "duration_diff_s": row["duration_diff_s"],
                "candidates": json.loads(row["candidates_json"] or "[]"),
            }
        )
    return items


# ---------------------------------------------------------------------------- seed check file


def write_seed_check(conn: sqlite3.Connection, seed_file: Path, out_path: Path) -> int:
    """One row per seed video with its result, the expected outcome from the seed file's
    `has_rss` column, and an empty column for the PM to fill in. Returns the row count."""
    seed_rows = []
    with Path(seed_file).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            video_id = video_ids_module.extract_video_id(row.get("youtube_url") or "")
            if video_id:
                seed_rows.append((video_id, (row.get("has_rss") or "").strip().lower()))
    videos = resolve_store.videos_by_ids(conn, [v for v, _ in seed_rows])
    out_path = Path(out_path)
    # Keep the PM's hand-marked answers when the file is written again.
    marks: dict[str, str] = {}
    if out_path.exists():
        with out_path.open(newline="", encoding="utf-8") as handle:
            for old_row in csv.DictReader(handle):
                marks[old_row.get("video_id", "")] = old_row.get("correct (y/n)", "") or ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SEED_CHECK_COLUMNS)
        for video_id, has_rss in seed_rows:
            video = videos.get(video_id)
            match = resolve_store.get_match(conn, video_id)
            episode = (
                resolve_store.get_episode(conn, match["episode_id"])
                if match is not None and match["episode_id"] is not None else None
            )
            expected = "matched" if has_rss == "y" else "not matched"
            status = match["status"] if match is not None else "no result"
            if match is None:
                auto = "no result"
            elif has_rss == "y":
                auto = "agrees" if status == "matched" else "disagrees"
            else:
                auto = "agrees" if status != "matched" else "disagrees"
            writer.writerow([
                video_id,
                video["title"] if video else "",
                video["published_at"] if video else "",
                video["duration_s"] if video else "",
                status,
                match["method"] if match is not None else "",
                f"{match['score']:.2f}" if match is not None and match["score"] is not None else "",
                episode["episode_id"] if episode else "",
                episode["title"] if episode else "",
                datetime.fromtimestamp(episode["published"]).strftime("%Y-%m-%d")
                if episode and episode["published"] else "",
                episode["duration_s"] if episode else "",
                match["duration_diff_s"] if match is not None and match["duration_diff_s"] is not None else "",
                expected,
                auto,
                marks.get(video_id, ""),
            ])
    return len(seed_rows)
