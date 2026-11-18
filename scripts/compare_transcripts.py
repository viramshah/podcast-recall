"""D13 comparison: a publisher's transcript (.vtt) versus Whisper, on the same stretch of one episode.

Neither transcript is ground truth. The script measures how closely they agree, how precise the
publisher's timing is, and lists the places where they disagree most, so you can listen at those
timestamps and decide which one was right.

Usage (from the repo root, after `uv sync`):
    uv run python scripts/compare_transcripts.py

Defaults compare Lenny's "Meta's Muse" episode from minute 10 to minute 15. To try another
episode, pass --name, --audio-url, --vtt-url, --start and --length (seconds).
Output goes to data/compare/ (git-ignored). The full episode audio is downloaded once (~80 MB).
"""

import argparse
import re
import shutil
import statistics
import subprocess
import time
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

OUT_DIR = Path("data/compare")
DEFAULT_AUDIO = (
    "https://pscrb.fm/rss/p/api.substack.com/feed/podcast/224231309/"
    "2cdd86d5061669c9821d9a2157b09063.mp3"
)
DEFAULT_VTT = (
    "https://api.substack.com/feed/podcast/transcript/224231309/"
    "f6e4596b37a2c26be368407658ea668b.vtt"
)
DEFAULT_MODEL = "mlx-community/whisper-small-mlx"
PHRASE_TOKENS = 12
PHRASES_PER_SIDE = 25

_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")
_CUE_LINE = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)")
_TAG = re.compile(r"<[^>]+>")
_VOICE_TAG = re.compile(r"<v[ .]([^>]+)>")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str
    speakers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tok:
    text: str
    time: float
    cue_start: bool = False


# ---------------------------------------------------------------------------- parsing


def to_seconds(text: str) -> float:
    match = _TIME.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"unreadable timestamp: {text!r}")
    hours, minutes, seconds, millis = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_vtt(text: str) -> list[Cue]:
    cues: list[Cue] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = _CUE_LINE.match(lines[i])
        if match is None:
            i += 1
            continue
        start, end = to_seconds(match.group(1)), to_seconds(match.group(2))
        i += 1
        body: list[str] = []
        while i < len(lines) and lines[i].strip():
            body.append(lines[i])
            i += 1
        raw = " ".join(body)
        speakers = tuple(sorted(set(_VOICE_TAG.findall(raw))))
        cues.append(Cue(start, end, _TAG.sub("", raw).strip(), speakers))
    return cues


def tokens_of(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))


def publisher_tokens(cues: Sequence[Cue], start: float, end: float) -> tuple[list[Tok], list[Cue]]:
    """Tokens of the cues that lie inside [start, end]. Token times are spread evenly across a cue
    (an estimate); the first token of each cue carries the cue's exact start time."""
    inside = [c for c in cues if c.start >= start and c.end <= end]
    result: list[Tok] = []
    for cue in inside:
        words = tokens_of(cue.text)
        for k, word in enumerate(words):
            when = cue.start + (cue.end - cue.start) * k / max(len(words), 1)
            result.append(Tok(word, when, cue_start=(k == 0)))
    return result, inside


def whisper_tokens(result: dict, offset: float) -> list[Tok]:
    found: list[Tok] = []
    for segment in result.get("segments", []):
        for word in segment.get("words", []):
            for piece in tokens_of(word.get("word", "")):
                found.append(Tok(piece, offset + float(word["start"])))
    return found


# ---------------------------------------------------------------------------- metrics


