"""Retry helper shared by the YouTube and Podcast Index clients."""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from podcast_recall.errors import ApiError, TransientError

RETRY_DELAYS = (1, 2, 4, 8, 16)  # seconds; up to 5 retries after the first attempt


def call_with_retries(
    fn: Callable[[], object],
    *,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
    delays: tuple[int, ...] = RETRY_DELAYS,
):
    """Call `fn`, retrying only on TransientError with the given delays plus jitter."""
    retries = 0
    while True:
        try:
            return fn()
        except TransientError as exc:
            if retries >= len(delays):
                raise ApiError(f"The service kept failing after {retries + 1} attempts ({exc}).") from exc
            sleep(delays[retries] * (0.5 + rng()))
            retries += 1
