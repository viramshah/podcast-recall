"""The deterministic rubric checks: R1, R2, R5 and R7 (decisions D5 and D18).

Each check is a plain function that returns a `Failure` (with the reason) or None. No model, no
network. Every threshold is a named constant here.

    R1  the citation is real: the quote matches the transcript near the cited time (Critical)
    R2  the source is in the library (Critical)
    R5  abstention: the answer's status matches what the question needs (Critical or Major)
    R7  timestamp: the cited time is near the gold time (a separate metric, not a pass/fail gate)
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from podcast_recall.answers import Answer, Citation
from podcast_recall.golden import (
    ANSWERABLE_TYPES,
    FALSE_PREMISE,
    SYNTHESIS,
    TIMED_TYPES,
    GoldenItem,
)
from podcast_recall.models import Transcript

MATCH_THRESHOLD = 0.90  # D5: how closely a quote must match the transcript
WINDOW_S = 15.0  # D5: the quote must be found within this many seconds of the cited time
R7_TOLERANCE_S = 15.0  # D5: the cited time must be within this of the gold time

CRITICAL = "critical"
MAJOR = "major"
MINOR = "minor"

_WORD = re.compile(r"\w+(?:'\w+)?", re.UNICODE)


@dataclass(frozen=True)
class Failure:
    rule: str
    severity: str
    reason: str


@dataclass
class EvalContext:
    """What the checkers need to know about the world."""

    library_episode_ids: set[int]
    video_to_episode: dict[str, int]  # every matched video, in the library or not
    transcript_for: Callable[[int], Transcript | None]
    episode_label: Callable[[int], tuple[str, str]] = lambda episode_id: ("", "")


# ---------------------------------------------------------------------------- text matching


def normalize(text: str) -> list[str]:
    """Lowercase words with punctuation, curly quotes and accents' composition differences removed."""
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'")
    return _WORD.findall(text.lower())


def window_tokens(transcript: Transcript, start_s: float, window_s: float = WINDOW_S) -> list[str]:
    """The words of every segment that overlaps the stretch around the cited time."""
    low, high = start_s - window_s, start_s + window_s
    words: list[str] = []
    for segment in sorted(transcript.segments, key=lambda s: (s.start, s.end)):
        if segment.end >= low and segment.start <= high:
            words.extend(normalize(segment.text))
    return words


def best_similarity(quote: Sequence[str], text: Sequence[str]) -> float:
    """The best word-level similarity between the quote and any run of the text (0 to 1)."""
    if not quote or not text:
        return 0.0
    length = len(quote)
    if len(text) <= length:
        return SequenceMatcher(None, list(quote), list(text), autojunk=False).ratio()
    best = 0.0
    for size in range(max(1, length - 2), length + 3):
        if size > len(text):
            continue
        for start in range(len(text) - size + 1):
            ratio = SequenceMatcher(
                None, list(quote), list(text[start:start + size]), autojunk=False
            ).ratio()
            if ratio > best:
                best = ratio
                if best >= 1.0:
                    return best
    return best


# ---------------------------------------------------------------------------- R1


def check_r1(citation: Citation, ctx: EvalContext) -> Failure | None:
    """The quote must be in the stored transcript within the window around the cited time."""
    transcript = ctx.transcript_for(citation.episode_id)
    if transcript is None:
        return Failure("R1", CRITICAL, f"no transcript is stored for episode {citation.episode_id}")
    quote = normalize(citation.quote)
    if not quote:
        return Failure("R1", CRITICAL, "the quote is empty")
    text = window_tokens(transcript, citation.start_s)
    if not text:
        return Failure(
            "R1", CRITICAL,
            f"the transcript has no words within {WINDOW_S:g} s of {citation.start_s:g} s",
        )
    score = best_similarity(quote, text)
    if score < MATCH_THRESHOLD:
        return Failure(
            "R1", CRITICAL,
            f"the quote matches the transcript near {citation.start_s:g} s at only {score:.2f} "
            f"(needs {MATCH_THRESHOLD:.2f})",
        )
    return None


