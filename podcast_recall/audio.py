"""Audio files: downloading, checking that they really are audio, and disk space."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.net import FetchInfo, SafeFetcher

AUDIO_MAX_BYTES = 600_000_000
AUDIO_TIMEOUT_S = 30 * 60
MIN_FREE_BYTES = 500_000_000
BYTES_PER_SECOND_GUESS = 16_000  # about a 128 kbit/s file, used when the size is not advertised
_OK_TYPES = {"video/mp4", "application/octet-stream", "binary/octet-stream", ""}
_EXTENSIONS = {
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a",
    "audio/aac": ".aac", "audio/ogg": ".ogg", "audio/wav": ".wav", "audio/x-wav": ".wav",
    "video/mp4": ".mp4",
}


class AudioError(ApiError):
    """The downloaded file is not usable audio."""


class InsufficientDiskSpace(ConfigError):
    """Not enough free disk space to download an episode. Stops the whole run."""


@dataclass(frozen=True)
class AudioInfo:
    duration_s: float


def accept_audio_type(content_type: str) -> bool:
    """The real test is `ffprobe`; this only turns away things that are plainly not audio."""
    return content_type.startswith("audio/") or content_type in _OK_TYPES


def extension_for(content_type: str) -> str:
    return _EXTENSIONS.get(content_type, ".mp3")


def check_disk_space(
    directory: Path,
    expected_seconds: int | None,
    free_bytes: Callable[[Path], int] = lambda p: shutil.disk_usage(p).free,
) -> None:
    """Require free space of at least the larger of twice the expected file size or 500 MB."""
    directory.mkdir(parents=True, exist_ok=True)
    expected = (expected_seconds or 3600) * BYTES_PER_SECOND_GUESS
    needed = max(2 * expected, MIN_FREE_BYTES)
    free = free_bytes(directory)
    if free < needed:
        raise InsufficientDiskSpace(
            f"Not enough free disk space ({free // 1_000_000} MB free, "
            f"{needed // 1_000_000} MB needed). Free some space and run again."
        )


def download_audio(
    fetcher: SafeFetcher, url: str, directory: Path, episode_id: int
) -> tuple[Path, FetchInfo]:
    """Download the audio into `directory`. The extension comes from the content type."""
    holder = directory / f"{episode_id}.download"
    info = fetcher.fetch_to_file(
        url, holder, max_bytes=AUDIO_MAX_BYTES, total_timeout_s=AUDIO_TIMEOUT_S, accept=accept_audio_type
    )
    final = directory / f"{episode_id}{extension_for(info.content_type)}"
    holder.replace(final)
    return final, info


def probe_audio(path: Path, runner: Callable = subprocess.run) -> AudioInfo:
    """Use `ffprobe` to confirm the file has an audio stream and a length above 0."""
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
        "-of", "json", str(path),
    ]
    try:
        completed = runner(command, capture_output=True, text=True, timeout=120, check=False)
    except FileNotFoundError:
        raise ConfigError("ffprobe is not installed. Run: brew install ffmpeg") from None
    except subprocess.TimeoutExpired:
        raise AudioError("ffprobe took too long to read the file") from None
    if completed.returncode != 0:
        raise AudioError("ffprobe could not read the file as audio")
    try:
        data = json.loads(completed.stdout or "{}")
        duration = float((data.get("format") or {}).get("duration") or 0)
    except (ValueError, AttributeError):
        raise AudioError("ffprobe gave an unreadable answer") from None
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams") or [])
    if not has_audio:
        raise AudioError("the file has no audio stream")
    if duration <= 0:
        raise AudioError("the audio has no length")
    return AudioInfo(duration)
