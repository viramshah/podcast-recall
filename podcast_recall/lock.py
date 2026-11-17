"""One sync at a time per user, using an operating-system file lock.

`flock` is released automatically when the process dies, so a crash never leaves a stuck lock.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import Self

from podcast_recall.errors import SyncAlreadyRunning


class SyncLock:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._handle = None

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            raise SyncAlreadyRunning(
                "A sync is already running for this user. Wait for it to finish, then try again."
            ) from None
        os.chmod(self.path, 0o600)
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        self._handle = handle
        return self

    def __exit__(self, *exc_info) -> None:
        if self._handle is not None:
            fcntl.flock(self._handle, fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None
