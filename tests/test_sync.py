"""Sync behaviour: the rules in specs/features/u1-youtube-connector/requirements.md."""

from __future__ import annotations

from podcast_recall import core
from podcast_recall.errors import ApiError, NotSignedIn, QuotaExceeded
from podcast_recall.models import ChannelInfo, PlaylistInfo
from tests.base import Base
from tests.fakes import FakeYouTube, make_video, standard_world


class FirstAndRepeatSync(Base):
    def test_first_sync_builds_the_library(self):
        fake = standard_world()
        result = self.run_sync(fake)
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.lib(), {"v1", "v2", "v3", "v4"})
        self.assertEqual(self.count("library_items"), 5)  # v3 is in two sources
        self.assertEqual(result.calls["videos.list"], 1)
        self.assertEqual(self.source(result, "playlist:PL1").added, 3)
        self.assertEqual(self.source(result, "liked").added, 2)

    def test_second_sync_is_identical_and_fetches_no_details(self):
        fake = standard_world()
        self.run_sync(fake)
        before = {t: self.count(t) for t in ("library_items", "videos", "channels", "playlists")}
        result = self.run_sync(fake)
        after = {t: self.count(t) for t in before}
        self.assertEqual(before, after)
        self.assertNotIn("videos.list", result.calls)
        self.assertEqual(result.status, "ok")

    def test_unmarked_channels_are_not_synced(self):
        self.run_sync(standard_world())
        self.assertFalse(self.lib("channel:UCa"))

    def test_progress_events_are_reported(self):
        events = []
        self.run_sync(standard_world(), on_progress=events.append)
        sources = {e["source"] for e in events if e["stage"] == "source"}
        self.assertEqual(sources, {"playlist:PL1", "liked"})

    def test_sync_run_is_recorded(self):
        result = self.run_sync(standard_world())
        run = self.conn.execute("SELECT * FROM sync_runs").fetchone()
        self.assertEqual(run["result"], "ok")
        self.assertEqual(run["estimated_units"], result.estimated_units)
        self.assertEqual(result.run_id, run["id"])


class RemovalRules(Base):
    def test_removing_a_playlist_item_removes_it_from_the_library(self):
        fake = standard_world()
        self.run_sync(fake)
        fake.items["PL1"] = ["v1", "v3"]
        result = self.run_sync(fake)
        self.assertNotIn("v2", self.lib())
        self.assertEqual(self.source(result, "playlist:PL1").removed, 1)

    def test_video_in_two_sources_stays_when_one_drops_it(self):
        fake = standard_world()
        self.run_sync(fake)
        fake.items["PL1"] = ["v1", "v2"]  # v3 leaves the playlist but is still liked
        self.run_sync(fake)
        self.assertIn("v3", self.lib())
        self.assertEqual(self.lib("liked"), {"v3", "v4"})
        fake.items["LLme"] = ["v4"]  # now v3 is in no source
        self.run_sync(fake)
        self.assertNotIn("v3", self.lib())

    def test_failed_listing_removes_nothing_and_marks_partial(self):
        ids = [f"p{i:03d}" for i in range(120)]
        fake = FakeYouTube(
            playlists=[PlaylistInfo("PL1", "Big")],
            items={"PL1": ids, "LLme": []},
            videos={i: make_video(i) for i in ids},
        )
        self.run_sync(fake)
        self.assertEqual(len(self.lib("playlist:PL1")), 120)
        fake.items["PL1"] = ids[:60]  # the playlist really shrank (to 2 pages)...
        # The first sync used pages 0-2. In the second sync, page 4 (its second page) fails.
        fake.errors[("playlistItems.list", "PL1", 4)] = ApiError("boom")
        result = self.run_sync(fake)
        self.assertEqual(result.status, "partial")
        self.assertFalse(self.source(result, "playlist:PL1").complete)
        self.assertEqual(len(self.lib("playlist:PL1")), 120)  # nothing was removed

    def test_deleted_playlist_loses_its_items(self):
        fake = standard_world()
        self.run_sync(fake)
        fake.playlists = []
        result = self.run_sync(fake)
        self.assertEqual(self.lib("playlist:PL1"), set())
        self.assertEqual(self.count("playlists"), 0)
        self.assertEqual(self.source(result, "playlist:PL1").removed, 3)


