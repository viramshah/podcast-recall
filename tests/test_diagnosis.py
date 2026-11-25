"""Week 4: explaining why golden questions failed, and the trace the answer run leaves behind."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from podcast_recall import core, diagnosis, golden
from podcast_recall.answering import AskResult
from podcast_recall.answers import Answer, Citation, Claim
from podcast_recall.cli import main as cli_main
from podcast_recall.verifier import Dropped
from tests.test_answers import AnswerBase, vid

E = golden.Evidence


def item(item_id, kind, evidence=(), split="dev"):
    return golden.GoldenItem(item_id, kind, f"question {item_id}?", "gold", (), tuple(evidence), "pm", split, (), "")


def not_found(item_id):
    return {"id": item_id, "status": "not_found", "claims": [], "summary": "I couldn't find that in your podcasts."}


def answered(item_id, episode_id=601, quote="A good pipeline has staging, review and a rollback plan."):
    return {"id": item_id, "status": "answered", "claims": [{"text": "c", "citations": [{
        "video_id": vid(episode_id), "episode_id": episode_id, "show": "Lenny's Podcast", "title": "T",
        "quote": quote, "start_s": 5.0, "url": f"https://youtu.be/{vid(episode_id)}?t=0"}]}]}


class Diagnosing(AnswerBase):
    def chunk_of(self, episode_id):
        return self.conn.execute(
            "SELECT chunk_id FROM chunks WHERE episode_id = ? ORDER BY start_s LIMIT 1", (episode_id,)
        ).fetchone()[0]

    def run_case(self, items, answers_by_id, traces):
        library = [vid(601), vid(602)]
        return core.diagnose_run(items, library, answers_by_id, traces, conn=self.conn)

    def causes(self, found):
        return {d.item_id: d.cause for d in found}

    def test_each_failing_question_gets_exactly_one_cause(self):
        items = [
            item("a_notshown", golden.SINGLE_FACT, [E(vid(601), 5.0)]),
            item("a_refused", golden.SINGLE_FACT, [E(vid(601), 5.0)]),
            item("a_emptied", golden.SINGLE_FACT, [E(vid(601), 5.0)]),
            item("a_nocheck", golden.SINGLE_FACT, [E(vid(601), 5.0)]),
            item("fp", golden.FALSE_PREMISE, [E(vid(601), 5.0)]),
            item("un", golden.UNANSWERABLE),
            item("ok", golden.UNANSWERABLE),
        ]
        answers = {i.id: not_found(i.id) for i in items}
        answers["un"] = answered("un")
        traces = {
            "a_notshown": {"id": "a_notshown", "chunk_ids": [self.chunk_of(602)], "dropped": []},
            "a_refused": {"id": "a_refused", "chunk_ids": [self.chunk_of(601)], "dropped": []},
            "a_emptied": {"id": "a_emptied", "chunk_ids": [self.chunk_of(601)],
                          "dropped": [{"claim": "x", "reason": "it pointed at a unit that does not exist"}]},
            "fp": {"id": "fp", "chunk_ids": [self.chunk_of(601)], "dropped": []},
            "un": {"id": "un", "chunk_ids": [self.chunk_of(601)], "dropped": []},
            "ok": {"id": "ok", "chunk_ids": [], "dropped": []},
        }
        grades, found = self.run_case(items, answers, traces)
        self.assertEqual(len(grades), 7)
        self.assertEqual(self.causes(found), {
            "a_notshown": diagnosis.NOT_SHOWN,
            "a_refused": diagnosis.MODEL_REFUSED,
            "a_emptied": diagnosis.VERIFIER_EMPTIED,
            "a_nocheck": diagnosis.NO_TRACE,
            "fp": diagnosis.PREMISE_MISSED,
            "un": diagnosis.INVENTED,
        })
        emptied = next(d for d in found if d.item_id == "a_emptied")
        self.assertIn("does not exist", emptied.detail)

    def test_a_passing_question_is_not_diagnosed(self):
        _g, found = self.run_case([item("ok", golden.UNANSWERABLE)], {"ok": not_found("ok")}, {})
        self.assertEqual(found, [])

    def test_only_questions_in_the_answers_file_are_graded(self):
        items = [item("a", golden.UNANSWERABLE), item("b", golden.UNANSWERABLE)]
        grades, _found = self.run_case(items, {"a": not_found("a")}, {})
        self.assertEqual([g.item_id for g in grades], ["a"])

    def test_the_report_counts_add_up_and_name_the_questions(self):
        found = [diagnosis.Diagnosis("q1", "single_fact", "not_found", diagnosis.NOT_SHOWN),
                 diagnosis.Diagnosis("q2", "single_fact", "not_found", diagnosis.NOT_SHOWN),
                 diagnosis.Diagnosis("q3", "synthesis", "not_found", diagnosis.MODEL_REFUSED)]
        text = diagnosis.format_diagnosis(found, 10)
        self.assertIn("Questions graded: 10; failing: 3", text)
        self.assertIn("2  gold_passage_not_shown", text)
        self.assertIn("q1, q2", text)
        self.assertIn("1  model_refused_with_gold_passage_shown", text)


class TraceAndCommand(AnswerBase):
    def test_the_trace_holds_the_shown_chunks_raw_reply_and_drops(self):
        cite = Citation(vid(601), 601, "S", "T", "q", 1.0, "u")
        result = AskResult(Answer("answered", (Claim("c", (cite,)),), ""), [Dropped("x", "R1: no")],
                           chunk_ids=[3, 4], model="m", latency_ms=1500, raw_reply={"status": "answered"})
        record = core.trace_record("p01", result)
        self.assertEqual(record["id"], "p01")
        self.assertEqual((record["chunk_ids"], record["raw_reply"], record["latency_ms"]), ([3, 4], {"status": "answered"}, 1500))
        self.assertEqual(record["dropped"], [{"claim": "x", "reason": "R1: no"}])
        json.dumps(record)  # must be writable as one JSON line

    def test_the_answer_path_keeps_the_raw_reply(self):
        from tests.test_answers import pointer_reply

        result = self.ask("What does a good pipeline have?", pointer_reply("staging"))
        self.assertEqual(result.raw_reply["status"], "answered")

    def test_the_command_reads_answers_and_trace_and_prints_causes(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        library = folder / "library.csv"
        library.write_text("youtube_url\n" + "".join(f"https://www.youtube.com/watch?v={vid(e)}\n" for e in (601, 602)))
        gold = folder / "golden.csv"
        golden.write_golden(gold, [item("a1", golden.SINGLE_FACT, [E(vid(601), 5.0)])])
        answers_file = folder / "run.answers.jsonl"
        answers_file.write_text(json.dumps(not_found("a1")) + "\n")
        (folder / "run.trace.jsonl").write_text(json.dumps({"id": "a1", "chunk_ids": [], "dropped": []}) + "\n")
        out_csv = folder / "causes.csv"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.run_cli_with_db(["eval", "diagnose", "--golden", str(gold), "--library", str(library),
                                         "--answers", str(answers_file), "--out", str(out_csv)])
        self.assertEqual(code, 0)
        self.assertIn("1  gold_passage_not_shown", out.getvalue())
        self.assertIn("a1,single_fact,not_found,gold_passage_not_shown", out_csv.read_text())

    def run_cli_with_db(self, argv):
        from unittest import mock

        with mock.patch("podcast_recall.core.open_db", lambda: _Keep(self.conn)):
            return cli_main(argv)


class _Keep:
    """A connection wrapper whose close() does nothing, so the test database stays open."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


