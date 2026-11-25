"""Hand grading of R3 (claim support) and R4 (attribution) on a real run (Week 4, decision D21).

The judge model is not qualified (see the Week 4 results), so a person grades each shown claim.
R3: does the quote say what the claim says (ignoring who is named)? yes / partly / no.
R4: are the named person, show and episode right, using the episode's speaker data? yes / no.
Also recorded: does the claim answer the question? yes / partly / no.

Scoring, per answered question: any R3 "no" or R4 "no" is Critical; any R3 "partly", or "no" on
answers-the-question, is Major; otherwise the answer passes the hand-graded rules.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from podcast_recall.errors import ConfigError
from podcast_recall.judge_calibration import ClaimRow

COLUMNS = ["claim_id", "question", "claim", "quote", "show", "episode", "r3_supported", "r4_attribution", "answers_question", "note"]
R3_VALUES = ("yes", "partly", "no")
R4_VALUES = ("yes", "no")


def write_sheet(path: str | Path, rows: Sequence[ClaimRow], places: dict[str, tuple[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for r in rows:
            show, episode = places.get(r.claim_id, ("", ""))
            writer.writerow([r.claim_id, r.question, r.claim, r.quote, show, episode, "", "", "", ""])


@dataclass(frozen=True)
class Grade:
    r3: str
    r4: str
    answers: str


def read_grades(path: str | Path) -> dict[str, Grade]:
    grades: dict[str, Grade] = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            r3 = (row.get("r3_supported") or "").strip().lower()
            r4 = (row.get("r4_attribution") or "").strip().lower()
            ans = (row.get("answers_question") or "").strip().lower()
            if not (r3 or r4 or ans):
                continue
            if r3 not in R3_VALUES or r4 not in R4_VALUES or ans not in R3_VALUES:
                raise ConfigError(f"{path} row {number}: r3_supported and answers_question need yes, partly or no; "
                                  f"r4_attribution needs yes or no (got '{r3}', '{r4}', '{ans}').")
            grades[row["claim_id"]] = Grade(r3, r4, ans)
    return grades


@dataclass(frozen=True)
class Score:
    answers: int
    passed: int
    critical: int
    major: int
    incomplete: int
    claims: int
    r3_yes: int
    r4_yes: int
    answers_yes: int


def score(rows: Sequence[ClaimRow], grades: dict[str, Grade]) -> Score:
    groups: dict[tuple[str, str], list[ClaimRow]] = {}
    for r in rows:
        groups.setdefault((r.source, r.question_id), []).append(r)
    answers = passed = critical = major = incomplete = 0
    for group in groups.values():
        if not any(r.claim_id in grades for r in group):
            continue
        if any(r.claim_id not in grades for r in group):
            incomplete += 1
            continue
        got = [grades[r.claim_id] for r in group]
        answers += 1
        if any(g.r3 == "no" or g.r4 == "no" for g in got):
            critical += 1
        elif any(g.r3 == "partly" or g.answers == "no" for g in got):
            major += 1
        else:
            passed += 1
    graded = list(grades.values())
    return Score(answers, passed, critical, major, incomplete, len(graded),
                 sum(g.r3 == "yes" for g in graded), sum(g.r4 == "yes" for g in graded),
                 sum(g.answers == "yes" for g in graded))
