"""A fake YouTube client for tests. It counts API calls the way the real client does (one call per
page or batch) and can simulate latency and failures. No real account data is used."""

from __future__ import annotations

import math

from podcast_recall.errors import ApiError, QuotaExceeded
from podcast_recall.models import ChannelInfo, MyChannel, PlaylistInfo, VideoInfo
from podcast_recall.youtube_client import YouTubeClient


def make_video(video_id: str, channel_id: str = "UCx", channel_title: str = "Channel X",
               duration_s: int = 600) -> VideoInfo:
    return VideoInfo(
        video_id=video_id,
        title=f"Title {video_id}",
        channel_id=channel_id,
        channel_title=channel_title,
        published_at="2026-01-01T00:00:00Z",
        duration_s=duration_s,
        description="A fake description.",
    )


class FakeYouTube(YouTubeClient):
    LATENCY = 0.3  # simulated seconds per API call

    def __init__(self, *, subs=(), playlists=(), items=None, videos=None, channels=None,
                 likes_id="LLme", me=None):
        super().__init__()
        self.subs = list(subs)
        self.playlists = list(playlists)
        self.items = dict(items or {})
        self.videos = dict(videos or {})
        self.channel_info = dict(channels or {})
        self.me = me or MyChannel("UCme", "Me", likes_id)
        # (method, key, n) -> exception raised on the n-th call (0-based) for that method and key
        self.errors: dict[tuple, Exception] = {}
        self.fail_after_calls: int | None = None
        self.fail_with: Exception = QuotaExceeded("quota used up")
        self._seen: dict[tuple, int] = {}

    @property
    def elapsed(self) -> float:
        return self.units * self.LATENCY

    def _call(self, method: str, key=None) -> None:
        if self.fail_after_calls is not None and self.units >= self.fail_after_calls:
            raise self.fail_with
        n = self._seen.get((method, key), 0)
        self._seen[(method, key)] = n + 1
        self._count(method)
        if (method, key, n) in self.errors:
            raise self.errors[(method, key, n)]

    @staticmethod
    def _pages(total: int, size: int = 50) -> int:
        return max(1, math.ceil(total / size))

    def my_channel(self) -> MyChannel:
        self._call("channels.list", "me")
        return self.me

    def list_subscriptions(self):
        for _ in range(self._pages(len(self.subs))):
            self._call("subscriptions.list")
        return list(self.subs)

    def list_playlists(self):
        for _ in range(self._pages(len(self.playlists))):
            self._call("playlists.list")
        return list(self.playlists)

    def list_playlist_video_ids(self, playlist_id, max_items=None):
        if playlist_id not in self.items:
            self._call("playlistItems.list", playlist_id)
            raise ApiError(f"playlist {playlist_id} not found")
        data = self.items[playlist_id]
        limit = len(data) if max_items is None else min(len(data), max_items)
        size = 50 if max_items is None else min(50, max_items)
        for _ in range(self._pages(limit, size)):
            self._call("playlistItems.list", playlist_id)
        return list(data[:limit])

    def get_channels(self, channel_ids):
        assert len(channel_ids) <= 50
        self._call("channels.list", "details")
        return [self.channel_info[c] for c in channel_ids if c in self.channel_info]

    def get_videos(self, video_ids):
        assert len(video_ids) <= 50
        self._call("videos.list", "batch")
        return [self.videos[i] for i in video_ids if i in self.videos]


def standard_world() -> FakeYouTube:
    """Two subscriptions, one playlist, Liked videos and one uploads playlist. v3 is in both the
    playlist and Liked videos."""
    return FakeYouTube(
        subs=[ChannelInfo("UCa", "Alpha"), ChannelInfo("UCb", "Beta")],
        playlists=[PlaylistInfo("PL1", "Mix")],
        items={"PL1": ["v1", "v2", "v3"], "LLme": ["v3", "v4"], "UUa": ["v5", "v6", "v7", "v8"]},
        videos={f"v{i}": make_video(f"v{i}") for i in range(1, 9)},
        channels={"UCa": ChannelInfo("UCa", "Alpha", "UUa"), "UCb": ChannelInfo("UCb", "Beta", "UUb")},
    )
