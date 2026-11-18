"""Decide which feed episode a YouTube video is. Pure functions: no network, no database.

The rules are in specs/features/u2-episode-resolver/requirements.md ("Matching rules"). Every
number that can be tuned is in the constants block below, so tuning on the seed list changes
numbers, not logic.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass

# ---------------------------------------------------------------------------- constants

W_TITLE, W_DATE, W_DURATION = 0.5, 0.3, 0.2
MATCHED_MIN = 0.85  # combined score for `matched` by score
MARGIN_MIN = 0.15  # lead over the second-best candidate needed for `matched` by score
REVIEW_MIN = 0.60  # combined score for `needs_review`
MIN_TITLE_WORDS = 2  # fewer words than this and the title signal is missing

DATE_FULL_DAYS = 1.0  # date signal is 1.0 up to this many days apart...
DATE_ZERO_DAYS = 4.0  # ...and falls in a straight line to 0 at this many

DURATION_TOLERANCE_FRACTION = 0.10  # duration signal is 1.0 within the larger of 10% or...
DURATION_TOLERANCE_MIN_S = 180  # ...180 seconds, then falls to 0 at three times that
CLIP_RATIO = 0.5  # a video shorter than half the episode is a probable clip

LOCK_DATE_MIN = 0.9  # "date and length lock": same day...
LOCK_DURATION_MIN = 0.9  # ...and length agrees...
LOCK_COMPETITOR_DURATION_MIN = 0.5  # ...and no other episode that day is similar in length
LOCK_CLOSE_FRACTION = 0.02  # lock gives `matched` only within the larger of 2% or...
LOCK_CLOSE_MIN_S = 30  # ...30 seconds, otherwise `needs_review`

STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have", "how",
    "i", "if", "in", "is", "it", "its", "of", "on", "or", "so", "that", "the", "their", "then",
    "there", "these", "this", "to", "was", "we", "what", "when", "who", "why", "will", "with",
    "you", "your",
})


# ---------------------------------------------------------------------------- text


def normalize(text: str) -> str:
    """Lowercase, straight quotes, '&' as 'and', accents removed, apostrophes dropped."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("’", "'").replace("‘", "'").replace("&", " and ")
    return text.replace("'", "")


def stem(word: str) -> str:
    """A light reduction so that `launched`, `makes` and `labs` match `launch`, `make` and `lab`."""
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def title_words(text: str) -> frozenset[str]:
    """The unique reduced words of a title, without common words. Non-Latin text gives none."""
    found = re.findall(r"[a-z0-9]+", normalize(text))
    return frozenset(
        stem(w) for w in found if w not in STOPWORDS and (len(w) > 1 or w.isdigit())
    )


# ---------------------------------------------------------------------------- signals


def title_score(video_words: frozenset[str], episode_words: frozenset[str]) -> float | None:
    """Share of the YouTube title's words found in the feed title. None if too few words."""
    if len(video_words) < MIN_TITLE_WORDS:
        return None
    return len(video_words & episode_words) / len(video_words)


def date_score(video_published: int | None, episode_published: int | None) -> float | None:
    if video_published is None or episode_published is None:
        return None
    days = abs(video_published - episode_published) / 86400
    if days <= DATE_FULL_DAYS:
        return 1.0
    return max(0.0, 1.0 - (days - DATE_FULL_DAYS) / (DATE_ZERO_DAYS - DATE_FULL_DAYS))


def duration_signal(
    video_s: int | None, episode_s: int | None
) -> tuple[float | None, int | None, bool]:
    """(score, YouTube minus feed in seconds, probable clip). Score None if either is unknown."""
    if not video_s or not episode_s:
        return None, None, False
    diff = video_s - episode_s
    if video_s < CLIP_RATIO * episode_s:
        return 0.0, diff, True
    tolerance = max(DURATION_TOLERANCE_FRACTION * episode_s, DURATION_TOLERANCE_MIN_S)
    gap = abs(diff)
    if gap <= tolerance:
        return 1.0, diff, False
    return max(0.0, 1.0 - (gap - tolerance) / (2 * tolerance)), diff, False


