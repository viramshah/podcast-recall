"""core.py: fetch, channels, sign-in, revoke, purge and the sync lock."""

from __future__ import annotations

import json

from podcast_recall import auth, core, paths, store
from podcast_recall.errors import (
    ApiError,
    ConfigError,
    NotSignedIn,
    QuotaExceeded,
    SyncAlreadyRunning,
)
from podcast_recall.lock import SyncLock
from podcast_recall.models import MyChannel
from podcast_recall.youtube_client import SCOPE
from tests.base import Base
from tests.fakes import FakeYouTube, make_video, standard_world


class Fetch(Base):
    def test_fetch_writes_only_to_shared_tables(self):
        fake = standard_world()
        result = core.fetch_videos(["v1", "v2", "nope"], "owner", conn=self.conn, client=fake,
                                   now=self.now)
        self.assertEqual(result.fetched, 2)
        self.assertEqual([i for i, _ in result.unavailable], ["nope"])
        self.assertEqual(self.count("library_items"), 0)
        self.assertEqual(self.count("videos"), 3)
        status = self.conn.execute("SELECT status FROM videos WHERE video_id='nope'").fetchone()[0]
        self.assertEqual(status, "unavailable")

    def test_fetched_seed_videos_are_not_removed_by_a_sync(self):
        fake = standard_world()
        core.fetch_videos(["v8"], "owner", conn=self.conn, client=fake, now=self.now)
        self.run_sync(fake)
        self.assertIsNotNone(
            self.conn.execute("SELECT 1 FROM videos WHERE video_id='v8'").fetchone())
        self.assertNotIn("v8", self.lib())

    def test_fetch_splits_into_batches_of_50_and_removes_duplicates(self):
        ids = [f"x{i:03d}" for i in range(120)]
        fake = FakeYouTube(videos={i: make_video(i) for i in ids})
        result = core.fetch_videos(ids + ids[:5], "owner", conn=self.conn, client=fake,
                                   now=self.now)
        self.assertEqual(result.requested, 120)
        self.assertEqual(result.calls["videos.list"], 3)

    def test_fetch_returns_partial_when_quota_runs_out_after_some_work(self):
        ids = [f"x{i:03d}" for i in range(120)]
        fake = FakeYouTube(videos={i: make_video(i) for i in ids})
        fake.fail_after_calls = 1
        result = core.fetch_videos(ids, "owner", conn=self.conn, client=fake, now=self.now)
        self.assertTrue(result.partial)
        self.assertEqual(result.fetched, 50)

    def test_fetch_raises_when_nothing_could_be_done(self):
        fake = FakeYouTube()
        fake.fail_after_calls = 0
        with self.assertRaises(QuotaExceeded):
            core.fetch_videos(["a"], "owner", conn=self.conn, client=fake, now=self.now)

    def test_fetch_needs_a_signed_in_user(self):
        with self.assertRaises(NotSignedIn):
            core.fetch_videos(["a"], "stranger", conn=self.conn, client=FakeYouTube())


class Channels(Base):
    def test_channels_are_fetched_when_none_are_stored(self):
        fake = standard_world()
        rows = core.list_channels("owner", conn=self.conn, client=fake, now=self.now)
        self.assertEqual([r.title for r in rows], ["Alpha", "Beta"])
        self.assertEqual(fake.calls["subscriptions.list"], 1)
        core.list_channels("owner", conn=self.conn, client=fake, now=self.now)
        self.assertEqual(fake.calls["subscriptions.list"], 1)  # stored, no second fetch
        core.list_channels("owner", refresh=True, conn=self.conn, client=fake, now=self.now)
        self.assertEqual(fake.calls["subscriptions.list"], 2)

    def test_marked_channels_come_first_and_can_be_filtered(self):
        fake = standard_world()
        core.list_channels("owner", conn=self.conn, client=fake, now=self.now)
        core.set_podcast_channel("owner", "UCb", True, conn=self.conn)
        rows = core.list_channels("owner", conn=self.conn, client=fake)
        self.assertEqual([r.title for r in rows], ["Beta", "Alpha"])
        marked = core.list_channels("owner", marked_only=True, conn=self.conn, client=fake)
        self.assertEqual([r.title for r in marked], ["Beta"])

    def test_cannot_mark_a_channel_you_are_not_subscribed_to(self):
        core.list_channels("owner", conn=self.conn, client=standard_world(), now=self.now)
        with self.assertRaises(ConfigError):
            core.set_podcast_channel("owner", "UCnope", True, conn=self.conn)


