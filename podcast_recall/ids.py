"""Turn YouTube URLs, bare IDs, CSV files and text files into video IDs."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from podcast_recall.errors import ConfigError

_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "music.youtube.com", "youtube-nocookie.com"}


def extract_video_id(text: str) -> str | None:
    """Return the 11-character video ID in `text`, or None. Ignores `&t=`, `&list=` and so on."""
    value = text.strip()
    if not value:
        return None
    if _ID.match(value):
        return value
    try:
        url = urlparse(value if "://" in value else "https://" + value)
        host = (url.hostname or "").lower()
    except ValueError:
        return None
    for prefix in ("www.", "m."):
        host = host.removeprefix(prefix)
    candidate = ""
    if host == "youtu.be":
        candidate = url.path.lstrip("/").split("/")[0]
    elif host in _YOUTUBE_HOSTS:
        parts = [p for p in url.path.split("/") if p]
        if parts[:1] == ["watch"]:
            candidate = parse_qs(url.query).get("v", [""])[0]
        elif parts[:1] in (["shorts"], ["embed"], ["live"], ["v"]) and len(parts) > 1:
            candidate = parts[1]
    return candidate if _ID.match(candidate) else None


def _read_source_file(path: Path) -> list[str]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "youtube_url" not in reader.fieldnames:
                raise ConfigError(f"{path} has no 'youtube_url' column.")
            return [row.get("youtube_url") or "" for row in reader]
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def load_ids(inputs: list[str]) -> tuple[list[str], list[str]]:
    """Read video IDs from files (CSV with `youtube_url`, or one URL or ID per line), URLs and
    bare IDs. Returns (unique IDs in order, entries that could not be parsed)."""
    entries: list[str] = []
    for item in inputs:
        path = Path(item).expanduser()
        if path.is_file():
            entries.extend(_read_source_file(path))
        else:
            entries.append(item)
    ids: list[str] = []
    seen: set[str] = set()
    unparsed: list[str] = []
    for entry in entries:
        video_id = extract_video_id(entry)
        if video_id is None:
            if entry.strip():
                unparsed.append(entry.strip())
        elif video_id not in seen:
            seen.add(video_id)
            ids.append(video_id)
    return ids, unparsed
