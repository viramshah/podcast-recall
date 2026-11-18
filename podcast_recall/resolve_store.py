"""SQL for U2: feeds, a channel's feed choice, episodes, and the match of each video."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence

from podcast_recall import matcher
from podcast_recall.models import EpisodeInfo, FeedInfo

CHUNK = 500


def _chunks(items: Sequence, size: int = CHUNK):
    for start in range(0, len(items), size):
        yield list(items[start:start + size])


# ---------------------------------------------------------------------------- feeds


def upsert_feed(conn: sqlite3.Connection, feed: FeedInfo) -> None:
    with conn:
        conn.execute(
            "INSERT INTO feeds (feed_id, title, url, author, language, episode_count_reported) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(feed_id) DO UPDATE SET title = excluded.title, "
            "url = excluded.url, author = excluded.author, language = excluded.language, "
            "episode_count_reported = excluded.episode_count_reported",
            (feed.feed_id, feed.title, feed.url, feed.author, feed.language, feed.episode_count),
        )


def get_feed(conn: sqlite3.Connection, feed_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM feeds WHERE feed_id = ?", (feed_id,)).fetchone()


def newest_published(conn: sqlite3.Connection, feed_id: int) -> int | None:
    row = conn.execute(
        "SELECT MAX(published) FROM episodes WHERE feed_id = ?", (feed_id,)
    ).fetchone()
    return row[0]


def update_feed_fetch(
    conn: sqlite3.Connection, feed_id: int, now: str, truncated: bool | None
) -> None:
    newest = newest_published(conn, feed_id)
    with conn:
        conn.execute(
            "UPDATE feeds SET fetched_at = ?, newest_published = ?, "
            "truncated = COALESCE(?, truncated) WHERE feed_id = ?",
            (now, newest, None if truncated is None else int(truncated), feed_id),
        )


def set_channel_feed(
    conn: sqlite3.Connection, channel_id: str, feed_id: int | None, now: str
) -> None:
    """Record the PM's choice (feed_id None means "none") and drop this channel's unreviewed
    results, which no longer apply."""
    with conn:
        conn.execute(
            "INSERT INTO channel_feeds (channel_id, feed_id, decided_at) VALUES (?, ?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET feed_id = excluded.feed_id, "
            "decided_at = excluded.decided_at",
            (channel_id, feed_id, now),
        )
        conn.execute(
            "DELETE FROM episode_matches WHERE reviewed = 0 AND video_id IN "
            "(SELECT video_id FROM videos WHERE channel_id = ?)",
            (channel_id,),
        )


def get_channel_feed(conn: sqlite3.Connection, channel_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM channel_feeds WHERE channel_id = ?", (channel_id,)
    ).fetchone()


def channel_title(conn: sqlite3.Connection, channel_id: str) -> str | None:
    row = conn.execute("SELECT title FROM channels WHERE channel_id = ?", (channel_id,)).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------- episodes


def save_episodes(
    conn: sqlite3.Connection, feed_id: int, episodes: Iterable[EpisodeInfo], now: str
) -> int:
    """Insert or refresh episodes. Returns how many were not stored before."""
    episodes = list(episodes)
    known: set[int] = set()
    for part in _chunks([e.episode_id for e in episodes]):
        marks = ",".join("?" * len(part))
        known.update(
            r[0] for r in conn.execute(
                f"SELECT episode_id FROM episodes WHERE episode_id IN ({marks})", part
            )
        )
    with conn:
        for e in episodes:
            conn.execute(
                "INSERT INTO episodes (episode_id, feed_id, guid, title, published, duration_s, "
                "audio_url, audio_type, transcript_url, transcripts_json, link, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(episode_id) DO UPDATE SET feed_id = excluded.feed_id, "
                "guid = excluded.guid, title = excluded.title, published = excluded.published, "
                "duration_s = excluded.duration_s, audio_url = excluded.audio_url, "
                "audio_type = excluded.audio_type, transcript_url = excluded.transcript_url, "
                "transcripts_json = excluded.transcripts_json, link = excluded.link, "
                "fetched_at = excluded.fetched_at",
                (
                    e.episode_id, feed_id, e.guid, e.title, e.published, e.duration_s,
                    e.audio_url, e.audio_type, e.transcript_url, json.dumps(e.transcripts),
                    e.link, now,
                ),
            )
    return sum(1 for e in episodes if e.episode_id not in known)


def load_episodes(conn: sqlite3.Connection, feed_id: int) -> list[matcher.PreparedEpisode]:
    rows = conn.execute(
        "SELECT episode_id, title, published, duration_s FROM episodes WHERE feed_id = ?", (feed_id,)
    ).fetchall()
    return [matcher.prepare_episode(r[0], r[1], r[2], r[3]) for r in rows]


def get_episode(conn: sqlite3.Connection, episode_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM episodes WHERE episode_id = ?", (episode_id,)).fetchone()


# ---------------------------------------------------------------------------- videos


def videos_by_ids(conn: sqlite3.Connection, ids: Sequence[str]) -> dict[str, sqlite3.Row]:
    found: dict[str, sqlite3.Row] = {}
    for part in _chunks(list(ids)):
        marks = ",".join("?" * len(part))
        for row in conn.execute(
            "SELECT video_id, title, channel_id, published_at, duration_s, status FROM videos "
            f"WHERE video_id IN ({marks})", part
        ):
            found[row["video_id"]] = row
    return found


def library_video_ids(conn: sqlite3.Connection, user_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT li.video_id FROM library_items li JOIN videos v ON v.video_id = li.video_id "
        "WHERE li.user_id = ? AND v.status = 'ok' ORDER BY li.video_id",
        (user_id,),
    )
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------- matches


def get_match(conn: sqlite3.Connection, video_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM episode_matches WHERE video_id = ?", (video_id,)).fetchone()


def save_match(
    conn: sqlite3.Connection,
    video_id: str,
    decision: matcher.Decision,
    now: str,
    *,
    reviewed: bool = False,
    episode_id: int | None = None,
) -> None:
    """Write a result. A result the PM already reviewed is never overwritten by an automatic one;
    a PM action (`reviewed=True`) always replaces it."""
    best = decision.best
    if episode_id is None and best and decision.status in ("matched", "needs_review"):
        episode_id = best.episode_id
    row = (
        video_id,
        episode_id,
        decision.status, decision.method, decision.reason,
        best.combined if best else None,
        best.title_score if best else None,
        best.date_score if best else None,
        best.duration_score if best else None,
        best.duration_diff_s if best else None,
        decision.margin if best else None,
        json.dumps([s.as_dict() for s in decision.top]),
        int(reviewed), now,
    )
    guard = "" if reviewed else " WHERE episode_matches.reviewed = 0"
    with conn:
        conn.execute(
            "INSERT INTO episode_matches (video_id, episode_id, status, method, reason, score, "
            "title_score, date_score, duration_score, duration_diff_s, margin, candidates_json, "
            "reviewed, resolved_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(video_id) DO UPDATE SET episode_id = excluded.episode_id, "
            "status = excluded.status, method = excluded.method, reason = excluded.reason, "
            "score = excluded.score, title_score = excluded.title_score, "
            "date_score = excluded.date_score, duration_score = excluded.duration_score, "
            "duration_diff_s = excluded.duration_diff_s, margin = excluded.margin, "
            "candidates_json = excluded.candidates_json, reviewed = excluded.reviewed, "
            f"resolved_at = excluded.resolved_at{guard}",
            row,
        )


def review_rows(conn: sqlite3.Connection, ids: Sequence[str]) -> list[sqlite3.Row]:
    """Unreviewed `needs_review` and `unmatched` results for these videos, with titles."""
    rows: list[sqlite3.Row] = []
    for part in _chunks(list(ids)):
        marks = ",".join("?" * len(part))
        rows.extend(
            conn.execute(
                "SELECT m.*, v.title AS video_title, e.title AS episode_title FROM episode_matches m "
                "JOIN videos v ON v.video_id = m.video_id "
                "LEFT JOIN episodes e ON e.episode_id = m.episode_id "
                "WHERE m.reviewed = 0 AND m.status IN ('needs_review', 'unmatched') "
                f"AND m.video_id IN ({marks})", part
            )
        )
    rows.sort(key=lambda r: (r["status"], r["video_title"]))
    return rows
