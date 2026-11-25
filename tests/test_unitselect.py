"""Week 4 (E5): show the model only the units closest to the question."""

from __future__ import annotations

from unittest import mock

from podcast_recall import answering, evalrun, indexer, paths, unitselect
from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.prompting import Passage
from podcast_recall.units import Unit
from tests.test_answers import AnswerBase, FakeChat, pointer_reply
from tests.test_index import FakeEmbedder


def unit(n, text):
    return Unit(n, n * 6.0, n * 6.0 + 5.0, text, None)


def passage(number, texts, first=1):
    hit = mock.Mock(show="S", title="T", start_s=0.0, end_s=60.0, episode_id=601)
    return Passage(number, hit, tuple(unit(first + i, t) for i, t in enumerate(texts)))


FILLER = "the weather is mild today and nothing else matters here"


class SelectingUnits(AnswerBase):
    def setUp(self):
        super().setUp()
        self.passages = [
            passage(1, [FILLER, FILLER, "kubernetes staging pipeline rollback", FILLER, FILLER, FILLER], first=1),
            passage(2, [FILLER, FILLER, FILLER, "bread flour dough hydration", FILLER, FILLER], first=7),
        ]

    def numbers(self, passages):
        return [[u.number for u in p.units] for p in passages]

    def test_the_best_units_and_their_neighbours_are_kept_with_original_numbers(self):
        reduced = unitselect.select_units("kubernetes staging pipeline", self.passages, FakeEmbedder(), top=1)
        self.assertEqual(self.numbers(reduced), [[2, 3, 4]])  # the match and one neighbour each side; passage 2 dropped

    def test_units_from_several_passages_and_passage_order_is_kept(self):
        reduced = unitselect.select_units("kubernetes staging bread flour dough", self.passages, FakeEmbedder(), top=2)
        self.assertEqual([p.number for p in reduced], [1, 2])
        self.assertEqual(self.numbers(reduced), [[2, 3, 4], [9, 10, 11]])

    def test_neighbours_stay_inside_their_passage(self):
        edge = [passage(1, ["kubernetes staging pipeline", FILLER, FILLER], first=1), passage(2, [FILLER, FILLER], first=4)]
        reduced = unitselect.select_units("kubernetes staging pipeline", edge, FakeEmbedder(), top=1)
        self.assertEqual(self.numbers(reduced), [[1, 2]])

    def test_zero_or_a_large_top_changes_nothing(self):
        self.assertEqual(unitselect.select_units("q", self.passages, FakeEmbedder(), top=0), self.passages)
        self.assertEqual(unitselect.select_units("q", self.passages, FakeEmbedder(), top=99), self.passages)

    def test_the_result_is_deterministic(self):
        a = unitselect.select_units("kubernetes bread", self.passages, FakeEmbedder(), top=3)
        b = unitselect.select_units("kubernetes bread", self.passages, FakeEmbedder(), top=3)
        self.assertEqual(a, b)


class UnitSelectionInTheAnswerPath(AnswerBase):
    def services_with(self, reply, unit_top):
        self.chat = FakeChat(reply)
        return answering.AnswerServices(index=indexer.IndexServices(embedder=self.embedder), chat=self.chat, unit_top=unit_top)

    def shown_units(self):
        import re

        return [int(n) for n in re.findall(r"^U(\d+) \(", self.chat.calls[0][1], re.MULTILINE)]

    def test_off_by_default_the_model_sees_every_unit(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            result = answering.answer_question(self.conn, self.services_with(pointer_reply("staging"), None), "pipeline staging", "owner")
        self.assertEqual(result.units_shown, result.units_total)
        self.assertEqual(len(self.shown_units()), result.units_total)

    def test_with_selection_the_prompt_is_smaller_and_the_answer_still_cites_real_text(self):
        result = answering.answer_question(self.conn, self.services_with(pointer_reply("staging"), 2),
                                           "What does a good pipeline have?", "owner")
        self.assertLess(result.units_shown, result.units_total)
        self.assertEqual(len(self.shown_units()), result.units_shown)
        self.assertEqual(result.answer.status, "answered")
        self.assertIn("staging", result.answer.claims[0].citations[0].quote)

    def test_a_pointer_to_a_unit_that_was_not_shown_is_dropped(self):
        shown_all = answering.answer_question(self.conn, self.services_with(pointer_reply("staging"), None), "pipeline", "owner")
        hidden = max(u for u in range(1, shown_all.units_total + 1))
        reply = {"status": "answered", "claims": [{"text": "x", "sources": [{"units": [hidden]}]}]}
        result = answering.answer_question(self.conn, self.services_with(reply, 1), "pipeline staging", "owner")
        self.assertEqual((result.answer.status, len(result.dropped)), ("not_found", 1))

    def test_an_unavailable_embedder_falls_back_to_every_unit_with_a_warning(self):
        services = self.services_with(pointer_reply("staging"), 2)

        def down(texts):
            raise ApiError("embedder down")

        self.embedder.embed_documents = down  # search only embeds the question, so retrieval still works
        result = answering.answer_question(self.conn, services, "What does a good pipeline have?", "owner")
        self.assertEqual(result.units_shown, result.units_total)
        self.assertTrue(any("Unit selection was skipped" in w for w in result.warnings))
        self.assertEqual(result.answer.status, "answered")

    def test_the_environment_setting_and_its_limits(self):
        with mock.patch.dict("os.environ", {"PODCAST_RECALL_UNIT_TOP": "12"}):
            self.assertEqual(paths.unit_top(), 12)
        for bad in ("-1", "1.5", "500", "x"):
            with mock.patch.dict("os.environ", {"PODCAST_RECALL_UNIT_TOP": bad}), self.assertRaises(ConfigError):
                paths.unit_top()

    def test_the_summary_reports_prompt_size_and_units_shown(self):
        result = answering.answer_question(self.conn, self.services_with(pointer_reply("staging"), 2), "pipeline staging", "owner")
        result.prompt_tokens = 700
        text = evalrun.format_answering(evalrun.summarize_answering([result], [1.0]))
        self.assertIn("Prompt size: median 700 tokens; units shown", text)
