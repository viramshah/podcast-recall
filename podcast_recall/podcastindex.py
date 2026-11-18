"""The only place that talks to Podcast Index.

Uses the standard library only. The network layer is a small function that tests replace, so no
test touches the network. Credentials never reach a log or the database.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from podcast_recall import paths
from podcast_recall.errors import ApiError, ConfigError, TransientError
from podcast_recall.models import EpisodeInfo, FeedInfo
from podcast_recall.retry import call_with_retries

BASE = "https://api.podcastindex.org/api/1.0"
TIMEOUT_S = 30
PAUSE_S = 0.2
MAX_EPISODES = 1000

Transport = Callable[[str, dict[str, str], float], tuple[int, bytes]]


@dataclass(frozen=True)
class Credentials:
    key: str
    secret: str


# ---------------------------------------------------------------------------- credentials


def parse_env_file(text: str) -> dict[str, str]:
    """Read lines like `export NAME=value` (or `NAME="value"`)."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        name, sep, value = line.partition("=")
        if sep:
            values[name.strip()] = value.strip().strip("'\"")
    return values


def load_credentials(
    env: Mapping[str, str] | None = None, env_file: Path | None = None
) -> Credentials:
    """Environment variables win. Otherwise read the credentials file, which must not be
    readable by other users."""
    env = os.environ if env is None else env
    key, secret = env.get("PODCASTINDEX_KEY"), env.get("PODCASTINDEX_SECRET")
    path = env_file or paths.podcastindex_env_path()
    if not (key and secret) and path.exists():
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ConfigError(
                f"{path} can be read by other users. Run `chmod 600 {path}` and try again."
            )
        values = parse_env_file(path.read_text(encoding="utf-8"))
        key = key or values.get("PODCASTINDEX_KEY")
        secret = secret or values.get("PODCASTINDEX_SECRET")
    if not key or not secret:
        raise ConfigError(
            "Podcast Index credentials not found. Set PODCASTINDEX_KEY and PODCASTINDEX_SECRET, "
            f"or put them in {path} (lines like `export PODCASTINDEX_KEY=...`, permissions 600)."
        )
    return Credentials(key, secret)


# ---------------------------------------------------------------------------- parsing


def parse_duration(value) -> int | None:
    """Seconds from a number, digits, or `HH:MM:SS` or `MM:SS` text. 0 and unknown give None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return int(value) if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text) or None
        parts = text.split(":")
        if 2 <= len(parts) <= 3 and all(p.strip().isdigit() for p in parts):
            seconds = 0
            for part in parts:
                seconds = seconds * 60 + int(part)
            return seconds or None
    return None


def _int_or_none(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def feed_from(raw: Mapping) -> FeedInfo:
    return FeedInfo(
        feed_id=int(raw["id"]),
        title=raw.get("title") or "",
        url=raw.get("url") or raw.get("originalUrl") or "",
        author=raw.get("author") or raw.get("ownerName") or "",
        language=raw.get("language") or "",
        episode_count=_int_or_none(raw.get("episodeCount")),
        last_update=_int_or_none(raw.get("lastUpdateTime")),
    )


def episode_from(raw: Mapping, feed_id: int) -> EpisodeInfo:
    transcripts = raw.get("transcripts")
    transcripts = transcripts if isinstance(transcripts, list) else []
    link = raw.get("transcriptUrl") or None
    if not link and transcripts and isinstance(transcripts[0], Mapping):
        link = transcripts[0].get("url") or None
    return EpisodeInfo(
        episode_id=int(raw["id"]),
        feed_id=int(raw.get("feedId") or feed_id),
        guid=raw.get("guid") or "",
        title=raw.get("title") or "",
        published=_int_or_none(raw.get("datePublished")),
        duration_s=parse_duration(raw.get("duration")),
        audio_url=raw.get("enclosureUrl") or "",
        audio_type=raw.get("enclosureType") or "",
        transcript_url=link,
        transcripts=transcripts,
        link=raw.get("link") or "",
    )


# ---------------------------------------------------------------------------- client


def _urllib_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class PodcastIndexClient:
    def __init__(
        self,
        credentials: Credentials,
        *,
        transport: Transport = _urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
        clock: Callable[[], float] = time.time,
        pause: float = PAUSE_S,
    ) -> None:
        self._credentials = credentials
        self._transport = transport
        self._sleep = sleep
        self._rng = rng
        self._clock = clock
        self._pause = pause
        self.calls: dict[str, int] = {}

    @property
    def total_calls(self) -> int:
        return sum(self.calls.values())

    def _get(self, name: str, path: str, **params) -> dict:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{BASE}{path}?{query}"

        def attempt() -> dict:
            self.calls[name] = self.calls.get(name, 0) + 1
            stamp = str(int(self._clock()))
            digest = hashlib.sha1(
                (self._credentials.key + self._credentials.secret + stamp).encode()
            ).hexdigest()
            headers = {
                "User-Agent": "podcast-recall/0.0.1",
                "X-Auth-Key": self._credentials.key,
                "X-Auth-Date": stamp,
                "Authorization": digest,
            }
            try:
                status, body = self._transport(url, headers, TIMEOUT_S)
            except (OSError, TimeoutError) as exc:
                raise TransientError(f"network error: {type(exc).__name__}") from exc
            if status in (401, 403):
                raise ConfigError(
                    f"Podcast Index rejected the credentials (HTTP {status}). "
                    "Check PODCASTINDEX_KEY and PODCASTINDEX_SECRET."
                )
            if status == 429 or 500 <= status < 600:
                raise TransientError(f"HTTP {status}")
            if status != 200:
                raise ApiError(f"Podcast Index returned HTTP {status}.")
            try:
                payload = json.loads(body)
            except ValueError as exc:
                raise ApiError("Podcast Index returned a response that could not be read.") from exc
            if not isinstance(payload, dict):
                raise ApiError("Podcast Index returned an unexpected response.")
            if str(payload.get("status")).lower() == "false":
                raise ApiError(f"Podcast Index error: {payload.get('description') or 'no details'}")
            return payload

        result = call_with_retries(attempt, sleep=self._sleep, rng=self._rng)
        if self._pause:
            self._sleep(self._pause)
        return result  # type: ignore[return-value]

    def search_feeds(self, term: str, max_results: int = 10) -> list[FeedInfo]:
        payload = self._get("search/byterm", "/search/byterm", q=term, max=max_results)
        return [feed_from(f) for f in payload.get("feeds") or [] if isinstance(f, Mapping)]

    @staticmethod
    def _single_feed(payload: dict) -> FeedInfo | None:
        feed = payload.get("feed")
        return feed_from(feed) if isinstance(feed, Mapping) and feed.get("id") else None

    def feed_by_url(self, url: str) -> FeedInfo | None:
        return self._single_feed(self._get("podcasts/byfeedurl", "/podcasts/byfeedurl", url=url))

    def feed_by_id(self, feed_id: int) -> FeedInfo | None:
        return self._single_feed(self._get("podcasts/byfeedid", "/podcasts/byfeedid", id=feed_id))

    def episodes(
        self, feed_id: int, since: int | None = None, max_items: int = MAX_EPISODES
    ) -> list[EpisodeInfo]:
        """A feed's episodes, newest first. `since` (epoch seconds) returns only newer ones."""
        payload = self._get(
            "episodes/byfeedid", "/episodes/byfeedid", id=feed_id, max=max_items, since=since
        )
        items = payload.get("items") or []
        return [episode_from(e, feed_id) for e in items if isinstance(e, Mapping) and e.get("id")]
