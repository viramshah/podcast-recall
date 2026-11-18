"""Run Whisper on an audio file and return segments with word times.

The actual Whisper call can be replaced in tests, so no test loads a model. The language is
detected by default and never forced to English (decision D11).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.models import Segment, Word

Transcriber = Callable[[str, str, str | None], dict]


@dataclass
class WhisperOutput:
    segments: list[Segment]
    language: str
    seconds: float


def real_transcriber(path: str, model: str, language: str | None) -> dict:
    """The real call: word timestamps on, and `condition_on_previous_text` off, which reduces
    long repeated-text loops on long audio."""
    try:
        import mlx_whisper
    except ImportError:
        raise ConfigError("mlx-whisper is not installed. Run `uv sync`.") from None
    options: dict = {"word_timestamps": True, "condition_on_previous_text": False}
    if language:
        options["language"] = language
    return mlx_whisper.transcribe(path, path_or_hf_repo=model, **options)


def to_segments(raw: dict) -> list[Segment]:
    segments: list[Segment] = []
    for item in raw.get("segments") or []:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        words = [
            Word(w["word"].strip(), float(w["start"]), float(w["end"]))
            for w in item.get("words") or []
            if (w.get("word") or "").strip()
        ]
        segments.append(Segment(float(item["start"]), float(item["end"]), text, None, words))
    return segments


def run_whisper(
    audio_path: str,
    model: str,
    language: str | None = None,
    transcriber: Transcriber = real_transcriber,
    clock: Callable[[], float] = time.monotonic,
) -> WhisperOutput:
    started = clock()
    try:
        raw = transcriber(audio_path, model, language)
    except (ConfigError, ApiError):
        raise
    except Exception as exc:
        raise ApiError(f"Whisper could not transcribe the audio ({type(exc).__name__})") from exc
    return WhisperOutput(to_segments(raw), (raw.get("language") or "").strip(), clock() - started)
