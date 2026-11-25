"""Why did each failing golden question fail? (Week 4, workstream A.)

Uses what `eval answer` saved for each question (the chunks the model was shown, its raw reply,
what the verifier removed) together with the golden evidence. No model is needed. Each failing
question gets exactly one cause, so the counts add up to the number of failures.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from podcast_recall.checkers import EvalContext
from podcast_recall.evalrun import Grade
from podcast_recall.golden import FALSE_PREMISE, GoldenItem

NOT_SHOWN = "gold_passage_not_shown"
VERIFIER_EMPTIED = "verifier_removed_every_claim"
MODEL_REFUSED = "model_refused_with_gold_passage_shown"
PREMISE_MISSED = "false_premise_not_corrected"
INVENTED = "invented_answer_to_unanswerable"
FAILED_RULE = "answered_but_failed_a_rule"
NO_TRACE = "no_trace_for_question"

CAUSES = (NOT_SHOWN, VERIFIER_EMPTIED, MODEL_REFUSED, PREMISE_MISSED, INVENTED, FAILED_RULE, NO_TRACE)

MEANING = {
    NOT_SHOWN: "Retrieval: none of the passages shown to the model covers the gold evidence time.",
    VERIFIER_EMPTIED: "The model answered, but the code or verifier removed every claim.",
    MODEL_REFUSED: "The gold passage was shown, yet the model said not_found or premise_corrected.",
    PREMISE_MISSED: "A false-premise question was not answered with premise_corrected.",
    INVENTED: "An unanswerable question received an answer.",
    FAILED_RULE: "The question was answered and a rule (R1, R2, R7 ...) failed.",
    NO_TRACE: "No saved trace for this question, so the cause cannot be told.",
}


@dataclass(frozen=True)
class Diagnosis:
    item_id: str
    type: str
    status: str
    cause: str
    detail: str = ""


def chunk_spans(conn: sqlite3.Connection, chunk_ids: Sequence[int]) -> list[tuple[int, float, float]]:
    """(episode_id, start_s, end_s) for each chunk id that still exists."""
    spans = []
    for chunk_id in chunk_ids:
        row = conn.execute(
            "SELECT episode_id, start_s, end_s FROM chunks WHERE chunk_id = ?", (chunk_id,)
        ).fetchone()
        if row:
            spans.append((row[0], row[1], row[2]))
    return spans


def evidence_shown(item: GoldenItem, spans: Sequence[tuple[int, float, float]], ctx: EvalContext) -> bool:
    """True when a chunk shown to the model covers the gold evidence time of any evidence video."""
    for evidence in item.evidence:
        episode_id = ctx.video_to_episode.get(evidence.video_id)
        if episode_id is None:
            continue
        if any(e == episode_id and start <= evidence.start_s < end for e, start, end in spans):
            return True
    return False


def classify(
    item: GoldenItem, grade: Grade, trace: dict | None, spans: Sequence[tuple[int, float, float]], ctx: EvalContext
) -> Diagnosis | None:
    """The cause of a failing question, or None when it passed."""
    if grade.passed:
        return None
    rules = ", ".join(sorted({f.rule for f in grade.failures}))
    if trace is None:
        return Diagnosis(item.id, item.type, grade.status, NO_TRACE)
    if item.type == FALSE_PREMISE:
        return Diagnosis(item.id, item.type, grade.status, PREMISE_MISSED, rules)
    if not item.answerable:
        return Diagnosis(item.id, item.type, grade.status, INVENTED, rules)
    refused = grade.status in ("not_found", "premise_corrected")
    if not refused:
        return Diagnosis(item.id, item.type, grade.status, FAILED_RULE, rules)
    if trace.get("dropped"):
        reasons = Counter(d.get("reason", "") for d in trace["dropped"])
        return Diagnosis(item.id, item.type, grade.status, VERIFIER_EMPTIED,
                         "; ".join(f"{r} ({n})" for r, n in reasons.most_common()))
    if not evidence_shown(item, spans, ctx):
        return Diagnosis(item.id, item.type, grade.status, NOT_SHOWN)
    return Diagnosis(item.id, item.type, grade.status, MODEL_REFUSED)


def diagnose(
    conn: sqlite3.Connection,
    items: Sequence[GoldenItem],
    grades: Sequence[Grade],
    traces: dict[str, dict],
    ctx: EvalContext,
) -> list[Diagnosis]:
    by_id = {i.id: i for i in items}
    found: list[Diagnosis] = []
    for grade in grades:
        item = by_id[grade.item_id]
        trace = traces.get(item.id)
        spans = chunk_spans(conn, trace.get("chunk_ids", [])) if trace else []
        verdict = classify(item, grade, trace, spans, ctx)
        if verdict:
            found.append(verdict)
    return found


def format_diagnosis(found: Sequence[Diagnosis], total: int) -> str:
    counts = Counter(d.cause for d in found)
    lines = [f"Questions graded: {total}; failing: {len(found)}", ""]
    for cause in CAUSES:
        if counts[cause]:
            ids = ", ".join(d.item_id for d in found if d.cause == cause)
            lines.append(f"{counts[cause]:>3}  {cause}: {MEANING[cause]}")
            lines.append(f"       {ids}")
    return "\n".join(lines)
