"""Can retrieval alone tell answerable questions from unanswerable ones? (Week 4, experiment E3.)

For each golden question, search the way the answering path does and note the best (smallest)
meaning distance among the hits. If unanswerable and not-in-library questions sit farther from the
library than answerable ones, a distance threshold can say "not found" before any model is called:
cheaper, faster, and it cannot invent an answer. No model is used here, only search.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from podcast_recall.golden import NOT_IN_LIBRARY, UNANSWERABLE, GoldenItem

ABSTAIN_TYPES = (UNANSWERABLE, NOT_IN_LIBRARY)  # the system should say "not found"


@dataclass(frozen=True)
class Row:
    item_id: str
    type: str
    best_distance: float | None  # None when search returned nothing
    hits: int

    @property
    def should_abstain(self) -> bool:
        return self.type in ABSTAIN_TYPES


@dataclass(frozen=True)
class Point:
    threshold: float
    wrongly_abstained: int  # questions that should be answered but were above the threshold
    wrongly_answered: int  # questions that should abstain but were at or below the threshold


def scan_rows(items: Sequence[GoldenItem], best: dict[str, tuple[float | None, int]]) -> list[Row]:
    return [Row(i.id, i.type, best[i.id][0], best[i.id][1]) for i in items if i.id in best]


def sweep(rows: Sequence[Row]) -> list[Point]:
    """For each observed distance used as a threshold ("abstain when the best distance is above
    it"), how many questions go wrong. A question with no hits always abstains."""
    values = sorted({r.best_distance for r in rows if r.best_distance is not None})
    points = []
    for t in values:
        wrong_abstain = wrong_answer = 0
        for r in rows:
            abstains = r.best_distance is None or r.best_distance > t
            if abstains and not r.should_abstain:
                wrong_abstain += 1
            if not abstains and r.should_abstain:
                wrong_answer += 1
        points.append(Point(t, wrong_abstain, wrong_answer))
    return points


def best_points(points: Sequence[Point]) -> list[Point]:
    """The thresholds with the fewest total errors (wrongly abstained counts first on ties,
    because a lost answer is cheaper than an invented one only when the invented ones are zero)."""
    if not points:
        return []
    low = min(p.wrongly_abstained + p.wrongly_answered for p in points)
    return [p for p in points if p.wrongly_abstained + p.wrongly_answered == low]


def format_scan(rows: Sequence[Row]) -> str:
    lines = ["Best meaning distance per question (0 = identical; smaller = closer to the library)", ""]
    by_type: dict[str, list[Row]] = {}
    for r in rows:
        by_type.setdefault(r.type, []).append(r)
    for kind in sorted(by_type):
        ds = sorted(r.best_distance for r in by_type[kind] if r.best_distance is not None)
        if ds:
            lines.append(f"{kind:<15} n={len(by_type[kind]):<3} min {ds[0]:.3f}  median {ds[len(ds) // 2]:.3f}  max {ds[-1]:.3f}")
        else:
            lines.append(f"{kind:<15} n={len(by_type[kind]):<3} no distances (keyword-only search?)")
    points = sweep(rows)
    should = sum(1 for r in rows if not r.should_abstain)
    must = sum(1 for r in rows if r.should_abstain)
    lines += ["", f"Questions that should be answered: {should}; that should say 'not found': {must}", ""]
    if points:
        lines.append("threshold  answerable questions lost   unanswerable questions answered")
        step = max(1, len(points) // 15)
        shown = points[::step]
        for p in shown:
            lines.append(f"  {p.threshold:.3f}      {p.wrongly_abstained:>3}                         {p.wrongly_answered:>3}")
        best = best_points(points)
        if best:
            first, last = best[0], best[-1]
            errors = first.wrongly_abstained + first.wrongly_answered
            lines += ["", f"Fewest errors ({errors}): thresholds {first.threshold:.3f} to {last.threshold:.3f}"]
    return "\n".join(lines)
