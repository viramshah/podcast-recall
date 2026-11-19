"""How much two people agree when they label the same questions (Cohen's kappa).

Kappa corrects raw agreement for the agreement two labellers would reach by chance. 1.0 is perfect,
0 is no better than chance. The Week 2 gate is 0.7 or more on the question type (decision D18).
The episode and the time are reported as plain percentages.
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from podcast_recall import golden
from podcast_recall.checkers import R7_TOLERANCE_S
from podcast_recall.errors import ConfigError

KAPPA_GATE = 0.7
LABEL_COLUMNS = ("id", "type", "gold_evidence")


@dataclass(frozen=True)
class Label:
    type: str
    evidence: tuple[golden.Evidence, ...]


@dataclass
class AgreementReport:
    n: int
    kappa: float
    type_agreement: float
    episode_agreement: float | None  # of the items both label as answerable-with-evidence
    time_agreement: float | None
    disagreements: list[tuple[str, str, str]] = field(default_factory=list)  # id, type A, type B

    @property
    def meets_gate(self) -> bool:
        return self.kappa >= KAPPA_GATE


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Cohen's kappa for two lists of labels about the same items.

    If both people used a single label throughout, chance agreement is 1 and kappa is undefined; it
    is reported as 1.0 when they agree on every item and 0.0 otherwise.
    """
    if len(a) != len(b):
        raise ValueError("the two label lists must be the same length")
    n = len(a)
    if n == 0:
        raise ValueError("there are no labels to compare")
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    count_a, count_b = Counter(a), Counter(b)
    expected = sum(count_a[k] * count_b[k] for k in set(a) | set(b)) / (n * n)
    if expected >= 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1 - expected)


def read_labels(path: str | Path) -> dict[str, Label]:
    """Read a label sheet: columns id, type, gold_evidence (other columns are ignored)."""
    labels: dict[str, Label] = {}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in LABEL_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ConfigError(f"{path} is missing these columns: {', '.join(missing)}")
        for number, row in enumerate(reader, 2):
            item_id = (row["id"] or "").strip()
            if not item_id:
                continue
            kind = (row["type"] or "").strip()
            if kind not in golden.TYPES:
                raise ConfigError(f"{path} row {number} ({item_id}): type '{kind}' must be one of "
                                  f"{', '.join(golden.TYPES)}")
            try:
                evidence = golden.parse_evidence(row["gold_evidence"])
            except ValueError as exc:
                raise ConfigError(f"{path} row {number} ({item_id}): gold_evidence {exc}") from None
            if item_id in labels:
                raise ConfigError(f"{path} row {number}: the id '{item_id}' appears twice")
            labels[item_id] = Label(kind, evidence)
    return labels


def labels_from_golden(items: Sequence[golden.GoldenItem]) -> dict[str, Label]:
    return {i.id: Label(i.type, i.evidence) for i in items}


def compare(a: dict[str, Label], b: dict[str, Label]) -> AgreementReport:
    """Compare two labellers on the items they both labelled."""
    shared = sorted(set(a) & set(b))
    if not shared:
        raise ConfigError("The two label sets have no question ids in common.")
    types_a = [a[i].type for i in shared]
    types_b = [b[i].type for i in shared]
    kappa = cohens_kappa(types_a, types_b)
    same_type = sum(1 for x, y in zip(types_a, types_b, strict=True) if x == y)
    both_evidence = [i for i in shared if a[i].evidence and b[i].evidence]
    same_episode = same_time = 0
    for i in both_evidence:
        eps_a = {e.video_id for e in a[i].evidence}
        eps_b = {e.video_id for e in b[i].evidence}
        if eps_a == eps_b:
            same_episode += 1
            close = all(
                any(abs(x.start_s - y.start_s) <= R7_TOLERANCE_S for y in b[i].evidence if y.video_id == x.video_id)
                for x in a[i].evidence
            )
            same_time += int(close)
    return AgreementReport(
        n=len(shared),
        kappa=kappa,
        type_agreement=same_type / len(shared),
        episode_agreement=same_episode / len(both_evidence) if both_evidence else None,
        time_agreement=same_time / len(both_evidence) if both_evidence else None,
        disagreements=[(i, a[i].type, b[i].type) for i in shared if a[i].type != b[i].type],
    )


def format_report(report: AgreementReport) -> str:
    lines = [
        f"Items compared: {report.n}",
        (f"Cohen's kappa on question type: {report.kappa:.2f}   (gate {KAPPA_GATE})"
        f"  {'MEETS THE GATE' if report.meets_gate else 'BELOW THE GATE'}"),
        f"Same question type: {report.type_agreement:.0%}",
    ]
    if report.episode_agreement is not None:
        lines.append(f"Same gold episode(s): {report.episode_agreement:.0%}")
        lines.append(f"Gold time within {R7_TOLERANCE_S:g} s: {report.time_agreement:.0%}")
    for item_id, a, b in report.disagreements:
        lines.append(f"  disagreement on {item_id}: A says {a}, B says {b}")
    return "\n".join(lines)


def sample_for_second_labeller(items: Sequence[golden.GoldenItem], count: int = 20) -> list[golden.GoldenItem]:
    """A fixed, stratified sample: the same input always gives the same 20, spread across types in
    proportion, taking every k-th item of each type in id order."""
    by_type: dict[str, list[golden.GoldenItem]] = {}
    for item in sorted(items, key=lambda i: i.id):
        by_type.setdefault(item.type, []).append(item)
    total = len(items)
    chosen: list[golden.GoldenItem] = []
    quotas = {t: max(1, round(count * len(rows) / total)) for t, rows in by_type.items()}
    for kind, rows in by_type.items():
        quota = min(quotas[kind], len(rows))
        step = len(rows) / quota
        chosen.extend(rows[int(k * step)] for k in range(quota))
    chosen.sort(key=lambda i: i.id)
    while len(chosen) > count:
        biggest = Counter(i.type for i in chosen).most_common(1)[0][0]
        chosen.remove(next(i for i in reversed(chosen) if i.type == biggest))
    return chosen


def write_labelling_sheet(path: str | Path, items: Sequence[golden.GoldenItem]) -> None:
    """The sheet for the second labeller: questions only, no gold answers."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "question", "type", "gold_evidence", "comment"])
        for item in items:
            writer.writerow([item.id, item.question, "", "", ""])
