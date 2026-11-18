"""The transcription queue, kept in SQLite.

States: queued, fetching (a publisher file), downloading (audio), transcribing, done, failed.
A failed attempt goes back to `queued` with a not-before time. After the third failed attempt the
job is `failed`. A crash returns a running job to `queued` without using an attempt.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Collection, Sequence
from datetime import datetime, timedelta

from podcast_recall import publisher
from podcast_recall.errors import ConfigError

MAX_ATTEMPTS = 3
BACKOFF_MINUTES = (2, 10)  # wait after the first and the second failure
RUNNING_STATES = ("fetching", "downloading", "transcribing")
_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def plus_minutes(now_iso: str, minutes: int) -> str:
    return (datetime.strptime(now_iso, _FORMAT) + timedelta(minutes=minutes)).strftime(_FORMAT)


# ---------------------------------------------------------------------------- enqueueing


def matched_episode_ids(conn: sqlite3.Connection, video_ids: Sequence[str] | None = None) -> list[int]:
    """Episodes with at least one `matched` result, optionally only for these videos."""
    if video_ids is None:
        rows = conn.execute(
            "SELECT DISTINCT episode_id FROM episode_matches WHERE status = 'matched' "
            "AND episode_id IS NOT NULL ORDER BY episode_id"
        )
        return [r[0] for r in rows]
    found: set[int] = set()
    ids = list(video_ids)
    for start in range(0, len(ids), 500):
        part = ids[start:start + 500]
        marks = ",".join("?" * len(part))
        found.update(
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT episode_id FROM episode_matches WHERE status = 'matched' "
                f"AND episode_id IS NOT NULL AND video_id IN ({marks})", part
            )
        )
    return sorted(found)


def enqueue_matched(
    conn: sqlite3.Connection, now: str, only_episode_ids: Collection[int] | None = None
) -> int:
    """Add a job for each matched episode that has no job and no transcript. Returns how many.
    Unreviewed, unmatched and no-feed results are never enqueued."""
    candidates = [
        e for e in matched_episode_ids(conn)
        if only_episode_ids is None or e in only_episode_ids
    ]
    have_job = {r[0] for r in conn.execute("SELECT episode_id FROM jobs")}
    have_transcript = {r[0] for r in conn.execute("SELECT episode_id FROM transcripts")}
    new = [e for e in candidates if e not in have_job and e not in have_transcript]
    with conn:
        conn.executemany(
            "INSERT INTO jobs (episode_id, state, attempts, force_whisper, created_at, updated_at) "
            "VALUES (?, 'queued', 0, 0, ?, ?)",
            [(e, now, now) for e in new],
        )
    return len(new)


# ---------------------------------------------------------------------------- choosing work


_JOB_QUERY = (
    "SELECT j.*, e.title, e.duration_s, e.audio_url, e.transcript_url, e.transcripts_json, "
    "e.feed_id, f.language AS feed_language FROM jobs j "
    "JOIN episodes e ON e.episode_id = j.episode_id JOIN feeds f ON f.feed_id = e.feed_id "
)


def due_jobs(
    conn: sqlite3.Connection, now: str, only_episode_ids: Collection[int] | None = None
) -> list[sqlite3.Row]:
    """Queued jobs that are due, in the order they should run: jobs with a usable publisher
    transcript first (they take seconds), then Whisper jobs, shortest episode first."""
    rows = conn.execute(
        _JOB_QUERY + "WHERE j.state = 'queued' AND (j.not_before IS NULL OR j.not_before <= ?)", (now,)
    ).fetchall()
    rows = [r for r in rows if only_episode_ids is None or r["episode_id"] in only_episode_ids]

    def key(row: sqlite3.Row):
        usable = not row["force_whisper"] and publisher.pick_transcript(
            json.loads(row["transcripts_json"] or "[]"), row["transcript_url"]
        )
        return (0 if usable else 1, row["duration_s"] or 10**9, row["episode_id"])

    return sorted(rows, key=key)


def waiting_count(
    conn: sqlite3.Connection, now: str, only_episode_ids: Collection[int] | None = None
) -> int:
    rows = conn.execute(
        "SELECT episode_id FROM jobs WHERE state = 'queued' AND not_before IS NOT NULL AND not_before > ?",
        (now,),
    )
    return sum(1 for r in rows if only_episode_ids is None or r[0] in only_episode_ids)


# ---------------------------------------------------------------------------- state changes


def set_state(conn: sqlite3.Connection, episode_id: int, state: str, now: str) -> None:
    with conn:
        conn.execute(
            "UPDATE jobs SET state = ?, updated_at = ?, "
            "started_at = CASE WHEN ? IN ('fetching', 'downloading', 'transcribing') "
            "AND state = 'queued' THEN ? ELSE started_at END WHERE episode_id = ?",
            (state, now, state, now, episode_id),
        )


def record_success(conn: sqlite3.Connection, episode_id: int, now: str) -> None:
    with conn:
        conn.execute(
            "UPDATE jobs SET state = 'done', last_error = NULL, not_before = NULL, "
            "updated_at = ?, finished_at = ? WHERE episode_id = ?",
            (now, now, episode_id),
        )


def record_failure(conn: sqlite3.Connection, episode_id: int, error: str, now: str) -> str:
    """One failed attempt. Returns the new state (`queued` to try again later, or `failed`)."""
    row = conn.execute("SELECT attempts FROM jobs WHERE episode_id = ?", (episode_id,)).fetchone()
    attempts = (row[0] if row else 0) + 1
    if attempts >= MAX_ATTEMPTS:
        state, not_before, finished = "failed", None, now
    else:
        state, not_before, finished = "queued", plus_minutes(now, BACKOFF_MINUTES[attempts - 1]), None
    with conn:
        conn.execute(
            "UPDATE jobs SET state = ?, attempts = ?, not_before = ?, last_error = ?, updated_at = ?, "
            "finished_at = ? WHERE episode_id = ?",
            (state, attempts, not_before, error[:500], now, finished, episode_id),
        )
    return state


def release(conn: sqlite3.Connection, episode_id: int, now: str) -> None:
    """Put a job back in the queue without using an attempt (interrupted or a setup problem)."""
    with conn:
        conn.execute(
            "UPDATE jobs SET state = 'queued', updated_at = ? WHERE episode_id = ? AND state <> 'done'",
            (now, episode_id),
        )


def recover(conn: sqlite3.Connection, now: str) -> int:
    """After a crash: jobs left running go back to the queue. Uses no attempt."""
    marks = ",".join("?" * len(RUNNING_STATES))
    with conn:
        cur = conn.execute(
            f"UPDATE jobs SET state = 'queued', updated_at = ? WHERE state IN ({marks})",
            (now, *RUNNING_STATES),
        )
    return cur.rowcount


def retry(conn: sqlite3.Connection, episode_id: int, force_whisper: bool, now: str) -> None:
    """Start a job again with a fresh set of attempts. Creates it if it does not exist."""
    if conn.execute("SELECT 1 FROM episodes WHERE episode_id = ?", (episode_id,)).fetchone() is None:
        raise ConfigError(f"Episode {episode_id} is not in the database.")
    with conn:
        conn.execute(
            "INSERT INTO jobs (episode_id, state, attempts, force_whisper, created_at, updated_at) "
            "VALUES (?, 'queued', 0, ?, ?, ?) ON CONFLICT(episode_id) DO UPDATE SET state = 'queued', "
            "attempts = 0, not_before = NULL, last_error = NULL, force_whisper = excluded.force_whisper, "
            "updated_at = excluded.updated_at, finished_at = NULL",
            (episode_id, int(force_whisper), now, now),
        )
