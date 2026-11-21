"""Week 2: the answer format, the golden set, the deterministic checkers, the harness and kappa.

No model and no network. A small world of episodes with real-looking transcripts stands in for the
seed library; an oracle and a fabricator prove the harness scores right and wrong answers correctly.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from podcast_recall import (
    agreement,
    answers,
    checkers,
    core,
    evalrun,
    golden,
    golden_check,
    indexer,
    oracle,
    paths,
    store,
)
from podcast_recall.answers import AnswerFormatError, Citation, Claim
from podcast_recall.checkers import CRITICAL, MAJOR
from podcast_recall.cli import main as cli_main
from podcast_recall.errors import ConfigError
from podcast_recall.golden import Evidence, GoldenItem
from tests.base import T0, Base
from tests.test_index import BREAD, KUBE, RUN, FakeEmbedder, World

QUOTE = "A good pipeline has staging, review and a rollback plan."

ASTRO = [
    "The telescope mirror must be polished to within a fraction of a wavelength.",
    "Astronomers wait for clear nights on a high dry mountain.",
    "Faint galaxies need hours of exposure to show their spiral arms.",
]
CHESS = [
    "Opening theory matters less than understanding pawn structure.",
    "Strong players calculate forcing lines before quiet moves.",
    "Endgames are won by king activity and patience.",
]
JAZZ = [
    "A walking bass line outlines the harmony beneath the soloist.",
    "Swing feel comes from the lilt between the eighth notes.",
    "Improvisation is conversation between the players on stage.",
]


def vid(episode_id: int) -> str:
    return f"vid{episode_id:08d}"


def item(item_id, kind, question="A question?", evidence=(), gold_answer="", split="dev", tags=(), author="pm"):
    if kind in golden.ANSWERABLE_TYPES and not gold_answer:
        gold_answer = "The gold answer."
    return GoldenItem(item_id, kind, question, gold_answer, (), tuple(evidence), author, split, tuple(tags), "")


def citation(episode_id=301, quote=QUOTE, start_s=5.0, video_id=None):
    return Citation(video_id or vid(episode_id), episode_id, "Show", "Title", quote, start_s, "")


def answer(status="answered", *claims):
    return answers.Answer(status, tuple(claims), "")


class EvalBase(Base):
    """Six episodes. 301 to 305 form the evaluation library; 306 is indexed but held back."""

    def setUp(self):
        super().setUp()
        self.world = World(self.conn)
        for episode_id, title, sentences in (
            (301, "Shipping with Kubernetes", KUBE), (302, "Bread Basics", BREAD),
            (303, "Running a Marathon", RUN), (304, "Telescopes", ASTRO), (305, "Chess", CHESS),
            (306, "Jazz (not in the library)", JAZZ),
        ):
            self.world.add_episode(episode_id, 1, title, "2026-10-01T10:00:00", sentences)
        self.library = [vid(e) for e in (301, 302, 303, 304, 305)]
        self.ctx = evalrun.build_context(self.conn, self.library)

    def write_files(self, items):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        golden_path = folder / "golden.csv"
        golden.write_golden(golden_path, items)
        library_path = folder / "library.csv"
        library_path.write_text(
            "youtube_url\n" + "".join(f"https://www.youtube.com/watch?v={v}\n" for v in self.library),
            encoding="utf-8",
        )
        return folder, golden_path, library_path


def sample_items():
    return [
        item("q01", golden.SINGLE_FACT, "What does a good pipeline have?", [Evidence(vid(301), 5.0)]),
        item("q02", golden.WHO_WHEN, "When is bread discussed?", [Evidence(vid(302), 0.0)], split="heldout"),
        item("q03", golden.SYNTHESIS, "What do the shows say about mornings?",
             [Evidence(vid(301), 0.0), Evidence(vid(302), 0.0)], tags=("raj",)),
        item("q04", golden.UNANSWERABLE, "What is the capital of Atlantis?"),
        item("q05", golden.FALSE_PREMISE, "Why did the guest say bread is poison?"),
        item("q06", golden.NOT_IN_LIBRARY, "How does a walking bass line work?", [Evidence(vid(306), 0.0)],
             gold_answer="Not in your library."),
    ]


# ---------------------------------------------------------------------------- the answer format


class AnswerFormat(Base):
    def good(self):
        return {
            "status": "answered",
            "claims": [{"text": "A claim.", "citations": [{
                "video_id": "abcdefghijk", "episode_id": 7, "show": "S", "title": "T",
                "quote": QUOTE, "start_s": 12.5, "url": "u"}]}],
            "summary": "s",
        }

    def test_a_good_answer_parses_and_round_trips(self):
        parsed = answers.parse_answer(self.good())
        self.assertEqual(parsed.status, "answered")
        self.assertEqual(parsed.claims[0].citations[0].start_s, 12.5)
        self.assertEqual(answers.answer_to_dict(parsed)["claims"][0]["citations"][0]["quote"], QUOTE)

    def test_structural_problems_are_clear_errors(self):
        def broken(change):
            data = self.good()
            change(data)
            return data

        cases = {
            "bad status": broken(lambda d: d.update(status="maybe")),
            "claims not a list": broken(lambda d: d.update(claims="x")),
            "claim not an object": broken(lambda d: d.update(claims=["x"])),
            "citation not an object": broken(lambda d: d["claims"][0].update(citations=["x"])),
            "episode id is text": broken(lambda d: d["claims"][0]["citations"][0].update(episode_id="7")),
            "episode id is a bool": broken(lambda d: d["claims"][0]["citations"][0].update(episode_id=True)),
            "negative time": broken(lambda d: d["claims"][0]["citations"][0].update(start_s=-1)),
            "time is text": broken(lambda d: d["claims"][0]["citations"][0].update(start_s="5")),
            "empty quote": broken(lambda d: d["claims"][0]["citations"][0].update(quote=" ")),
            "no video id": broken(lambda d: d["claims"][0]["citations"][0].pop("video_id")),
            "claim without text": broken(lambda d: d["claims"][0].update(text="")),
            "summary not text": broken(lambda d: d.update(summary=3)),
        }
        for name, data in cases.items():
            with self.assertRaises(AnswerFormatError, msg=name):
                answers.parse_answer(data)
        with self.assertRaises(AnswerFormatError):
            answers.parse_answer([1, 2])

    def test_a_quote_may_be_at_most_sixty_words_even_without_any_punctuation(self):
        data = self.good()
        data["claims"][0]["citations"][0]["quote"] = " ".join(["word"] * 61)
        with self.assertRaises(AnswerFormatError) as caught:
            answers.parse_answer(data)
        self.assertIn("60 words", str(caught.exception))
        data["claims"][0]["citations"][0]["quote"] = " ".join(["word"] * 60)
        self.assertEqual(len(answers.parse_answer(data).claims), 1)

    def test_a_quote_may_be_at_most_two_sentences(self):
        data = self.good()
        data["claims"][0]["citations"][0]["quote"] = "One. Two. Three."
        with self.assertRaises(AnswerFormatError):
            answers.parse_answer(data)
        data["claims"][0]["citations"][0]["quote"] = "One sentence here. And another here!"
        self.assertEqual(len(answers.parse_answer(data).claims), 1)

    def test_a_not_found_answer_needs_no_claims(self):
        parsed = answers.parse_answer({"status": "not_found"})
        self.assertEqual((parsed.status, parsed.claims), ("not_found", ()))

    def test_the_link_opens_ten_seconds_early_and_never_before_zero(self):
        self.assertEqual(answers.link_for("abcdefghijk", 100.9), "https://youtu.be/abcdefghijk?t=90")
        self.assertEqual(answers.link_for("abcdefghijk", 4), "https://youtu.be/abcdefghijk?t=0")

    def test_reading_an_answers_file(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        good = folder / "a.jsonl"
        good.write_text(json.dumps({"id": "q1", "status": "not_found"}) + "\n\n"
                        + json.dumps({"id": "q2", "status": "not_found"}) + "\n", encoding="utf-8")
        self.assertEqual(set(answers.load_answers(good)), {"q1", "q2"})
        for name, text in (("bad.jsonl", "not json\n"), ("noid.jsonl", '{"status": "answered"}\n'),
                           ("dup.jsonl", '{"id": "a"}\n{"id": "a"}\n')):
            (folder / name).write_text(text, encoding="utf-8")
            with self.assertRaises(ConfigError, msg=name):
                answers.load_answers(folder / name)


# ---------------------------------------------------------------------------- matching text


class TextMatching(EvalBase):
    def test_normalising_ignores_case_punctuation_and_curly_quotes(self):
        self.assertEqual(checkers.normalize("It’s SO hard -- to build, anything!"),
                         ["it's", "so", "hard", "to", "build", "anything"])

    def test_similarity_on_word_runs(self):
        text = checkers.normalize("Before this. A good pipeline has staging, review and a rollback plan. After that.")
        quote = checkers.normalize(QUOTE)
        self.assertEqual(checkers.best_similarity(quote, text), 1.0)
        # one wrong word in the middle: 9 of 10 words match, exactly the threshold, so it passes
        one_wrong = checkers.normalize("A good pipeline has staging, checking and a rollback plan.")
        self.assertAlmostEqual(checkers.best_similarity(one_wrong, text), 0.9, places=6)
        self.assertGreaterEqual(checkers.best_similarity(one_wrong, text), checkers.MATCH_THRESHOLD)
        two_wrong = checkers.normalize("A great pipeline has staging, checking and a rollback plan.")
        self.assertAlmostEqual(checkers.best_similarity(two_wrong, text), 0.8, places=6)
        self.assertLess(checkers.best_similarity(two_wrong, text), checkers.MATCH_THRESHOLD)
        # a changed last word reads as a quote that stops one word early, which is still a real quote
        end_wrong = checkers.normalize("A good pipeline has staging, review and a rollback scheme.")
        self.assertGreater(checkers.best_similarity(end_wrong, text), 0.9)
        self.assertEqual(checkers.best_similarity(checkers.normalize("cats and dogs and mice"), text) < 0.5, True)

    def test_empty_inputs_score_zero(self):
        self.assertEqual(checkers.best_similarity([], ["a"]), 0.0)
        self.assertEqual(checkers.best_similarity(["a"], []), 0.0)

    def test_the_window_holds_only_segments_near_the_cited_time(self):
        transcript = self.ctx.transcript_for(301)
        near = checkers.window_tokens(transcript, 5.0)
        self.assertIn("pipeline", near)
        far = checkers.window_tokens(transcript, 600.0)
        self.assertEqual(far, [])


# ---------------------------------------------------------------------------- R1


class CheckR1(EvalBase):
    def test_a_real_quote_at_the_right_time_passes(self):
        self.assertIsNone(checkers.check_r1(citation(), self.ctx))

    def test_a_small_timing_error_still_passes(self):
        self.assertIsNone(checkers.check_r1(citation(start_s=14.0), self.ctx))  # within 15 s

    def test_a_quote_cited_far_from_where_it_was_said_fails(self):
        failure = checkers.check_r1(citation(start_s=400.0), self.ctx)
        self.assertEqual((failure.rule, failure.severity), ("R1", CRITICAL))
        self.assertIn("no words within", failure.reason)

    def test_an_invented_quote_fails_with_the_score_in_the_reason(self):
        failure = checkers.check_r1(citation(quote=oracle.INVENTED), self.ctx)
        self.assertEqual(failure.severity, CRITICAL)
        self.assertIn("needs 0.90", failure.reason)

    def test_a_real_quote_from_another_episode_fails(self):
        failure = checkers.check_r1(citation(episode_id=301, quote="Flour and water and patience make the best bread."),
                                    self.ctx)
        self.assertIsNotNone(failure)

    def test_a_missing_transcript_and_an_empty_quote_fail(self):
        self.assertIn("no transcript", checkers.check_r1(citation(episode_id=999), self.ctx).reason)
        self.assertIn("empty", checkers.check_r1(citation(quote="..."), self.ctx).reason)

    def test_a_quote_split_across_two_segments_passes(self):
        both = "Today we talk about the kubernetes deployment pipeline for our team. A good pipeline has staging,"
        self.assertIsNone(checkers.check_r1(citation(quote=both, start_s=0.0), self.ctx))

    def test_an_uncited_claim_fails_r1(self):
        failures = checkers.check_claims_cited(answer("answered", Claim("No source", ()), Claim("Has one", (citation(),))))
        self.assertEqual([f.reason for f in failures], ["claim 1 has no citation"])


# ---------------------------------------------------------------------------- R2


class CheckR2(EvalBase):
    def test_a_library_episode_passes(self):
        self.assertIsNone(checkers.check_r2(citation(), self.ctx))

    def test_an_episode_outside_the_library_fails(self):
        failure = checkers.check_r2(citation(episode_id=306), self.ctx)
        self.assertEqual((failure.rule, failure.severity), ("R2", CRITICAL))
        self.assertIn("not in the library", failure.reason)

    def test_a_video_that_belongs_to_another_episode_fails(self):
        failure = checkers.check_r2(citation(episode_id=301, video_id=vid(302)), self.ctx)
        self.assertIn("belongs to episode", failure.reason)

    def test_an_unknown_video_id_is_judged_on_the_episode_alone(self):
        self.assertIsNone(checkers.check_r2(citation(video_id="zzzzzzzzzzz"), self.ctx))


# ---------------------------------------------------------------------------- R5


class CheckR5(EvalBase):
    def run_r5(self, kind, status, claims=()):
        return checkers.check_r5(answer(status, *claims), item("x", kind, evidence=[Evidence(vid(301), 0)]
                                                              if kind in golden.ANSWERABLE_TYPES or kind == golden.NOT_IN_LIBRARY else []))

    def test_each_question_type_needs_its_own_status(self):
        self.assertEqual({k: checkers.expected_status(item("x", k, evidence=[Evidence(vid(301), 0), Evidence(vid(302), 0)]))
                          for k in golden.TYPES},
                         {"single_fact": "answered", "synthesis": "answered", "who_when": "answered",
                          "unanswerable": "not_found", "false_premise": "premise_corrected",
                          "not_in_library": "not_found"})

    def test_correct_statuses_pass(self):
        cite = Claim("c", (citation(),))
        for kind, status, claims in ((golden.SINGLE_FACT, "answered", (cite,)),
                                     (golden.UNANSWERABLE, "not_found", ()),
                                     (golden.NOT_IN_LIBRARY, "not_found", ()),
                                     (golden.FALSE_PREMISE, "premise_corrected", ())):
            failure, _review = self.run_r5(kind, status, claims)
            self.assertIsNone(failure, msg=kind)

    def test_inventing_an_answer_is_critical(self):
        cite = (Claim("invented", (citation(),)),)
        for kind in (golden.UNANSWERABLE, golden.FALSE_PREMISE, golden.NOT_IN_LIBRARY):
            failure, _ = self.run_r5(kind, "answered", cite)
            self.assertEqual((failure.rule, failure.severity), ("R5", CRITICAL), msg=kind)

    def test_refusing_an_answerable_question_is_major(self):
        for status in ("not_found", "premise_corrected"):
            failure, _ = self.run_r5(golden.SINGLE_FACT, status)
            self.assertEqual(failure.severity, MAJOR)
            self.assertIn("refused", failure.reason)

    def test_not_found_with_claims_is_inconsistent(self):
        failure, _ = self.run_r5(golden.UNANSWERABLE, "not_found", (Claim("c", (citation(),)),))
        self.assertEqual(failure.severity, MAJOR)

    def test_a_wrong_non_answer_status_is_major(self):
        failure, _ = self.run_r5(golden.FALSE_PREMISE, "not_found")
        self.assertEqual(failure.severity, MAJOR)
        failure, _ = self.run_r5(golden.UNANSWERABLE, "premise_corrected")
        self.assertEqual(failure.severity, MAJOR)

    def test_every_false_premise_answer_is_flagged_for_a_person(self):
        _failure, review = self.run_r5(golden.FALSE_PREMISE, "premise_corrected")
        self.assertTrue(review)
        _failure, review = self.run_r5(golden.UNANSWERABLE, "not_found")
        self.assertFalse(review)


# ---------------------------------------------------------------------------- R7 and episode coverage


class CheckR7(EvalBase):
    def test_timing_is_checked_against_the_gold_time(self):
        gold = item("x", golden.SINGLE_FACT, evidence=[Evidence(vid(301), 100.0)])
        near = answer("answered", Claim("c", (citation(start_s=114.0),)))
        far = answer("answered", Claim("c", (citation(start_s=116.0),)))
        self.assertIsNone(checkers.check_r7(near, gold))
        self.assertIn("16 s", checkers.check_r7(far, gold).reason)

    def test_the_best_of_several_citations_counts(self):
        gold = item("x", golden.WHO_WHEN, evidence=[Evidence(vid(301), 100.0)])
        multi = answer("answered", Claim("c", (citation(start_s=900.0), citation(start_s=95.0))))
        self.assertIsNone(checkers.check_r7(multi, gold))

    def test_citing_another_episode_fails_r7(self):
        gold = item("x", golden.SINGLE_FACT, evidence=[Evidence(vid(301), 100.0)])
        wrong = answer("answered", Claim("c", (citation(episode_id=302, start_s=100.0),)))
        self.assertIn("no citation to the gold episode", checkers.check_r7(wrong, gold).reason)

    def test_r7_does_not_apply_to_other_types(self):
        for kind in (golden.UNANSWERABLE, golden.FALSE_PREMISE):
            self.assertIsNone(checkers.check_r7(answer("not_found"), item("x", kind)))
        synthesis = item("x", golden.SYNTHESIS, evidence=[Evidence(vid(301), 0), Evidence(vid(302), 0)])
        self.assertIsNone(checkers.check_r7(answer("answered"), synthesis))

    def test_synthesis_is_scored_by_the_share_of_gold_episodes_cited(self):
        gold = item("x", golden.SYNTHESIS, evidence=[Evidence(vid(301), 0), Evidence(vid(302), 0)])
        half = answer("answered", Claim("c", (citation(episode_id=301),)))
        both = answer("answered", Claim("c", (citation(episode_id=301), citation(episode_id=302))))
        self.assertEqual(checkers.episode_recall(half, gold, self.ctx), 0.5)
        self.assertEqual(checkers.episode_recall(both, gold, self.ctx), 1.0)
        single = item("y", golden.SINGLE_FACT, evidence=[Evidence(vid(301), 0)])
        self.assertIsNone(checkers.episode_recall(both, single, self.ctx))


# ---------------------------------------------------------------------------- the golden file


class GoldenFile(Base):
    HEADER = "id,type,question,gold_answer,key_points,gold_evidence,author,split,tags,notes\n"

    def write(self, text):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        path = folder / "g.csv"
        path.write_text(self.HEADER + text, encoding="utf-8")
        return path

    def test_a_good_file_round_trips(self):
        path = self.write(
            "q1,single_fact,What?,An answer.,a; b,abcdefghijk@12:30,pm,dev,raj; x,note\n"
            "q2,unanswerable,Why?,,,,claude,heldout,,\n"
            "q3,synthesis,How?,An answer.,,abcdefghijk@1:02:03; bcdefghijkl@45,claude,dev,,\n"
        )
        items = golden.load_golden(path)
        self.assertEqual(items[0].evidence, (Evidence("abcdefghijk", 750.0),))
        self.assertEqual(items[0].key_points, ("a", "b"))
        self.assertEqual(items[0].tags, ("raj", "x"))
        self.assertEqual(items[2].evidence[0].start_s, 3723.0)
        self.assertEqual(items[2].evidence[1].start_s, 45.0)
        out = path.with_name("out.csv")
        golden.write_golden(out, items)
        self.assertEqual(golden.load_golden(out), items)

    def test_every_problem_is_listed_with_its_row(self):
        path = self.write(
            "q1,bogus,What?,A,,abcdefghijk@1:00,pm,dev,,\n"
            "q1,single_fact,,A,,abcdefghijk@1:00,pm,dev,,\n"
            "q3,single_fact,What?,,,,pm,maybe,,\n"
            "q4,synthesis,What?,A,,abcdefghijk@1:00,pm,dev,,\n"
            "q5,unanswerable,What?,,,abcdefghijk@1:00,pm,dev,,\n"
            "q6,not_in_library,What?,,,,pm,dev,,\n"
            "q7,single_fact,What?,A,,not-evidence,pm,dev,,\n"
            "q8,single_fact,What?,A,,abcdefghijk@1:00; bcdefghijkl@2:00,pm,dev,,\n"
            "q9,single_fact,What?,A,,abcdefghijk@1:00,,dev,,\n"
        )
        with self.assertRaises(golden.GoldenError) as caught:
            golden.load_golden(path)
        message = str(caught.exception)
        for fragment in ("row 2 (q1): type 'bogus'", "the id appears twice", "the question is empty",
                         "split 'maybe'", "needs a gold_answer", "needs gold_evidence", "at least 2 episodes",
                         "must have no gold_evidence", "not video_id@mm:ss", "exactly one piece of evidence",
                         "author is empty", "needs gold_evidence (the episode that is outside the library)"):
            self.assertIn(fragment, message)

    def test_a_missing_column_is_reported(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        path = folder / "g.csv"
        path.write_text("id,question\nq1,What?\n", encoding="utf-8")
        with self.assertRaises(golden.GoldenError) as caught:
            golden.load_golden(path)
        self.assertIn("missing these columns", str(caught.exception))

    def test_times_can_be_written_three_ways(self):
        self.assertEqual(golden.parse_time("34:12"), 2052.0)
        self.assertEqual(golden.parse_time("1:02:03"), 3723.0)
        self.assertEqual(golden.parse_time("90"), 90.0)
        self.assertEqual(golden.format_time(3723), "1:02:03")
        self.assertEqual(golden.format_time(75), "1:15")

    def test_the_v0_mix_adds_up_to_sixty(self):
        self.assertEqual(sum(golden.V0_MIX.values()), 60)

    def test_counts_by_type_and_split(self):
        counts = golden.split_counts(sample_items())
        self.assertEqual(counts["split"], {"dev": 5, "heldout": 1})
        self.assertEqual(counts["type"]["single_fact"], 1)

    def test_the_library_file(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        good = folder / "lib.csv"
        good.write_text("youtube_url\nhttps://www.youtube.com/watch?v=abcdefghijk\n", encoding="utf-8")
        self.assertEqual(golden.load_library(good), ["abcdefghijk"])
        bad = folder / "bad.csv"
        bad.write_text("youtube_url\nnot a video\n", encoding="utf-8")
        with self.assertRaises(ConfigError):
            golden.load_library(bad)
        empty = folder / "empty.csv"
        empty.write_text("youtube_url\n", encoding="utf-8")
        with self.assertRaises(ConfigError):
            golden.load_library(empty)


# ---------------------------------------------------------------------------- the harness


class Harness(EvalBase):
    def grade(self, **kwargs):
        return {g.item_id: g for g in core.run_eval(sample_items(), self.library, conn=self.conn, **kwargs)}

    def test_the_oracle_scores_every_question_right(self):
        grades = self.grade(use_oracle=True)
        self.assertEqual(len(grades), 6)
        for g in grades.values():
            self.assertTrue(g.passed, msg=(g.item_id, [f.reason for f in g.failures]))
        summary = evalrun.summarize(list(grades.values()))
        self.assertEqual((summary["accuracy"], summary["hallucination_rate"]), (1.0, 0.0))
        self.assertEqual(summary["r7_applicable"], 2)
        self.assertEqual(summary["r7_passed"], 2)
        self.assertEqual(summary["episode_recall_mean"], 1.0)
        self.assertEqual(summary["needs_review"], 1)  # the false-premise answer

    def test_an_invented_quote_fails_r1_on_every_answerable_question(self):
        grades = self.grade(fabricate="invented_quote")
        for item_id in ("q01", "q02", "q03"):
            self.assertIn("R1", grades[item_id].rules_failed)
            self.assertTrue(grades[item_id].critical)
        for item_id in ("q04", "q05", "q06"):
            self.assertTrue(grades[item_id].passed)  # nothing to fabricate for these

    def test_citing_outside_the_library_fails_r2(self):
        grades = self.grade(fabricate="outside_library")
        for item_id in ("q01", "q02", "q03"):
            self.assertIn("R2", grades[item_id].rules_failed)
            self.assertTrue(grades[item_id].critical)

    def test_a_wrong_time_fails_r1_and_r7(self):
        grades = self.grade(fabricate="wrong_time")
        for item_id in ("q01", "q02"):
            self.assertIn("R1", grades[item_id].rules_failed)
            self.assertIs(grades[item_id].r7, False)

    def test_inventing_an_answer_fails_r5_on_the_unanswerable_types_only(self):
        grades = self.grade(fabricate="invents_answer")
        for item_id in ("q04", "q05", "q06"):
            self.assertIn("R5", grades[item_id].rules_failed)
            self.assertTrue(grades[item_id].critical)
        for item_id in ("q01", "q02", "q03"):
            self.assertTrue(grades[item_id].passed)

    def test_an_uncited_claim_fails(self):
        grades = self.grade(fabricate="uncited_claim")
        for item_id in ("q01", "q02", "q03"):
            self.assertIn("R1", grades[item_id].rules_failed)

    def test_refusing_everything_fails_the_answerable_questions_as_major(self):
        grades = self.grade(fabricate="refuses")
        for item_id in ("q01", "q02", "q03"):
            self.assertFalse(grades[item_id].passed)
            self.assertFalse(grades[item_id].critical)  # Major, not Critical
        for item_id in ("q04", "q06"):
            self.assertTrue(grades[item_id].passed)
        self.assertFalse(grades["q05"].passed)  # a false premise must be corrected, not just refused

    def test_unknown_fabrication_mode_is_an_error(self):
        with self.assertRaises(ConfigError):
            self.grade(fabricate="nonsense")

    def test_a_missing_or_malformed_answer_fails_the_question(self):
        good = oracle.answers_for(sample_items(), self.ctx, oracle=True)
        del good["q01"]
        good["q02"] = {"id": "q02", "status": "weird"}
        grades = {g.item_id: g for g in evalrun.grade_all(sample_items(), good, self.ctx)}
        self.assertEqual(grades["q01"].failures[0].reason, "no answer was given")
        self.assertEqual(grades["q02"].failures[0].rule, "format")
        self.assertFalse(grades["q01"].critical)

    def test_splits_and_tags_are_reported_separately(self):
        grades = list(self.grade(use_oracle=True).values())
        summary = evalrun.summarize(grades)
        self.assertEqual(summary["by_split"], {"dev": {"n": 5, "passed": 5}, "heldout": {"n": 1, "passed": 1}})
        self.assertEqual(summary["by_tag"], {"raj": {"n": 1, "passed": 1}})
        only_heldout = evalrun.grade_all(sample_items(), oracle.answers_for(sample_items(), self.ctx, oracle=True),
                                         self.ctx, "heldout")
        self.assertEqual([g.item_id for g in only_heldout], ["q02"])

    def test_the_summary_says_the_judge_rules_have_not_run(self):
        text = evalrun.format_summary(evalrun.summarize(list(self.grade(use_oracle=True).values())))
        self.assertIn("R3, R4 and R6 are not run", text)
        self.assertIn("Grounded accuracy", text)

    def test_the_scorecard_file(self):
        grades = list(self.grade(fabricate="invented_quote").values())
        out = Path(tempfile.mkdtemp()) / "sub" / "card.csv"
        self.addCleanup(__import__("shutil").rmtree, out.parent.parent, True)
        evalrun.write_scorecard(out, grades)
        rows = out.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 7)
        self.assertIn("R1", rows[1])
        self.assertIn("claim 1, citation 1", rows[1])

    def test_a_reasonable_quote_with_one_changed_word_still_passes_the_matching(self):
        # 14 of 15 words match: similarity 0.93, above 0.90
        cited = citation(quote="Today we talk about the kubernetes deployment pipeline for our crew.", start_s=0.0)
        self.assertIsNone(checkers.check_r1(cited, self.ctx))

    def test_the_oracle_stays_short_on_a_transcript_with_no_punctuation(self):
        """Regression: publisher transcripts can have no sentence ends, and the oracle once built a quote
        of thousands of words from the rest of the episode."""
        run_on = [f"and then we talked about topic number {i} for a while and kept going without stopping" for i in range(80)]
        self.world.add_episode(307, 1, "No punctuation", "2026-10-02T10:00:00", run_on)
        ctx = evalrun.build_context(self.conn, [*self.library, vid(307)])
        quote, start = oracle.real_quote(ctx, 307, 200.0)
        self.assertLessEqual(len(quote.split()), answers.MAX_QUOTE_WORDS)
        self.assertEqual(start, 200.0)
        self.assertIsNone(checkers.check_r1(citation(episode_id=307, quote=quote, start_s=start, video_id=vid(307)), ctx))
        gold = item("long", golden.SINGLE_FACT, "What was said?", [Evidence(vid(307), 200.0)])
        grade = evalrun.grade_all([gold], oracle.answers_for([gold], ctx, oracle=True), ctx)[0]
        self.assertTrue(grade.passed, [f.reason for f in grade.failures])

    def test_the_oracle_quote_is_real_and_at_most_two_sentences(self):
        for evidence in (Evidence(vid(301), 5.0), Evidence(vid(304), 0.0), Evidence(vid(305), 6.0)):
            quote, start = oracle.real_quote(self.ctx, self.ctx.video_to_episode[evidence.video_id], evidence.start_s)
            self.assertLessEqual(answers.sentence_count(quote), 2)
            self.assertIsNone(checkers.check_r1(
                citation(episode_id=self.ctx.video_to_episode[evidence.video_id], quote=quote, start_s=start),
                self.ctx))


# ---------------------------------------------------------------------------- retrieval on the golden set


class RetrievalOnGolden(EvalBase):
    def setUp(self):
        super().setUp()
        self.embedder = FakeEmbedder()
        indexer.build_index(self.conn, indexer.IndexServices(embedder=self.embedder), now=self.now)
        self.services = indexer.IndexServices(embedder=self.embedder)

    def items(self):
        return [
            item("r1", golden.SINGLE_FACT, "What do astronomers wait for on a mountain?", [Evidence(vid(304), 5.0)]),
            item("r2", golden.WHO_WHEN, "Where does swing feel come from?", [Evidence(vid(306), 5.0)]),
            item("r3", golden.SYNTHESIS, "What do shows say about pipelines and chess endgames?",
                 [Evidence(vid(301), 0.0), Evidence(vid(305), 0.0)]),
            item("r4", golden.UNANSWERABLE, "What is the capital of Atlantis?"),
        ]

    def test_hits_are_scored_against_the_gold_time(self):
        outcomes = {o.item_id: o for o in core.eval_retrieval(
            self.items(), self.library, services=self.services, conn=self.conn)}
        self.assertEqual(outcomes["r1"].rank, 1)
        self.assertIsNone(outcomes["r2"].rank)  # the jazz episode is outside the library, so it cannot be found
        self.assertFalse(any(o.leaked for o in outcomes.values()))
        self.assertEqual(outcomes["r3"].episode_recall, 1.0)
        summary = evalrun.retrieval_summary(list(outcomes.values()))
        self.assertEqual(summary["timed_n"], 2)
        self.assertEqual(summary["recall_at_5"], 0.5)
        self.assertEqual(summary["misses"], ["r2"])
        self.assertEqual(summary["leaks"], 0)
        self.assertEqual(summary["synthesis_episode_recall"], 1.0)

    def test_a_result_from_outside_the_library_is_flagged_as_a_leak(self):
        from podcast_recall import retrieval

        def leaky(question):
            hits = retrieval.find(self.conn, self.embedder, question, "owner", video_ids=[vid(306)], limit=3).hits
            return hits

        outcomes = evalrun.retrieval_outcomes(self.items(), self.ctx, leaky)
        self.assertTrue(all(o.leaked for o in outcomes if o.item_id != "r4") or any(o.leaked for o in outcomes))

    def test_a_miss_is_searched_again_deeper_to_show_where_the_right_chunk_really_ranks(self):
        from podcast_recall.models import SearchHit

        def hit(episode_id, start, end, distance):
            return SearchHit(1, episode_id, "s", "t", start, end, "x", None, None, None, 1, distance, 0.1)

        ep = self.ctx.video_to_episode[vid(304)]
        wrong = [hit(999, 0, 100, 0.30), hit(998, 0, 100, 0.31)]
        deep = [hit(999, 0, 100, 0.30)] * 11 + [hit(ep, 0, 100, 0.42)]  # the right chunk is 12th
        gold = item("r1", golden.SINGLE_FACT, "What?", [Evidence(vid(304), 5.0)])
        with_deep = evalrun.retrieval_outcomes([gold], self.ctx, lambda q: wrong, lambda q: deep)[0]
        self.assertTrue(with_deep.id_missed)
        self.assertEqual((with_deep.deep_rank, with_deep.gold_distance), (12, 0.42))
        self.assertEqual(len(with_deep.top), 2)
        plain = evalrun.retrieval_outcomes([gold], self.ctx, lambda q: wrong)[0]
        self.assertIsNone(plain.deep_rank)  # no deeper search was asked for
        found = evalrun.retrieval_outcomes([gold], self.ctx, lambda q: [hit(ep, 0, 100, 0.2)], lambda q: deep)[0]
        self.assertFalse(found.id_missed)
        self.assertIsNone(found.deep_rank)  # a hit needs no diagnosis

    def test_diagnose_runs_through_the_core_function(self):
        outcomes = core.eval_retrieval(self.items(), self.library, diagnose=True, services=self.services, conn=self.conn)
        missed = [o for o in outcomes if o.id_missed]
        self.assertEqual([o.item_id for o in missed], ["r2"])  # the jazz episode is outside the library
        self.assertIsNone(missed[0].deep_rank)

    def test_the_split_filter_applies(self):
        items = self.items()
        items[0] = GoldenItem("r1", golden.SINGLE_FACT, items[0].question, "a", (), items[0].evidence, "pm", "heldout", (), "")
        outcomes = core.eval_retrieval(items, self.library, split="heldout", services=self.services, conn=self.conn)
        self.assertEqual([o.item_id for o in outcomes], ["r1"])


# ---------------------------------------------------------------------------- checks on the golden set


class GoldenChecks(EvalBase):
    def problems(self, items):
        return golden_check.check_all(self.conn, items, self.ctx)

    def test_a_clean_set_has_no_problems(self):
        indexer.build_index(self.conn, indexer.IndexServices(embedder=FakeEmbedder()), now=self.now)
        self.assertEqual(self.problems(sample_items()), [])

    def test_evidence_must_be_a_matched_episode_in_the_library(self):
        found = self.problems([item("a", golden.SINGLE_FACT, evidence=[Evidence("zzzzzzzzzzz", 5.0)])])
        self.assertIn("not a matched, indexed episode", found[0].message)
        outside = self.problems([item("b", golden.SINGLE_FACT, evidence=[Evidence(vid(306), 5.0)])])
        self.assertIn("not in the evaluation library", outside[0].message)

    def test_evidence_in_the_first_three_minutes_of_a_long_episode_is_flagged_as_a_possible_teaser(self):
        self.world.add_episode(308, 1, "A long one", "2026-10-03T10:00:00", [f"Sentence number {i} is here." for i in range(80)])
        ctx = evalrun.build_context(self.conn, [*self.library, vid(308)])  # 400 seconds long
        early = golden_check.check_item(self.conn, item("a", golden.SINGLE_FACT, evidence=[Evidence(vid(308), 5.0)]), ctx)
        self.assertEqual([p.kind for p in early], ["warning"])
        self.assertIn("cold-open teaser", early[0].message)
        later = golden_check.check_item(self.conn, item("b", golden.SINGLE_FACT, evidence=[Evidence(vid(308), 300.0)]), ctx)
        self.assertEqual(later, [])

    def test_a_short_episode_is_not_flagged_for_early_evidence(self):
        short = self.problems([item("a", golden.SINGLE_FACT, evidence=[Evidence(vid(301), 5.0)])])  # a 15 second episode
        self.assertEqual(short, [])

    def test_evidence_time_must_be_inside_the_transcript(self):
        found = self.problems([item("a", golden.SINGLE_FACT, evidence=[Evidence(vid(301), 5000.0)])])
        self.assertIn("no words within", found[0].message)

    def test_not_in_library_evidence_must_be_outside_the_library(self):
        fine = self.problems([item("a", golden.NOT_IN_LIBRARY, evidence=[Evidence(vid(306), 0.0)])])
        self.assertEqual(fine, [])
        wrong = self.problems([item("b", golden.NOT_IN_LIBRARY, evidence=[Evidence(vid(301), 0.0)])])
        self.assertIn("is in the library", wrong[0].message)

    def test_an_unanswerable_question_whose_terms_exist_is_flagged(self):
        indexer.build_index(self.conn, indexer.IndexServices(embedder=FakeEmbedder()), now=self.now)
        present = self.problems([item("a", golden.UNANSWERABLE, "How does sourdough starter feeding work every morning?")])
        self.assertEqual(present[0].kind, "warning")
        self.assertIn("is the answer really absent", present[0].message)
        absent = self.problems([item("b", golden.FALSE_PREMISE, "Why did the guest say bread is poison?")])
        self.assertEqual(absent, [])

    def test_the_items_own_search_phrases_are_used_when_given(self):
        indexer.build_index(self.conn, indexer.IndexServices(embedder=FakeEmbedder()), now=self.now)
        # the speaker's name is not in any transcript, so searching the question's words finds nothing...
        plain = item("a", golden.UNANSWERABLE, "What does Snyder say about the sourdough starter feeding?")
        self.assertEqual(self.problems([plain]), [])
        # ...but the concept phrases the writer chose do find the sourdough episode
        phrased = GoldenItem("b", golden.UNANSWERABLE, plain.question, "", ("sourdough starter", "feeding"), (), "pm",
                             "dev", (), "")
        found = self.problems([phrased])
        self.assertEqual(len(found), 1)
        self.assertIn("'sourdough starter', 'feeding'", found[0].message)
        self.assertEqual(golden_check.search_phrases(phrased), ["sourdough starter", "feeding"])

    def test_key_terms_are_the_longest_non_stop_words(self):
        self.assertEqual(golden_check.key_terms("Why did the guest recommend intermittent fasting?"),
                         ["intermittent", "recommend", "fasting", "guest"])
        self.assertEqual(golden_check.key_terms("the of a"), [])

    def test_showing_an_item_prints_the_transcript_at_its_gold_time(self):
        text = golden_check.show_item(item("q01", golden.SINGLE_FACT, "What?", [Evidence(vid(301), 5.0)]), self.ctx)
        self.assertIn("rollback plan", text)
        self.assertIn(f"https://youtu.be/{vid(301)}?t=5", text)
        self.assertIn("Question: What?", text)


# ---------------------------------------------------------------------------- agreement


class Agreement(Base):
    def test_kappa_on_worked_examples(self):
        self.assertEqual(agreement.cohens_kappa(["a", "b", "a"], ["a", "b", "a"]), 1.0)
        self.assertAlmostEqual(agreement.cohens_kappa(list("xxyy"), list("xyxy")), 0.0)
        a = list("AAABBBBBBB")
        b = list("AABBBBBBBB")
        self.assertAlmostEqual(agreement.cohens_kappa(a, b), 0.7368, places=4)
        self.assertAlmostEqual(agreement.cohens_kappa(list("ab"), list("ba")), -1.0)

    def test_degenerate_cases(self):
        self.assertEqual(agreement.cohens_kappa(["a", "a"], ["a", "a"]), 1.0)
        self.assertEqual(agreement.cohens_kappa(["a", "a"], ["b", "b"]), 0.0)
        with self.assertRaises(ValueError):
            agreement.cohens_kappa(["a"], ["a", "b"])
        with self.assertRaises(ValueError):
            agreement.cohens_kappa([], [])

    def labels(self, mapping):
        return {i: agreement.Label(t, tuple(Evidence(v, s) for v, s in ev)) for i, (t, ev) in mapping.items()}

    def test_comparing_two_labellers(self):
        a = self.labels({"q1": ("single_fact", [("abcdefghijk", 100)]), "q2": ("unanswerable", []),
                         "q3": ("single_fact", [("abcdefghijk", 300)]), "q4": ("false_premise", [])})
        b = self.labels({"q1": ("single_fact", [("abcdefghijk", 110)]), "q2": ("false_premise", []),
                         "q3": ("single_fact", [("bcdefghijkl", 300)]), "q4": ("false_premise", [])})
        report = agreement.compare(a, b)
        self.assertEqual(report.n, 4)
        self.assertEqual(report.type_agreement, 0.75)
        self.assertEqual(report.disagreements, [("q2", "unanswerable", "false_premise")])
        self.assertEqual(report.episode_agreement, 0.5)  # q1 same episode, q3 different
        self.assertEqual(report.time_agreement, 0.5)  # q1 within 15 s
        self.assertFalse(report.meets_gate)
        self.assertIn("BELOW THE GATE", agreement.format_report(report))

    def test_time_agreement_counts_only_the_types_whose_time_is_scored(self):
        a = self.labels({"q1": ("single_fact", [("abcdefghijk", 100)]),
                         "q2": ("synthesis", [("abcdefghijk", 100), ("bcdefghijkl", 50)]),
                         "q3": ("not_in_library", [("cdefghijklm", 300)])})
        b = self.labels({"q1": ("single_fact", [("abcdefghijk", 105)]),
                         "q2": ("synthesis", [("abcdefghijk", 900), ("bcdefghijkl", 400)]),
                         "q3": ("not_in_library", [("cdefghijklm", 900)])})
        report = agreement.compare(a, b)
        self.assertEqual(report.episode_agreement, 1.0)  # same episodes everywhere
        self.assertEqual(report.time_items, 1)  # only q1 is a timed type
        self.assertEqual(report.time_agreement, 1.0)  # minutes apart on q2 and q3 do not count
        self.assertIn("single-fact and who/when only, 1 items", agreement.format_report(report))

    def test_perfect_agreement_meets_the_gate(self):
        a = self.labels({f"q{i}": ("single_fact" if i % 2 else "unanswerable", []) for i in range(10)})
        report = agreement.compare(a, dict(a))
        self.assertEqual(report.kappa, 1.0)
        self.assertTrue(report.meets_gate)
        self.assertIsNone(report.episode_agreement)

    def test_no_shared_ids_is_an_error(self):
        with self.assertRaises(ConfigError):
            agreement.compare(self.labels({"a": ("single_fact", [])}), self.labels({"b": ("single_fact", [])}))

    def test_reading_a_label_sheet_and_its_errors(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        good = folder / "s.csv"
        good.write_text("id,question,type,gold_evidence,comment\nq1,Q?,single_fact,abcdefghijk@1:00,\n", encoding="utf-8")
        self.assertEqual(agreement.read_labels(good)["q1"].type, "single_fact")
        for name, text in (("a.csv", "id,type\nq1,single_fact\n"),
                           ("b.csv", "id,type,gold_evidence\nq1,bogus,\n"),
                           ("c.csv", "id,type,gold_evidence\nq1,single_fact,oops\n"),
                           ("d.csv", "id,type,gold_evidence\nq1,unanswerable,\nq1,unanswerable,\n")):
            (folder / name).write_text(text, encoding="utf-8")
            with self.assertRaises(ConfigError, msg=name):
                agreement.read_labels(folder / name)

    def test_the_sample_for_the_second_labeller_is_fixed_and_spread_across_types(self):
        items = []
        for kind, count in golden.V0_MIX.items():
            for n in range(count):
                evidence = [] if kind in (golden.UNANSWERABLE, golden.FALSE_PREMISE) else [Evidence("abcdefghijk", 5.0 * n)]
                if kind == golden.SYNTHESIS:
                    evidence = [Evidence("abcdefghijk", 1.0), Evidence("bcdefghijkl", 2.0)]
                items.append(item(f"{kind[:2]}{n:02d}", kind, f"Question {kind} {n}?", evidence,
                                  gold_answer=f"SECRET {kind} {n}" if kind in golden.ANSWERABLE_TYPES else ""))
        first = agreement.sample_for_second_labeller(items, 20)
        self.assertEqual(len(first), 20)
        self.assertEqual([i.id for i in first], [i.id for i in agreement.sample_for_second_labeller(list(reversed(items)), 20)])
        self.assertEqual({i.type for i in first}, set(golden.TYPES))
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        sheet = folder / "sheet.csv"
        agreement.write_labelling_sheet(sheet, first)
        text = sheet.read_text(encoding="utf-8")
        self.assertNotIn("SECRET", text)
        self.assertIn("Question", text)


# ---------------------------------------------------------------------------- the commands


class EvalCli(Base):
    """The commands, against a real database file in the data folder."""

    def setUp(self):
        super().setUp()
        paths.ensure_data_home()
        self.file_conn = store.connect(paths.db_path(), paths.backup_dir())
        self.addCleanup(self.file_conn.close)
        store.upsert_user(self.file_conn, "owner", "UCme", "Me", T0)
        self.world = World(self.file_conn)
        for episode_id, title, sentences in ((301, "Shipping", KUBE), (302, "Bread", BREAD), (306, "Jazz", JAZZ)):
            self.world.add_episode(episode_id, 1, title, "2026-10-01T10:00:00", sentences)
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.folder, True)
        self.items = [
            item("q01", golden.SINGLE_FACT, "What does a good pipeline have?", [Evidence(vid(301), 5.0)]),
            item("q02", golden.UNANSWERABLE, "What is the capital of Atlantis?"),
            item("q03", golden.NOT_IN_LIBRARY, "How does swing feel work?", [Evidence(vid(306), 0.0)]),
        ]
        self.golden_path = self.folder / "golden.csv"
        golden.write_golden(self.golden_path, self.items)
        self.library_path = self.folder / "library.csv"
        self.library_path.write_text(
            f"youtube_url\nhttps://www.youtube.com/watch?v={vid(301)}\nhttps://www.youtube.com/watch?v={vid(302)}\n",
            encoding="utf-8")
        self.common = ["--golden", str(self.golden_path), "--library", str(self.library_path)]

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli_main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_the_oracle_run_scores_100_percent_and_exits_ok(self):
        card = self.folder / "card.csv"
        code, out, _ = self.run_cli("eval", "run", *self.common, "--oracle", "--out", str(card))
        self.assertEqual(code, 0)
        self.assertIn("3/3 = 100%", out)
        self.assertIn("R3, R4 and R6 are not run", out)
        self.assertTrue(card.exists())

    def test_a_fabricator_run_shows_the_failing_rule_and_exits_partial(self):
        code, out, _ = self.run_cli("eval", "run", *self.common, "--fabricate", "invented_quote")
        self.assertEqual(code, 2)
        self.assertIn("R1 [critical]", out)
        self.assertIn("q01 (single_fact) failed", out)

    def test_answers_from_a_file(self):
        ctx = evalrun.build_context(self.file_conn, golden.load_library(self.library_path))
        raw = oracle.answers_for(self.items, ctx, oracle=True)
        path = self.folder / "answers.jsonl"
        path.write_text("".join(json.dumps(a) + "\n" for a in raw.values()), encoding="utf-8")
        code, out, _ = self.run_cli("eval", "run", *self.common, "--answers", str(path), "--split", "dev")
        self.assertEqual(code, 0)
        self.assertIn("3/3 = 100%", out)

    def test_a_source_of_answers_is_required(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli_main(["eval", "run", *self.common])

    def test_check_reports_a_clean_set(self):
        code, out, _ = self.run_cli("eval", "check", *self.common)
        self.assertEqual(code, 0)
        self.assertIn("3 questions", out)
        self.assertIn("0 error(s)", out)

    def test_check_fails_when_evidence_is_outside_the_library(self):
        bad = self.items + [item("q04", golden.SINGLE_FACT, "Jazz?", [Evidence(vid(306), 0.0)])]
        golden.write_golden(self.golden_path, bad)
        code, out, _ = self.run_cli("eval", "check", *self.common)
        self.assertEqual(code, 1)
        self.assertIn("[error] q04", out)

    def test_show_prints_an_item_and_rejects_an_unknown_id(self):
        code, out, _ = self.run_cli("eval", "show", "q01", *self.common)
        self.assertEqual(code, 0)
        self.assertIn("rollback plan", out)
        code, _out, err = self.run_cli("eval", "show", "nope", *self.common)
        self.assertEqual(code, 1)
        self.assertIn("No question with the id", err)

    def test_the_sheet_and_kappa_round_trip(self):
        sheet = self.folder / "sheet.csv"
        code, out, _ = self.run_cli("eval", "sheet", "--golden", str(self.golden_path), "--out", str(sheet), "--count", "3")
        self.assertEqual(code, 0)
        self.assertNotIn("The gold answer", sheet.read_text(encoding="utf-8"))
        filled = self.folder / "filled.csv"
        filled.write_text(
            "id,question,type,gold_evidence,comment\n"
            f"q01,Q,single_fact,{vid(301)}@0:05,\nq02,Q,unanswerable,,\nq03,Q,not_in_library,{vid(306)}@0:00,\n",
            encoding="utf-8")
        code, out, _ = self.run_cli("eval", "kappa", "--golden", str(self.golden_path), "--labels-b", str(filled))
        self.assertEqual(code, 0)
        self.assertIn("MEETS THE GATE", out)
        disagree = self.folder / "disagree.csv"
        disagree.write_text(
            "id,question,type,gold_evidence,comment\nq01,Q,unanswerable,,\nq02,Q,single_fact,,\nq03,Q,single_fact,,\n",
            encoding="utf-8")
        code, out, _ = self.run_cli("eval", "kappa", "--golden", str(self.golden_path), "--labels-b", str(disagree))
        self.assertEqual(code, 2)
        self.assertIn("BELOW THE GATE", out)

    def test_a_bad_golden_file_is_a_clear_error(self):
        self.golden_path.write_text("id,question\nq1,What?\n", encoding="utf-8")
        code, _out, err = self.run_cli("eval", "check", *self.common)
        self.assertEqual(code, 1)
        self.assertIn("missing these columns", err)