def good_flow(channel_id="UCme", scopes=None, refresh=True):
    creds = json.dumps({"refresh_token": "1//refresh", "token": "ya29.access"})
    return lambda: auth.FlowResult(creds, set(scopes or [SCOPE]), refresh)


def client_for(channel_id="UCme", title="Me"):
    return lambda _creds: FakeYouTube(me=MyChannel(channel_id, title, "LLme"))


class SignIn(Base):
    def setUp(self):
        super().setUp()
        self.conn.execute("DELETE FROM users")
        self.conn.commit()
        self.tokens = auth.InMemoryTokenStore()

    def sign_in(self, flow=None, client=None, **kw):
        return core.sign_in("owner", conn=self.conn, token_store=self.tokens,
                            run_flow=flow or good_flow(), client_factory=client or client_for(),
                            now=self.now, **kw)

    def test_sign_in_saves_the_token_and_identifies_by_channel(self):
        result = self.sign_in()
        self.assertEqual((result.channel_id, result.channel_title), ("UCme", "Me"))
        self.assertIsNotNone(self.tokens.get("owner"))
        self.assertEqual(store.get_user(self.conn, "owner")["youtube_channel_id"], "UCme")

    def test_signing_in_again_replaces_the_token(self):
        self.sign_in()
        again = self.sign_in()
        self.assertTrue(again.token_replaced)
        self.assertEqual(self.count("users"), 1)

    def test_a_wrong_scope_is_refused_and_nothing_is_saved(self):
        broader = [SCOPE, "https://www.googleapis.com/auth/youtube"]
        with self.assertRaises(ConfigError):
            self.sign_in(flow=good_flow(scopes=broader))
        self.assertIsNone(self.tokens.get("owner"))
        self.assertEqual(self.count("users"), 0)

    def test_a_missing_refresh_token_is_refused(self):
        with self.assertRaises(ConfigError):
            self.sign_in(flow=good_flow(refresh=False))
        self.assertIsNone(self.tokens.get("owner"))

    def test_a_different_channel_is_refused_without_force(self):
        self.sign_in()
        old_token = self.tokens.get("owner")
        with self.assertRaises(ConfigError):
            self.sign_in(flow=lambda: auth.FlowResult('{"refresh_token":"1//other"}', {SCOPE}, True),
                         client=client_for("UCother", "Other"))
        self.assertEqual(self.tokens.get("owner"), old_token)
        self.assertEqual(store.get_user(self.conn, "owner")["youtube_channel_id"], "UCme")

    def test_force_replaces_the_channel_and_clears_the_library(self):
        self.sign_in()
        self.run_sync(standard_world())
        self.assertTrue(self.lib())
        result = self.sign_in(client=client_for("UCother", "Other"), force=True)
        self.assertTrue(result.library_cleared)
        self.assertEqual(self.lib(), set())
        self.assertEqual(store.get_user(self.conn, "owner")["youtube_channel_id"], "UCother")

    def test_user_names_are_validated(self):
        for bad in ("", "Owner", "has space", "x" * 33, "../etc"):
            with self.assertRaises(ConfigError):
                auth.validate_user_id(bad)
        self.assertEqual(auth.validate_user_id("a_b-9"), "a_b-9")


