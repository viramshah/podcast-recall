"""End to end through the real database file, lock file and data folder, with a fake YouTube."""

from __future__ import annotations

import os

from podcast_recall import auth, core, paths
from podcast_recall.errors import NotSignedIn
from tests.base import Base
from tests.fakes import standard_world
from tests.test_core import client_for, good_flow


class EndToEnd(Base):
    def test_sign_in_sync_status_revoke_with_real_files(self):
        tokens = auth.InMemoryTokenStore()
        core.sign_in("ana", token_store=tokens, run_flow=good_flow(), client_factory=client_for())

        fake = standard_world()
        result = core.sync_library("ana", client=fake, token_store=tokens)  # real lock, real db
        self.assertEqual(result.status, "ok")

        status = core.get_status("ana")  # a separate connection sees the committed data
        self.assertEqual(status.unique_videos, 4)
        self.assertEqual(status.channel_title, "Me")

        self.assertEqual(os.stat(paths.data_home()).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(paths.db_path()).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(paths.lock_path("ana")).st_mode & 0o777, 0o600)

        again = core.sync_library("ana", client=fake, token_store=tokens)
        self.assertNotIn("videos.list", again.calls)

        core.revoke("ana", token_store=tokens, http_post=lambda url, params: 200)
        with self.assertRaises(NotSignedIn):
            core.get_status("ana")
        with self.assertRaises(NotSignedIn):
            core.sync_library("ana", client=fake, token_store=tokens)

    def test_users_are_isolated(self):
        tokens = auth.InMemoryTokenStore()
        core.sign_in("ana", token_store=tokens, run_flow=good_flow(), client_factory=client_for())
        core.sign_in("ben", token_store=tokens, run_flow=good_flow(),
                     client_factory=client_for("UCben", "Ben"))
        fake = standard_world()
        core.sync_library("ana", client=fake, token_store=tokens)
        self.assertEqual(core.get_status("ben").unique_videos, 0)
        core.revoke("ana", token_store=tokens, http_post=lambda u, p: 200)
        self.assertEqual(core.get_status("ben").channel_title, "Ben")
        self.assertIsNotNone(tokens.get("ben"))
