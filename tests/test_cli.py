"""The command line: exit codes, confirmation and output. Core functions are replaced by mocks."""

from __future__ import annotations

import contextlib
import io
import logging
from unittest import mock

from podcast_recall import cli
from podcast_recall.errors import ApiError, ConfigError, NotSignedIn
from podcast_recall.models import (
    ChannelRow,
    FetchResult,
    RevokeResult,
    SourceResult,
    SyncResult,
)
from tests.base import Base


def sync_result(status="ok", reason=None, calls=None):
    return SyncResult(
        user_id="owner", status=status, reason=reason,
        sources=[SourceResult("liked", "Liked videos", found=4, added=2, removed=1)],
        calls=calls if calls is not None else {"playlistItems.list": 2, "videos.list": 1},
        estimated_units=3, videos_fetched=4, warnings=[], started_at="a", finished_at="b",
    )


class CliBase(Base):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        for handler in list(logging.getLogger("podcast_recall").handlers):
            handler.close()
            logging.getLogger("podcast_recall").removeHandler(handler)
        return code, out.getvalue(), err.getvalue()


class ExitCodes(CliBase):
    def test_ok_partial_error_and_sign_in_needed(self):
        with mock.patch("podcast_recall.core.sync_library", return_value=sync_result()):
            self.assertEqual(self.run_cli("sync")[0], 0)
        with mock.patch("podcast_recall.core.sync_library",
                        return_value=sync_result("partial", "quota")):
            self.assertEqual(self.run_cli("sync")[0], 2)
        with mock.patch("podcast_recall.core.sync_library", side_effect=ApiError("down")):
            code, _out, err = self.run_cli("sync")
            self.assertEqual(code, 1)
            self.assertIn("down", err)
        with mock.patch("podcast_recall.core.sync_library", side_effect=NotSignedIn("sign in")):
            code, _out, err = self.run_cli("sync")
            self.assertEqual(code, 3)
            self.assertIn("sign in", err)

    def test_user_option_is_passed_through_and_defaults_to_owner(self):
        with mock.patch("podcast_recall.core.sync_library", return_value=sync_result()) as sync:
            self.run_cli("sync")
            self.run_cli("sync", "--user", "ana")
        self.assertEqual([c.args[0] for c in sync.call_args_list], ["owner", "ana"])

    def test_purge_takes_no_user_option(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.build_parser().parse_args(["purge", "--user", "ana"])

    def test_config_errors_exit_1(self):
        with mock.patch("podcast_recall.core.get_status", side_effect=ConfigError("bad setup")):
            self.assertEqual(self.run_cli("status")[0], 1)


class Output(CliBase):
    def test_sync_output_lists_sources_calls_and_units(self):
        text = cli.format_sync(sync_result())
        self.assertIn("Liked videos: found 4, added 2, removed 1", text)
        self.assertIn("playlistItems.list: 2", text)
        self.assertIn("Estimated quota units: 3", text)

    def test_sync_output_shows_zero_detail_calls_when_none_were_made(self):
        text = cli.format_sync(sync_result(calls={"playlistItems.list": 2}))
        self.assertIn("videos.list: 0", text)

    def test_incomplete_sources_say_nothing_was_removed(self):
        result = sync_result("partial", "boom")
        result.sources = [SourceResult("liked", "Liked videos", complete=False, error="boom")]
        self.assertIn("NOT COMPLETE, nothing removed", cli.format_sync(result))


class Revoke(CliBase):
    def test_asks_for_confirmation_and_does_nothing_on_no(self):
        with mock.patch("podcast_recall.core.revoke") as revoke, mock.patch("builtins.input",
                                                                           return_value="n"):
            code, out, _err = self.run_cli("revoke")
        self.assertEqual(code, 0)
        revoke.assert_not_called()
        self.assertIn("Nothing changed", out)

    def test_yes_flag_skips_the_question(self):
        with mock.patch("podcast_recall.core.revoke",
                        return_value=RevokeResult(True, [])) as revoke, mock.patch(
                "builtins.input", side_effect=AssertionError("must not ask")):
            code, out, _err = self.run_cli("revoke", "--yes")
        self.assertEqual(code, 0)
        revoke.assert_called_once()
        self.assertIn("revoked", out.lower())

    def test_confirming_with_y_revokes_and_warnings_go_to_stderr(self):
        with mock.patch("podcast_recall.core.revoke",
                        return_value=RevokeResult(False, ["Google unreachable"])), mock.patch(
                "builtins.input", return_value="y"):
            code, _out, err = self.run_cli("revoke")
        self.assertEqual(code, 0)
        self.assertIn("Google unreachable", err)

    def test_no_terminal_means_no(self):
        with mock.patch("podcast_recall.core.revoke") as revoke, mock.patch(
                "builtins.input", side_effect=EOFError):
            self.run_cli("revoke")
        revoke.assert_not_called()


class Fetch(CliBase):
    def test_exit_codes_for_fetch(self):
        ok = FetchResult(requested=1, fetched=1, unavailable=[], calls={"videos.list": 1},
                         estimated_units=1)
        some_missing = FetchResult(requested=2, fetched=1, unavailable=[("zzz", "gone")],
                                   calls={"videos.list": 1}, estimated_units=1)
        with mock.patch("podcast_recall.core.fetch_videos", return_value=ok):
            self.assertEqual(self.run_cli("fetch", "3I6QYkccd3o")[0], 0)
        with mock.patch("podcast_recall.core.fetch_videos", return_value=some_missing):
            self.assertEqual(self.run_cli("fetch", "3I6QYkccd3o", "YS9In813jJ0")[0], 2)
        with mock.patch("podcast_recall.core.fetch_videos", return_value=ok):
            code, out, _err = self.run_cli("fetch", "3I6QYkccd3o", "not a video")
        self.assertEqual(code, 2)  # one entry could not be read
        self.assertIn("could not read: not a video", out)

    def test_nothing_to_fetch_is_an_error(self):
        code, _out, err = self.run_cli("fetch", "garbage")
        self.assertEqual(code, 1)
        self.assertIn("No video IDs", err)


class Channels(CliBase):
    def test_list_and_mark(self):
        rows = [ChannelRow("UC1", "Alpha", True, True), ChannelRow("UC2", "Beta", True, False)]
        with mock.patch("podcast_recall.core.list_channels", return_value=rows) as lister:
            code, out, _err = self.run_cli("channels", "list", "--marked", "--refresh")
        self.assertEqual(code, 0)
        self.assertIn("[podcast]  UC1  Alpha", out)
        self.assertEqual(lister.call_args.kwargs, {"marked_only": True, "refresh": True})
        with mock.patch("podcast_recall.core.set_podcast_channel", return_value=rows[0]) as mark:
            code, out, _err = self.run_cli("channels", "mark", "UC1")
        self.assertEqual(mark.call_args.args, ("owner", "UC1", True))
        self.assertIn("next sync", out)
        with mock.patch("podcast_recall.core.set_podcast_channel", return_value=rows[1]) as mark:
            self.run_cli("channels", "unmark", "UC2")
        self.assertEqual(mark.call_args.args, ("owner", "UC2", False))
