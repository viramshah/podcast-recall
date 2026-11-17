"""Logging with redaction. Nothing secret may reach a log file or the terminal."""

from __future__ import annotations

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(authorization[\"']?\s*[:=]\s*)(?:bearer\s+)?[^\s,;\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"(?i)((?:access_token|refresh_token|id_token|client_secret|token|code)"
            r"[\"']?\s*[=:]\s*[\"']?)[^&\s\"',}]+"
        ),
        r"\1[REDACTED]",
    ),
    (re.compile(r"\bya29\.[A-Za-z0-9._-]+"), "[REDACTED]"),
    (re.compile(r"\b1//[A-Za-z0-9._-]+"), "[REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[REDACTED-EMAIL]"),
]


def redact(text: str) -> str:
    """Remove tokens, authorization headers, client secrets and email addresses from `text`."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFormatter(logging.Formatter):
    """Redacts the whole formatted record, including tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


_MARK = "_podcast_recall_handler"


def setup_logging(log_dir: Path | None, *, stderr: bool = True, level: int = logging.INFO) -> None:
    """Rotating log file (5 files of 1 MB) plus optional stderr output. Safe to call twice."""
    logger = logging.getLogger("podcast_recall")
    for handler in list(logger.handlers):
        if getattr(handler, _MARK, False):
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(level)
    logger.propagate = False
    fmt = RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(log_dir, 0o700)
        file_handler = RotatingFileHandler(
            log_dir / "podcast-recall.log", maxBytes=1_000_000, backupCount=4, encoding="utf-8"
        )
        os.chmod(log_dir / "podcast-recall.log", 0o600)
        file_handler.setFormatter(fmt)
        setattr(file_handler, _MARK, True)
        logger.addHandler(file_handler)
    if stderr:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(RedactingFormatter("%(levelname)s: %(message)s"))
        stream.setLevel(logging.WARNING)
        setattr(stream, _MARK, True)
        logger.addHandler(stream)
