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
