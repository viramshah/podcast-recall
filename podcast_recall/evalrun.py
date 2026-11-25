"""Run the deterministic rubric checks over answers and write a scorecard (decision D18).

Only the deterministic rules run here: R1, R2, R5 and R7. The judge rules (R3 claim support, R4
attribution, R6 completeness) need a model and come later, so every scorecard says so.
"""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from podcast_recall import checkers, jobs, probe, transcripts
from podcast_recall.answers import AnswerFormatError, parse_answer
from podcast_recall.checkers import CRITICAL, MAJOR, EvalContext, Failure
from podcast_recall.golden import (
    SYNTHESIS,
    TIMED_TYPES,
    GoldenItem,
)

JUDGE_NOTE = (
    "Deterministic checks only (R1, R2, R5, R7). The judge rules R3, R4 and R6 are not run yet, "
    "so these numbers can only get worse once they are."
)


@dataclass
class Grade:
    item_id: str
    type: str
    split: str
    tags: tuple[str, ...]
    status: str
    failures: list[Failure] = field(default_factory=list)
    review: bool = False
    r7: bool | None = None  # None when R7 does not apply
    episode_recall: float | None = None

    @property
    def passed(self) -> bool:
        return not any(f.severity in (CRITICAL, MAJOR) for f in self.failures)

    @property
    def critical(self) -> bool:
        return any(f.severity == CRITICAL for f in self.failures)

    @property
    def rules_failed(self) -> list[str]:
        return sorted({f.rule for f in self.failures if f.severity in (CRITICAL, MAJOR)})


# ---------------------------------------------------------------------------- context


def build_context(conn: sqlite3.Connection, library_video_ids: Sequence[str]) -> EvalContext:
    """The world the checkers need: which episodes are in the library, and every matched video."""
    video_to_episode = {
        r["video_id"]: r["episode_id"]
        for r in conn.execute(
            "SELECT video_id, episode_id FROM episode_matches "
            "WHERE status = 'matched' AND episode_id IS NOT NULL"
        )
    }
    library_episodes = set(jobs.matched_episode_ids(conn, list(library_video_ids)))
    cache: dict[int, object] = {}

    def transcript_for(episode_id: int):
        if episode_id not in cache:
            cache[episode_id] = transcripts.load_transcript(conn, episode_id)
        return cache[episode_id]

    def episode_label(episode_id: int) -> tuple[str, str]:
        row = conn.execute(
            "SELECT f.title AS show, e.title AS title FROM episodes e "
            "JOIN feeds f ON f.feed_id = e.feed_id WHERE e.episode_id = ?",
            (episode_id,),
        ).fetchone()
        return (row["show"], row["title"]) if row else ("", "")

    return EvalContext(library_episodes, video_to_episode, transcript_for, episode_label)


# ---------------------------------------------------------------------------- grading


def grade_answer(item: GoldenItem, raw: object, ctx: EvalContext) -> Grade:
    base = {"item_id": item.id, "type": item.type, "split": item.split, "tags": item.tags}
    if raw is None:
        return Grade(**base, status="missing", failures=[Failure("answer", MAJOR, "no answer was given")])
    try:
        answer = parse_answer(raw)
    except AnswerFormatError as exc:
        return Grade(**base, status="invalid", failures=[Failure("format", MAJOR, str(exc))])
    failures: list[Failure] = []
    r5, review = checkers.check_r5(answer, item)
    if r5:
        failures.append(r5)
    failures.extend(checkers.check_claims_cited(answer))
    for claim_number, claim in enumerate(answer.claims, 1):
        for citation_number, citation in enumerate(claim.citations, 1):
            for check in (checkers.check_r1, checkers.check_r2):
                failure = check(citation, ctx)
                if failure:
                    failures.append(
                        Failure(failure.rule, failure.severity,
                                f"claim {claim_number}, citation {citation_number}: {failure.reason}")
                    )
    r7 = checkers.check_r7(answer, item)
    if r7:
        failures.append(r7)
    return Grade(
        **base, status=answer.status, failures=failures, review=review,
        r7=None if item.type not in TIMED_TYPES else r7 is None,
        episode_recall=checkers.episode_recall(answer, item, ctx),
    )


