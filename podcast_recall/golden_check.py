"""Checks on the golden set itself, so the questions are trustworthy (decision D18, question 18).

For answerable questions: the evidence must point into a transcript, in the library. For
unanswerable and false-premise questions: the key terms must not turn up in any indexed episode.
For not-in-library questions: the episode must be indexed but outside the library.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from podcast_recall import golden, retrieval
from podcast_recall.checkers import WINDOW_S, EvalContext, normalize
from podcast_recall.golden import GoldenItem

MAX_TERMS = 4  # key terms used to look for an answer that should not exist


@dataclass(frozen=True)
class Problem:
    item_id: str
    kind: str  # "error" must be fixed; "warning" needs a person's look
    message: str


def key_terms(question: str) -> list[str]:
    """The most distinctive words of a question: no stop words, longest first."""
    _phrases, words = retrieval.parse_query(question)
    unique = list(dict.fromkeys(w for w in words if len(w) > 2 and w not in retrieval.STOPWORDS))
    return sorted(unique, key=lambda w: (-len(w), w))[:MAX_TERMS]


def presence_hits(conn: sqlite3.Connection, terms: Sequence[str], limit: int = 3) -> list[tuple[int, float, str]]:
    """Chunks anywhere in the index that contain ALL the terms: (episode id, start, snippet)."""
    if not terms:
        return []
    expression = " AND ".join(f'"{t}"' for t in terms)
    rows = conn.execute(
        "SELECT c.episode_id, c.start_s, c.text FROM chunks_fts f JOIN chunks c ON c.chunk_id = f.rowid "
        "WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
        (expression, limit),
    )
    return [(r[0], r[1], r[2][:160]) for r in rows]


def text_near(ctx: EvalContext, episode_id: int, at_s: float, window_s: float = WINDOW_S) -> str:
    transcript = ctx.transcript_for(episode_id)
    if transcript is None:
        return ""
    low, high = at_s - window_s, at_s + window_s
    return " ".join(
        s.text for s in sorted(transcript.segments, key=lambda s: s.start) if s.end >= low and s.start <= high
    )


def check_item(conn: sqlite3.Connection, item: GoldenItem, ctx: EvalContext) -> list[Problem]:
    problems: list[Problem] = []

    def add(kind: str, message: str) -> None:
        problems.append(Problem(item.id, kind, message))

    if item.type in golden.ANSWERABLE_TYPES or item.type == golden.NOT_IN_LIBRARY:
        for evidence in item.evidence:
            episode_id = ctx.video_to_episode.get(evidence.video_id)
            if episode_id is None:
                add("error", f"{evidence.video_id} is not a matched, indexed episode")
                continue
            in_library = episode_id in ctx.library_episode_ids
            if item.type == golden.NOT_IN_LIBRARY and in_library:
                add("error", f"{evidence.video_id} is in the library, so it cannot be a not-in-library question")
            if item.type != golden.NOT_IN_LIBRARY and not in_library:
                add("error", f"{evidence.video_id} is not in the evaluation library")
            if not normalize(text_near(ctx, episode_id, evidence.start_s)):
                add("error", f"the transcript has no words within {WINDOW_S:g} s of "
                             f"{golden.format_time(evidence.start_s)} in {evidence.video_id}")
    elif item.type in (golden.UNANSWERABLE, golden.FALSE_PREMISE):
        terms = key_terms(item.question)
        if not terms:
            add("warning", "the question has no distinctive words to check for")
        for episode_id, start, snippet in presence_hits(conn, terms):
            add("warning",
                f"all of {', '.join(terms)} appear together in episode {episode_id} at "
                f"{golden.format_time(start)}: \"{snippet}\" (is the answer really absent?)")
    return problems


def check_all(conn: sqlite3.Connection, items: Sequence[GoldenItem], ctx: EvalContext) -> list[Problem]:
    found: list[Problem] = []
    for item in items:
        found.extend(check_item(conn, item, ctx))
    return found


def show_item(item: GoldenItem, ctx: EvalContext) -> str:
    """What a reviewer needs to verify one item: the question, the gold answer, and the transcript text
    at each gold time."""
    lines = [f"{item.id}  [{item.type}, {item.split}]", f"Question: {item.question}"]
    if item.gold_answer:
        lines.append(f"Gold answer: {item.gold_answer}")
    if item.key_points:
        lines.append("Key points: " + "; ".join(item.key_points))
    for evidence in item.evidence:
        episode_id = ctx.video_to_episode.get(evidence.video_id)
        lines.append(f"Evidence: {evidence.video_id} at {golden.format_time(evidence.start_s)}"
                     f"   https://youtu.be/{evidence.video_id}?t={int(evidence.start_s)}")
        if episode_id is None:
            lines.append("  (this video is not a matched, indexed episode)")
        else:
            show, title = ctx.episode_label(episode_id)
            lines.append(f"  {show}: {title}")
            lines.append(f"  Transcript near that time: {text_near(ctx, episode_id, evidence.start_s, 20.0)}")
    return "\n".join(lines)
