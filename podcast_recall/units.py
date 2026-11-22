"""Passage units: the pieces of transcript the answering model points at.

A chunk is about two minutes of talk. Inside it, consecutive transcript segments are merged into
units of roughly 5 to 15 seconds, never across a speaker change. The model cites units by number;
the code copies a unit's text word for word and takes its start time, so a citation is exact to
the unit and never invented (decision D19, questions 3 and 6).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from podcast_recall.models import Segment

MIN_UNIT_S = 5.0  # a unit may end at a sentence end once it is this long
MAX_UNIT_S = 15.0  # a unit is cut here even without a sentence end (publisher text has none)
_CLOSERS = "\"')]"
EDGE_S = 0.5  # tolerance when picking the segments that belong to a chunk


@dataclass(frozen=True)
class Unit:
    number: int  # 1-based inside the passage
    start_s: float
    end_s: float
    text: str
    speaker: str | None


def build_units(segments: Sequence[Segment], chunk_start_s: float, chunk_end_s: float) -> list[Unit]:
    """The units of one chunk, in time order. Deterministic."""
    inside = sorted(
        (
            s for s in segments
            if s.text.strip() and s.start >= chunk_start_s - EDGE_S and s.start < chunk_end_s - EDGE_S + 1
        ),
        key=lambda s: (s.start, s.end),
    )
    units: list[Unit] = []
    current: list[Segment] = []

    def flush() -> None:
        if not current:
            return
        text = " ".join(s.text.strip() for s in current)
        units.append(Unit(len(units) + 1, current[0].start, max(s.end for s in current), text, current[0].speaker))
        current.clear()

    for segment in inside:
        if current and (
            segment.speaker != current[-1].speaker
            or max(segment.end, *(s.end for s in current)) - current[0].start > MAX_UNIT_S
        ):
            flush()
        current.append(segment)
        length = max(s.end for s in current) - current[0].start
        ends_sentence = segment.text.strip().rstrip(_CLOSERS).endswith((".", "!", "?"))
        if length >= MAX_UNIT_S or (length >= MIN_UNIT_S and ends_sentence):
            flush()
    flush()
    return units
