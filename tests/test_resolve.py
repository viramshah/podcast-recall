"""The resolver flows against a real (in-memory) database and a fake Podcast Index."""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from podcast_recall import core, store
from podcast_recall.errors import ApiError, ConfigError
from tests.base import Base
from tests.fake_pi import FakePodcastIndex, make_episode, make_feed, make_video

LENNY_FEED = make_feed(100, "Lenny's Podcast: Product | Career | Growth", "https://feeds.example.com/lenny.rss")
LENNY_EPISODES = [
    make_episode(1, 100, "Meta’s Muse: How we launched the most successful consumer product this year | Mona",
                 "2026-11-15T13:31:28", 5235, transcript="https://t.example.com/muse.vtt"),
    make_episode(2, 100, "Why PMs are suddenly valuable again | Tulsee Doshi", "2026-11-08T13:31:32", 3513),
    make_episode(3, 100, "How to close $100K+ enterprise deals, step by step | Jen Abel", "2026-08-23T12:31:43", 5097),
]
MUSE = ("v_muse", "The rise of Muse: Inside the launch of the most successful consumer product this year",
        "2026-11-15T10:00:00", 5240)
TULSEE = ("v_tulsee", "Why PMs are suddenly valuable again | Tulsee Doshi (Head of Product Gemini)",
          "2026-11-08T10:00:00", 3500)


class ResolveBase(Base):
    def setUp(self):
        super().setUp()
        self.pi = FakePodcastIndex(feeds=[LENNY_FEED], episodes={100: LENNY_EPISODES},
                                   search=[LENNY_FEED, make_feed(101, "Lenny's Daily Podcast")])

    def add(self, spec, channel_id="UCl", channel_title="Lenny's Podcast"):
        video_id, title, iso, duration = spec
        store.save_videos(self.conn, [video_id],
                          [make_video(video_id, title, iso, duration, channel_id, channel_title)], self.now())

    def choose_lenny_feed(self, channel_id="UCl"):
        return core.set_channel_feed(channel_id, str(LENNY_FEED.feed_id), conn=self.conn,
                                     pi_client=self.pi, now=self.now)

    def resolve(self, ids, **kwargs):
        return core.resolve_videos(ids, conn=self.conn, pi_client=self.pi, now=self.now, **kwargs)

    def match(self, video_id):
        return self.conn.execute("SELECT * FROM episode_matches WHERE video_id = ?", (video_id,)).fetchone()


class ChoosingFeeds(ResolveBase):
    def test_a_feed_can_be_set_by_id_or_by_url_and_is_stored(self):
        self.add(MUSE)
        feed = self.choose_lenny_feed()
        self.assertEqual(feed.title, LENNY_FEED.title)
        row = self.conn.execute("SELECT * FROM channel_feeds WHERE channel_id = 'UCl'").fetchone()
        self.assertEqual(row["feed_id"], 100)
        self.assertEqual(self.conn.execute("SELECT title FROM feeds WHERE feed_id = 100").fetchone()[0], LENNY_FEED.title)
        again = core.set_channel_feed("UCl", LENNY_FEED.url, conn=self.conn, pi_client=self.pi, now=self.now)
        self.assertEqual(again.feed_id, 100)
        self.assertIn("podcasts/byfeedurl", self.pi.calls)

    def test_none_needs_no_podcast_index_at_all(self):
        self.add(MUSE)
        self.assertIsNone(core.set_channel_feed("UCl", "None", conn=self.conn, now=self.now))
        row = self.conn.execute("SELECT * FROM channel_feeds").fetchone()
        self.assertIsNone(row["feed_id"])
        self.assertEqual(self.pi.calls, {})

    def test_unknown_feeds_and_channels_are_refused(self):
        self.add(MUSE)
        with self.assertRaises(ConfigError):
            core.set_channel_feed("UCl", "999", conn=self.conn, pi_client=self.pi, now=self.now)
        with self.assertRaises(ConfigError):
            core.set_channel_feed("UCnope", "100", conn=self.conn, pi_client=self.pi, now=self.now)

    def test_candidates_are_searched_by_the_channels_title_and_limited(self):
        self.add(MUSE)
        found = core.find_feed_candidates("UCl", limit=1, conn=self.conn, pi_client=self.pi)
        self.assertEqual([f.feed_id for f in found], [100])
        self.assertEqual(self.pi.requests[0][1]["term"], "Lenny's Podcast")
        with self.assertRaises(ConfigError):
            core.find_feed_candidates("UCnope", conn=self.conn, pi_client=self.pi)

    def test_channels_needing_a_feed_are_listed_until_a_choice_is_made(self):
        self.add(MUSE)
        self.add(TULSEE)
        waiting = core.channels_needing_feed(["v_muse", "v_tulsee"], conn=self.conn)
        self.assertEqual([(c.channel_id, c.video_count) for c in waiting], [("UCl", 2)])
        self.choose_lenny_feed()
        self.assertEqual(core.channels_needing_feed(["v_muse", "v_tulsee"], conn=self.conn), [])


