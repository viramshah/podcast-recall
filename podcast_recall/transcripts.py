"""Reading and writing transcripts: the JSON file (the contract with U4) and its database row.

Files are written to a temporary name and then renamed, so a crash never leaves a half-written
transcript that looks finished.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from podcast_recall import paths, quality
from podcast_recall.errors import ConfigError
from podcast_recall.models import Segment, Transcript, Word

# ---------------------------------------------------------------------------- conversion


def segment_to_dict(seg: Segment) -> dict:
    data: dict = {"start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text}
    if seg.speaker:
        data["speaker"] = seg.speaker
    data["words"] = [
        {"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3)} for w in seg.words
    ]
    return data


def segment_from_dict(data: dict) -> Segment:
    words = [Word(w["text"], float(w["start"]), float(w["end"])) for w in data.get("words") or []]
    return Segment(float(data["start"]), float(data["end"]), data["text"], data.get("speaker"), words)


def transcript_to_dict(t: Transcript) -> dict:
    return {
        "episode_id": t.episode_id,
        "source": t.source,
        "timing_detail": t.timing_detail,
        "model": t.model,
        "language": t.language,
        "audio_duration_s": t.audio_duration_s,
        "created_at": t.created_at,
        "segments": [segment_to_dict(s) for s in t.segments],
    }


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def relative(path: Path) -> str:
    """A path inside the data folder, stored relative to it so the folder can be moved."""
    return str(path.relative_to(paths.data_home()))


# ---------------------------------------------------------------------------- database


def save_transcript(conn: sqlite3.Connection, t: Transcript, raw_path: Path | None = None) -> Path:
    """Write the transcript file, then its database row (replacing any earlier transcript of
    this episode). Returns the file's path."""
    target = paths.transcripts_dir() / f"{t.episode_id}.json"
    write_atomic(target, json.dumps(transcript_to_dict(t), indent=1, ensure_ascii=False))
    with conn:
        conn.execute(
            "INSERT INTO transcripts (episode_id, path, raw_path, source, timing_detail, model, "
            "language, audio_duration_s, transcript_end_s, word_count, status, flags_json, "
            "publisher_url, fallback_reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(episode_id) DO UPDATE SET path = excluded.path, raw_path = excluded.raw_path, "
            "source = excluded.source, timing_detail = excluded.timing_detail, model = excluded.model, "
            "language = excluded.language, audio_duration_s = excluded.audio_duration_s, "
            "transcript_end_s = excluded.transcript_end_s, word_count = excluded.word_count, "
            "status = excluded.status, flags_json = excluded.flags_json, "
            "publisher_url = excluded.publisher_url, fallback_reason = excluded.fallback_reason, "
            "created_at = excluded.created_at",
            (
                t.episode_id, relative(target), relative(raw_path) if raw_path else None, t.source,
                t.timing_detail, t.model, t.language, t.audio_duration_s,
                quality.end_time(t.segments), quality.word_count(t.segments), t.status,
                json.dumps(t.flags), t.publisher_url, t.fallback_reason, t.created_at,
            ),
        )
    return target


def get_row(conn: sqlite3.Connection, episode_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM transcripts WHERE episode_id = ?", (episode_id,)).fetchone()


def load_transcript(conn: sqlite3.Connection, episode_id: int) -> Transcript | None:
    """The stored transcript, or None if the episode has none. Raises if the row exists but its
    file is missing."""
    row = get_row(conn, episode_id)
    if row is None:
        return None
    path = paths.data_home() / row["path"]
    if not path.is_file():
        raise ConfigError(
            f"The transcript file for episode {episode_id} is missing. "
            f"Rebuild it with: podcast-recall transcribe retry {episode_id}"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return Transcript(
        episode_id=data["episode_id"],
        source=data["source"],
        timing_detail=data["timing_detail"],
        model=data.get("model", ""),
        language=data.get("language", ""),
        audio_duration_s=data.get("audio_duration_s"),
        created_at=data.get("created_at", ""),
        segments=[segment_from_dict(s) for s in data.get("segments") or []],
        status=row["status"],
        flags=json.loads(row["flags_json"] or "[]"),
        publisher_url=row["publisher_url"],
        fallback_reason=row["fallback_reason"],
    )


def accept(conn: sqlite3.Connection, episode_id: int) -> None:
    """Mark a transcript `ok` after a human has looked at it."""
    if get_row(conn, episode_id) is None:
        raise ConfigError(f"Episode {episode_id} has no transcript to accept.")
    with conn:
        conn.execute("UPDATE transcripts SET status = 'ok' WHERE episode_id = ?", (episode_id,))


def window_segments(
    transcript: Transcript, at: float, window: float
) -> list[tuple[float, float, str]]:
    """The segments that overlap the stretch from `at - window` to `at + window` seconds."""
    low, high = at - window, at + window
    return [(s.start, s.end, s.text) for s in transcript.segments if s.end >= low and s.start <= high]


def missing_files(conn: sqlite3.Connection, episode_ids: Iterable[int] | None = None) -> list[int]:
    wanted = set(episode_ids) if episode_ids is not None else None
    missing = []
    for row in conn.execute("SELECT episode_id, path FROM transcripts ORDER BY episode_id"):
        if wanted is not None and row["episode_id"] not in wanted:
            continue
        if not (paths.data_home() / row["path"]).is_file():
            missing.append(row["episode_id"])
    return missing
