"""The sync-time target, proved with a fake API that simulates 300 ms per call.

Library: about 200 subscriptions, 20 playlists with 2,000 items in total, Liked videos, and 10
podcast channels. First sync: at most 250 calls and 120 simulated seconds. Repeat sync (nothing
stale): at most 150 calls and 60 simulated seconds.
"""

from __future__ import annotations

from podcast_recall import core
from podcast_recall.models import ChannelInfo, PlaylistInfo
from tests.base import Base
from tests.fakes import FakeYouTube, make_video


def big_world() -> FakeYouTube:
    subs = [ChannelInfo(f"UC{i:03d}", f"Channel {i:03d}") for i in range(200)]
    playlists = [PlaylistInfo(f"PL{i:02d}", f"Playlist {i:02d}") for i in range(20)]
    items: dict[str, list[str]] = {}
    videos = {}
    for p in range(20):  # 20 playlists x 100 items = 2,000 playlist items
        ids = [f"p{p:02d}v{i:03d}" for i in range(100)]
        items[f"PL{p:02d}"] = ids
        videos.update({v: make_video(v) for v in ids})
    liked = [f"liked{i:03d}" for i in range(300)]
    items["LLme"] = liked
    videos.update({v: make_video(v) for v in liked})
    channels = {}
    for c in range(10):  # 10 podcast channels x 50 uploads
        uploads = [f"c{c:02d}u{i:03d}" for i in range(50)]
        items[f"UU{c:03d}"] = uploads
        videos.update({v: make_video(v) for v in uploads})
        channels[f"UC{c:03d}"] = ChannelInfo(f"UC{c:03d}", f"Channel {c:03d}", f"UU{c:03d}")
    return FakeYouTube(subs=subs, playlists=playlists, items=items, videos=videos, channels=channels)


class SyncTimeTarget(Base):
    def test_first_and_repeat_sync_stay_within_the_targets(self):
        fake = big_world()
        core.list_channels("owner", conn=self.conn, client=fake, now=self.now)
        for c in range(10):
            core.set_podcast_channel("owner", f"UC{c:03d}", True, conn=self.conn)

        first = self.run_sync(fake)
        self.assertEqual(first.status, "ok")
        self.assertLessEqual(first.estimated_units, 250)
        self.assertLessEqual(first.estimated_units * FakeYouTube.LATENCY, 120)
        self.assertEqual(self.count("videos"), 2000 + 300 + 500)

        repeat = self.run_sync(fake)
        self.assertEqual(repeat.status, "ok")
        self.assertLessEqual(repeat.estimated_units, 150)
        self.assertLessEqual(repeat.estimated_units * FakeYouTube.LATENCY, 60)
        self.assertNotIn("videos.list", repeat.calls)