class Resolving(ResolveBase):
    def test_a_channel_without_a_choice_gets_no_result_and_is_listed_as_waiting(self):
        self.add(MUSE)
        result = self.resolve(["v_muse"])
        self.assertEqual(self.match("v_muse"), None)
        self.assertEqual([c.channel_id for c in result.waiting], ["UCl"])
        self.assertEqual(self.pi.calls, {})  # nothing to fetch for a channel without a feed

    def test_a_channel_set_to_none_gives_no_feed(self):
        self.add(MUSE)
        core.set_channel_feed("UCl", "none", conn=self.conn, now=self.now)
        result = self.resolve(["v_muse"])
        row = self.match("v_muse")
        self.assertEqual((row["status"], row["episode_id"]), ("no_feed", None))
        self.assertEqual(result.counts["no_feed"], 1)

    def test_videos_are_matched_and_the_scores_are_stored(self):
        self.add(MUSE)
        self.add(TULSEE)
        self.choose_lenny_feed()
        result = self.resolve(["v_muse", "v_tulsee"])
        self.assertEqual(result.counts["matched"], 2)
        row = self.match("v_muse")
        self.assertEqual((row["status"], row["episode_id"], row["method"]), ("matched", 1, "score"))
        self.assertGreater(row["score"], 0.85)
        self.assertEqual(row["duration_diff_s"], 5240 - 5235)
        self.assertGreaterEqual(row["margin"], 0.15)
        self.assertEqual(row["reviewed"], 0)
        candidates = json.loads(row["candidates_json"])
        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0]["episode_id"], 1)
        for column in ("title_score", "date_score", "duration_score"):
            self.assertIsNotNone(row[column], column)

    def test_the_transcript_link_and_audio_url_are_kept_for_the_next_unit(self):
        self.add(MUSE)
        self.choose_lenny_feed()
        self.resolve(["v_muse"])
        episode = self.conn.execute("SELECT * FROM episodes WHERE episode_id = 1").fetchone()
        self.assertEqual(episode["transcript_url"], "https://t.example.com/muse.vtt")
        self.assertEqual(json.loads(episode["transcripts_json"])[0]["type"], "text/vtt")
        self.assertEqual(episode["audio_url"], "https://audio.example.com/1.mp3")
        self.assertEqual(episode["guid"], "guid-1")
        self.assertIsNone(
            self.conn.execute("SELECT transcript_url FROM episodes WHERE episode_id = 2").fetchone()[0])

    def test_running_twice_creates_no_duplicates_and_changes_nothing(self):
        self.add(MUSE)
        self.add(TULSEE)
        self.choose_lenny_feed()
        self.resolve(["v_muse", "v_tulsee"])
        before = [tuple(r) for r in self.conn.execute("SELECT video_id, episode_id, status, score FROM episode_matches ORDER BY 1")]
        self.resolve(["v_muse", "v_tulsee"])
        after = [tuple(r) for r in self.conn.execute("SELECT video_id, episode_id, status, score FROM episode_matches ORDER BY 1")]
        self.assertEqual(before, after)
        self.assertEqual(self.count("episode_matches"), 2)

    def test_two_videos_may_share_one_episode(self):
        self.add(MUSE)
        self.add(("v_muse_copy", MUSE[1], "2026-11-15T11:00:00", 5238))
        self.choose_lenny_feed()
        self.resolve(["v_muse", "v_muse_copy"])
        self.assertEqual({self.match("v_muse")["episode_id"], self.match("v_muse_copy")["episode_id"]}, {1})

    def test_unavailable_and_missing_videos_are_listed_not_resolved(self):
        self.add(MUSE)
        store.save_videos(self.conn, ["v_gone"], [], self.now())  # stored as unavailable
        self.choose_lenny_feed()
        result = self.resolve(["v_muse", "v_gone", "v_unknown"])
        self.assertEqual(result.unavailable, ["v_gone"])
        self.assertEqual(result.missing, ["v_unknown"])
        self.assertIsNone(self.match("v_gone"))

    def test_the_result_lists_each_video_with_its_status(self):
        self.add(MUSE)
        self.add(("v_other", "Cooking pasta at home", "2026-11-14T10:00:00", 600))
        self.choose_lenny_feed()
        result = self.resolve(["v_muse", "v_other"])
        statuses = {v.video_id: v.status for v in result.videos}
        self.assertEqual(statuses, {"v_muse": "matched", "v_other": "unmatched"})


