"""Shared test setup: an in-memory database, a temporary data folder and a controllable clock."""

from __future__ import annotations

import os
import tempfile
import unittest

from podcast_recall import store

T0 = "2026-11-17T12:00:00Z"


class Base(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = os.path.join(tmp.name, "home")
        old = os.environ.get("PODCAST_RECALL_HOME")
        os.environ["PODCAST_RECALL_HOME"] = self.home

        def restore() -> None:
            if old is None:
                os.environ.pop("PODCAST_RECALL_HOME", None)
            else:
                os.environ["PODCAST_RECALL_HOME"] = old

        self.addCleanup(restore)
        self.conn = store.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.clock = T0
        self.now = lambda: self.clock
        store.upsert_user(self.conn, "owner", "UCme", "Me", T0)

    # -- helpers ---------------------------------------------------------------------------

    def lib(self, source: str | None = None, user: str = "owner") -> set[str]:
        sql = "SELECT video_id FROM library_items WHERE user_id = ?"
        args: list = [user]
        if source:
            sql += " AND source = ?"
            args.append(source)
        return {r[0] for r in self.conn.execute(sql, args)}

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def run_sync(self, fake, **kwargs):
        from podcast_recall import core

        return core.sync_library(
            "owner", conn=self.conn, client=fake, now=self.now, use_lock=False, **kwargs
        )

    @staticmethod
    def source(result, name: str):
        return next(s for s in result.sources if s.source == name)
