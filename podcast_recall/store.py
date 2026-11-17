"""SQLite access: connection settings, migrations, and every query the connector needs.

Shared tables: `channels`, `videos`. Per-user tables carry `user_id` and are removed when the
user row is deleted. Later units add their own numbered migration files.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path

from podcast_recall.models import ChannelInfo, ChannelRow, PlaylistInfo, VideoInfo

KEEP_BACKUPS = 3
DESCRIPTION_LIMIT = 500


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def cutoff(now_iso: str, days: int) -> str:
    """The timestamp `days` before `now_iso` (same format), for comparing last-fetched times."""
    moment = datetime.strptime(now_iso, "%Y-%m-%dT%H:%M:%SZ")
    return (moment - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _chunks(items: Sequence, size: int) -> Iterator[Sequence]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


# ---------------------------------------------------------------------------- connection


def _db_file(conn: sqlite3.Connection) -> Path | None:
    for _, name, file in conn.execute("PRAGMA database_list"):
        if name == "main" and file:
            return Path(file)
    return None


def connect(path: Path | str, backup_dir: Path | None = None) -> sqlite3.Connection:
    """Open the database (WAL mode, foreign keys on, 5-second busy timeout) and migrate it."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    db_file = _db_file(conn)
    if db_file is not None and db_file.exists():
        os.chmod(db_file, 0o600)
    migrate(conn, backup_dir)
    return conn


def _migration_files() -> list[tuple[int, str, str]]:
    folder = resources.files("podcast_recall") / "migrations"
    found = []
    for entry in folder.iterdir():
        if entry.name.endswith(".sql"):
            found.append((int(entry.name.split("_", 1)[0]), entry.name, entry.read_text("utf-8")))
    return sorted(found)


def migrate(conn: sqlite3.Connection, backup_dir: Path | None = None) -> None:
    """Apply numbered migration files in order, each inside one transaction.

    Before upgrading an existing database, back it up with SQLite's backup feature (not a file
    copy, which is unsafe while the database is open) and keep the three most recent backups.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    conn.commit()
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_version")}
    pending = [m for m in _migration_files() if m[0] not in applied]
    if not pending:
        return
    db_file = _db_file(conn)
    if applied and db_file is not None and backup_dir is not None:
        _backup(conn, Path(backup_dir), max(applied))
    for version, _name, sql in pending:
        script = (
            f"BEGIN;\n{sql}\n"
            f"INSERT INTO schema_version (version, applied_at) VALUES ({version}, '{utc_now()}');\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script)
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise


def _backup(conn: sqlite3.Connection, backup_dir: Path, version: int) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    dest = backup_dir / f"podcast_recall-v{version}-{stamp}.db"
    target = sqlite3.connect(str(dest))
    try:
        conn.backup(target)
    finally:
        target.close()
    os.chmod(dest, 0o600)
    for old in sorted(backup_dir.glob("podcast_recall-v*.db"))[:-KEEP_BACKUPS]:
        old.unlink()
    return dest


# ---------------------------------------------------------------------------- users


def get_user(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def upsert_user(conn: sqlite3.Connection, user_id: str, channel_id: str, title: str, now: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO users (user_id, youtube_channel_id, youtube_channel_title, created_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
            "youtube_channel_id = excluded.youtube_channel_id, "
            "youtube_channel_title = excluded.youtube_channel_title",
            (user_id, channel_id, title, now),
        )


def clear_user_data(conn: sqlite3.Connection, user_id: str) -> None:
    """Delete a user's library, channels, playlists and run history but keep the user row."""
    with conn:
        for table in ("library_items", "user_channels", "playlists", "sync_runs"):
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))


def delete_user(conn: sqlite3.Connection, user_id: str) -> None:
    """Delete the user row; foreign keys cascade to every per-user table."""
    with conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


# ---------------------------------------------------------------------------- channels


def upsert_channel(
    conn: sqlite3.Connection, channel_id: str, title: str, now: str, uploads: str | None = None
) -> None:
    """Insert or refresh a shared channel row. Does not commit: call inside `with conn`."""
    conn.execute(
        "INSERT INTO channels (channel_id, title, uploads_playlist_id, updated_at) "
        "VALUES (?, ?, ?, ?) ON CONFLICT(channel_id) DO UPDATE SET "
        "title = CASE WHEN excluded.title <> '' THEN excluded.title ELSE channels.title END, "
        "uploads_playlist_id = COALESCE(excluded.uploads_playlist_id, channels.uploads_playlist_id), "
        "updated_at = excluded.updated_at",
        (channel_id, title, uploads, now),
    )