class Refreshing(ResolveBase):
    def test_the_first_fetch_asks_for_everything_and_later_ones_ask_for_newer_episodes(self):
        self.add(MUSE)
        self.choose_lenny_feed()
        result = self.resolve(["v_muse"])
        self.assertEqual(result.feeds_refreshed, [(100, 3, False)])
        first = self.pi.requests[-1][1]
        self.assertEqual((first["since"], first["max_items"]), (None, 1000))

        self.pi.episodes_by_feed[100].append(
            make_episode(4, 100, "A brand new episode", "2026-11-20T10:00:00", 3000))
        result = self.resolve(["v_muse"])
        later = self.pi.requests[-1][1]
        newest_before = max(e.published for e in LENNY_EPISODES)
        self.assertEqual(later["since"], newest_before)
        self.assertEqual(result.feeds_refreshed, [(100, 1, False)])
        self.assertEqual(self.count("episodes"), 4)

    def test_no_refresh_uses_the_stored_episodes_without_calling_podcast_index(self):
        self.add(MUSE)
        self.choose_lenny_feed()
        self.resolve(["v_muse"])
        calls = dict(self.pi.calls)
        result = self.resolve(["v_muse"], refresh=False)
        self.assertEqual(self.pi.calls, calls)
        self.assertEqual(result.counts["matched"], 1)

    def test_full_refresh_fetches_everything_again(self):
        self.add(MUSE)
        self.choose_lenny_feed()
        self.resolve(["v_muse"])
        self.resolve(["v_muse"], full_refresh=True)
        self.assertIsNone(self.pi.requests[-1][1]["since"])

    def test_a_feed_that_returns_a_thousand_episodes_is_flagged_as_truncated(self):
        many = [make_episode(1000 + i, 100, f"Episode number {i}", "2026-01-01T10:00:00", 1800)
                for i in range(1000)]
        self.pi.episodes_by_feed[100] = many
        self.add(MUSE)
        self.choose_lenny_feed()
        result = self.resolve(["v_muse"])
        self.assertEqual(result.feeds_refreshed, [(100, 1000, True)])
        self.assertTrue(any("older ones may be missing" in w for w in result.warnings))
        self.assertEqual(self.conn.execute("SELECT truncated FROM feeds WHERE feed_id = 100").fetchone()[0], 1)

    def test_a_feed_failure_with_stored_episodes_makes_the_run_partial(self):
        self.add(MUSE)
        self.choose_lenny_feed()
        self.resolve(["v_muse"])
        self.pi.errors["episodes/byfeedid"] = ApiError("Podcast Index is down")
        result = self.resolve(["v_muse"])
        self.assertTrue(result.partial)
        self.assertEqual(result.counts["matched"], 1)  # resolved from the stored episodes
        self.assertTrue(any("Could not refresh" in w for w in result.warnings))

    def test_a_feed_failure_with_nothing_stored_and_nothing_else_to_do_is_raised(self):
        self.add(MUSE)
        self.choose_lenny_feed()
        self.pi.errors["episodes/byfeedid"] = ApiError("Podcast Index is down")
        with self.assertRaises(ApiError):
            self.resolve(["v_muse"])

    def test_a_feed_failure_is_only_partial_when_other_channels_could_be_resolved(self):
        self.add(MUSE)
        self.add(("v_other", "Some other video", "2026-11-01T10:00:00", 900), "UCother", "Other Channel")
        self.choose_lenny_feed()
        core.set_channel_feed("UCother", "none", conn=self.conn, now=self.now)
        self.pi.errors["episodes/byfeedid"] = ApiError("down")
        result = self.resolve(["v_muse", "v_other"])
        self.assertTrue(result.partial)
        self.assertEqual(result.counts["no_feed"], 1)

    def test_bad_credentials_stop_the_run_immediately(self):
        self.add(MUSE)
        self.choose_lenny_feed()
        self.pi.errors["episodes/byfeedid"] = ConfigError("Podcast Index rejected the credentials")
        with self.assertRaises(ConfigError):
            self.resolve(["v_muse"])