def combine(title: float | None, date: float | None, duration: float | None) -> float:
    """Weighted mean of the signals that exist, with the weights scaled to add up to 1."""
    parts = [(W_TITLE, title), (W_DATE, date), (W_DURATION, duration)]
    available = [(w, s) for w, s in parts if s is not None]
    total = sum(w for w, _ in available)
    return sum(w * s for w, s in available) / total if total else 0.0


# ---------------------------------------------------------------------------- data


@dataclass(frozen=True)
class VideoFacts:
    title: str
    published: int | None  # epoch seconds, UTC
    duration_s: int | None


@dataclass(frozen=True)
class PreparedEpisode:
    """An episode with its title words computed once, so many videos can be scored cheaply."""

    episode_id: int
    title: str
    published: int | None
    duration_s: int | None
    words: frozenset[str]


@dataclass(frozen=True)
class Scored:
    episode_id: int
    title: str
    title_score: float | None
    date_score: float | None
    duration_score: float | None
    duration_diff_s: int | None
    clip: bool
    combined: float
    episode_duration_s: int | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Decision:
    status: str  # matched, needs_review, unmatched or no_feed
    method: str
    reason: str
    best: Scored | None
    margin: float
    top: list[Scored]


def prepare_episode(
    episode_id: int, title: str, published: int | None, duration_s: int | None
) -> PreparedEpisode:
    return PreparedEpisode(episode_id, title, published, duration_s, title_words(title))


def score_episode(
    video: VideoFacts, video_words: frozenset[str], episode: PreparedEpisode
) -> Scored:
    title = title_score(video_words, episode.words)
    date = date_score(video.published, episode.published)
    duration, diff, clip = duration_signal(video.duration_s, episode.duration_s)
    return Scored(
        episode_id=episode.episode_id,
        title=episode.title,
        title_score=title,
        date_score=date,
        duration_score=duration,
        duration_diff_s=diff,
        clip=clip,
        combined=combine(title, date, duration),
        episode_duration_s=episode.duration_s,
    )


# ---------------------------------------------------------------------------- decision


def _lock_applies(best: Scored, others: Sequence[Scored]) -> bool:
    """Date and length lock: same day, same length, and no other episode that day is similar in
    length."""
    if best.date_score is None or best.duration_score is None:
        return False
    if best.date_score < LOCK_DATE_MIN or best.duration_score < LOCK_DURATION_MIN:
        return False
    for other in others:
        same_day = other.date_score is not None and other.date_score >= LOCK_DATE_MIN
        similar = other.duration_score is None or other.duration_score >= LOCK_COMPETITOR_DURATION_MIN
        if same_day and similar:
            return False
    return True


def decide(video: VideoFacts, episodes: Sequence[PreparedEpisode]) -> Decision:
    """Pick the best episode for a video and say how sure we are. See the requirements."""
    if not episodes:
        return Decision("unmatched", "none", "the feed has no episodes", None, 0.0, [])
    words = title_words(video.title)
    scored = sorted(
        (score_episode(video, words, e) for e in episodes),
        key=lambda s: (-s.combined, s.episode_id),
    )
    best = scored[0]
    second = scored[1].combined if len(scored) > 1 else 0.0
    margin = best.combined - second
    top = scored[:3]

    if best.clip:
        return Decision(
            "unmatched", "clip", "much shorter than the best episode (probably a clip)",
            best, margin, top,
        )
    if best.title_score is not None and best.combined >= MATCHED_MIN:
        if margin >= MARGIN_MIN:
            return Decision("matched", "score", "title, date and length agree", best, margin, top)
        return Decision(
            "needs_review", "score", "a close second candidate; check which one is right",
            best, margin, top,
        )
    if _lock_applies(best, scored[1:]):
        episode_s = best.episode_duration_s or 0
        close = abs(best.duration_diff_s or 0) <= max(LOCK_CLOSE_FRACTION * episode_s, LOCK_CLOSE_MIN_S)
        if close:
            return Decision(
                "matched", "date_duration",
                "same day and nearly the same length; no other episode fits",
                best, margin, top,
            )
        return Decision(
            "needs_review", "date_duration",
            f"same day and similar length (off by {best.duration_diff_s} s); the title differs",
            best, margin, top,
        )
    if best.combined >= REVIEW_MIN:
        return Decision(
            "needs_review", "partial", "title, date and length only partly agree", best, margin, top
        )
    return Decision("unmatched", "none", "no episode is close enough", best, margin, top)
