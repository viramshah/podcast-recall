"""Week 0 step 0.4: transcribe one audio file with word-level timestamps.

Usage:
    uv run python scripts/transcribe_test.py path/to/clip.mp3 [--model REPO] [--out data/transcripts/clip.json]

Prints the real-time factor (RTF): seconds of compute per second of audio.
RTF 0.1 means a 1-hour episode takes about 6 minutes.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

import mlx_whisper

DEFAULT_MODEL = "mlx-community/whisper-small-mlx"


def audio_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("audio", type=Path)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    duration = audio_seconds(args.audio)
    start = time.time()
    result = mlx_whisper.transcribe(
        str(args.audio),
        path_or_hf_repo=args.model,
        word_timestamps=True,
    )
    elapsed = time.time() - start

    words = [
        {"word": w["word"], "start": w["start"], "end": w["end"]}
        for seg in result["segments"]
        for w in seg.get("words", [])
    ]
    out_path = args.out or Path("data/transcripts") / f"{args.audio.stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        {"audio": str(args.audio), "model": args.model, "duration_s": duration,
         "text": result["text"], "words": words},
        indent=2,
    ))

    print(f"audio: {duration:.0f}s  compute: {elapsed:.0f}s  RTF: {elapsed / duration:.3f}")
    print(f"words with timestamps: {len(words)}")
    if words:
        w = words[0]
        print(f"first word: {w['word']!r} {w['start']:.2f}-{w['end']:.2f}s")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
