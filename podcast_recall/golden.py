"""The golden set: hand-labelled questions with known answers (decision D18).

One CSV file. Columns: id, type, question, gold_answer, key_points, gold_evidence, author, split,
tags, notes. `gold_evidence` is one or more `video_id@mm:ss` separated by semicolons (a time may also
be `h:mm:ss` or plain seconds). `key_points` and `tags` are separated by semicolons.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from podcast_recall import ids
from podcast_recall.errors import ConfigError

SINGLE_FACT = "single_fact"
SYNTHESIS = "synthesis"
WHO_WHEN = "who_when"
UNANSWERABLE = "unanswerable"
FALSE_PREMISE = "false_premise"
NOT_IN_LIBRARY = "not_in_library"

TYPES = (SINGLE_FACT, SYNTHESIS, WHO_WHEN, UNANSWERABLE, FALSE_PREMISE, NOT_IN_LIBRARY)
ANSWERABLE_TYPES = (SINGLE_FACT, SYNTHESIS, WHO_WHEN)
TIMED_TYPES = (SINGLE_FACT, WHO_WHEN)  # R7 applies to these
SPLITS = ("dev", "heldout")
COLUMNS = (
    "id", "type", "question", "gold_answer", "key_points", "gold_evidence", "author", "split",
    "tags", "notes",
)

# The v0 mix of 60 (decision D18, question 16).
V0_MIX = {
    SINGLE_FACT: 20, SYNTHESIS: 13, WHO_WHEN: 10, UNANSWERABLE: 7, FALSE_PREMISE: 5,
    NOT_IN_LIBRARY: 5,
}

_EVIDENCE = re.compile(r"^\s*([A-Za-z0-9_-]{11})\s*@\s*([0-9:.]+)\s*$")


class GoldenError(ConfigError):
    """The golden file has problems. The message lists every one, with its row."""


@dataclass(frozen=True)
class Evidence:
    video_id: str
    start_s: float


@dataclass(frozen=True)
class GoldenItem:
    id: str
    type: str
    question: str
    gold_answer: str
    key_points: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    author: str
    split: str
    tags: tuple[str, ...]
    notes: str

    @property
    def answerable(self) -> bool:
        return self.type in ANSWERABLE_TYPES


def parse_time(text: str) -> float:
    """`34:12`, `1:02:03` or plain seconds to seconds."""
    seconds = 0.0
    for part in text.strip().split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


def format_time(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def parse_evidence(text: str) -> tuple[Evidence, ...]:
    found = []
    for piece in (text or "").split(";"):
        if not piece.strip():
            continue
        match = _EVIDENCE.match(piece)
        if not match:
            raise ValueError(f"'{piece.strip()}' is not video_id@mm:ss")
        try:
            found.append(Evidence(match.group(1), parse_time(match.group(2))))
        except ValueError:
            raise ValueError(f"'{piece.strip()}' has a time that is not mm:ss") from None
    return tuple(found)


def format_evidence(evidence: Sequence[Evidence]) -> str:
    return "; ".join(f"{e.video_id}@{format_time(e.start_s)}" for e in evidence)


def _split(text: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in (text or "").split(";") if p.strip())


def load_golden(path: str | Path) -> list[GoldenItem]:
    """Read and validate the golden file. Raises `GoldenError` listing every problem."""
    problems: list[str] = []
    items: list[GoldenItem] = []
    seen: set[str] = set()
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise GoldenError(f"{path} is missing these columns: {', '.join(missing)}")
        for row_number, row in enumerate(reader, 2):
            if not any((v or "").strip() for v in row.values()):
                continue
            where = f"row {row_number}"
            item_id = (row["id"] or "").strip()
            if not item_id:
                problems.append(f"{where}: id is empty")
                continue
            where = f"row {row_number} ({item_id})"
            if item_id in seen:
                problems.append(f"{where}: the id appears twice")
            seen.add(item_id)
            kind = (row["type"] or "").strip()
            if kind not in TYPES:
                problems.append(f"{where}: type '{kind}' must be one of {', '.join(TYPES)}")
            split = (row["split"] or "").strip()
            if split not in SPLITS:
                problems.append(f"{where}: split '{split}' must be dev or heldout")
            question = (row["question"] or "").strip()
            if not question:
                problems.append(f"{where}: the question is empty")
            try:
                evidence = parse_evidence(row["gold_evidence"])
            except ValueError as exc:
                problems.append(f"{where}: gold_evidence {exc}")
                evidence = ()
            gold_answer = (row["gold_answer"] or "").strip()
            if kind in ANSWERABLE_TYPES:
                if not gold_answer:
                    problems.append(f"{where}: an answerable question needs a gold_answer")
                if not evidence:
                    problems.append(f"{where}: an answerable question needs gold_evidence")
            if kind == SYNTHESIS and len({e.video_id for e in evidence}) < 2:
                problems.append(f"{where}: a synthesis question needs evidence from at least 2 episodes")
            if kind in (SINGLE_FACT, WHO_WHEN) and len(evidence) != 1:
                problems.append(f"{where}: this type needs exactly one piece of evidence")
            if kind in (UNANSWERABLE, FALSE_PREMISE) and evidence:
                problems.append(f"{where}: this type must have no gold_evidence (the answer is absent)")
            if kind == NOT_IN_LIBRARY and not evidence:
                problems.append(f"{where}: needs gold_evidence (the episode that is outside the library)")
            if not (row["author"] or "").strip():
                problems.append(f"{where}: author is empty")
            items.append(
                GoldenItem(
                    id=item_id, type=kind, question=question, gold_answer=gold_answer,
                    key_points=_split(row["key_points"]), evidence=evidence,
                    author=(row["author"] or "").strip(), split=split,
                    tags=_split(row["tags"]), notes=(row["notes"] or "").strip(),
                )
            )
    if problems:
        raise GoldenError(f"{path} has {len(problems)} problem(s):\n  " + "\n  ".join(problems))
    return items


def write_golden(path: str | Path, items: Sequence[GoldenItem]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for item in items:
            writer.writerow({
                "id": item.id, "type": item.type, "question": item.question,
                "gold_answer": item.gold_answer, "key_points": "; ".join(item.key_points),
                "gold_evidence": format_evidence(item.evidence), "author": item.author,
                "split": item.split, "tags": "; ".join(item.tags), "notes": item.notes,
            })


def split_counts(items: Sequence[GoldenItem]) -> dict[str, dict[str, int]]:
    """Counts per type and per split, for reports."""
    return {
        "type": dict(Counter(i.type for i in items)),
        "split": dict(Counter(i.split for i in items)),
    }


def load_library(path: str | Path) -> list[str]:
    """The evaluation library: video IDs from a CSV with a `youtube_url` column (or a list)."""
    found, unparsed = ids.load_ids([str(path)])
    if unparsed:
        raise ConfigError(f"{path}: could not read these entries: {', '.join(unparsed[:5])}")
    if not found:
        raise ConfigError(f"{path} lists no videos.")
    return found
