"""Where podcast-recall keeps its data, and how settings are read from the environment."""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

from podcast_recall.errors import ConfigError

log = logging.getLogger(__name__)

DEFAULT_HOME = "~/.podcast-recall"
DEFAULT_CLIENT_SECRET = "~/.podcast-recall/client_secret.json"
DEFAULT_REFRESH_DAYS = 30
DEFAULT_WHISPER_MODEL = "mlx-community/whisper-small-mlx"
DEFAULT_FALLBACK_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_CHUNK_SECONDS = 120.0  # D17: the middle of the 100 to 150 s plateau found on 2026-11-18
DEFAULT_CHUNK_OVERLAP_SECONDS = 24.0  # for the default length; scales with a changed length
OVERLAP_FRACTION = 0.2
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


def data_home() -> Path:
    return Path(os.environ.get("PODCAST_RECALL_HOME") or DEFAULT_HOME).expanduser()


def ensure_data_home() -> Path:
    """Create the data folder with permissions 700, tightening it (and warning) if it is looser."""
    home = data_home()
    if home.exists():
        mode = stat.S_IMODE(home.stat().st_mode)
        if mode & 0o077:
            os.chmod(home, 0o700)
            log.warning("Data folder %s had permissions %o; tightened to 700.", home, mode)
    else:
        home.mkdir(parents=True)
        os.chmod(home, 0o700)
    return home


def db_path() -> Path:
    return data_home() / "podcast_recall.db"


def log_dir() -> Path:
    return data_home() / "logs"


def backup_dir() -> Path:
    return data_home() / "backups"


def lock_path(user_id: str) -> Path:
    return data_home() / f"sync-{user_id}.lock"


def audio_dir() -> Path:
    return data_home() / "audio"


def transcripts_dir() -> Path:
    return data_home() / "transcripts"


def raw_transcripts_dir() -> Path:
    return transcripts_dir() / "raw"


def transcribe_lock_path() -> Path:
    return data_home() / "transcribe.lock"


def _number_setting(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number of seconds, not '{raw}'.") from None


def chunk_seconds() -> float:
    """Target length of a search chunk in seconds (setting `PODCAST_RECALL_CHUNK_SECONDS`)."""
    value = _number_setting("PODCAST_RECALL_CHUNK_SECONDS", DEFAULT_CHUNK_SECONDS)
    if not 15 <= value <= 300:
        raise ConfigError("PODCAST_RECALL_CHUNK_SECONDS must be between 15 and 300.")
    return value


def chunk_overlap_seconds() -> float:
    """How far each chunk reaches back into the previous one (`PODCAST_RECALL_CHUNK_OVERLAP_SECONDS`).
    When not set it is 20% of the chunk length (24 s for the default 120 s)."""
    value = _number_setting(
        "PODCAST_RECALL_CHUNK_OVERLAP_SECONDS", round(chunk_seconds() * OVERLAP_FRACTION)
    )
    if not 0 <= value <= chunk_seconds() / 2:
        raise ConfigError("PODCAST_RECALL_CHUNK_OVERLAP_SECONDS must be between 0 and half the chunk length.")
    return value


def intro_weight() -> float:
    """The factor applied to the score of chunks from an episode's opening minutes
    (`PODCAST_RECALL_INTRO_WEIGHT`). 1 means no change, which is the default; the 2026-11-20
    experiments found 0.5 helps on the dev questions but was not confirmed on the held-out ones."""
    value = _number_setting("PODCAST_RECALL_INTRO_WEIGHT", 1.0)
    if value < 0:
        raise ConfigError("PODCAST_RECALL_INTRO_WEIGHT cannot be negative.")
    return value


def index_lock_path() -> Path:
    return data_home() / "index.lock"


def embed_model() -> str:
    return os.environ.get("PODCAST_RECALL_EMBED_MODEL") or DEFAULT_EMBED_MODEL


def ollama_url() -> str:
    return (os.environ.get("PODCAST_RECALL_OLLAMA_URL") or DEFAULT_OLLAMA_URL).rstrip("/")


def whisper_model() -> str:
    return os.environ.get("PODCAST_RECALL_WHISPER_MODEL") or DEFAULT_WHISPER_MODEL


def whisper_fallback_model() -> str | None:
    """The larger model tried once when the first run times out or is flagged, or None if the
    retry is turned off (`PODCAST_RECALL_WHISPER_FALLBACK_MODEL=none`)."""
    value = os.environ.get("PODCAST_RECALL_WHISPER_FALLBACK_MODEL")
    if value is None or not value.strip():
        return DEFAULT_FALLBACK_MODEL
    return None if value.strip().lower() == "none" else value.strip()


def whisper_language() -> str | None:
    """A forced Whisper language, or None to let Whisper detect it (the default)."""
    return os.environ.get("PODCAST_RECALL_WHISPER_LANGUAGE") or None


def podcastindex_env_path() -> Path:
    return data_home() / "podcastindex.env"


def client_secret_path() -> Path:
    return Path(os.environ.get("CLIENT_SECRET_PATH") or DEFAULT_CLIENT_SECRET).expanduser()


def video_refresh_days() -> int:
    raw = os.environ.get("PODCAST_RECALL_VIDEO_REFRESH_DAYS")
    if raw is None or raw == "":
        return DEFAULT_REFRESH_DAYS
    try:
        days = int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"PODCAST_RECALL_VIDEO_REFRESH_DAYS must be a whole number, got {raw!r}."
        ) from exc
    if days < 1:
        raise ConfigError("PODCAST_RECALL_VIDEO_REFRESH_DAYS must be at least 1.")
    return days
