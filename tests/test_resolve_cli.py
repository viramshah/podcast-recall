"""The `resolve` commands: prompts, exit codes and output. Core functions are replaced by mocks."""

from __future__ import annotations

import contextlib
import csv
import io
import logging
import os
import tempfile
from pathlib import Path
from unittest import mock

from podcast_recall import cli, core, store
from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.models import ChannelNeedingFeed, ResolvedVideo, ResolveResult
from tests.base import Base
from tests.fake_pi import FakePodcastIndex, make_feed, make_video
from tests.test_resolve import LENNY_EPISODES, LENNY_FEED

FEEDS = [make_feed(100, "Lenny's Podcast", "https://f/lenny.rss", "Lenny"), make_feed(101, "Lenny's Daily")]
CHANNEL = ChannelNeedingFeed("UCl", "Lenny's Podcast", 3, ("Episode one", "Episode two"))


def result(**kwargs) -> ResolveResult:
    base = {
        "counts": {"matched": 1, "needs_review": 0, "unmatched": 0, "no_feed": 0},
        "videos": [ResolvedVideo("v1", "A video", "matched", episode_id=1, episode_title="An episode", score=0.9)],
        "waiting": [], "unavailable": [], "missing": [], "kept_reviewed": 0, "feeds_refreshed": [],
        "calls": {}, "warnings": [],
    }
    base.update(kwargs)
    return ResolveResult(**base)


class CliBase(Base):
    def run_cli(self, *argv, answers=None):
        out, err = io.StringIO(), io.StringIO()
        asked = iter(answers or [])

        def fake_input(_prompt=""):
            try:
                return next(asked)
            except StopIteration:
                raise EOFError from None

        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch(
                "builtins.input", side_effect=fake_input):
            code = cli.main(list(argv))
        for handler in list(logging.getLogger("podcast_recall").handlers):
            handler.close()
            logging.getLogger("podcast_recall").removeHandler(handler)
        return code, out.getvalue(), err.getvalue()


