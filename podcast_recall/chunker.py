"""Split a transcript into overlapping chunks (decisions D17, questions 5 to 8).

A pure function: the same segments and settings always give the same chunks. A chunk is made of
whole segments (a segment is never cut), holds about `TARGET_S` seconds, and the next chunk starts
about `OVERLAP_S` seconds before the previous one ended, so a sentence on a boundary is in both.
Change any of the three numbers by also changing `CHUNKING_VERSION`, which makes the next index
build redo every episode.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from podcast_recall.models import Segment

CHUNKING_VERSION = 1
TARGET_S = 75.0
OVERLAP_S = 15.0


@dataclass(frozen=True)
class ChunkDraft:
    chunk_no: int
    start_s: float
    end_s: float
    text: str
    word_count: int
    speaker: str | None


def _speaker(segments: Sequence[Segment]) -> str | None:
    """A label only when one label covers more than half of the chunk's words."""
    words: Counter[str] = Counter()
    total = 0
    for seg in segments:
        count = len(seg.text.split())
        total += count
        if seg.speaker:
            words[seg.speaker] += count
    if not words or total == 0:
        return None
    label, count = words.most_common(1)[0]
    return label if count * 2 > total else None


def chunk_segments(
    segments: Sequence[Segment], target_s: float = TARGET_S, overlap_s: float = OVERLAP_S
) -> list[ChunkDraft]:
    ordered = sorted((s for s in segments if s.text.strip()), key=lambda s: (s.start, s.end))
    chunks: list[ChunkDraft] = []
    i, n = 0, len(ordered)
    while i < n:
        start = ordered[i].start
        j = i + 1  # always take at least one segment, even a very long one
        while j < n and ordered[j].end - start <= target_s:
            j += 1
        group = ordered[i:j]
        text = " ".join(seg.text.strip() for seg in group)
        chunks.append(
            ChunkDraft(
                chunk_no=len(chunks),
                start_s=group[0].start,
                end_s=max(seg.end for seg in group),
                text=text,
                word_count=len(text.split()),
                speaker=_speaker(group),
            )
        )
        if j >= n:
            break
        boundary = group[-1].end - overlap_s
        # the first later segment that begins at or after the overlap boundary; always moves on
        next_i = next((k for k in range(i + 1, j) if ordered[k].start >= boundary), j)
        i = next_i
    return chunks
