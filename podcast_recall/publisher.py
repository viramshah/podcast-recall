"""Publisher transcripts (decision D13): choose a transcript link, download the file, and read its
timed cues into the same structure Whisper produces (with chunk timing).

Supported in v1: WebVTT and SubRip. Everything here except the download is a pure function.
"""

from __future__ import annotations

import html
import re
import urllib.parse
from collections.abc import Mapping, Sequence
from pathlib import Path

from podcast_recall.models import Segment
from podcast_recall.net import SafeFetcher

TRANSCRIPT_MAX_BYTES = 20_000_000
TRANSCRIPT_TIMEOUT_S = 120
SUPPORTED_FORMATS = ("vtt", "srt")  # in order of preference

_TIME = r"(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3}"
_CUE_LINE = re.compile(rf"^\s*({_TIME})\s+-->\s+({_TIME})")
_VOICE = re.compile(r"<v(?:\.[^\s>]+)*\s+([^>]+)>")
_TAG = re.compile(r"<[^>]+>")
_TEXT_OK = {"application/octet-stream", "binary/octet-stream", "application/x-subrip",
            "application/srt", "application/vtt", ""}


class TranscriptParseError(ValueError):
    """The file is not a usable transcript."""


# ---------------------------------------------------------------------------- choosing


def format_of(url: str, mime: str | None) -> str | None:
    """`vtt`, `srt` or None (not supported), from the stored type and then the file extension."""
    kind = (mime or "").lower()
    if "vtt" in kind:
        return "vtt"
    if "srt" in kind or "subrip" in kind:
        return "srt"
    path = urllib.parse.urlsplit(url).path.lower()
    if path.endswith(".vtt"):
        return "vtt"
    if path.endswith(".srt"):
        return "srt"
    return None


def pick_transcript(
    transcripts: Sequence[Mapping] | None, fallback_url: str | None
) -> tuple[str, str] | None:
    """The best usable (url, format) among an episode's transcript links, or None."""
    options: list[tuple[str, str]] = []
    for entry in transcripts or []:
        if isinstance(entry, Mapping) and entry.get("url"):
            fmt = format_of(str(entry["url"]), entry.get("type"))
            if fmt:
                options.append((str(entry["url"]), fmt))
    if fallback_url:
        fmt = format_of(fallback_url, None)
        if fmt and all(url != fallback_url for url, _ in options):
            options.append((fallback_url, fmt))
    for wanted in SUPPORTED_FORMATS:
        for url, fmt in options:
            if fmt == wanted:
                return url, fmt
    return None


# ---------------------------------------------------------------------------- parsing


def to_seconds(text: str) -> float:
    parts = text.strip().replace(",", ".").split(":")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def _clean(raw: str) -> str:
    return " ".join(html.unescape(_TAG.sub("", raw)).split())


def parse_cues(text: str, fmt: str) -> list[Segment]:
    """Read WebVTT or SubRip text into segments (one per cue).

    Header, NOTE and STYLE blocks and cue identifiers are ignored. Markup is removed, entities
    decoded and white space collapsed. Empty cues are dropped and repeated consecutive cues are
    merged. A speaker label (`<v SPEAKER_00>`) is kept. Cue times must not run backwards.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿").split("\n")
    if fmt == "vtt" and not (lines and lines[0].strip().startswith("WEBVTT")):
        raise TranscriptParseError("the file does not start with WEBVTT")
    segments: list[Segment] = []
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
        voice = next(_VOICE.finditer(raw), None)
        cleaned = _clean(raw)
        if end < start:
            raise TranscriptParseError("a cue ends before it starts")
        if cleaned:
            segments.append(Segment(start, end, cleaned, voice.group(1).strip() if voice else None))
    if not segments:
        raise TranscriptParseError("no cues with text were found")
    merged: list[Segment] = []
    for seg in segments:
        if merged and seg.start < merged[-1].start - 0.5:
            raise TranscriptParseError("cue times run backwards")
        last = merged[-1] if merged else None
        if last and seg.text == last.text and seg.speaker == last.speaker and seg.start <= last.end + 1.0:
            last.end = max(last.end, seg.end)
        else:
            merged.append(seg)
    return merged


# ---------------------------------------------------------------------------- downloading


def accept_content_type(content_type: str) -> bool:
    """Plain text and the usual 'unknown' types. A web page (`text/html`) is not a transcript."""
    if content_type == "text/html":
        return False
    return content_type.startswith("text/") or content_type in _TEXT_OK


def download_transcript(fetcher: SafeFetcher, url: str, dest: Path) -> str:
    """Download a transcript file to `dest` (kept as the raw original) and return its text."""
    fetcher.fetch_to_file(
        url, dest, max_bytes=TRANSCRIPT_MAX_BYTES, total_timeout_s=TRANSCRIPT_TIMEOUT_S,
        accept=accept_content_type,
    )
    return dest.read_text(encoding="utf-8", errors="replace")
