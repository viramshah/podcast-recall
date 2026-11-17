"""The only place that talks to the YouTube Data API.

`YouTubeClient` is the interface the rest of the code uses, so tests can use a fake.
`GoogleYouTubeClient` is the real implementation. Google's libraries are imported only when it is
built, so everything else works (and is tested) without them.

Rules: read-only scope, `search.list` is never called, every request is counted (list calls cost
1 quota unit each), failures are retried only when they are temporary.
"""

from __future__ import annotations

import json
import random
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable

from podcast_recall.errors import (
    ApiError,
    ConfigError,
    NotSignedIn,
    PodcastRecallError,
    QuotaExceeded,
    TransientError,
)
from podcast_recall.models import ChannelInfo, MyChannel, PlaylistInfo, VideoInfo

SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
REQUEST_TIMEOUT_S = 30
RETRY_DELAYS = (1, 2, 4, 8, 16)  # seconds; up to 5 retries after the first attempt
BATCH_SIZE = 50
DESCRIPTION_LIMIT = 500
_QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded"}
_RATE_REASONS = {"rateLimitExceeded", "userRateLimitExceeded"}

_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def parse_iso8601_duration(text: str | None) -> int:
    """'PT1H2M3S' -> 3723. Live and upcoming videos report 'P0D' -> 0. Unknown text -> 0."""
    match = _DURATION.match(text or "")
    if not match:
        return 0
    days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


def call_with_retries(
    fn: Callable[[], object],
    *,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
    delays: tuple[int, ...] = RETRY_DELAYS,
):
    """Call `fn`, retrying only on TransientError with the given delays plus jitter."""
    retries = 0
    while True:
        try:
            return fn()
        except TransientError as exc:
            if retries >= len(delays):
                raise ApiError(
                    f"YouTube kept failing after {retries + 1} attempts ({exc})."
                ) from exc
            sleep(delays[retries] * (0.5 + rng()))
            retries += 1


class YouTubeClient(ABC):
    """What the sync code needs from YouTube. Methods raise NotSignedIn, QuotaExceeded or
    ApiError. Each API request is counted in `calls` (one quota unit per list call)."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    def _count(self, method: str) -> None:
        self.calls[method] = self.calls.get(method, 0) + 1

    @property
    def units(self) -> int:
        return sum(self.calls.values())

    @abstractmethod
    def my_channel(self) -> MyChannel: ...

    @abstractmethod
    def list_subscriptions(self) -> list[ChannelInfo]:
        """The complete subscription list."""

    @abstractmethod
    def list_playlists(self) -> list[PlaylistInfo]:
        """The complete list of playlists the user owns."""

    @abstractmethod
    def list_playlist_video_ids(self, playlist_id: str, max_items: int | None = None) -> list[str]:
        """Video IDs in a playlist, newest first. Raises if the listing cannot be completed."""

    @abstractmethod
    def get_channels(self, channel_ids: list[str]) -> list[ChannelInfo]:
        """Channel details for at most 50 IDs (one API call)."""

    @abstractmethod
    def get_videos(self, video_ids: list[str]) -> list[VideoInfo]:
        """Video details for at most 50 IDs (one API call). Unknown IDs are simply missing."""


def _reason(exc: Exception) -> str:
    try:
        payload = json.loads(exc.content)  # type: ignore[attr-defined]
        return payload["error"]["errors"][0]["reason"]
    except (AttributeError, ValueError, KeyError, IndexError, TypeError):
        return ""


def _classify(exc: Exception) -> PodcastRecallError:
    """Turn a Google library or network exception into one of our errors. Messages never
    include URLs or tokens."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError:  # pragma: no cover - libraries missing
        HttpError = ()  # type: ignore[assignment]
    try:
        from google.auth.exceptions import RefreshError, TransportError
    except ImportError:  # pragma: no cover
        RefreshError = TransportError = ()  # type: ignore[assignment]
    if isinstance(exc, RefreshError):
        return NotSignedIn("Your sign-in expired or was revoked. Please sign in again.")
    if isinstance(exc, HttpError):
        status = getattr(getattr(exc, "resp", None), "status", 0)
        reason = _reason(exc)
        if status == 401:
            return NotSignedIn("Your sign-in expired or was revoked. Please sign in again.")
        if status == 403 and reason in _QUOTA_REASONS:
            return QuotaExceeded("YouTube's daily quota is used up. Try again tomorrow.")
        if status == 429 or 500 <= status < 600 or (status == 403 and reason in _RATE_REASONS):
            return TransientError(f"HTTP {status}")
        return ApiError(f"YouTube returned HTTP {status} ({reason or 'no reason given'}).")
    if isinstance(exc, (TransportError, OSError, TimeoutError)) or type(exc).__module__.startswith(
        "httplib2"
    ):
        return TransientError(f"network error: {type(exc).__name__}")
    return ApiError(f"Unexpected error talking to YouTube: {type(exc).__name__}.")