def grade_all(
    items: Sequence[GoldenItem], answers: dict[str, object], ctx: EvalContext, split: str = "all"
) -> list[Grade]:
    chosen = [i for i in items if split == "all" or i.split == split]
    return [grade_answer(i, answers.get(i.id), ctx) for i in chosen]


# ---------------------------------------------------------------------------- scorecard


UNANSWERABLE_TYPES = ("unanswerable", "not_in_library")
ANSWERABLE_TYPES = ("single_fact", "synthesis", "who_when")


def _rate(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def summarize(grades: Sequence[Grade]) -> dict:
    n = len(grades)
    passed = sum(1 for g in grades if g.passed)
    by_type: dict[str, list[Grade]] = defaultdict(list)
    by_split: dict[str, list[Grade]] = defaultdict(list)
    by_tag: dict[str, list[Grade]] = defaultdict(list)
    for g in grades:
        by_type[g.type].append(g)
        by_split[g.split].append(g)
        for tag in g.tags:
            by_tag[tag].append(g)

    def table(groups: dict[str, list[Grade]]) -> dict[str, dict]:
        return {
            key: {"n": len(rows), "passed": sum(1 for g in rows if g.passed)}
            for key, rows in sorted(groups.items())
        }

    rule_failures: Counter[str] = Counter()
    for g in grades:
        rule_failures.update(g.rules_failed)
    r7_rows = [g for g in grades if g.r7 is not None]
    recalls = [g.episode_recall for g in grades if g.episode_recall is not None]
    return {
        "n": n,
        "passed": passed,
        "accuracy": _rate(passed, n),
        "critical": sum(1 for g in grades if g.critical),
        "hallucination_rate": _rate(sum(1 for g in grades if g.critical), n),
        "by_type": table(by_type),
        "by_split": table(by_split),
        "by_tag": table(by_tag),
        "rule_failures": dict(sorted(rule_failures.items())),
        "integrity_failures": sum(1 for g in grades if {"R1", "R2"} & set(g.rules_failed)),
        "unanswerable_n": sum(1 for g in grades if g.type in UNANSWERABLE_TYPES),
        "unanswerable_answered": sum(1 for g in grades if g.type in UNANSWERABLE_TYPES and g.status != "not_found"),
        "answerable_n": sum(1 for g in grades if g.type in ANSWERABLE_TYPES),
        "answerable_refused": sum(1 for g in grades if g.type in ANSWERABLE_TYPES and g.status == "not_found"),
        "r7_applicable": len(r7_rows),
        "r7_passed": sum(1 for g in r7_rows if g.r7),
        "episode_recall_mean": sum(recalls) / len(recalls) if recalls else None,
        "needs_review": sum(1 for g in grades if g.review),
    }


def format_summary(summary: dict) -> str:
    def pct(part: int, whole: int) -> str:
        return f"{part}/{whole} = {_rate(part, whole):.0%}" if whole else "0/0"

    n = summary["n"]
    lines = [
        JUDGE_NOTE,
        f"Questions graded: {n}",
        "Release gate (D22), safety, must be 0 failures:",
        f"  Invented or out-of-library citations (R1, R2): {summary['integrity_failures']}/{n}",
        f"  Unanswerable or not-in-library questions answered: {summary['unanswerable_answered']}/{summary['unanswerable_n']}",
        "Original targets (D20), kept as stretch targets, not release conditions:",
        f"  Grounded accuracy (deterministic rules): {pct(summary['passed'], n)}   (target 90%)",
        f"  Answers with a Critical failure:         {pct(summary['critical'], n)}   (target 2% or less)",
        f"Answerable questions refused (reported): {summary['answerable_refused']}/{summary['answerable_n']}",
    ]
    if summary["r7_applicable"]:
        lines.append(f"Timestamp within 15 s (R7):              {pct(summary['r7_passed'], summary['r7_applicable'])}")
    if summary["episode_recall_mean"] is not None:
        lines.append(f"Synthesis episode coverage (mean):       {summary['episode_recall_mean']:.0%}")
    if summary["needs_review"]:
        lines.append(f"Answers for a person to read (false premise): {summary['needs_review']}")
    lines.append("By type:")
    for key, row in summary["by_type"].items():
        lines.append(f"  {key:<15} {pct(row['passed'], row['n'])}")
    if len(summary["by_split"]) > 1:
        lines.append("By split:")
        for key, row in summary["by_split"].items():
            lines.append(f"  {key:<15} {pct(row['passed'], row['n'])}")
    if summary["by_tag"]:
        lines.append("By tag:")
        for key, row in summary["by_tag"].items():
            lines.append(f"  {key:<15} {pct(row['passed'], row['n'])}")
    if summary["rule_failures"]:
        lines.append("Failures by rule: " + ", ".join(f"{k} {v}" for k, v in summary["rule_failures"].items()))
    return "\n".join(lines)


def write_scorecard(path: str | Path, grades: Sequence[Grade]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "type", "split", "tags", "status", "passed", "critical", "rules_failed",
                         "r7", "episode_recall", "needs_review", "reasons"])
        for g in grades:
            writer.writerow([
                g.item_id, g.type, g.split, ";".join(g.tags), g.status, int(g.passed), int(g.critical),
                ";".join(g.rules_failed), "" if g.r7 is None else int(g.r7),
                "" if g.episode_recall is None else f"{g.episode_recall:.2f}", int(g.review),
                " | ".join(f"{f.rule}: {f.reason}" for f in g.failures),
            ])


