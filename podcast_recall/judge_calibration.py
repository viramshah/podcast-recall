"""Is the judge model as good as a person at reading a claim against its quote? (Week 4, Q8 and Q9.)

A sample of claims from saved runs is written to a sheet with the question, the claim and the
quote, and no judge verdict. A person fills in two labels per claim (the same two questions the
judge answers): is the claim supported by the quote, and does the claim answer the question. The
judge is then run on the same claims and the two sets of labels are compared. The bar (decision
D20): at least 85% agreement on "passes" (both yes) and kappa at least 0.6.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from podcast_recall import judge
from podcast_recall.agreement import cohens_kappa
from podcast_recall.answers import Claim, parse_answer
from podcast_recall.errors import ConfigError
from podcast_recall.golden import GoldenItem

LABELS = ("yes", "partly", "no")
MIN_AGREEMENT = 0.85
MIN_KAPPA = 0.6
SHEET_COLUMNS = ["claim_id", "question", "claim", "quote", "human_supported", "human_answers_question"]


@dataclass(frozen=True)
class ClaimRow:
    claim_id: str
    source: str
    question_id: str
    question: str
    claim: str
    quote: str
    answer_status: str


def source_name(path: str | Path) -> str:
    found = re.findall(r"\d{8}-\d{4}", str(path))
    return found[-1] if found else Path(path).stem


def collect_claims(paths: Sequence[str | Path], items: Sequence[GoldenItem]) -> list[ClaimRow]:
    from podcast_recall.answers import load_answers

    questions = {i.id: i.question for i in items}
    rows: list[ClaimRow] = []
    for path in paths:
        source = source_name(path)
        for item_id, raw in load_answers(path).items():
            if item_id not in questions:
                continue
            answer = parse_answer(raw)
            for number, claim in enumerate(answer.claims, 1):
                quote = " / ".join(c.quote for c in claim.citations)
                rows.append(ClaimRow(f"{source}:{item_id}#{number}", source, item_id, questions[item_id],
                                     claim.text, quote, answer.status))
    return rows


def _key(claim_id: str) -> str:
    return hashlib.sha1(claim_id.encode("utf-8")).hexdigest()


def sample(rows: Sequence[ClaimRow], count: int) -> list[ClaimRow]:
    """A deterministic sample spread evenly across the source runs, ordered by a hash of the claim id."""
    by_source: dict[str, list[ClaimRow]] = {}
    for row in rows:
        by_source.setdefault(row.source, []).append(row)
    sources = sorted(by_source)
    if not sources:
        return []
    share = max(1, count // len(sources))
    chosen: list[ClaimRow] = []
    for source in sources:
        chosen.extend(sorted(by_source[source], key=lambda r: _key(r.claim_id))[:share])
    leftovers = sorted((r for r in rows if r not in chosen), key=lambda r: _key(r.claim_id))
    chosen.extend(leftovers[: max(0, count - len(chosen))])
    return sorted(chosen[:count], key=lambda r: _key(r.claim_id))


def write_sheet(path: str | Path, rows: Sequence[ClaimRow]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SHEET_COLUMNS)
        for r in rows:
            writer.writerow([r.claim_id, r.question, r.claim, r.quote, "", ""])


def read_labels(path: str | Path) -> dict[str, tuple[str, str]]:
    """The filled-in rows only. A label must be yes, partly or no."""
    labels: dict[str, tuple[str, str]] = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            supported = (row.get("human_supported") or "").strip().lower()
            answers = (row.get("human_answers_question") or "").strip().lower()
            if not supported and not answers:
                continue
            if supported not in LABELS or answers not in LABELS:
                raise ConfigError(f"{path} row {number}: labels must be yes, partly or no (got '{supported}' and '{answers}').")
            labels[row["claim_id"]] = (supported, answers)
    return labels


def run_judge(chat, rows: Sequence[ClaimRow], wanted: set[str]) -> dict[str, tuple[str, str]]:
    """The judge's verdict for each wanted claim, asked the way production asks it: one call per
    answer with all of that answer's claims in order."""
    groups: dict[tuple[str, str], list[ClaimRow]] = {}
    for r in rows:
        groups.setdefault((r.source, r.question_id), []).append(r)
    verdicts: dict[str, tuple[str, str]] = {}
    for group in groups.values():
        if not any(r.claim_id in wanted for r in group):
            continue
        claims = [_with_quote(r) for r in group]
        result = judge.check_answer(chat, group[0].question, "answered", claims)
        if result.raw is None:
            continue
        parsed = judge.parse_verdicts(result.raw, len(claims))
        for number, r in enumerate(group, 1):
            if number in parsed:
                verdicts[r.claim_id] = parsed[number]
    return verdicts


def _with_quote(row: ClaimRow) -> Claim:
    from podcast_recall.answers import Citation

    return Claim(row.claim, (Citation("x", 0, "", "", row.quote, 0.0, ""),))


@dataclass
class Report:
    n: int
    supported_agreement: float
    answers_agreement: float
    pass_agreement: float
    kappa: float
    judge_too_strict: int  # a person passes the claim, the judge does not
    judge_too_lenient: int  # the judge passes the claim, a person does not
    missing_verdicts: int

    @property
    def meets_bar(self) -> bool:
        return self.n > 0 and self.pass_agreement >= MIN_AGREEMENT and self.kappa >= MIN_KAPPA


def _passes(pair: tuple[str, str]) -> str:
    return "pass" if pair == ("yes", "yes") else "fail"


def compare(human: dict[str, tuple[str, str]], machine: dict[str, tuple[str, str]]) -> Report:
    ids = sorted(set(human) & set(machine))
    missing = len(set(human) - set(machine))
    if not ids:
        return Report(0, 0.0, 0.0, 0.0, 0.0, 0, 0, missing)
    n = len(ids)
    h_pass = [_passes(human[i]) for i in ids]
    m_pass = [_passes(machine[i]) for i in ids]
    return Report(
        n=n,
        supported_agreement=sum(human[i][0] == machine[i][0] for i in ids) / n,
        answers_agreement=sum(human[i][1] == machine[i][1] for i in ids) / n,
        pass_agreement=sum(h == m for h, m in zip(h_pass, m_pass, strict=True)) / n,
        kappa=cohens_kappa(h_pass, m_pass),
        judge_too_strict=sum(h == "pass" and m == "fail" for h, m in zip(h_pass, m_pass, strict=True)),
        judge_too_lenient=sum(h == "fail" and m == "pass" for h, m in zip(h_pass, m_pass, strict=True)),
        missing_verdicts=missing,
    )


def format_report(report: Report) -> str:
    if report.n == 0:
        return "No claims could be compared (no filled-in labels, or the judge gave no verdicts)."
    lines = [
        f"Claims compared: {report.n}" + (f" ({report.missing_verdicts} had no judge verdict)" if report.missing_verdicts else ""),
        f"Agreement on 'supported':          {report.supported_agreement:.0%}",
        f"Agreement on 'answers the question': {report.answers_agreement:.0%}",
        f"Agreement on 'passes' (both yes):  {report.pass_agreement:.0%}   (bar {MIN_AGREEMENT:.0%})",
        f"Kappa on 'passes':                 {report.kappa:.2f}   (bar {MIN_KAPPA})",
        f"Judge stricter than a person (person passes, judge fails): {report.judge_too_strict}",
        f"Judge more lenient than a person (judge passes, person fails): {report.judge_too_lenient}",
        "",
        "Bar met: the judge may score R3 for the gate." if report.meets_bar
        else "Bar NOT met: R3 and R4 must be graded by hand on the gate run (or the judge improved first).",
    ]
    return "\n".join(lines)