class ReviewedResults(ResolveBase):
    def setUp(self):
        super().setUp()
        self.add(MUSE)
        self.add(TULSEE)
        self.choose_lenny_feed()
        self.resolve(["v_muse", "v_tulsee"])

    def test_a_confirmed_result_is_never_overwritten(self):
        confirmed = core.confirm_match("v_tulsee", 3, conn=self.conn, now=self.now)  # deliberately another episode
        self.assertEqual((confirmed.status, confirmed.episode_id, confirmed.reviewed), ("matched", 3, True))
        result = self.resolve(["v_muse", "v_tulsee"])
        row = self.match("v_tulsee")
        self.assertEqual((row["episode_id"], row["method"], row["reviewed"]), (3, "confirmed", 1))
        self.assertEqual(result.kept_reviewed, 1)

    def test_a_rejected_result_stays_rejected(self):
        core.reject_match("v_muse", conn=self.conn, now=self.now)
        self.resolve(["v_muse"])
        row = self.match("v_muse")
        self.assertEqual((row["status"], row["episode_id"], row["reviewed"], row["method"]),
                         ("unmatched", None, 1, "rejected"))

    def test_confirm_and_reject_validate_their_inputs(self):
        with self.assertRaises(ConfigError):
            core.confirm_match("v_unknown", 1, conn=self.conn)
        with self.assertRaises(ConfigError):
            core.confirm_match("v_muse", 99999, conn=self.conn)
        with self.assertRaises(ConfigError):
            core.reject_match("v_unknown", conn=self.conn)

    def test_changing_a_channels_feed_drops_its_unreviewed_results_but_keeps_reviewed_ones(self):
        core.confirm_match("v_tulsee", 2, conn=self.conn, now=self.now)
        core.set_channel_feed("UCl", "none", conn=self.conn, now=self.now)
        self.assertIsNone(self.match("v_muse"))  # unreviewed: dropped
        self.assertEqual(self.match("v_tulsee")["reviewed"], 1)  # reviewed: kept
        self.resolve(["v_muse", "v_tulsee"])
        self.assertEqual(self.match("v_muse")["status"], "no_feed")
        self.assertEqual(self.match("v_tulsee")["status"], "matched")

    def test_the_review_list_shows_unreviewed_problems_only(self):
        self.add(("v_other", "Cooking pasta at home", "2026-11-14T10:00:00", 600))
        self.resolve(["v_muse", "v_tulsee", "v_other"])
        items = core.list_review_items(["v_muse", "v_tulsee", "v_other"], conn=self.conn)
        self.assertEqual([(i["video_id"], i["status"]) for i in items], [("v_other", "unmatched")])
        core.reject_match("v_other", conn=self.conn, now=self.now)
        self.assertEqual(core.list_review_items(["v_other"], conn=self.conn), [])

    def test_a_video_with_a_match_survives_the_u1_purge(self):
        old = "2020-01-01T00:00:00Z"
        self.conn.execute("UPDATE videos SET last_fetched_at = ?", (old,))
        store.save_videos(self.conn, ["v_free"], [make_video("v_free", "Nothing refers to me", "2026-01-01T00:00:00", 60)], old)
        result = core.purge_stale_videos(30, conn=self.conn, now=self.now)
        ids = {r[0] for r in self.conn.execute("SELECT video_id FROM videos")}
        self.assertNotIn("v_free", ids)
        self.assertIn("v_muse", ids)
        self.assertGreaterEqual(result.kept, 2)