class Run(CliBase):
    def test_exit_codes(self):
        patch = "podcast_recall.core.resolve_videos"
        self.enterContext(mock.patch("podcast_recall.core.resolvable_library_videos", return_value=["v1"]))
        with mock.patch(patch, return_value=result()):
            self.assertEqual(self.run_cli("resolve", "run")[0], 0)
        needs_review = {"matched": 0, "needs_review": 1, "unmatched": 0, "no_feed": 0}
        for extra in ({"partial": True}, {"waiting": [CHANNEL]}, {"missing": ["v9"]}, {"counts": needs_review}):
            with mock.patch(patch, return_value=result(**extra)):
                self.assertEqual(self.run_cli("resolve", "run")[0], 2, extra)
        with mock.patch(patch, side_effect=ApiError("Podcast Index is down")):
            code, _out, err = self.run_cli("resolve", "run")
        self.assertEqual(code, 1)
        self.assertIn("Podcast Index is down", err)
        with mock.patch(patch, side_effect=ConfigError("no credentials")):
            self.assertEqual(self.run_cli("resolve", "run")[0], 1)

    def test_options_reach_the_core_function(self):
        with mock.patch("podcast_recall.core.resolvable_library_videos", return_value=["v1"]), mock.patch(
                "podcast_recall.core.resolve_videos", return_value=result()) as resolve:
            self.run_cli("resolve", "run", "--no-refresh", "--full-refresh")
        self.assertEqual(resolve.call_args.args[0], ["v1"])
        self.assertEqual(resolve.call_args.kwargs, {"refresh": False, "full_refresh": True})

    def test_seed_mode_reads_the_seed_file_and_writes_the_check_file(self):
        with mock.patch("podcast_recall.ids.load_ids", return_value=(["a" * 11], [])) as load, mock.patch(
                "podcast_recall.core.resolve_videos", return_value=result()), mock.patch(
                "podcast_recall.core.write_seed_check", return_value=20) as write:
            code, out, _err = self.run_cli("resolve", "run", "--seed")
        self.assertEqual(code, 0)
        load.assert_called_once_with(["data/seed_episodes.csv"])
        write.assert_called_once_with("data/seed_episodes.csv", "data/seed_resolver_check.csv")
        self.assertIn("Wrote data/seed_resolver_check.csv (20 rows)", out)

    def test_a_custom_seed_file_is_used(self):
        with mock.patch("podcast_recall.ids.load_ids", return_value=(["a" * 11], [])) as load, mock.patch(
                "podcast_recall.core.resolve_videos", return_value=result()), mock.patch(
                "podcast_recall.core.write_seed_check", return_value=1):
            self.run_cli("resolve", "run", "--seed", "other.csv")
        load.assert_called_once_with(["other.csv"])

    def test_the_summary_lists_problems_waiting_channels_and_calls(self):
        text = cli.format_resolve(result(
            counts={"matched": 1, "needs_review": 1, "unmatched": 1, "no_feed": 2},
            videos=[
                ResolvedVideo("v1", "Close one", "needs_review", reason="a close second candidate",
                              episode_id=7, episode_title="Maybe this", score=0.72, title_score=0.5,
                              date_score=1.0, duration_score=1.0),
                ResolvedVideo("v2", "Nothing fits", "unmatched", reason="no episode is close enough"),
                ResolvedVideo("v3", "Fine", "matched", episode_id=1, episode_title="Ok", score=0.9),
            ],
            waiting=[CHANNEL], unavailable=["x"], missing=["y", "z"], kept_reviewed=2,
            feeds_refreshed=[(100, 4, True)], calls={"episodes/byfeedid": 1}, warnings=["be careful"]))
        for expected in ("matched 1, needs_review 1, unmatched 1, no_feed 2",
                         "needs_review: Close one -> Maybe this (episode 7): score 0.72 (title 0.50, date 1.00, length 1.00)",
                         "unmatched: Nothing fits", "Lenny's Podcast (UCl): 3 video(s)", "Skipped 1 unavailable",
                         "2 video(s) are not in the database", "Kept 2 result(s)", "Feed 100: 4 new episode(s) (list may be truncated)",
                         "Podcast Index calls: episodes/byfeedid: 1", "Warning: be careful"):
            self.assertIn(expected, text)
        self.assertNotIn("Fine ->", text)  # matched results are not listed one by one


class ChooseFeeds(CliBase):
    def run_feeds(self, answers, **patches):
        with mock.patch("podcast_recall.core.resolvable_library_videos", return_value=["v1"]), mock.patch(
                "podcast_recall.core.channels_needing_feed", return_value=[CHANNEL]), mock.patch(
                "podcast_recall.core.find_feed_candidates", return_value=FEEDS), mock.patch(
                "podcast_recall.core.set_channel_feed", **patches) as setter:
            code, out, err = self.run_cli("resolve", "feeds", answers=answers)
        return code, out, err, setter

    def test_picking_a_number_saves_that_feed(self):
        code, out, _err, setter = self.run_feeds(["1"], return_value=FEEDS[0])
        self.assertEqual(code, 0)
        setter.assert_called_once_with("UCl", "100")
        self.assertIn("1. Lenny's Podcast | by Lenny | 100 episodes", out)
        self.assertIn("Saved: Lenny's Podcast", out)

    def test_n_means_no_feed(self):
        code, _out, _err, setter = self.run_feeds(["n"], return_value=None)
        self.assertEqual(code, 0)
        setter.assert_called_once_with("UCl", "none")

    def test_u_asks_for_a_url_and_retries_after_an_error(self):
        setter_results = [ConfigError("Podcast Index does not know the feed"), FEEDS[1]]
        code, _out, err, setter = self.run_feeds(["u", "bad-url", "u", "https://f/daily.rss"],
                                                 side_effect=setter_results)
        self.assertEqual(code, 0)
        self.assertEqual([c.args for c in setter.call_args_list],
                         [("UCl", "bad-url"), ("UCl", "https://f/daily.rss")])
        self.assertIn("does not know the feed", err)

    def test_skipping_or_having_no_terminal_exits_with_the_partial_code(self):
        code, _out, _err, setter = self.run_feeds(["s"], return_value=None)
        self.assertEqual(code, 2)
        setter.assert_not_called()
        code, _out, _err, setter = self.run_feeds([], return_value=None)  # no input at all
        self.assertEqual(code, 2)

    def test_invalid_answers_are_asked_again(self):
        code, out, _err, setter = self.run_feeds(["9", "what", "2"], return_value=FEEDS[1])
        self.assertEqual(code, 0)
        setter.assert_called_once_with("UCl", "101")
        self.assertEqual(out.count("Please choose one of the options."), 2)

    def test_nothing_to_choose(self):
        with mock.patch("podcast_recall.core.resolvable_library_videos", return_value=["v1"]), mock.patch(
                "podcast_recall.core.channels_needing_feed", return_value=[]):
            code, out, _err = self.run_cli("resolve", "feeds")
        self.assertEqual(code, 0)
        self.assertIn("already has a feed choice", out)


