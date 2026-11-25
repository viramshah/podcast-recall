"""Week 4: calibrating the judge against a person's labels."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import tempfile
from pathlib import Path

from podcast_recall import golden
from podcast_recall import judge_calibration as jc
from podcast_recall.cli import main as cli_main
from podcast_recall.errors import ConfigError
from tests.base import Base
from tests.test_answers import FakeChat, vid
from tests.test_diagnosis import item


def write_run(folder: Path, stamp: str, question_claims: dict[str, list[tuple[str, str]]]) -> Path:
    path = folder / f"answers_dev_{stamp}.answers.jsonl"
    lines = []
    for qid, claims in question_claims.items():
        lines.append(json.dumps({"id": qid, "status": "answered", "claims": [
            {"text": text, "citations": [{"video_id": vid(601), "episode_id": 601, "show": "S", "title": "T", "quote": quote,
                                          "start_s": 5.0, "url": "u"}]} for text, quote in claims]}))
    path.write_text("\n".join(lines) + "\n")
    return path


class Calibration(Base):
    def setUp(self):
        super().setUp()
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.folder, True)
        self.items = [item("q1", golden.SINGLE_FACT, [golden.Evidence(vid(601), 5.0)]),
                      item("q2", golden.SINGLE_FACT, [golden.Evidence(vid(601), 9.0)])]
        self.run_a = write_run(self.folder, "20261123-0319", {
            "q1": [("c1", "quote one"), ("c2", "quote two")], "q2": [("c3", "quote three")]})
        self.run_b = write_run(self.folder, "20261123-0005", {"q1": [("c4", "quote four"), ("c5", "quote five")]})

    def test_claims_are_collected_with_stable_ids_and_the_question_text(self):
        rows = jc.collect_claims([self.run_a, self.run_b], self.items)
        self.assertEqual(sorted(r.claim_id for r in rows), [
            "20261123-0005:q1#1", "20261123-0005:q1#2", "20261123-0319:q1#1", "20261123-0319:q1#2", "20261123-0319:q2#1"])
        self.assertEqual(rows[0].question, "question q1?")

    def test_the_sample_is_deterministic_spread_over_runs_and_capped(self):
        rows = jc.collect_claims([self.run_a, self.run_b], self.items)
        a, b = jc.sample(rows, 4), jc.sample(rows, 4)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 4)
        self.assertEqual({r.source for r in a}, {"20261123-0319", "20261123-0005"})
        self.assertEqual(len(jc.sample(rows, 99)), 5)
        self.assertEqual(jc.sample([], 5), [])

    def test_the_sheet_hides_the_judge_and_has_empty_label_columns(self):
        rows = jc.collect_claims([self.run_a], self.items)
        path = self.folder / "sheet.csv"
        jc.write_sheet(path, rows)
        with open(path, newline="") as handle:
            written = list(csv.DictReader(handle))
        self.assertEqual(list(written[0]), jc.SHEET_COLUMNS)
        self.assertTrue(all(r["human_supported"] == "" and r["human_answers_question"] == "" for r in written))
        self.assertNotIn("judge", " ".join(jc.SHEET_COLUMNS))

    def fill(self, path, labels):
        with open(path, newline="") as handle:
            rows = list(csv.DictReader(handle))
        for r in rows:
            if r["claim_id"] in labels:
                r["human_supported"], r["human_answers_question"] = labels[r["claim_id"]]
        with open(path, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=jc.SHEET_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def test_only_filled_rows_are_read_and_bad_labels_are_refused(self):
        rows = jc.collect_claims([self.run_a], self.items)
        path = self.folder / "sheet.csv"
        jc.write_sheet(path, rows)
        self.fill(path, {"20261123-0319:q1#1": ("yes", "yes"), "20261123-0319:q1#2": ("no", "no")})
        self.assertEqual(jc.read_labels(path), {"20261123-0319:q1#1": ("yes", "yes"), "20261123-0319:q1#2": ("no", "no")})
        self.fill(path, {"20261123-0319:q2#1": ("maybe", "yes")})
        with self.assertRaises(ConfigError):
            jc.read_labels(path)

    def test_agreement_counts_both_kinds_of_disagreement_and_the_bar(self):
        human = {"a": ("yes", "yes"), "b": ("yes", "yes"), "c": ("no", "no"), "d": ("partly", "yes"), "e": ("no", "no")}
        machine = {"a": ("yes", "yes"), "b": ("yes", "no"), "c": ("no", "no"), "d": ("yes", "yes"), "e": ("no", "no")}
        report = jc.compare(human, machine)
        self.assertEqual((report.n, report.judge_too_strict, report.judge_too_lenient), (5, 1, 1))
        self.assertAlmostEqual(report.pass_agreement, 0.6)
        self.assertFalse(report.meets_bar)
        perfect = jc.compare(human, human)
        self.assertEqual((perfect.pass_agreement, perfect.kappa, perfect.meets_bar), (1.0, 1.0, True))
        self.assertEqual(jc.compare({}, {}).n, 0)
        self.assertIn("NOT met", jc.format_report(report))
        self.assertIn("Bar met", jc.format_report(perfect))

    def test_the_judge_is_asked_once_per_answer_in_claim_order(self):
        rows = jc.collect_claims([self.run_a], self.items)
        chat = FakeChat({"claims": [{"claim": 1, "supported": "yes", "answers_question": "yes"},
                                    {"claim": 2, "supported": "no", "answers_question": "no"}]})
        verdicts = jc.run_judge(chat, rows, {"20261123-0319:q1#1", "20261123-0319:q1#2"})
        self.assertEqual(verdicts, {"20261123-0319:q1#1": ("yes", "yes"), "20261123-0319:q1#2": ("no", "no")})
        self.assertEqual(len(chat.calls), 1)  # q2 had no labelled claim, so it was not asked about
        self.assertIn("[2] Claim: c2", chat.calls[0][1])

    def test_the_commands_write_a_sheet_and_report_agreement(self):
        gold = self.folder / "golden.csv"
        golden.write_golden(gold, self.items)
        library = self.folder / "library.csv"
        library.write_text("youtube_url\n" + f"https://www.youtube.com/watch?v={vid(601)}\n")
        sheet = self.folder / "sheet.csv"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli_main(["eval", "judge-sheet", "--golden", str(gold), "--library", str(library),
                             "--answers", str(self.run_a), "--count", "3", "--out", str(sheet)])
        self.assertEqual(code, 0)
        self.assertIn("3 claims in 1 run(s); 3 written", out.getvalue())
        with open(sheet, newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 3)

