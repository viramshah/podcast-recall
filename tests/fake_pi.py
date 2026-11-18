"""A fake Podcast Index client and helpers for building feeds, episodes and videos in tests."""

from __future__ import annotations

from datetime import UTC, datetime

from podcast_recall.models import EpisodeInfo, FeedInfo, VideoInfo


def epoch(iso: str) -> int:
    return int(datetime.fromisoformat(iso).replace(tzinfo=UTC).timestamp())


def make_feed(feed_id: int, title: str, url: str = "", author: str = "Host") -> FeedInfo:
    return FeedInfo(feed_id, title, url or f"https://feeds.example.com/{feed_id}.xml", author, "en", 100)


def make_episode(episode_id: int, feed_id: int, title: str, iso: str, duration_s: int | None,
                 transcript: str | None = None) -> EpisodeInfo:
    return EpisodeInfo(
        episode_id=episode_id,
        feed_id=feed_id,
        guid=f"guid-{episode_id}",
        title=title,
        published=epoch(iso),
        duration_s=duration_s,
        audio_url=f"https://audio.example.com/{episode_id}.mp3",
        audio_type="audio/mpeg",
        transcript_url=transcript,
        transcripts=[{"url": transcript, "type": "text/vtt"}] if transcript else [],
        link=f"https://example.com/episodes/{episode_id}",
    )


def make_video(video_id: str, title: str, iso: str, duration_s: int,
               channel_id: str = "UCl", channel_title: str = "Lenny's Podcast") -> VideoInfo:
    return VideoInfo(
        video_id=video_id, title=title, channel_id=channel_id, channel_title=channel_title,
        published_at=iso + "Z", duration_s=duration_s, description="",
    )


class FakePodcastIndex:
    """Same interface as PodcastIndexClient, with no network."""

    def __init__(self, feeds=(), episodes=None, search=None) -> None:
        self.calls: dict[str, int] = {}
        self.requests: list[tuple[str, dict]] = []
        self.feeds = {f.feed_id: f for f in feeds}
        self.episodes_by_feed = {k: list(v) for k, v in (episodes or {}).items()}
        self.search_results = list(search or [])
        self.errors: dict[str, Exception] = {}  # method name -> error raised on every call

    def _hit(self, name: str, **info) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1
        self.requests.append((name, info))
        if name in self.errors:
            raise self.errors[name]

    def search_feeds(self, term, max_results=10):
        self._hit("search/byterm", term=term, max_results=max_results)
        return list(self.search_results)[:max_results]

    def feed_by_url(self, url):
        self._hit("podcasts/byfeedurl", url=url)
        return next((f for f in self.feeds.values() if f.url == url), None)

    def feed_by_id(self, feed_id):
        self._hit("podcasts/byfeedid", feed_id=feed_id)
        return self.feeds.get(feed_id)

    def episodes(self, feed_id, since=None, max_items=1000):
        self._hit("episodes/byfeedid", feed_id=feed_id, since=since, max_items=max_items)
        items = sorted(self.episodes_by_feed.get(feed_id, []), key=lambda e: -(e.published or 0))
        if since is not None:
            items = [e for e in items if (e.published or 0) > since]
        return items[:max_items]