class OtherCommands(CliBase):
    def test_set_feed_confirm_and_reject(self):
        with mock.patch("podcast_recall.core.set_channel_feed", return_value=FEEDS[0]) as setter:
            code, out, _err = self.run_cli("resolve", "set-feed", "UCl", "100")
        self.assertEqual((code, setter.call_args.args), (0, ("UCl", "100")))
        self.assertIn("Saved: Lenny's Podcast", out)
        with mock.patch("podcast_recall.core.set_channel_feed", return_value=None):
            self.assertIn("no feed", self.run_cli("resolve", "set-feed", "UCl", "none")[1])
        done = ResolvedVideo("v1", "A video", "matched", episode_title="An episode")
        with mock.patch("podcast_recall.core.confirm_match", return_value=done) as confirm:
            code, out, _err = self.run_cli("resolve", "confirm", "v1", "42")
        self.assertEqual((code, confirm.call_args.args), (0, ("v1", 42)))
        self.assertIn("Confirmed: A video -> An episode", out)
        with mock.patch("podcast_recall.core.reject_match", return_value=done) as reject:
            code, out, _err = self.run_cli("resolve", "reject", "v1")
        self.assertEqual((code, reject.call_args.args), (0, ("v1",)))
        self.assertIn("Rejected", out)

    def test_confirm_needs_a_numeric_episode_id(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.build_parser().parse_args(["resolve", "confirm", "v1", "not-a-number"])

    def test_review_prints_items_and_waiting_channels(self):
        item = {"video_id": "v2", "video_title": "Close one", "status": "needs_review", "method": "partial",
                "reason": "partly agree", "score": 0.7, "title_score": 0.5, "date_score": 1.0,
                "duration_score": 0.6, "duration_diff_s": 400,
                "candidates": [{"episode_id": 7, "title": "Maybe this", "combined": 0.7}]}
        with mock.patch("podcast_recall.core.resolvable_library_videos", return_value=["v2"]), mock.patch(
                "podcast_recall.core.list_review_items", return_value=[item]), mock.patch(
                "podcast_recall.core.channels_needing_feed", return_value=[CHANNEL]):
            code, out, _err = self.run_cli("resolve", "review")
        self.assertEqual(code, 0)
        self.assertIn("needs_review: Close one (v2)", out)
        self.assertIn("1. episode 7: Maybe this (score 0.70)", out)
        self.assertIn("Waiting for a feed choice: Lenny's Podcast (UCl)", out)

    def test_review_with_nothing_to_do(self):
        with mock.patch("podcast_recall.core.resolvable_library_videos", return_value=["v2"]), mock.patch(
                "podcast_recall.core.list_review_items", return_value=[]), mock.patch(
                "podcast_recall.core.channels_needing_feed", return_value=[]):
            self.assertIn("Nothing to review", self.run_cli("resolve", "review")[1])

    def test_resolve_commands_take_the_user_option_where_it_makes_sense(self):
        with mock.patch("podcast_recall.core.resolvable_library_videos", return_value=[]) as lib, mock.patch(
                "podcast_recall.core.resolve_videos", return_value=result()):
            self.run_cli("resolve", "run", "--user", "ana")
        self.assertEqual(lib.call_args.args, ("ana",))


class EndToEnd(CliBase):
    """The real commands, a real database file and a fake Podcast Index."""

    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        previous = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, previous)
        self.pi = FakePodcastIndex(feeds=[LENNY_FEED], episodes={100: LENNY_EPISODES}, search=[LENNY_FEED])
        self.enterContext(mock.patch("podcast_recall.podcastindex.load_credentials", return_value=object()))
        self.enterContext(mock.patch("podcast_recall.podcastindex.PodcastIndexClient", return_value=self.pi))
        conn = core.open_db()
        store.upsert_user(conn, "owner", "UCme", "Me", "2026-11-17T12:00:00Z")
        rows = [
            ("MuseVideo01", "The rise of Muse: Inside the launch of the most successful consumer product this year",
             "2026-11-15T10:00:00", 5240),
            ("TulseeVid01", "Why PMs are suddenly valuable again | Tulsee Doshi (Head of Product Gemini)",
             "2026-11-08T10:00:00", 3500),
        ]
        for video_id, title, iso, duration in rows:
            store.save_videos(conn, [video_id], [make_video(video_id, title, iso, duration)], "2026-11-17T12:00:00Z")
        conn.close()
        self.seed = self.work / "seed.csv"
        self.seed.write_text(
            "youtube_url,show,title,date,has_rss,notes\n"
            "https://www.youtube.com/watch?v=MuseVideo01,Lenny,Muse,2026-11-15,y,\n"
            "https://www.youtube.com/watch?v=TulseeVid01,Lenny,Tulsee,2026-11-08,y,\n", encoding="utf-8")

    def test_choose_a_feed_resolve_review_and_confirm(self):
        code, out, _err = self.run_cli("resolve", "run", "--seed", str(self.seed))
        self.assertEqual(code, 2)  # the channel is still waiting for a feed choice
        self.assertIn("Channels waiting for a feed choice", out)

        code, out, _err = self.run_cli("resolve", "feeds", "--seed", str(self.seed), answers=["1"])
        self.assertEqual(code, 0)
        self.assertIn("Saved: Lenny's Podcast", out)

        code, out, _err = self.run_cli("resolve", "run", "--seed", str(self.seed))
        self.assertEqual(code, 0)
        self.assertIn("matched 2", out)
        self.assertIn("Feed 100: 3 new episode(s)", out)

        with (self.work / "data" / "seed_resolver_check.csv").open(encoding="utf-8") as handle:
            check = list(csv.DictReader(handle))
        self.assertEqual([(r["video_id"], r["status"], r["auto_check"]) for r in check],
                         [("MuseVideo01", "matched", "agrees"), ("TulseeVid01", "matched", "agrees")])

        code, out, _err = self.run_cli("resolve", "run", "--seed", str(self.seed))
        self.assertIn("Feed 100: 0 new episode(s)", out)  # the second run asks only for newer episodes
        self.assertEqual(self.pi.requests[-1][1]["since"], max(e.published for e in LENNY_EPISODES))

        code, out, _err = self.run_cli("resolve", "review", "--seed", str(self.seed))
        self.assertIn("Nothing to review", out)

        code, out, _err = self.run_cli("resolve", "confirm", "TulseeVid01", "3")
        self.assertEqual(code, 0)
        code, out, _err = self.run_cli("resolve", "run", "--seed", str(self.seed))
        self.assertIn("Kept 1 result(s) you already reviewed", out)
