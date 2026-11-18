"""Score retrieval against a small hand-made probe set (U4's own check until the Week 2 golden set).

Each probe row is a question, the YouTube video it is answered in, and `gold_s`, a second inside
the answer. A search result counts as correct when it is a chunk of that episode whose time range
contains `gold_s`. Recall@5 is the share of questions with a correct chunk in the top 5.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from podcast_recall.errors import ConfigError
from podcast_recall.models import SearchHit

REQUIRED = ("question", "video_id", "gold_s")


@dataclass(frozen=True)
class ProbeRow:
    question: str
    video_id: str
    gold_s: float
    author: str
    tag: str


@dataclass
class ProbeOutcome:
    row: ProbeRow
    rank: int | None  # 1-based position of the first correct chunk, or None
    top: list[SearchHit]


def load_probe(path: str | Path) -> list[ProbeRow]:
    rows: list[ProbeRow] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ConfigError(f"The probe file needs these columns: {', '.join(missing)}")
        for number, record in enumerate(reader, 2):
            question = (record["question"] or "").strip()
            video_id = (record["video_id"] or "").strip()
            if not question and not video_id:
                continue
            try:
                gold = float(record["gold_s"])
            except (TypeError, ValueError):
                raise ConfigError(f"Probe line {number}: gold_s must be a number of seconds.") from None
            if not question or not video_id:
                raise ConfigError(f"Probe line {number}: question and video_id are both required.")
            rows.append(
                ProbeRow(question, video_id, gold, (record.get("author") or "").strip(),
                         (record.get("tag") or "").strip())
            )
    return rows


def gold_rank(hits: Sequence[SearchHit], episode_id: int, gold_s: float) -> int | None:
    for position, hit in enumerate(hits, 1):
        if hit.episode_id == episode_id and hit.start_s <= gold_s <= hit.end_s:
            return position
    return None


def recall_at(outcomes: Sequence[ProbeOutcome], k: int) -> float:
    return sum(1 for o in outcomes if o.rank is not None and o.rank <= k) / len(outcomes) if outcomes else 0.0


def mean_reciprocal_rank(outcomes: Sequence[ProbeOutcome]) -> float:
    return sum(1 / o.rank for o in outcomes if o.rank) / len(outcomes) if outcomes else 0.0