# ---------------------------------------------------------------------------- retrieval on the golden set


@dataclass
class RetrievalOutcome:
    item_id: str
    type: str
    split: str
    tags: tuple[str, ...]
    rank: int | None  # timed types: rank of the chunk holding the gold time
    episode_recall: float | None  # synthesis: share of gold episodes in the top 5
    leaked: bool  # a hit came from an episode outside the library (must never happen)
    deep_rank: int | None = None  # a miss, searched again 50 deep with no per-episode cap
    gold_distance: float | None = None  # the meaning distance of the right chunk in that deep search
    top: list = field(default_factory=list)  # the first few hits actually returned (for a miss)

    @property
    def id_missed(self) -> bool:
        """A single-fact or who/when question whose right chunk is not in the top 5."""
        return self.type in TIMED_TYPES and not (self.rank and self.rank <= 5)

    @property
    def recall_ok(self) -> bool:
        """True for a synthesis outcome that has an episode-recall value."""
        return self.episode_recall is not None


def retrieval_outcomes(items, ctx: EvalContext, search, deep_search=None) -> list[RetrievalOutcome]:
    """`search(question)` returns a list of SearchHit. Answerable types are scored on the gold
    evidence. Every question is also checked for results leaking out of the library. When
    `deep_search` is given, each miss is searched again (deeper, with no per-episode cap) to show
    where the right chunk really ranks."""
    outcomes = []
    for item in items:
        hits = search(item.question)
        leaked = any(h.episode_id not in ctx.library_episode_ids for h in hits)
        rank, recall = None, None
        deep_rank = gold_distance = None
        top: list = []
        if item.type in TIMED_TYPES and item.evidence:
            gold = item.evidence[0]
            episode_id = ctx.video_to_episode.get(gold.video_id)
            if episode_id is not None:
                rank = probe.gold_rank(hits, episode_id, gold.start_s)
                if (rank is None or rank > 5) and deep_search is not None:
                    deep = deep_search(item.question)
                    deep_rank = probe.gold_rank(deep, episode_id, gold.start_s)
                    found = next((h for h in deep if probe.holds_gold(h, episode_id, gold.start_s)), None)
                    gold_distance = found.vector_distance if found else None
                    top = list(hits[:3])
        elif item.type == SYNTHESIS and item.evidence:
            gold_eps = {ctx.video_to_episode.get(e.video_id) for e in item.evidence} - {None}
            top = {h.episode_id for h in hits[:5]}
            recall = len(gold_eps & top) / len(gold_eps) if gold_eps else None
        outcomes.append(
            RetrievalOutcome(item.id, item.type, item.split, item.tags, rank, recall, leaked,
                             deep_rank, gold_distance, top)
        )
    return outcomes


