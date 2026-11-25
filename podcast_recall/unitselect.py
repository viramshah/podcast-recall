"""Show the model only the units closest to the question (Week 4, experiment E5).

Chunk search finds a few two-minute passages (about 3,000 tokens for four of them). Seven to
eight billion parameter models point at the wrong unit too often in that much text (E4), and
reading it is slow. Here the units of the retrieved passages are embedded, the ones most similar to
the question are kept together with their immediate neighbours, and only those are shown. Unit
numbers are not renumbered, so a number still means exactly one place and gaps between kept runs
simply end a run of consecutive units.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Sequence

from podcast_recall.prompting import Passage
from podcast_recall.retrieval import embedding_text


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def select_units(
    question: str, passages: Sequence[Passage], embedder, top: int, neighbours: int = 1
) -> list[Passage]:
    """The passages reduced to the `top` best-matching units plus `neighbours` units on each side
    (inside the same passage). Passages left with no unit are dropped; order is unchanged."""
    flat = [(p_index, u_index) for p_index, p in enumerate(passages) for u_index in range(len(p.units))]
    if top <= 0 or len(flat) <= top:
        return list(passages)
    texts = [passages[p].units[u].text for p, u in flat]
    vectors = embedder.embed_documents(texts)
    query = embedder.embed_query(embedding_text(question))
    scores = [_cosine(query, v) for v in vectors]
    best = sorted(range(len(flat)), key=lambda i: (-scores[i], i))[:top]
    keep: set[tuple[int, int]] = set()
    for i in best:
        p, u = flat[i]
        for j in range(u - neighbours, u + neighbours + 1):
            if 0 <= j < len(passages[p].units):
                keep.add((p, j))
    reduced: list[Passage] = []
    for p_index, passage in enumerate(passages):
        kept = tuple(unit for u_index, unit in enumerate(passage.units) if (p_index, u_index) in keep)
        if kept:
            reduced.append(dataclasses.replace(passage, units=kept))
    return reduced
