"""How one episode gets its transcript, and how the queue is run.

For each job: use the publisher's transcript file if there is a usable one that passes the checks
(decision D13), and otherwise download the audio and run Whisper. Every fallback records why.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from pathlib import Path

from podcast_recall import audio, jobs, paths, publisher, quality, transcripts, whisper_runner
from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.models import JobOutcome, RunResult, TranscribeStatus, Transcript
from podcast_recall.net import DownloadError, SafeFetcher


@dataclass
class Services:
    """Everything that touches the outside world, so tests can replace each piece."""

    fetcher: SafeFetcher = field(default_factory=SafeFetcher)
    transcriber: whisper_runner.Transcriber = whisper_runner.real_transcriber
    prober: Callable[[Path], audio.AudioInfo] = audio.probe_audio
    free_bytes: Callable[[Path], int] | None = None
    clock: Callable[[], float] = time.monotonic


def _language(feed_language: str | None) -> str:
    return quality.primary_language(feed_language)


# ---------------------------------------------------------------------------- one job


def process_job(
    conn: sqlite3.Connection,
    job: sqlite3.Row,
    services: Services,
    now: Callable[[], str],
    *,
    keep_audio: bool = False,
) -> JobOutcome:
    started = services.clock()
    episode_id, title = job["episode_id"], job["title"]
    feed_language, feed_duration = job["feed_language"], job["duration_s"]
    fallback: str | None = None

    if job["force_whisper"]:
        fallback = "forced to Whisper"
    else:
        choice = publisher.pick_transcript(json.loads(job["transcripts_json"] or "[]"), job["transcript_url"])
        if choice is None:
            fallback = "no supported publisher transcript"
        else:
            url, fmt = choice
            jobs.set_state(conn, episode_id, "fetching", now())
            raw_path = paths.raw_transcripts_dir() / f"{episode_id}.{fmt}"
            try:
                text = publisher.download_transcript(services.fetcher, url, raw_path)
                segments = publisher.parse_cues(text, fmt)
            except (ApiError, publisher.TranscriptParseError) as exc:
                fallback = f"publisher transcript unusable: {exc}"
                raw_path.unlink(missing_ok=True)
            else:
                reasons = quality.check_publisher(segments, feed_duration)
                if reasons:
                    fallback = "publisher transcript rejected: " + "; ".join(reasons)
                    raw_path.unlink(missing_ok=True)
                else:
                    transcript = Transcript(
                        episode_id=episode_id, source="publisher", timing_detail="chunk",
                        model=f"publisher:{fmt}", language=_language(feed_language),
                        audio_duration_s=feed_duration, created_at=now(), segments=segments,
                        status="ok", flags=[], publisher_url=None, fallback_reason=None,
                    )
                    transcripts.save_transcript(conn, transcript, raw_path)
                    return JobOutcome(
                        episode_id, title, "publisher", "ok", [], None, services.clock() - started
                    )
    return _whisper_path(conn, job, services, now, keep_audio, fallback, started)


def _whisper_path(
    conn: sqlite3.Connection,
    job: sqlite3.Row,
    services: Services,
    now: Callable[[], str],
    keep_audio: bool,
    fallback: str | None,
    started: float,
) -> JobOutcome:
    episode_id, title = job["episode_id"], job["title"]
    feed_language, feed_duration = job["feed_language"], job["duration_s"]
    directory = paths.audio_dir()
    if services.free_bytes is not None:
        audio.check_disk_space(directory, feed_duration, services.free_bytes)
    else:
        audio.check_disk_space(directory, feed_duration)
    if not job["audio_url"]:
        raise DownloadError("the episode has no audio link")
    jobs.set_state(conn, episode_id, "downloading", now())
    audio_path: Path | None = None
    try:
        audio_path, _info = audio.download_audio(services.fetcher, job["audio_url"], directory, episode_id)
        info = services.prober(audio_path)
        jobs.set_state(conn, episode_id, "transcribing", now())
        model = paths.whisper_model()
        output = whisper_runner.run_whisper(
            str(audio_path), model, paths.whisper_language(), services.transcriber, services.clock
        )
        review = quality.check_whisper(
            output.segments, audio_duration_s=info.duration_s, language=output.language,
            feed_language=feed_language, feed_duration_s=feed_duration,
        )
        status = "needs_review" if review.blocking else "ok"
        transcript = Transcript(
            episode_id=episode_id, source="whisper", timing_detail="word", model=model,
            language=output.language or _language(feed_language), audio_duration_s=round(info.duration_s),
            created_at=now(), segments=output.segments, status=status, flags=review.flags,
            publisher_url=None, fallback_reason=fallback,
        )
        transcripts.save_transcript(conn, transcript, None)
    finally:
        if audio_path is not None and not keep_audio:
            audio_path.unlink(missing_ok=True)
        for leftover in (directory / f"{episode_id}.download", directory / f"{episode_id}.download.part"):
            leftover.unlink(missing_ok=True)
    return JobOutcome(
        episode_id, title, "whisper", status, review.flags, info.duration_s,
        services.clock() - started, fallback,
    )


# ---------------------------------------------------------------------------- the queue


def run_queue(
    conn: sqlite3.Connection,
    services: Services,
    *,
    now: Callable[[], str],
    limit: int | None = None,
    only_episode_ids: Collection[int] | None = None,
    keep_audio: bool = False,
    on_progress: Callable[[dict], None] | None = None,
) -> RunResult:
    """Recover crashed jobs, enqueue matched episodes, then process the due jobs one at a time.

    A failed job is recorded and the run moves on. A setup problem (no disk space, Whisper not
    installed) or Ctrl+C puts the current job back in the queue without using an attempt and
    stops the run.
    """
    recovered = jobs.recover(conn, now())
    enqueued = jobs.enqueue_matched(conn, now(), only_episode_ids)
    todo = jobs.due_jobs(conn, now(), only_episode_ids)
    waiting = jobs.waiting_count(conn, now(), only_episode_ids)
    if limit is not None:
        todo = todo[:limit]
    outcomes: list[JobOutcome] = []
    failures: list[tuple[int, str, str]] = []

    def emit(event: dict) -> None:
        if on_progress:
            on_progress(event)

    for position, job in enumerate(todo, 1):
        episode_id, title = job["episode_id"], job["title"]
        emit({"stage": "start", "position": position, "total": len(todo),
              "episode_id": episode_id, "title": title})
        try:
            outcome = process_job(conn, job, services, now, keep_audio=keep_audio)
        except (KeyboardInterrupt, ConfigError):
            jobs.release(conn, episode_id, now())
            raise
        except ApiError as exc:
            new_state = jobs.record_failure(conn, episode_id, str(exc), now())
            failures.append((episode_id, title, str(exc)))
            emit({"stage": "failed", "episode_id": episode_id, "title": title,
                  "error": str(exc), "state": new_state})
            continue
        except Exception as exc:
            jobs.record_failure(conn, episode_id, f"unexpected error: {type(exc).__name__}", now())
            raise
        jobs.record_success(conn, episode_id, now())
        outcomes.append(outcome)
        emit({"stage": "done", "episode_id": episode_id, "title": title, "source": outcome.source,
              "status": outcome.status, "flags": outcome.flags, "audio_seconds": outcome.audio_seconds,
              "elapsed_s": outcome.elapsed_s, "fallback_reason": outcome.fallback_reason})
    return RunResult(outcomes, failures, waiting, enqueued, recovered)


# ---------------------------------------------------------------------------- status


def _folder_bytes(folder: Path) -> int:
    if not folder.is_dir():
        return 0
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())


def build_status(
    conn: sqlite3.Connection,
    now: str,
    episode_ids: Collection[int] | None = None,
    video_ids: list[str] | None = None,
) -> TranscribeStatus:
    """Counts and problems. With `episode_ids` and `video_ids` the numbers cover only that scope
    (for example the seed list)."""
    scope = set(episode_ids) if episode_ids is not None else set(jobs.matched_episode_ids(conn))
    matched = sorted(scope)

    needs_review: list[tuple[int, str, list[str]]] = []
    ok = 0
    for row in conn.execute(
        "SELECT t.episode_id, t.status, t.flags_json, e.title FROM transcripts t "
        "JOIN episodes e ON e.episode_id = t.episode_id ORDER BY t.episode_id"
    ):
        if row["episode_id"] not in scope:
            continue
        if row["status"] == "ok":
            ok += 1
        else:
            needs_review.append((row["episode_id"], row["title"], json.loads(row["flags_json"] or "[]")))

    queued = waiting = running = 0
    failed: list[tuple[int, str, str]] = []
    for row in conn.execute(
        "SELECT j.episode_id, j.state, j.not_before, j.last_error, e.title FROM jobs j "
        "JOIN episodes e ON e.episode_id = j.episode_id ORDER BY j.episode_id"
    ):
        if row["episode_id"] not in scope:
            continue
        if row["state"] == "failed":
            failed.append((row["episode_id"], row["title"], row["last_error"] or ""))
        elif row["state"] == "queued":
            if row["not_before"] and row["not_before"] > now:
                waiting += 1
            else:
                queued += 1
        elif row["state"] in jobs.RUNNING_STATES:
            running += 1

    if video_ids is not None:
        marks = ",".join("?" * len(video_ids)) or "NULL"
        indexable = {
            r[0] for r in conn.execute(
                f"SELECT DISTINCT video_id FROM episode_matches WHERE status = 'matched' "
                f"AND video_id IN ({marks})", video_ids
            )
        }
        not_indexable = len([v for v in video_ids if v not in indexable])
    else:
        not_indexable = conn.execute(
            "SELECT COUNT(*) FROM episode_matches WHERE status <> 'matched'"
        ).fetchone()[0]

    return TranscribeStatus(
        matched_episodes=len(matched),
        transcripts_ok=ok,
        needs_review=needs_review,
        queued=queued,
        waiting=waiting,
        running=running,
        failed=failed,
        not_indexable_videos=not_indexable,
        missing_files=transcripts.missing_files(conn, scope),
        audio_bytes=_folder_bytes(paths.audio_dir()),
        transcript_bytes=_folder_bytes(paths.transcripts_dir()),
    )
