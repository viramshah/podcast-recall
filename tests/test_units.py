"""Small pure pieces: URL parsing, durations, retries, redaction, paths, locks, migrations."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

from podcast_recall import ids, logging_setup, paths, store
from podcast_recall.errors import (
    ApiError,
    ConfigError,
    QuotaExceeded,
    SyncAlreadyRunning,
    TransientError,
)
from podcast_recall.lock import SyncLock
from podcast_recall.youtube_client import (
    GoogleYouTubeClient,
    call_with_retries,
    parse_iso8601_duration,
)
from tests.base import Base

REPO = Path(__file__).resolve().parent.parent


class VideoIds(unittest.TestCase):
    def test_urls_with_extras(self):
        for text in (
            "https://www.youtube.com/watch?v=3I6QYkccd3o&list=LL&index=22&t=3013s",
            "https://youtu.be/3I6QYkccd3o?t=5",
            "https://www.youtube.com/shorts/3I6QYkccd3o",
            "https://www.youtube.com/embed/3I6QYkccd3o",
            "https://m.youtube.com/watch?v=3I6QYkccd3o",
            "music.youtube.com/watch?v=3I6QYkccd3o",
            "3I6QYkccd3o",
            "  3I6QYkccd3o  ",
        ):
            self.assertEqual(ids.extract_video_id(text), "3I6QYkccd3o", text)

    def test_things_that_are_not_video_urls(self):
        for text in ("", "hello", "https://example.com/watch?v=3I6QYkccd3o",
                     "https://www.youtube.com/playlist?list=PL123", "https://www.youtube.com/watch?v=short"):
            self.assertIsNone(ids.extract_video_id(text), text)

    def test_load_ids_from_csv_and_text_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "seed.csv"
            csv_path.write_text(
                "youtube_url,show\nhttps://youtu.be/3I6QYkccd3o,A\nhttps://youtu.be/3I6QYkccd3o,A\n"
                "not a url,B\nhttps://www.youtube.com/watch?v=YS9In813jJ0&t=3s,C\n", encoding="utf-8")
            txt = Path(tmp) / "ids.txt"
            txt.write_text("# comment\nWY0cdD4gNoQ\n\n", encoding="utf-8")
            found, unparsed = ids.load_ids([str(csv_path), str(txt), "BgeNDG5jD60", "bad entry"])
        self.assertEqual(found, ["3I6QYkccd3o", "YS9In813jJ0", "WY0cdD4gNoQ", "BgeNDG5jD60"])
        self.assertEqual(unparsed, ["not a url", "bad entry"])

    def test_csv_without_the_column_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            path.write_text("title\nfoo\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                ids.load_ids([str(path)])


class Durations(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_iso8601_duration("PT1H2M3S"), 3723)
        self.assertEqual(parse_iso8601_duration("PT45S"), 45)
        self.assertEqual(parse_iso8601_duration("PT2M"), 120)
        self.assertEqual(parse_iso8601_duration("P0D"), 0)
        self.assertEqual(parse_iso8601_duration("P1DT1H"), 90000)
        self.assertEqual(parse_iso8601_duration("nonsense"), 0)
        self.assertEqual(parse_iso8601_duration(None), 0)


class Retries(unittest.TestCase):
    def test_retries_only_transient_errors_with_growing_delays(self):
        attempts, sleeps = [], []

        def flaky():
            attempts.append(1)
            if len(attempts) < 4:
                raise TransientError("HTTP 503")
            return "ok"

        self.assertEqual(call_with_retries(flaky, sleep=sleeps.append, rng=lambda: 0.5), "ok")
        self.assertEqual(sleeps, [1, 2, 4])  # jitter factor is 1.0 when rng returns 0.5

    def test_gives_up_after_five_retries(self):
        calls, sleeps = [], []

        def always():
            calls.append(1)
            raise TransientError("network error")

        with self.assertRaises(ApiError):
            call_with_retries(always, sleep=sleeps.append, rng=lambda: 0.5)
        self.assertEqual(len(calls), 6)
        self.assertEqual(sleeps, [1, 2, 4, 8, 16])

    def test_other_errors_are_not_retried(self):
        for error in (ApiError("HTTP 404"), QuotaExceeded("quota")):
            calls = []

            def once(error=error, calls=calls):
                calls.append(1)
                raise error

            with self.assertRaises(type(error)):
                call_with_retries(once, sleep=lambda s: None)
            self.assertEqual(len(calls), 1)


class NoSearchList(unittest.TestCase):
    def test_search_list_is_never_called(self):
        pattern = re.compile(r"\.search\s*\(")
        for path in (REPO / "podcast_recall").rglob("*.py"):
            self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")), str(path))

    def test_the_client_refuses_search_list(self):
        client = GoogleYouTubeClient(service=object())
        with self.assertRaises(ConfigError):
            client._execute("search.list", lambda: None)

    def test_only_known_read_methods_are_used(self):
        source = (REPO / "podcast_recall" / "youtube_client.py").read_text(encoding="utf-8")
        used = set(re.findall(r'"([a-zA-Z]+\.list)"', source))
        self.assertEqual(
            used - {"search.list"},
            {"channels.list", "subscriptions.list", "playlists.list", "playlistItems.list",
             "videos.list"},
        )

    def test_the_scope_is_read_only(self):
        from podcast_recall.youtube_client import SCOPE

        self.assertEqual(SCOPE, "https://www.googleapis.com/auth/youtube.readonly")


class Redaction(unittest.TestCase):
    SECRETS: ClassVar[list[str]] = [
        "Authorization: Bearer ya29.A0AfH6SMBxxxxxxxxxxxx",
        "refresh_token=1//0gAbCdEfGhIjKlMnOp",
        '{"client_secret": "GOCSPX-abcdef123", "access_token": "ya29.zzz"}',
        "https://example.com/cb?code=4/0AX4XfWh&state=1",
        "contact someone.name@example.com for help",
    ]

    def test_secrets_are_removed(self):
        for text in self.SECRETS:
            cleaned = logging_setup.redact(text)
            for secret in ("ya29", "1//0gA", "GOCSPX", "4/0AX4", "someone.name@"):
                self.assertNotIn(secret, cleaned, text)
            self.assertIn("REDACTED", cleaned)

    def test_ordinary_text_is_unchanged(self):
        text = "playlist:PL1: found 120, added 3, removed 1"
        self.assertEqual(logging_setup.redact(text), text)

    def test_log_files_never_contain_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            logging_setup.setup_logging(Path(tmp), stderr=False)
            log = logging.getLogger("podcast_recall.test")
            try:
                log.warning("token problem: refresh_token=1//SECRETVALUE and ya29.SECRETACCESS")
                try:
                    raise RuntimeError("Authorization: Bearer ya29.SECRETINTRACE")
                except RuntimeError:
                    log.exception("failed for me@example.com")
            finally:
                for h in list(logging.getLogger("podcast_recall").handlers):
                    h.flush()
                    h.close()
                    logging.getLogger("podcast_recall").removeHandler(h)
            text = (Path(tmp) / "podcast-recall.log").read_text(encoding="utf-8")
        for secret in ("SECRETVALUE", "SECRETACCESS", "SECRETINTRACE", "me@example.com"):
            self.assertNotIn(secret, text)
        self.assertIn("REDACTED", text)


class DataFolder(Base):
    def test_folder_is_created_with_private_permissions(self):
        home = paths.ensure_data_home()
        self.assertEqual(os.stat(home).st_mode & 0o777, 0o700)

    def test_looser_permissions_are_tightened(self):
        os.makedirs(self.home)
        os.chmod(self.home, 0o755)
        with self.assertLogs("podcast_recall.paths", level="WARNING"):
            paths.ensure_data_home()
        self.assertEqual(os.stat(self.home).st_mode & 0o777, 0o700)

    def test_log_folder_and_file_are_private(self):
        paths.ensure_data_home()
        logging_setup.setup_logging(paths.log_dir(), stderr=False)
        try:
            self.assertEqual(os.stat(paths.log_dir()).st_mode & 0o777, 0o700)
            log_file = paths.log_dir() / "podcast-recall.log"
            self.assertEqual(os.stat(log_file).st_mode & 0o777, 0o600)
        finally:
            logger = logging.getLogger("podcast_recall")
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

    def test_database_file_is_private(self):
        paths.ensure_data_home()
        conn = store.connect(paths.db_path(), paths.backup_dir())
        conn.close()
        self.assertEqual(os.stat(paths.db_path()).st_mode & 0o777, 0o600)

    def test_refresh_days_setting(self):
        old = os.environ.pop("PODCAST_RECALL_VIDEO_REFRESH_DAYS", None)
        try:
            self.assertEqual(paths.video_refresh_days(), 30)
            os.environ["PODCAST_RECALL_VIDEO_REFRESH_DAYS"] = "7"
            self.assertEqual(paths.video_refresh_days(), 7)
            os.environ["PODCAST_RECALL_VIDEO_REFRESH_DAYS"] = "abc"
            with self.assertRaises(ConfigError):
                paths.video_refresh_days()
        finally:
            os.environ.pop("PODCAST_RECALL_VIDEO_REFRESH_DAYS", None)
            if old is not None:
                os.environ["PODCAST_RECALL_VIDEO_REFRESH_DAYS"] = old


class Locks(unittest.TestCase):
    def test_second_lock_is_refused_and_released_afterwards(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sync.lock"
            with SyncLock(path), self.assertRaises(SyncAlreadyRunning):
                SyncLock(path).__enter__()
            with SyncLock(path):  # free again
                pass

    def test_a_killed_process_does_not_leave_a_stuck_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sync.lock"
            code = (
                "import sys, time\n"
                "from podcast_recall.lock import SyncLock\n"
                f"lock = SyncLock(r'{path}')\n"
                "lock.__enter__()\n"
                "print('locked', flush=True)\n"
                "time.sleep(60)\n"
            )
            proc = subprocess.Popen([sys.executable, "-B", "-c", code], cwd=REPO,
                                    stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(proc.stdout.readline().strip(), "locked")
                with self.assertRaises(SyncAlreadyRunning):
                    SyncLock(path).__enter__()
                proc.kill()
                proc.wait()
                with SyncLock(path):  # the OS released it
                    pass
            finally:
                proc.kill()
                proc.wait()
                proc.stdout.close()


class Migrations(Base):
    def test_all_tables_exist_and_foreign_keys_are_enforced(self):
        names = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"videos", "channels", "users", "library_items", "user_channels",
                         "playlists", "sync_runs", "schema_version"} <= names)
        with self.assertRaises(sqlite3.IntegrityError), self.conn:
            self.conn.execute("INSERT INTO library_items VALUES ('owner','nope','liked','x')")

    def test_migrating_again_changes_nothing(self):
        before = self.conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        store.migrate(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0], before)

    def test_upgrade_backs_up_and_keeps_three_backups(self):
        db = Path(self.home) / "t.db"
        backups = Path(self.home) / "backups"
        conn = store.connect(db, backups)
        latest = max(v for v, _name, _sql in store._migration_files())
        for n in range(latest + 1, latest + 6):  # five more upgrades than the real ones
            extra = [(1, "001_initial.sql", ""), (n, f"{n:03d}_extra.sql", f"CREATE TABLE extra{n} (a);")]
            store._migration_files = lambda extra=extra: extra
            store.migrate(conn, backups)
        conn.close()
        self.assertEqual(len(list(backups.glob("podcast_recall-v*.db"))), 3)

    def test_a_failing_migration_rolls_back(self):
        conn = store.connect(":memory:")
        original = store._migration_files
        try:
            store._migration_files = lambda: original() + [
                (99, "099_bad.sql", "CREATE TABLE half_done (a); INSERT INTO nope VALUES (1);")]
            with self.assertRaises(sqlite3.OperationalError):
                store.migrate(conn)
        finally:
            store._migration_files = original
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("half_done", tables)
        latest = max(v for v, _name, _sql in original())
        self.assertEqual(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0], latest)
        conn.close()

    def test_backups_use_a_consistent_copy(self):
        db = Path(self.home) / "t.db"
        backups = Path(self.home) / "backups"
        conn = store.connect(db, backups)
        store.upsert_user(conn, "owner", "UC1", "Me", "2026-01-01T00:00:00Z")
        original = store._migration_files
        try:
            store._migration_files = lambda: original() + [
                (99, "099_extra.sql", "CREATE TABLE extra (a);")]
            store.migrate(conn, backups)
        finally:
            store._migration_files = original
        backup = next(backups.glob("podcast_recall-v*.db"))
        copy = sqlite3.connect(str(backup))
        self.assertEqual(copy.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
        copy.close()
        conn.close()