def apply_subscriptions(
    conn: sqlite3.Connection, user_id: str, subs: Iterable[ChannelInfo], now: str
) -> list[str]:
    """Record a COMPLETE subscription listing. Returns the channel IDs that are no longer
    subscribed. Only call this after the whole listing succeeded."""
    subs = list(subs)
    current = {s.channel_id for s in subs}
    with conn:
        for sub in subs:
            upsert_channel(conn, sub.channel_id, sub.title, now, sub.uploads_playlist_id)
            conn.execute(
                "INSERT INTO user_channels (user_id, channel_id, subscribed, is_podcast) "
                "VALUES (?, ?, 1, 0) ON CONFLICT(user_id, channel_id) DO UPDATE SET subscribed = 1",
                (user_id, sub.channel_id),
            )
        gone = [
            row[0]
            for row in conn.execute(
                "SELECT channel_id FROM user_channels WHERE user_id = ? AND subscribed = 1",
                (user_id,),
            )
            if row[0] not in current
        ]
        for channel_id in gone:
            conn.execute(
                "UPDATE user_channels SET subscribed = 0 WHERE user_id = ? AND channel_id = ?",
                (user_id, channel_id),
            )
    return gone


def channel_rows(conn: sqlite3.Connection, user_id: str) -> list[ChannelRow]:
    """Subscribed channels, marked ones first, then alphabetical."""
    rows = conn.execute(
        "SELECT uc.channel_id, c.title, uc.subscribed, uc.is_podcast FROM user_channels uc "
        "JOIN channels c ON c.channel_id = uc.channel_id WHERE uc.user_id = ? AND uc.subscribed = 1",
        (user_id,),
    ).fetchall()
    result = [ChannelRow(r[0], r[1], bool(r[2]), bool(r[3])) for r in rows]
    result.sort(key=lambda c: (not c.is_podcast, c.title.casefold(), c.channel_id))
    return result


def get_user_channel(conn: sqlite3.Connection, user_id: str, channel_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM user_channels WHERE user_id = ? AND channel_id = ?", (user_id, channel_id)
    ).fetchone()


def set_podcast_flag(conn: sqlite3.Connection, user_id: str, channel_id: str, value: bool) -> None:
    with conn:
        conn.execute(
            "UPDATE user_channels SET is_podcast = ? WHERE user_id = ? AND channel_id = ?",
            (1 if value else 0, user_id, channel_id),
        )


def effective_podcast_channels(conn: sqlite3.Connection, user_id: str) -> list[ChannelInfo]:
    """Channels that are both subscribed and marked as podcast."""
    rows = conn.execute(
        "SELECT uc.channel_id, c.title, c.uploads_playlist_id FROM user_channels uc "
        "JOIN channels c ON c.channel_id = uc.channel_id "
        "WHERE uc.user_id = ? AND uc.subscribed = 1 AND uc.is_podcast = 1 ORDER BY c.title",
        (user_id,),
    ).fetchall()
    return [ChannelInfo(r[0], r[1], r[2]) for r in rows]


def save_channel_infos(conn: sqlite3.Connection, infos: Iterable[ChannelInfo], now: str) -> None:
    with conn:
        for info in infos:
            upsert_channel(conn, info.channel_id, info.title, now, info.uploads_playlist_id)


def remove_inactive_channel_items(conn: sqlite3.Connection, user_id: str) -> dict[str, int]:
    """Remove `channel:<id>` items for channels that are no longer marked or subscribed."""
    active = {c.channel_id for c in effective_podcast_channels(conn, user_id)}
    removed: dict[str, int] = {}
    sources = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT source FROM library_items WHERE user_id = ? AND source LIKE 'channel:%'",
            (user_id,),
        )
    ]
    with conn:
        for source in sources:
            if source[len("channel:"):] not in active:
                cur = conn.execute(
                    "DELETE FROM library_items WHERE user_id = ? AND source = ?", (user_id, source)
                )
                removed[source] = cur.rowcount
    return removed