def check_claims_cited(answer: Answer) -> list[Failure]:
    """An answered claim without any citation fails R1 (every factual statement must be cited)."""
    return [
        Failure("R1", CRITICAL, f"claim {n} has no citation")
        for n, claim in enumerate(answer.claims, 1)
        if not claim.citations
    ]


# ---------------------------------------------------------------------------- R2


def check_r2(citation: Citation, ctx: EvalContext) -> Failure | None:
    """The cited episode must be in the user's library, and the video must belong to it."""
    known = ctx.video_to_episode.get(citation.video_id)
    if known is not None and known != citation.episode_id:
        return Failure(
            "R2", CRITICAL,
            f"video {citation.video_id} belongs to episode {known}, not {citation.episode_id}",
        )
    if citation.episode_id not in ctx.library_episode_ids:
        return Failure(
            "R2", CRITICAL, f"episode {citation.episode_id} is not in the library"
        )
    return None


# ---------------------------------------------------------------------------- R5


def expected_status(item: GoldenItem) -> str:
    if item.type in ANSWERABLE_TYPES:
        return "answered"
    if item.type == FALSE_PREMISE:
        return "premise_corrected"
    return "not_found"  # unanswerable, and indexed-but-not-in-the-library


def check_r5(answer: Answer, item: GoldenItem) -> tuple[Failure | None, bool]:
    """Abstention. Returns (failure or None, whether a person should read the answer).

    Inventing an answer to something that cannot be answered is Critical. Refusing a question
    that can be answered is Major. A false-premise answer is always flagged for a person.
    """
    wanted = expected_status(item)
    review = item.type == FALSE_PREMISE and answer.status == "premise_corrected"
    if answer.status == wanted:
        if wanted == "not_found" and answer.claims:
            return Failure("R5", MAJOR, "the status is not_found but the answer also makes claims"), review
        return None, review
    if wanted == "answered":
        return Failure("R5", MAJOR, f"refused to answer (status {answer.status}) a question that can be answered"), review
    if answer.status == "answered":
        return Failure("R5", CRITICAL, f"answered a question that should get '{wanted}'"), review
    return Failure("R5", MAJOR, f"the status is {answer.status}, expected {wanted}"), review


# ---------------------------------------------------------------------------- R7


def check_r7(answer: Answer, item: GoldenItem) -> Failure | None:
    """For single-fact and who/when questions: a citation to the gold video near the gold time.
    Returns None when it passes or does not apply."""
    if item.type not in TIMED_TYPES or not item.evidence:
        return None
    gold = item.evidence[0]
    cited = [c for claim in answer.claims for c in claim.citations if c.video_id == gold.video_id]
    if not cited:
        return Failure("R7", MINOR, f"no citation to the gold episode ({gold.video_id})")
    nearest = min(abs(c.start_s - gold.start_s) for c in cited)
    if nearest > R7_TOLERANCE_S:
        return Failure(
            "R7", MINOR,
            f"the nearest cited time is {nearest:.0f} s from the gold time (allowed {R7_TOLERANCE_S:g} s)",
        )
    return None


def episode_recall(answer: Answer, item: GoldenItem, ctx: EvalContext) -> float | None:
    """For synthesis questions: the share of the gold episodes that the answer cites."""
    if item.type != SYNTHESIS or not item.evidence:
        return None
    gold = {ctx.video_to_episode.get(e.video_id) for e in item.evidence} - {None}
    if not gold:
        return None
    cited = {c.episode_id for claim in answer.claims for c in claim.citations}
    return len(gold & cited) / len(gold)


# ---------------------------------------------------------------------------- not in the library


def cites_outside_library(answer: Answer, ctx: EvalContext) -> bool:
    return any(
        c.episode_id not in ctx.library_episode_ids for claim in answer.claims for c in claim.citations
    )
