"""Quality checks for transcripts. Pure functions; every tunable number is in the block below
(decision D15 records the final values after the seed run)."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass, field

from podcast_recall.models import Segment

PUBLISHER_MIN_WORDS = 50
PUBLISHER_END_RATIO_MIN = 0.85  # last cue ends at least this far into the feed's stated duration...
PUBLISHER_END_RATIO_MAX = 1.05  # ...and no further than this
WORDS_PER_MINUTE_MIN = 80
WORDS_PER_MINUTE_MAX = 260
WHISPER_END_RATIO_MIN = 0.90  # last segment ends at least this far into the measured audio
MAX_GAP_S = 120  # longest silence allowed between segments
VERY_LONG_EPISODE_S = 3 * 3600
DURATION_MISMATCH_FRACTION = 0.02  # measured audio versus the feed's stated duration


@dataclass
class Review:
    """`blocking` flags make a Whisper transcript `needs_review`. `info` flags are only noted."""

    blocking: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def flags(self) -> list[str]:
        return [*self.blocking, *self.info]


def word_count(segments: Sequence[Segment]) -> int:
    return sum(len(s.text.split()) for s in segments)


def end_time(segments: Sequence[Segment]) -> float:
    return max((s.end for s in segments), default=0.0)


def primary_language(tag: str | None) -> str:
    """`en-US` and `en_us` both give `en`."""
    return (tag or "").strip().lower().replace("_", "-").split("-")[0]


def words_per_minute(segments: Sequence[Segment]) -> float:
    minutes = end_time(segments) / 60
    return word_count(segments) / minutes if minutes > 0 else 0.0


def check_publisher(segments: Sequence[Segment], feed_duration_s: int | None) -> list[str]:
    """Reasons a publisher transcript cannot be trusted (empty list means it passes). A failure
    means the job falls back to Whisper."""
    reasons: list[str] = []
    words = word_count(segments)
    if words < PUBLISHER_MIN_WORDS:
        reasons.append(f"the transcript has only {words} words")
        return reasons
    end = end_time(segments)
    if feed_duration_s:
        ratio = end / feed_duration_s
        if not PUBLISHER_END_RATIO_MIN <= ratio <= PUBLISHER_END_RATIO_MAX:
            reasons.append(
                f"the transcript ends at {ratio:.0%} of the episode's length "
                f"(expected {PUBLISHER_END_RATIO_MIN:.0%} to {PUBLISHER_END_RATIO_MAX:.0%})"
            )
    wpm = words_per_minute(segments)
    if not WORDS_PER_MINUTE_MIN <= wpm <= WORDS_PER_MINUTE_MAX:
        reasons.append(
            f"{wpm:.0f} words per minute is outside {WORDS_PER_MINUTE_MIN} to {WORDS_PER_MINUTE_MAX}"
        )
    return reasons


def check_whisper(
    segments: Sequence[Segment],
    *,
    audio_duration_s: float,
    language: str,
    feed_language: str | None,
    feed_duration_s: int | None,
) -> Review:
    review = Review()
    if not segments or word_count(segments) == 0:
        review.blocking.append("empty")
        return review
    wpm = words_per_minute(segments)
    if wpm < WORDS_PER_MINUTE_MIN:
        review.blocking.append("low_words_per_minute")
    elif wpm > WORDS_PER_MINUTE_MAX:
        review.blocking.append("high_words_per_minute")
    if audio_duration_s > 0 and end_time(segments) < WHISPER_END_RATIO_MIN * audio_duration_s:
        review.blocking.append("ends_early")
    ordered = sorted(segments, key=lambda s: s.start)
    if any(b.start - a.end > MAX_GAP_S for a, b in itertools.pairwise(ordered)):
        review.blocking.append("long_gap")
    wanted = primary_language(feed_language)
    if wanted and language and primary_language(language) != wanted:
        review.blocking.append("language_mismatch")
    if audio_duration_s > VERY_LONG_EPISODE_S:
        review.info.append("very_long_episode")
    if feed_duration_s and abs(audio_duration_s - feed_duration_s) > DURATION_MISMATCH_FRACTION * feed_duration_s:
        review.info.append("audio_duration_mismatch")
    return review
