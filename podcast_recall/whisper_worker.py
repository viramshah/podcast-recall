"""Runs Whisper in its own process so the main program can stop it if it takes too long.

Usage (done by `whisper_runner`, not by hand):
    python -m podcast_recall.whisper_worker AUDIO MODEL LANGUAGE OUT_JSON

LANGUAGE is empty to detect it. The result is written to OUT_JSON. Exit code 3 means the
mlx-whisper package is missing.
"""

from __future__ import annotations

import json
import sys

EXIT_MISSING_PACKAGE = 3


def main(argv: list[str]) -> int:
    audio_path, model, language, out_path = argv
    try:
        import mlx_whisper
    except ImportError:
        return EXIT_MISSING_PACKAGE
    options: dict = {"word_timestamps": True, "condition_on_previous_text": False}
    if language:
        options["language"] = language
    result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=model, **options)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
