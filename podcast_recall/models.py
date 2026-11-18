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


@dataclass(frozen=True)
class FeedInfo:
    feed_id: int
    title: str = ""
    url: str = ""
    author: str = ""
    language: str = ""
    episode_count: int | None = None
    last_update: int | None = None


@dataclass(frozen=True)
class EpisodeInfo:
    episode_id: int
    feed_id: int
    guid: str
    title: str
    published: int | None
    duration_s: int | None
    audio_url: str = ""
    audio_type: str = ""
    transcript_url: str | None = None
    transcripts: list = field(default_factory=list)
    link: str = ""


@dataclass
class ResolvedVideo:
    video_id: str
    video_title: str
    status: str
    method: str = ""
    reason: str = ""
    episode_id: int | None = None
    episode_title: str = ""
    score: float | None = None
    title_score: float | None = None
    date_score: float | None = None
    duration_score: float | None = None
    duration_diff_s: int | None = None
    margin: float | None = None
    reviewed: bool = False


@dataclass(frozen=True)
class ChannelNeedingFeed:
    channel_id: str
    title: str
    video_count: int
    sample_titles: tuple[str, ...] = ()


@dataclass
class ResolveResult:
    counts: dict[str, int]
    videos: list[ResolvedVideo]
    waiting: list[ChannelNeedingFeed]
    unavailable: list[str]
    missing: list[str]
    kept_reviewed: int
    feeds_refreshed: list[tuple[int, int, bool]]  # (feed id, new episodes, truncated)
    calls: dict[str, int]
    warnings: list[str]
    partial: bool = False
