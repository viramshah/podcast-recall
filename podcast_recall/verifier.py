"""The production guard: no claim reaches the user unless its citations are real (decision D19).

It runs the Week 2 checks R1 (the quote is in the transcript near the cited time) and R2 (the cited
episode is in the user's library) on every citation, drops any claim that fails or has no citation,
caps the number of claims, and says "not found" when nothing survives.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from podcast_recall import checkers
from podcast_recall.answers import Answer, Claim
from podcast_recall.prompting import MAX_CLAIMS

NOT_FOUND_TEXT = "I couldn't find that in your podcasts."


@dataclass(frozen=True)
class Dropped:
    claim: str
    reason: str


@dataclass
class Verified:
    answer: Answer
    dropped: list[Dropped] = field(default_factory=list)
    uncited_note: bool = False  # a premise correction kept without any quoted support


def verify(answer: Answer, ctx: checkers.EvalContext, *, note: str = "") -> Verified:
    kept: list[Claim] = []
    dropped: list[Dropped] = []
    for claim in answer.claims:
        if not claim.citations:
            dropped.append(Dropped(claim.text, "the claim had no citation"))
            continue
        reason = None
        for citation in claim.citations:
            for check in (checkers.check_r1, checkers.check_r2):
                failure = check(citation, ctx)
                if failure:
                    reason = f"{failure.rule}: {failure.reason}"
                    break
            if reason:
                break
        if reason:
            dropped.append(Dropped(claim.text, reason))
        else:
            kept.append(claim)
    for extra in kept[MAX_CLAIMS:]:
        dropped.append(Dropped(extra.text, "more than the allowed number of claims"))
    kept = kept[:MAX_CLAIMS]

    if answer.status == "not_found":
        return Verified(Answer("not_found", (), NOT_FOUND_TEXT), dropped)
    if kept:
        summary = note.strip()[:240] if answer.status == "premise_corrected" else ""
        return Verified(Answer(answer.status, tuple(kept), summary), dropped)
    if answer.status == "premise_corrected" and note.strip():
        # the model corrected a false premise but nothing it quoted could be verified: keep the
        # correction, clearly marked as having no quoted support
        return Verified(Answer("premise_corrected", (), note.strip()[:240]), dropped, uncited_note=True)
    return Verified(Answer("not_found", (), NOT_FOUND_TEXT), dropped)