# ---------------------------------------------------------------------------- playlists


def apply_playlists(
    conn: sqlite3.Connection, user_id: str, playlists: Iterable[PlaylistInfo], now: str
) -> dict[str, int]:
    """Record a COMPLETE playlist listing. Playlists that no longer exist are dropped together
    with their library items. Returns {source: items removed} for the dropped playlists."""
    playlists = list(playlists)
    current = {p.playlist_id for p in playlists}
    removed: dict[str, int] = {}
    with conn:
        for p in playlists:
            conn.execute(
                "INSERT INTO playlists (user_id, playlist_id, title, refreshed_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, playlist_id) DO UPDATE SET title = excluded.title, "
                "refreshed_at = excluded.refreshed_at",
                (user_id, p.playlist_id, p.title, now),
            )
        known = [r[0] for r in conn.execute(
            "SELECT playlist_id FROM playlists WHERE user_id = ?", (user_id,))]
        for playlist_id in known:
            if playlist_id in current:
                continue
            source = f"playlist:{playlist_id}"
            cur = conn.execute(
                "DELETE FROM library_items WHERE user_id = ? AND source = ?", (user_id, source)
            )
            conn.execute(
                "DELETE FROM playlists WHERE user_id = ? AND playlist_id = ?", (user_id, playlist_id)
            )
            removed[source] = cur.rowcount
    return removed


def list_playlists(conn: sqlite3.Connection, user_id: str) -> list[PlaylistInfo]:
    rows = conn.execute(
        "SELECT playlist_id, title FROM playlists WHERE user_id = ? ORDER BY title, playlist_id",
        (user_id,),
    ).fetchall()
    return [PlaylistInfo(r[0], r[1]) for r in rows]


# ---------------------------------------------------------------------------- videos


def videos_needing_fetch(conn: sqlite3.Connection, ids: Sequence[str], cutoff: str) -> list[str]:
    """IDs not stored yet, or stored but last fetched before `cutoff`. Order is preserved."""
    fresh: set[str] = set()
    for part in _chunks(list(ids), 500):
        marks = ",".join("?" * len(part))
        for row in conn.execute(
            f"SELECT video_id FROM videos WHERE last_fetched_at >= ? AND video_id IN ({marks})",
            (cutoff, *part),
        ):
            fresh.add(row[0])
    return [i for i in ids if i not in fresh]


def video_status_map(conn: sqlite3.Connection, ids: Sequence[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in _chunks(list(ids), 500):
        marks = ",".join("?" * len(part))
        for row in conn.execute(
            f"SELECT video_id, status FROM videos WHERE video_id IN ({marks})", tuple(part)
        ):
            result[row[0]] = row[1]
    return result


def save_videos(
    conn: sqlite3.Connection, requested: Sequence[str], found: Iterable[VideoInfo], now: str
) -> list[str]:
    """Store videos returned by `videos.list`. Requested IDs that were not returned (deleted,
    private or mistyped) are stored as `unavailable`. Returns those IDs."""
    found = list(found)
    returned = {v.video_id for v in found}
    missing = [i for i in requested if i not in returned]
    with conn:
        for v in found:
            upsert_channel(conn, v.channel_id, v.channel_title, now)
            conn.execute(
                "INSERT INTO videos (video_id, title, channel_id, published_at, duration_s, "
                "description, status, unavailable_reason, is_live_or_upcoming, last_fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'ok', NULL, ?, ?) "
                "ON CONFLICT(video_id) DO UPDATE SET title = excluded.title, "
                "channel_id = excluded.channel_id, published_at = excluded.published_at, "
                "duration_s = excluded.duration_s, description = excluded.description, "
                "status = 'ok', unavailable_reason = NULL, "
                "is_live_or_upcoming = excluded.is_live_or_upcoming, "
                "last_fetched_at = excluded.last_fetched_at",
                (
                    v.video_id, v.title, v.channel_id, v.published_at, v.duration_s,
                    v.description[:DESCRIPTION_LIMIT], 1 if v.is_live_or_upcoming else 0, now,
                ),
            )
        for video_id in missing:
            conn.execute(
                "INSERT INTO videos (video_id, status, unavailable_reason, last_fetched_at) "
                "VALUES (?, 'unavailable', ?, ?) ON CONFLICT(video_id) DO UPDATE SET "
                "status = 'unavailable', unavailable_reason = excluded.unavailable_reason, "
                "last_fetched_at = excluded.last_fetched_at",
                (video_id, UNAVAILABLE_REASON, now),
            )
    return missing


UNAVAILABLE_REASON = "not returned by YouTube (deleted, private or wrong ID)"


# ---------------------------------------------------------------------------- library items


def library_video_ids(conn: sqlite3.Connection, user_id: str, source: str) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT video_id FROM library_items WHERE user_id = ? AND source = ?", (user_id, source)
        )
    }


