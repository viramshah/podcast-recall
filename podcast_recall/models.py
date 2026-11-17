"""Plain data objects passed between the YouTube client, the store and the core functions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChannelInfo:
    channel_id: str
    title: str = ""
    uploads_playlist_id: str | None = None


@dataclass(frozen=True)
class PlaylistInfo:
    playlist_id: str
    title: str = ""


@dataclass(frozen=True)
class MyChannel:
    channel_id: str
    title: str
    likes_playlist_id: str | None


@dataclass(frozen=True)
class VideoInfo:
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    published_at: str
    duration_s: int
    description: str
    is_live_or_upcoming: bool = False


@dataclass
class SourceResult:
    source: str
    label: str
    found: int = 0
    added: int = 0
    removed: int = 0
    skipped_unavailable: int = 0
    deferred: int = 0
    complete: bool = True
    error: str | None = None


@dataclass
class SyncResult:
    user_id: str
    status: str  # "ok" or "partial"
    reason: str | None
    sources: list[SourceResult]
    calls: dict[str, int]
    estimated_units: int
    videos_fetched: int
    warnings: list[str]
    started_at: str
    finished_at: str
    run_id: int | None = None

    @property
    def partial(self) -> bool:
        return self.status == "partial"


@dataclass
class FetchResult:
    requested: int
    fetched: int
    unavailable: list[tuple[str, str]]
    calls: dict[str, int]
    estimated_units: int
    partial: bool = False
    reason: str | None = None
    unparsed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChannelRow:
    channel_id: str
    title: str
    subscribed: bool
    is_podcast: bool


@dataclass
class SignInResult:
    user_id: str
    channel_id: str
    channel_title: str
    token_replaced: bool
    library_cleared: bool = False


@dataclass
class StatusResult:
    user_id: str
    channel_title: str
    last_run: dict | None
    unique_videos: int
    per_source: list[tuple[str, int]]
    unavailable_in_library: int
    last_run_units: int | None


@dataclass
class RevokeResult:
    google_revoked: bool
    warnings: list[str]


@dataclass
class PurgeResult:
    deleted: int
    kept: int