def retrieval_summary(outcomes: Sequence[RetrievalOutcome]) -> dict:
    timed = [o for o in outcomes if o.type in TIMED_TYPES]
    synthesis = [o for o in outcomes if o.recall_ok]
    return {
        "timed_n": len(timed),
        "recall_at_5": _rate(sum(1 for o in timed if o.rank and o.rank <= 5), len(timed)),
        "recall_at_10": _rate(sum(1 for o in timed if o.rank and o.rank <= 10), len(timed)),
        "mrr": sum(1 / o.rank for o in timed if o.rank) / len(timed) if timed else 0.0,
        "synthesis_n": len(synthesis),
        "synthesis_episode_recall": (
            sum(o.episode_recall for o in synthesis) / len(synthesis) if synthesis else None
        ),
        "leaks": sum(1 for o in outcomes if o.leaked),
        "by_type": {
            t: {
                "n": len([o for o in timed if o.type == t]),
                "recall_at_5": _rate(
                    sum(1 for o in timed if o.type == t and o.rank and o.rank <= 5),
                    len([o for o in timed if o.type == t]),
                ),
            }
            for t in sorted({o.type for o in timed})
        },
        "misses": [o.item_id for o in timed if not (o.rank and o.rank <= 5)],
    }


# ---------------------------------------------------------------------------- the answering system, run on the golden set


def _median(values: Sequence[float]) -> float | None:
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else None


def summarize_answering(results: Sequence, latencies_s: Sequence[float]) -> dict:
    """Status counts, claims kept and dropped (with the reasons) and the time taken, for a run of the
    real answering system. `results` are `AskResult`s."""
    statuses: Counter[str] = Counter(r.answer.status for r in results)
    reasons: Counter[str] = Counter()
    for r in results:
        for d in r.dropped:
            reasons[d.reason.split(":")[0][:80]] += 1
    ordered = sorted(latencies_s)

    def percentile(p: float) -> float | None:
        if not ordered:
            return None
        return ordered[min(len(ordered) - 1, round(p * (len(ordered) - 1)))]

    return {
        "questions": len(results),
        "statuses": dict(statuses),
        "claims_kept": sum(len(r.answer.claims) for r in results),
        "claims_dropped": sum(len(r.dropped) for r in results),
        "drop_reasons": dict(reasons.most_common(6)),
        "median_s": percentile(0.5),
        "p90_s": percentile(0.9),
        "models": sorted({r.model for r in results if r.model}),
        "model_errors": sum(1 for r in results if any("could not be used" in w for w in r.warnings)),
        "median_prompt_tokens": _median([r.prompt_tokens for r in results if r.prompt_tokens]),
        "median_units_shown": _median([r.units_shown for r in results if r.units_total]),
        "median_units_total": _median([r.units_total for r in results if r.units_total]),
    }


def format_answering(summary: dict) -> str:
    def seconds(value) -> str:
        return "n/a" if value is None else f"{value:.1f} s"

    lines = [
        f"Questions answered by the system: {summary['questions']} (model: {', '.join(summary['models']) or 'n/a'})",
        "Answer statuses: " + ", ".join(f"{k} {v}" for k, v in sorted(summary["statuses"].items())),
        f"Claims shown: {summary['claims_kept']}; claims removed by the verifier: {summary['claims_dropped']}",
    ]
    if summary["drop_reasons"]:
        lines.append("Why claims were removed: " + "; ".join(f"{k} ({v})" for k, v in summary["drop_reasons"].items()))
    if summary["model_errors"]:
        lines.append(f"Questions where the model's reply could not be used: {summary['model_errors']}")
    if summary.get("median_prompt_tokens"):
        shown = summary.get("median_units_shown")
        total = summary.get("median_units_total")
        units = f"; units shown {shown:g} of {total:g} (median)" if shown and total else ""
        lines.append(f"Prompt size: median {summary['median_prompt_tokens']:g} tokens{units}")
    lines.append(f"Time to answer: median {seconds(summary['median_s'])}, 90th percentile {seconds(summary['p90_s'])} (target: median under 15 s)")
    return "\n".join(lines)