class ChoosingQuestions(AnswerBase):
    def setUp(self):
        super().setUp()
        self.items = [item("a", golden.SINGLE_FACT, split="dev"), item("b", golden.SINGLE_FACT, split="dev"),
                      item("c", golden.SINGLE_FACT, split="heldout")]

    def test_a_split_a_limit_and_ids(self):
        ids = lambda chosen: [i.id for i in chosen]
        self.assertEqual(ids(core.choose_items(self.items, "dev")), ["a", "b"])
        self.assertEqual(ids(core.choose_items(self.items, "dev", limit=1)), ["a"])
        self.assertEqual(ids(core.choose_items(self.items, "dev", ids=["b", "a"])), ["a", "b"])
        self.assertEqual(ids(core.choose_items(self.items, "dev", ids=["c"])), ["c"])  # an explicit id wins

    def test_an_unknown_id_is_refused(self):
        from podcast_recall.errors import ConfigError

        with self.assertRaises(ConfigError):
            core.choose_items(self.items, "dev", ids=["zzz"])


class AbstentionScan(AnswerBase):
    def test_sweep_finds_the_threshold_that_separates_the_two_groups(self):
        from podcast_recall import abstention as ab

        rows = [ab.Row("a1", golden.SINGLE_FACT, 0.30, 4), ab.Row("a2", golden.WHO_WHEN, 0.34, 4),
                ab.Row("f1", golden.FALSE_PREMISE, 0.36, 4),
                ab.Row("u1", golden.UNANSWERABLE, 0.42, 4), ab.Row("n1", golden.NOT_IN_LIBRARY, 0.45, 4)]
        points = ab.sweep(rows)
        best = ab.best_points(points)
        self.assertEqual([(p.threshold, p.wrongly_abstained, p.wrongly_answered) for p in best], [(0.36, 0, 0)])
        text = ab.format_scan(rows)
        self.assertIn("Questions that should be answered: 3; that should say 'not found': 2", text)
        self.assertIn("Fewest errors (0)", text)

    def test_overlapping_groups_show_errors_on_both_sides(self):
        from podcast_recall import abstention as ab

        rows = [ab.Row("a", golden.SINGLE_FACT, 0.40, 4), ab.Row("u", golden.UNANSWERABLE, 0.38, 4)]
        low, high = ab.sweep(rows)
        self.assertEqual((low.wrongly_abstained, low.wrongly_answered), (1, 1))  # 0.38: both sides wrong
        self.assertEqual((high.wrongly_abstained, high.wrongly_answered), (0, 1))  # 0.40: unanswerable below it

    def test_a_question_with_no_hits_always_abstains(self):
        from podcast_recall import abstention as ab

        rows = [ab.Row("a", golden.SINGLE_FACT, None, 0), ab.Row("b", golden.SINGLE_FACT, 0.3, 4)]
        self.assertEqual(ab.sweep(rows)[0].wrongly_abstained, 1)

    def test_the_scan_searches_each_question_and_records_the_best_distance(self):
        items = [item("a", golden.SINGLE_FACT, [E(vid(601), 5.0)]), item("u", golden.UNANSWERABLE)]
        rows = core.abstention_scan(items, [vid(601), vid(602)], split="dev", passages=4,
                                    services=self.services().index, conn=self.conn)
        self.assertEqual([r.item_id for r in rows], ["a", "u"])
        self.assertTrue(all(r.hits >= 0 for r in rows))