class PlaceholdersAndRefresh(Base):
    def _world_with_ghost(self):
        fake = standard_world()
        fake.items["PL1"] = ["v1", "ghost"]
        return fake

    def test_unavailable_videos_are_skipped_and_counted(self):
        fake = self._world_with_ghost()
        result = self.run_sync(fake)
        self.assertEqual(self.lib("playlist:PL1"), {"v1"})
        self.assertEqual(self.source(result, "playlist:PL1").skipped_unavailable, 1)
        row = self.conn.execute("SELECT status FROM videos WHERE video_id = 'ghost'").fetchone()
        self.assertEqual(row["status"], "unavailable")

    def test_unavailable_videos_are_not_refetched_while_fresh(self):
        fake = self._world_with_ghost()
        self.run_sync(fake)
        result = self.run_sync(fake)
        self.assertNotIn("videos.list", result.calls)

    def test_stale_videos_are_fetched_again_and_can_become_available(self):
        fake = self._world_with_ghost()
        self.run_sync(fake)
        fake.videos["ghost"] = make_video("ghost")
        self.clock = "2026-12-25T12:00:00Z"  # more than 30 days later
        result = self.run_sync(fake)
        self.assertIn("videos.list", result.calls)
        self.assertEqual(self.lib("playlist:PL1"), {"v1", "ghost"})

    def test_video_that_turns_private_is_marked_unavailable_but_kept(self):
        fake = standard_world()
        self.run_sync(fake)
        del fake.videos["v1"]
        self.clock = "2026-12-25T12:00:00Z"
        self.run_sync(fake)
        status = self.conn.execute("SELECT status FROM videos WHERE video_id='v1'").fetchone()[0]
        self.assertEqual(status, "unavailable")
        self.assertIn("v1", self.lib())

    def test_video_from_an_unsubscribed_channel_still_gets_a_channel_row(self):
        fake = standard_world()
        fake.videos["v1"] = make_video("v1", channel_id="UCz", channel_title="Stranger")
        self.run_sync(fake)
        row = self.conn.execute("SELECT title FROM channels WHERE channel_id = 'UCz'").fetchone()
        self.assertEqual(row["title"], "Stranger")