def edit_distance(a: Sequence[str], b: Sequence[str]) -> int:
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def quote_survival(source: Sequence[str], target: Sequence[str]) -> float:
    """Take evenly spaced 12-word phrases from `source` and see how many still appear in
    `target` with at most one differing word (similarity of at least 0.90)."""
    if len(source) < PHRASE_TOKENS or len(target) < PHRASE_TOKENS:
        return 0.0
    step = max((len(source) - PHRASE_TOKENS) // PHRASES_PER_SIDE, 1)
    starts = list(range(0, len(source) - PHRASE_TOKENS + 1, step))[:PHRASES_PER_SIDE]
    survived = 0
    for s in starts:
        phrase = source[s:s + PHRASE_TOKENS]
        best = min(
            edit_distance(phrase, target[t:t + PHRASE_TOKENS])
            for t in range(len(target) - PHRASE_TOKENS + 1)
        )
        if 1 - best / PHRASE_TOKENS >= 0.90:
            survived += 1
    return survived / len(starts)


def timing_offsets(
    pub: Sequence[Tok], wh: Sequence[Tok], blocks: Sequence[tuple[int, int, int]]
) -> list[float]:
    """For tokens that start a publisher cue and match a Whisper token, the difference
    (Whisper time minus cue start), in seconds."""
    offsets: list[float] = []
    for i, j, size in blocks:
        if size < 3:
            continue
        for k in range(size):
            if pub[i + k].cue_start:
                offsets.append(wh[j + k].time - pub[i + k].time)
    return offsets


def share_within(values: Sequence[float], limit: float) -> float:
    return sum(1 for v in values if abs(v) <= limit) / len(values) if values else 0.0


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def disagreements(
    pub: Sequence[Tok], wh: Sequence[Tok], opcodes: Sequence[tuple[str, int, int, int, int]], top: int
) -> list[dict]:
    found = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal" or min(i1, j1) < 3 or i2 > len(pub) - 3 or j2 > len(wh) - 3:
            continue  # ignore the first and last few words: window edges never line up exactly
        when = wh[j1].time if j1 < len(wh) else pub[i1].time
        found.append(
            {
                "size": max(i2 - i1, j2 - j1),
                "time": when,
                "before": " ".join(t.text for t in pub[max(i1 - 5, 0):i1]),
                "publisher": " ".join(t.text for t in pub[i1:i2]) or "(nothing)",
                "whisper": " ".join(t.text for t in wh[j1:j2]) or "(nothing)",
                "after": " ".join(t.text for t in pub[i2:i2 + 5]),
            }
        )
    found.sort(key=lambda d: d["size"], reverse=True)
    return sorted(found[:top], key=lambda d: d["time"])


def compare(pub: list[Tok], wh: list[Tok], cues: Sequence[Cue], top: int = 15) -> dict:
    pub_words = [t.text for t in pub]
    wh_words = [t.text for t in wh]
    matcher = SequenceMatcher(None, pub_words, wh_words, autojunk=False)
    distance = edit_distance(pub_words, wh_words)
    offsets = timing_offsets(pub, wh, matcher.get_matching_blocks())
    lengths = [c.end - c.start for c in cues]
    return {
        "publisher_words": len(pub_words),
        "whisper_words": len(wh_words),
        "similarity": matcher.ratio(),
        "word_difference_rate": distance / max(len(pub_words), 1),
        "cue_count": len(cues),
        "cue_seconds_mean": statistics.mean(lengths) if lengths else 0.0,
        "cue_seconds_max": max(lengths) if lengths else 0.0,
        "offset_samples": len(offsets),
        "offset_median": statistics.median(offsets) if offsets else 0.0,
        "within_2s": share_within(offsets, 2),
        "within_5s": share_within(offsets, 5),
        "within_15s": share_within(offsets, 15),
        "offset_worst": max(offsets, key=abs) if offsets else 0.0,
        "publisher_quotes_found_in_whisper": quote_survival(pub_words, wh_words),
        "whisper_quotes_found_in_publisher": quote_survival(wh_words, pub_words),
        "disagreements": disagreements(pub, wh, matcher.get_opcodes(), top),
        "speakers": sorted({s for c in cues for s in c.speakers}),
    }


def render_report(name: str, start: float, length: float, model: str, whisper_seconds: float,
                  m: dict) -> str:
    lines = [
        f"# Publisher transcript versus Whisper: {name}",
        "",
        (
            f"Section: {mmss(start)} to {mmss(start + length)} of the episode ({length:.0f} s). "
            f"Whisper model: `{model}`, {whisper_seconds:.0f} s to transcribe "
            f"(real-time factor {whisper_seconds / length:.2f})."
        ),
        "",
        "Neither transcript is ground truth. These numbers show how closely they agree.",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Words (publisher / Whisper) | {m['publisher_words']} / {m['whisper_words']} |",
        f"| Overall similarity (1.00 = identical) | {m['similarity']:.3f} |",
        f"| Words that differ, as a share of the publisher's words | {m['word_difference_rate']:.1%} |",
        f"| Publisher cues in this section | {m['cue_count']} |",
        f"| Cue length, mean / longest | {m['cue_seconds_mean']:.1f} s / {m['cue_seconds_max']:.1f} s |",
        f"| Cue starts compared with Whisper's word times | {m['offset_samples']} |",
        f"| Median timing difference | {m['offset_median']:+.2f} s |",
        f"| Within 2 s / 5 s / 15 s | {m['within_2s']:.0%} / {m['within_5s']:.0%} / {m['within_15s']:.0%} |",
        f"| Worst timing difference | {m['offset_worst']:+.1f} s |",
        (
            "| 12-word quotes from the publisher that appear in Whisper (at least 0.90 similar) | "
            f"{m['publisher_quotes_found_in_whisper']:.0%} |"
        ),
        (
            "| 12-word quotes from Whisper that appear in the publisher's (at least 0.90 similar) | "
            f"{m['whisper_quotes_found_in_publisher']:.0%} |"
        ),
        f"| Speaker labels in the publisher file | {', '.join(m['speakers']) or 'none found'} |",
        "",
        "## Where they disagree most (listen at these times)",
        "",
        "For each one, play the episode at the time shown and note which version matches what is said.",
        "",
        "| # | Time | Context before | Publisher says | Whisper says | Which is right? |",
        "|---|---|---|---|---|---|",
    ]
    for n, d in enumerate(m["disagreements"], 1):
        lines.append(
            f"| {n} | {mmss(d['time'])} | ...{d['before']} | {d['publisher']} | {d['whisper']} |  |"
        )
    lines += [
        "",
        "## How to read this",
        (
            "- **Similarity** above about 0.90 and timing within 2 s for most cue starts means the "
            "publisher file is a good substitute for Whisper for citations."
        ),
        (
            "- **Cue length** is the precision of the publisher's timing. A 20-second cue cannot point "
            "to the exact second, but it can still support a link that opens a few seconds early."
        ),
        "- The table above is what decides it: count how often each side was right.",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------- doing the work


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  using the existing {dest}")
        return
    print(f"  downloading {dest.name} ...")
    request = urllib.request.Request(url, headers={"User-Agent": "podcast-recall-compare/0.0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def cut_clip(source: Path, start: float, length: float, dest: Path) -> None:
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
        "-ss", str(start), "-t", str(length), "-vn", "-ac", "1", "-ar", "16000", str(dest),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=600)
    except FileNotFoundError:
        raise SystemExit("ffmpeg is not installed. Run: brew install ffmpeg") from None
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"ffmpeg failed: {exc.stderr.decode('utf-8', 'replace')[:300]}") from None


def run_whisper(clip: Path, model: str, language: str) -> tuple[dict, float]:
    import mlx_whisper  # imported here so the pure helpers above work without it

    began = time.time()
    result = mlx_whisper.transcribe(
        str(clip), path_or_hf_repo=model, word_timestamps=True, language=language
    )
    return result, time.time() - began


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare a publisher transcript with Whisper.")
    parser.add_argument("--name", default="muse")
    parser.add_argument("--audio-url", default=DEFAULT_AUDIO)
    parser.add_argument("--vtt-url", default=DEFAULT_VTT)
    parser.add_argument("--start", type=float, default=600.0, help="section start, seconds")
    parser.add_argument("--length", type=float, default=300.0, help="section length, seconds")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--language", default="en")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audio = OUT_DIR / f"{args.name}-episode.mp3"
    vtt_path = OUT_DIR / f"{args.name}.vtt"
    clip = OUT_DIR / f"{args.name}-clip.wav"
    end = args.start + args.length

    print("1. Publisher transcript")
    download(args.vtt_url, vtt_path)
    raw = vtt_path.read_text(encoding="utf-8", errors="replace")
    print("   first lines of the file:")
    for line in raw.splitlines()[:10]:
        print(f"     {line}")
    cues = parse_vtt(raw)
    pub, inside = publisher_tokens(cues, args.start, end)
    if not inside:
        raise SystemExit("No publisher cues fall inside that section.")

    print("2. Audio section")
    download(args.audio_url, audio)
    cut_clip(audio, args.start, args.length, clip)

    print(f"3. Whisper ({args.model})")
    result, seconds = run_whisper(clip, args.model, args.language)
    (OUT_DIR / f"{args.name}-whisper.txt").write_text(result.get("text", ""), encoding="utf-8")
    wh = whisper_tokens(result, args.start)

    print("4. Comparing")
    metrics = compare(pub, wh, inside)
    report = render_report(args.name, args.start, args.length, args.model, seconds, metrics)
    report_path = OUT_DIR / f"{args.name}-report.md"
    report_path.write_text(report, encoding="utf-8")
    print()
    print(report)
    print(f"Saved to {report_path}")


if __name__ == "__main__":
    main()