class GoogleYouTubeClient(YouTubeClient):
    def __init__(
        self,
        service,
        *,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ) -> None:
        super().__init__()
        self._service = service
        self._sleep = sleep
        self._rng = rng

    @classmethod
    def from_credentials_json(cls, credentials_json: str, **kwargs) -> GoogleYouTubeClient:
        try:
            import httplib2
            from google.oauth2.credentials import Credentials
            from google_auth_httplib2 import AuthorizedHttp
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise ConfigError("Google libraries are not installed. Run `uv sync`.") from exc
        creds = Credentials.from_authorized_user_info(json.loads(credentials_json), scopes=[SCOPE])
        http = AuthorizedHttp(creds, http=httplib2.Http(timeout=REQUEST_TIMEOUT_S))
        service = build("youtube", "v3", http=http, cache_discovery=False)
        return cls(service, **kwargs)

    # -- plumbing ---------------------------------------------------------------------------

    def _execute(self, name: str, build_request: Callable[[], object]) -> dict:
        if name == "search.list":
            raise ConfigError("search.list is never called by this app.")

        def attempt():
            self._count(name)
            try:
                return build_request().execute()  # type: ignore[attr-defined]
            except PodcastRecallError:
                raise
            except Exception as exc:
                raise _classify(exc) from exc

        return call_with_retries(attempt, sleep=self._sleep, rng=self._rng)  # type: ignore[return-value]

    def _pages(self, name: str, make_request: Callable[[str | None], object]):
        token: str | None = None
        while True:
            response = self._execute(name, lambda tok=token: make_request(tok))
            yield response
            token = response.get("nextPageToken")
            if not token:
                return

    # -- API calls --------------------------------------------------------------------------

    def my_channel(self) -> MyChannel:
        resp = self._execute(
            "channels.list",
            lambda: self._service.channels().list(part="snippet,contentDetails", mine=True),
        )
        items = resp.get("items", [])
        if not items:
            raise ApiError("No YouTube channel was found for this Google account.")
        item = items[0]
        likes = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("likes") or None
        return MyChannel(item["id"], item.get("snippet", {}).get("title", ""), likes)

    def list_subscriptions(self) -> list[ChannelInfo]:
        found: list[ChannelInfo] = []
        for page in self._pages(
            "subscriptions.list",
            lambda tok: self._service.subscriptions().list(
                part="snippet", mine=True, maxResults=BATCH_SIZE, pageToken=tok
            ),
        ):
            for item in page.get("items", []):
                snippet = item.get("snippet", {})
                channel_id = snippet.get("resourceId", {}).get("channelId")
                if channel_id:
                    found.append(ChannelInfo(channel_id, snippet.get("title", "")))
        return found

    def list_playlists(self) -> list[PlaylistInfo]:
        found: list[PlaylistInfo] = []
        for page in self._pages(
            "playlists.list",
            lambda tok: self._service.playlists().list(
                part="snippet", mine=True, maxResults=BATCH_SIZE, pageToken=tok
            ),
        ):
            for item in page.get("items", []):
                found.append(PlaylistInfo(item["id"], item.get("snippet", {}).get("title", "")))
        return found

    def list_playlist_video_ids(self, playlist_id: str, max_items: int | None = None) -> list[str]:
        size = min(BATCH_SIZE, max_items) if max_items else BATCH_SIZE
        ids: list[str] = []
        for page in self._pages(
            "playlistItems.list",
            lambda tok: self._service.playlistItems().list(
                part="contentDetails", playlistId=playlist_id, maxResults=size, pageToken=tok
            ),
        ):
            for item in page.get("items", []):
                video_id = item.get("contentDetails", {}).get("videoId")
                if video_id:
                    ids.append(video_id)
            if max_items and len(ids) >= max_items:
                return ids[:max_items]
        return ids

    def get_channels(self, channel_ids: list[str]) -> list[ChannelInfo]:
        if len(channel_ids) > BATCH_SIZE:
            raise ValueError("get_channels takes at most 50 IDs")
        resp = self._execute(
            "channels.list",
            lambda: self._service.channels().list(
                part="snippet,contentDetails", id=",".join(channel_ids)
            ),
        )
        return [
            ChannelInfo(
                item["id"],
                item.get("snippet", {}).get("title", ""),
                item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
            )
            for item in resp.get("items", [])
        ]

    def get_videos(self, video_ids: list[str]) -> list[VideoInfo]:
        if len(video_ids) > BATCH_SIZE:
            raise ValueError("get_videos takes at most 50 IDs")
        resp = self._execute(
            "videos.list",
            lambda: self._service.videos().list(
                part="snippet,contentDetails", id=",".join(video_ids)
            ),
        )
        videos = []
        for item in resp.get("items", []):
            snippet = item.get("snippet", {})
            videos.append(
                VideoInfo(
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    published_at=snippet.get("publishedAt", ""),
                    duration_s=parse_iso8601_duration(item.get("contentDetails", {}).get("duration")),
                    description=(snippet.get("description") or "")[:DESCRIPTION_LIMIT],
                    is_live_or_upcoming=snippet.get("liveBroadcastContent", "none")
                    in ("live", "upcoming"),
                )
            )
        return videos
