"""Run Whisper on an audio file and return segments with word times.

The actual Whisper call can be replaced in tests, so no test loads a model. The language is
detected by default and never forced to English (decision D11).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass

from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.models import Segment, Word
from podcast_recall.whisper_worker import EXIT_MISSING_PACKAGE

Transcriber = Callable[[str, str, str | None, float], dict]

TIMEOUT_FRACTION = 0.5  # of the audio length...
TIMEOUT_EXTRA_S = 300  # ...plus this
TIMEOUT_MIN_S = 600


class WhisperTimeout(ApiError):
    """Whisper ran past its time limit and was stopped (decision D16)."""


@dataclass
class WhisperOutput:
    segments: list[Segment]
    language: str
    seconds: float


def timeout_for(audio_seconds: float) -> float:
    """Half the audio length plus 5 minutes, never under 10 minutes."""
    return max(float(TIMEOUT_MIN_S), TIMEOUT_FRACTION * audio_seconds + TIMEOUT_EXTRA_S)


def real_transcriber(
    path: str, model: str, language: str | None, timeout_s: float, runner=subprocess.run
) -> dict:
    """Run Whisper in a separate process (see `whisper_worker`) so it can be stopped. Word
    timestamps are on and `condition_on_previous_text` is off, which reduces repeated-text loops.
    The process's progress messages (for example a first model download) are left visible."""
    with tempfile.TemporaryDirectory() as folder:
        out_path = os.path.join(folder, "result.json")
        command = [
            sys.executable, "-m", "podcast_recall.whisper_worker", path, model, language or "", out_path,
        ]
        try:
            completed = runner(command, stdout=subprocess.DEVNULL, timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired:
            raise WhisperTimeout(
                f"Whisper ({model.rsplit('/', 1)[-1]}) took longer than {int(timeout_s // 60)} minutes "
                "and was stopped"
            ) from None
        if completed.returncode == EXIT_MISSING_PACKAGE:
            raise ConfigError("mlx-whisper is not installed. Run `uv sync`.")
        if completed.returncode != 0 or not os.path.exists(out_path):
            raise ApiError(f"Whisper stopped with an error (exit code {completed.returncode})")
        with open(out_path, encoding="utf-8") as handle:
            return json.load(handle)


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
    *,
    timeout_s: float = float(TIMEOUT_MIN_S),
) -> WhisperOutput:
    started = clock()
    try:
        raw = transcriber(audio_path, model, language, timeout_s)
    except (ConfigError, ApiError):
        raise
    except Exception as exc:
        raise ApiError(f"Whisper could not transcribe the audio ({type(exc).__name__})") from exc
    return WhisperOutput(to_segments(raw), (raw.get("language") or "").strip(), clock() - started)