def apply_source(
    conn: sqlite3.Connection,
    user_id: str,
    source: str,
    add: Iterable[str],
    remove: Iterable[str],
    now: str,
) -> None:
    """Add and remove one source's items in a single transaction."""
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO library_items (user_id, video_id, source, first_seen_at) "
            "VALUES (?, ?, ?, ?)",
            [(user_id, v, source, now) for v in add],
        )
        conn.executemany(
            "DELETE FROM library_items WHERE user_id = ? AND source = ? AND video_id = ?",
            [(user_id, source, v) for v in remove],
        )


# ---------------------------------------------------------------------------- runs and status


def record_sync_run(
    conn: sqlite3.Connection,
    user_id: str,
    started: str,
    finished: str,
    result: str,
    reason: str | None,
    counts: dict,
    units: int,
    error: str | None = None,
) -> int | None:
    if get_user(conn, user_id) is None:
        return None
    with conn:
        cur = conn.execute(
            "INSERT INTO sync_runs (user_id, started_at, finished_at, result, reason, counts_json, "
            "estimated_units, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, started, finished, result, reason, json.dumps(counts), units, error),
        )
    return cur.lastrowid


def last_sync_run(conn: sqlite3.Connection, user_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM sync_runs WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["counts"] = json.loads(data.pop("counts_json") or "{}")
    return data


def library_counts(conn: sqlite3.Connection, user_id: str) -> tuple[int, list[tuple[str, int]], int]:
    """(unique videos, [(source label, count)], unavailable videos in the library)."""
    unique = conn.execute(
        "SELECT COUNT(DISTINCT video_id) FROM library_items WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    per_source = []
    for source, count in conn.execute(
        "SELECT source, COUNT(*) FROM library_items WHERE user_id = ? GROUP BY source", (user_id,)
    ).fetchall():
        per_source.append((source_label(conn, user_id, source), count))
    per_source.sort(key=lambda item: item[0].casefold())
    unavailable = conn.execute(
        "SELECT COUNT(DISTINCT li.video_id) FROM library_items li JOIN videos v "
        "ON v.video_id = li.video_id WHERE li.user_id = ? AND v.status = 'unavailable'",
        (user_id,),
    ).fetchone()[0]
    return unique, per_source, unavailable


def source_label(conn: sqlite3.Connection, user_id: str, source: str) -> str:
    if source == "liked":
        return "Liked videos"
    kind, _, key = source.partition(":")
    if kind == "playlist":
        row = conn.execute(
            "SELECT title FROM playlists WHERE user_id = ? AND playlist_id = ?", (user_id, key)
        ).fetchone()
        return f"Playlist: {row[0] or key}" if row else f"Playlist: {key}"
    if kind == "channel":
        row = conn.execute("SELECT title FROM channels WHERE channel_id = ?", (key,)).fetchone()
        return f"Channel: {row[0] or key}" if row else f"Channel: {key}"
    return source


def purge(conn: sqlite3.Connection, cutoff: str) -> tuple[int, int]:
    """Delete video rows last fetched before `cutoff` that no other table refers to by foreign
    key. Returns (deleted, kept). Foreign keys do the protecting, so later units only need to
    declare their references to `videos`."""
    old = [r[0] for r in conn.execute("SELECT video_id FROM videos WHERE last_fetched_at < ?", (cutoff,))]
    deleted = kept = 0
    for video_id in old:
        try:
            with conn:
                conn.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
            deleted += 1
        except sqlite3.IntegrityError:
            kept += 1
    return deleted, kept