class ChannelSources(Base):
    def _mark_alpha(self, fake):
        self.run_sync(fake)  # stores the subscriptions
        core.set_podcast_channel("owner", "UCa", True, conn=self.conn)

    def test_marked_channel_uploads_are_added(self):
        fake = standard_world()
        self._mark_alpha(fake)
        result = self.run_sync(fake)
        self.assertEqual(self.lib("channel:UCa"), {"v5", "v6", "v7", "v8"})
        self.assertEqual(self.source(result, "channel:UCa").added, 4)

    def test_channel_items_are_cumulative_not_a_window(self):
        fake = standard_world()
        self._mark_alpha(fake)
        self.run_sync(fake)
        fake.items["UUa"] = ["v1", "v2"]  # newest uploads moved on; old ones fall out of the window
        result = self.run_sync(fake)
        self.assertTrue({"v5", "v6", "v7", "v8"} <= self.lib("channel:UCa"))
        self.assertEqual(self.source(result, "channel:UCa").removed, 0)

    def test_only_the_latest_50_uploads_are_checked(self):
        fake = standard_world()
        many = [f"u{i:03d}" for i in range(80)]
        fake.items["UUa"] = many
        fake.videos.update({i: make_video(i) for i in many})
        self._mark_alpha(fake)
        self.run_sync(fake)
        self.assertEqual(len(self.lib("channel:UCa")), 50)

    def test_unmarking_removes_channel_items_at_next_sync(self):
        fake = standard_world()
        self._mark_alpha(fake)
        self.run_sync(fake)
        core.set_podcast_channel("owner", "UCa", False, conn=self.conn)
        result = self.run_sync(fake)
        self.assertEqual(self.lib("channel:UCa"), set())
        self.assertEqual(self.source(result, "channel:UCa").removed, 4)

    def test_unsubscribing_removes_channel_items(self):
        fake = standard_world()
        self._mark_alpha(fake)
        self.run_sync(fake)
        fake.subs = [ChannelInfo("UCb", "Beta")]
        self.run_sync(fake)
        self.assertEqual(self.lib("channel:UCa"), set())
        flag = self.conn.execute(
            "SELECT subscribed FROM user_channels WHERE channel_id = 'UCa'").fetchone()[0]
        self.assertEqual(flag, 0)

    def test_incomplete_subscription_listing_unsubscribes_nobody(self):
        fake = standard_world()
        self._mark_alpha(fake)
        self.run_sync(fake)
        # A 60-channel list without UCa takes 2 pages. Page 2 fails, so the listing is incomplete.
        fake.subs = [ChannelInfo(f"UCn{i}", f"N{i}") for i in range(60)]
        next_page = fake._seen.get(("subscriptions.list", None), 0)
        fake.errors[("subscriptions.list", None, next_page + 1)] = ApiError("boom")
        result = self.run_sync(fake)
        self.assertEqual(result.status, "partial")
        self.assertTrue(self.lib("channel:UCa"))
        flag = self.conn.execute(
            "SELECT subscribed FROM user_channels WHERE channel_id = 'UCa'").fetchone()[0]
        self.assertEqual(flag, 1)

    def test_uploads_playlist_id_is_cached(self):
        fake = standard_world()
        self._mark_alpha(fake)
        self.run_sync(fake)
        result = self.run_sync(fake)
        # no `channels.list` for details on the second run (only the call for your own channel)
        self.assertEqual(result.calls.get("channels.list", 0), 1)


class Failures(Base):
    def test_quota_exceeded_partway_returns_a_partial_result(self):
        fake = standard_world()
        fake.fail_after_calls = 3  # subscriptions, playlists and your channel succeed
        result = self.run_sync(fake)
        self.assertEqual(result.status, "partial")
        self.assertIn("quota", result.reason.lower())
        self.assertEqual(self.lib(), set())

    def test_quota_exceeded_before_any_call_raises(self):
        fake = standard_world()
        fake.fail_after_calls = 0
        with self.assertRaises(QuotaExceeded):
            self.run_sync(fake)
        run = self.conn.execute("SELECT result FROM sync_runs").fetchone()
        self.assertEqual(run["result"], "failed")

    def test_not_signed_in_raises_and_records_a_failed_run(self):
        fake = standard_world()
        fake.fail_after_calls = 0
        fake.fail_with = NotSignedIn("expired")
        with self.assertRaises(NotSignedIn):
            self.run_sync(fake)
        self.assertEqual(self.conn.execute("SELECT result FROM sync_runs").fetchone()[0], "failed")

    def test_failure_of_one_step_does_not_stop_the_others(self):
        fake = standard_world()
        fake.errors[("channels.list", "me", 0)] = ApiError("boom")  # no Liked videos this time
        result = self.run_sync(fake)
        self.assertEqual(result.status, "partial")
        self.assertEqual(self.lib("playlist:PL1"), {"v1", "v2", "v3"})
        self.assertEqual(self.lib("liked"), set())

    def test_everything_failing_raises_the_api_error(self):
        fake = standard_world()
        fake.fail_after_calls = 0
        fake.fail_with = ApiError("network down")
        with self.assertRaises(ApiError):
            self.run_sync(fake)

    def test_unknown_user_is_not_signed_in(self):
        with self.assertRaises(NotSignedIn):
            core.sync_library("nobody", conn=self.conn, client=standard_world(), use_lock=False)

    def test_failed_video_details_are_retried_next_sync(self):
        fake = standard_world()
        fake.errors[("videos.list", "batch", 0)] = ApiError("boom")
        result = self.run_sync(fake)
        self.assertEqual(result.status, "partial")
        self.assertEqual(self.lib(), set())  # nothing could be added yet
        result = self.run_sync(fake)
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.lib(), {"v1", "v2", "v3", "v4"})