class Revoke(Base):
    def setUp(self):
        super().setUp()
        self.tokens = auth.InMemoryTokenStore()
        self.tokens.save("owner", json.dumps({"refresh_token": "1//refresh"}))
        fake = standard_world()
        self.run_sync(fake)
        core.set_podcast_channel("owner", "UCa", True, conn=self.conn)

    def test_revoke_deletes_per_user_rows_and_the_token_but_keeps_shared_data(self):
        posted = []
        result = core.revoke("owner", conn=self.conn, token_store=self.tokens,
                             http_post=lambda url, params: posted.append((url, params)) or 200)
        self.assertTrue(result.google_revoked)
        self.assertEqual(posted[0][0], auth.REVOKE_URL)
        for table in ("users", "library_items", "user_channels", "playlists", "sync_runs"):
            self.assertEqual(self.count(table), 0, table)
        self.assertGreater(self.count("videos"), 0)
        self.assertGreater(self.count("channels"), 0)
        self.assertIsNone(self.tokens.get("owner"))

    def test_local_data_is_deleted_even_if_google_cannot_be_reached(self):
        result = core.revoke("owner", conn=self.conn, token_store=self.tokens,
                             http_post=lambda url, params: 400)
        self.assertFalse(result.google_revoked)
        self.assertTrue(any("myaccount.google.com" in w for w in result.warnings))
        self.assertEqual(self.count("users"), 0)
        self.assertIsNone(self.tokens.get("owner"))

    def test_sync_after_revoke_says_to_sign_in_again(self):
        core.revoke("owner", conn=self.conn, token_store=self.tokens, http_post=lambda u, p: 200)
        with self.assertRaises(NotSignedIn):
            core.sync_library("owner", conn=self.conn, client=standard_world(), use_lock=False)

    def test_revoking_an_unknown_user_raises(self):
        with self.assertRaises(NotSignedIn):
            core.revoke("nobody", conn=self.conn, token_store=auth.InMemoryTokenStore())

    def test_revoke_at_google_never_raises(self):
        def boom(url, params):
            raise OSError("offline")

        self.assertFalse(auth.revoke_at_google('{"refresh_token": "x"}', boom))
        self.assertFalse(auth.revoke_at_google("not json", boom))


class PurgeAndStatus(Base):
    def test_purge_keeps_videos_that_something_refers_to(self):
        fake = standard_world()
        self.run_sync(fake)
        orphan = make_video("orphan")
        store.save_videos(self.conn, ["orphan"], [orphan], "2026-01-01T00:00:00Z")
        store.save_videos(self.conn, ["v1"], [fake.videos["v1"]], "2026-01-01T00:00:00Z")  # old but in library
        result = core.purge_stale_videos(30, conn=self.conn, now=self.now)
        self.assertEqual(result.deleted, 1)
        self.assertEqual(result.kept, 1)
        ids = {r[0] for r in self.conn.execute("SELECT video_id FROM videos")}
        self.assertNotIn("orphan", ids)
        self.assertIn("v1", ids)

    def test_purge_rejects_a_bad_age(self):
        with self.assertRaises(ConfigError):
            core.purge_stale_videos(0, conn=self.conn)

    def test_status_counts_unique_videos_and_names_sources(self):
        self.run_sync(standard_world())
        status = core.get_status("owner", conn=self.conn)
        self.assertEqual(status.unique_videos, 4)
        labels = dict(status.per_source)
        self.assertEqual(labels["Playlist: Mix"], 3)
        self.assertEqual(labels["Liked videos"], 2)
        self.assertEqual(status.channel_title, "Me")
        self.assertGreater(status.last_run_units, 0)

    def test_status_for_unknown_user_raises(self):
        with self.assertRaises(NotSignedIn):
            core.get_status("nobody", conn=self.conn)


class Locking(Base):
    def test_a_second_sync_is_refused_while_one_is_running(self):
        with SyncLock(paths.lock_path("owner")), self.assertRaises(SyncAlreadyRunning):
            core.sync_library("owner", conn=self.conn, client=standard_world(), now=self.now)
        # released afterwards
        result = core.sync_library("owner", conn=self.conn, client=standard_world(), now=self.now)
        self.assertEqual(result.status, "ok")

    def test_api_errors_are_not_swallowed(self):
        fake = standard_world()
        fake.fail_after_calls = 0
        fake.fail_with = ApiError("down")
        with self.assertRaises(ApiError):
            self.run_sync(fake)