class SeedCheckFile(ResolveBase):
    def test_the_check_file_has_one_row_per_seed_video_with_the_expected_outcome(self):
        self.add(("MuseVideo01", MUSE[1], MUSE[2], MUSE[3]))
        self.add(("OnlyVideo01", "Some creator video", "2026-11-01T10:00:00", 900), "UCx", "Some Creator")
        self.choose_lenny_feed()
        core.set_channel_feed("UCx", "none", conn=self.conn, now=self.now)
        self.resolve(["MuseVideo01", "OnlyVideo01"])
        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "seed.csv"
            seed.write_text(
                "youtube_url,show,title,date,has_rss,notes\n"
                "https://www.youtube.com/watch?v=MuseVideo01&t=3s,Lenny,Muse,2026-11-15,y,\n"
                "https://youtu.be/OnlyVideo01,Creator,Video,2026-11-01,n,\n"
                "https://www.youtube.com/watch?v=NeverFetchd,Nobody,Missing,2026-01-01,y,\n",
                encoding="utf-8",
            )
            out = Path(tmp) / "out" / "check.csv"
            rows = core.write_seed_check(seed, out, conn=self.conn)
            self.assertEqual(rows, 3)
            with out.open(encoding="utf-8") as handle:
                data = list(csv.DictReader(handle))
        by_id = {r["video_id"]: r for r in data}
        muse = by_id["MuseVideo01"]
        self.assertEqual((muse["status"], muse["expected"], muse["auto_check"]),
                         ("matched", "matched", "agrees"))
        self.assertEqual(muse["method"], "score")
        self.assertTrue(muse["episode_title"].startswith("Meta"))
        self.assertEqual(muse["correct (y/n)"], "")
        only = by_id["OnlyVideo01"]
        self.assertEqual((only["status"], only["expected"], only["auto_check"]),
                         ("no_feed", "not matched", "agrees"))
        self.assertEqual(by_id["NeverFetchd"]["auto_check"], "no result")

    def test_hand_marked_answers_survive_writing_the_file_again(self):
        self.add(("MuseVideo01", MUSE[1], MUSE[2], MUSE[3]))
        self.choose_lenny_feed()
        self.resolve(["MuseVideo01"])
        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "seed.csv"
            seed.write_text("youtube_url,show,title,date,has_rss,notes\n"
                            "https://youtu.be/MuseVideo01,Lenny,Muse,2026-11-15,y,\n", encoding="utf-8")
            out = Path(tmp) / "check.csv"
            core.write_seed_check(seed, out, conn=self.conn)
            text = out.read_text(encoding="utf-8").replace("agrees,\n", "agrees,y\n")
            out.write_text(text, encoding="utf-8")
            core.write_seed_check(seed, out, conn=self.conn)  # a second `resolve run --seed`
            with out.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["correct (y/n)"], "y")
