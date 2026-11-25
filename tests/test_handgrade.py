"""Week 4: the R3/R4 hand-grading sheet and its score."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from podcast_recall import golden, handgrade
from podcast_recall import judge_calibration as jc
from podcast_recall.errors import ConfigError
from tests.base import Base
from tests.test_answers import vid
from tests.test_diagnosis import item
from tests.test_judge_calibration import write_run


class HandGrade(Base):
    def setUp(self):
        super().setUp()
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.folder, True)
        items = [item("q1", golden.SINGLE_FACT, [golden.Evidence(vid(601), 5.0)]),
                 item("q2", golden.SINGLE_FACT, [golden.Evidence(vid(601), 9.0)])]
        run = write_run(self.folder, "20261124-0613", {"q1": [("c1", "a"), ("c2", "b")], "q2": [("c3", "c")]})
        self.rows = jc.collect_claims([run], items)

    def sheet(self, labels):
        path = self.folder / "s.csv"
        places = {r.claim_id: ("Show", "Title") for r in self.rows}
        handgrade.write_sheet(path, self.rows, places)
        with open(path, newline="") as handle:
            data = list(csv.DictReader(handle))
        for row in data:
            if row["claim_id"] in labels:
                row["r3_supported"], row["r4_attribution"], row["answers_question"] = labels[row["claim_id"]]
        with open(path, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=handgrade.COLUMNS)
            writer.writeheader()
            writer.writerows(data)
        return path

    def test_scores_passes_critical_major_and_incomplete(self):
        ids = [r.claim_id for r in self.rows]
        path = self.sheet({ids[0]: ("yes", "yes", "yes"), ids[1]: ("partly", "yes", "yes"), ids[2]: ("no", "yes", "yes")})
        result = handgrade.score(self.rows, handgrade.read_grades(path))
        self.assertEqual((result.answers, result.passed, result.major, result.critical), (2, 0, 1, 1))

    def test_answer_with_ungraded_claim_is_left_out(self):
        ids = [r.claim_id for r in self.rows]
        path = self.sheet({ids[0]: ("yes", "yes", "yes")})
        result = handgrade.score(self.rows, handgrade.read_grades(path))
        self.assertEqual((result.answers, result.incomplete), (0, 1))

    def test_bad_label_is_refused(self):
        path = self.sheet({self.rows[0].claim_id: ("partly", "partly", "yes")})
        with self.assertRaises(ConfigError):
            handgrade.read_grades(path)
