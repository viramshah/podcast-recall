"""The matching rules, using real pairs from the seed list (feed data from the Podcast Index probe)."""

from __future__ import annotations

import unittest

from podcast_recall import matcher as m
from tests.fake_pi import epoch


def prep(episode_id: int, title: str, iso: str, duration_s: int | None) -> m.PreparedEpisode:
    return m.prepare_episode(episode_id, title, epoch(iso), duration_s)


def video(title: str, iso: str, duration_s: int | None) -> m.VideoFacts:
    return m.VideoFacts(title, epoch(iso), duration_s)


LENNY = [
    prep(1, "Meta’s Muse: How we launched the most successful consumer product this year | Mona Sarantakos",
         "2026-11-15T13:31:28", 5235),
    prep(2, "Why PMs are suddenly valuable again | Tulsee Doshi (Head of Product, Gemini)",
         "2026-11-08T13:31:32", 3513),
    prep(3, "How to close $100K+ enterprise deals, step by step | Jen Abel", "2026-08-23T12:31:43", 5097),
    prep(4, "Why every company now needs to think and operate like a lab team | Josh Woodward "
            "(Google Labs, Gemini, AI Studio)", "2026-10-11T12:31:59", 3731),
]
GREG = [
    prep(10, "My OpenClaw setup that finally works (Complete Walkthrough)", "2026-03-19T19:45:00", 3881),
    prep(11, "AI Agents Full Course 59 Minutes (for beginners)", "2026-03-17T19:25:00", 3535),
    prep(12, "Autoresearch clearly explained (why it matters)", "2026-03-11T22:00:00", 1461),
]
RAJ = [
    prep(20, "Why Your Communication Makes People Ignore You & How To Fix It | Vinh Giang | FO588 Raj Shamani",
         "2026-11-14T15:35:01", 8542),
    prep(21, "Diet Expert: Weight Loss, Calories, Digestion, Sugar & Belly Fats | Pooja Makhija | FO433 Raj Shamani",
         "2025-11-15T15:39:01", 4296),
]


class Text(unittest.TestCase):
    def test_normalisation_absorbs_quotes_ampersands_and_accents(self):
        self.assertEqual(m.normalize("Meta’s Café & Co"), "metas cafe  and  co")
        self.assertEqual(m.title_words("Meta’s Muse"), m.title_words("Metas MUSE"))

    def test_stemming_joins_common_word_forms(self):
        self.assertEqual(m.stem("launched"), "launch")
        self.assertEqual(m.stem("makes"), "make")
        self.assertEqual(m.stem("labs"), "lab")
        self.assertEqual(m.stem("building"), "build")
        self.assertEqual(m.stem("class"), "class")  # 'ss' endings are left alone
        self.assertEqual(m.stem("bus"), "bus")  # too short to change

    def test_common_words_and_single_letters_are_dropped(self):
        self.assertEqual(m.title_words("The rise of a Muse"), frozenset({"rise", "muse"}))
        self.assertIn("7", m.title_words("Sugar 7 fat"))

    def test_non_latin_titles_have_no_words(self):
        self.assertEqual(m.title_words("फिगरिंग आउट"), frozenset())


class Signals(unittest.TestCase):
    def test_title_score_is_the_share_of_the_youtube_titles_words_found(self):
        yt = m.title_words("Diet Expert Weight Loss")
        feed = m.title_words("Diet Expert: Weight Loss | Some Guest | FO433")
        self.assertEqual(m.title_score(yt, feed), 1.0)  # extra feed words cost nothing
        self.assertEqual(m.title_score(m.title_words("alpha beta"), m.title_words("alpha gamma")), 0.5)

    def test_title_signal_is_missing_with_fewer_than_two_words(self):
        self.assertIsNone(m.title_score(m.title_words("Intro"), m.title_words("Intro to everything")))
        self.assertIsNone(m.title_score(frozenset(), m.title_words("Anything")))

    def test_date_signal(self):
        day = 86400
        self.assertEqual(m.date_score(0, 0), 1.0)
        self.assertEqual(m.date_score(0, day), 1.0)
        self.assertAlmostEqual(m.date_score(0, 2 * day), 2 / 3)
        self.assertEqual(m.date_score(0, 4 * day), 0.0)
        self.assertEqual(m.date_score(0, 30 * day), 0.0)
        self.assertIsNone(m.date_score(None, 5))

    def test_duration_signal(self):
        self.assertEqual(m.duration_signal(5000, 5100), (1.0, -100, False))  # within tolerance
        score, diff, clip = m.duration_signal(4080, 5100)  # tolerance is 510 s (10%); 1,020 s off
        self.assertEqual((diff, clip), (-1020, False))
        self.assertAlmostEqual(score, 0.5)
        self.assertEqual(m.duration_signal(600, 5000), (0.0, -4400, True))  # a clip
        self.assertEqual(m.duration_signal(None, 5000), (None, None, False))
        self.assertEqual(m.duration_signal(0, 5000), (None, None, False))  # live video
        self.assertEqual(m.duration_signal(5000, None), (None, None, False))

    def test_short_episodes_use_the_minimum_tolerance(self):
        self.assertEqual(m.duration_signal(600, 700)[0], 1.0)  # 100 s off, tolerance 180 s

    def test_combined_score_scales_the_weights_of_the_signals_that_exist(self):
        self.assertAlmostEqual(m.combine(1.0, 1.0, 1.0), 1.0)
        self.assertAlmostEqual(m.combine(0.0, 1.0, 1.0), 0.5)
        self.assertAlmostEqual(m.combine(1.0, 1.0, None), 1.0)  # no duration: weights rescaled
        self.assertAlmostEqual(m.combine(None, 1.0, 0.0), 0.6)
        self.assertEqual(m.combine(None, None, None), 0.0)


class SeedPairs(unittest.TestCase):
    def test_muse_matches_despite_the_different_title(self):
        d = m.decide(video("The rise of Muse: Inside the launch of the most successful consumer product "
                           "this year", "2026-11-15T10:00:00", 5240), LENNY)
        self.assertEqual((d.status, d.method, d.best.episode_id), ("matched", "score", 1))
        self.assertGreaterEqual(d.best.combined, m.MATCHED_MIN)
        self.assertGreaterEqual(d.margin, m.MARGIN_MIN)

    def test_guest_bracket_differences_are_absorbed(self):
        d = m.decide(video("Why every company now needs to think and operate like a lab team | Josh Woodward "
                           "(VP Google Labs)", "2026-10-11T09:00:00", 3740), LENNY)
        self.assertEqual((d.status, d.best.episode_id), ("matched", 4))

    def test_raj_shamani_episodes_match(self):
        d = m.decide(video("Why your communication makes people ignore you and how to fix it",
                           "2026-11-14T10:00:00", 8500), RAJ)
        self.assertEqual((d.status, d.best.episode_id), ("matched", 20))
        d = m.decide(video("Diet Expert: Weight Loss , calories , Digestion , Sugar 7 belly Fat",
                           "2025-11-15T10:00:00", 4300), RAJ)
        self.assertEqual((d.status, d.best.episode_id), ("matched", 21))

    def test_jen_abel_matches_on_date_and_length_when_the_title_barely_overlaps(self):
        d = m.decide(video("84 minutes of enterprise sales alpha | Jen Abel", "2026-08-23T09:00:00", 5100), LENNY)
        self.assertEqual((d.status, d.method, d.best.episode_id), ("matched", "date_duration", 3))

    def test_greg_isenberg_hard_case_with_a_close_length_is_matched(self):
        d = m.decide(video("Building AI agents that actually work", "2026-03-17T15:00:00", 3540), GREG)
        self.assertEqual((d.status, d.method, d.best.episode_id), ("matched", "date_duration", 11))
        self.assertEqual(d.best.title_score, 0.4)  # only 'AI agents' is shared
        self.assertLess(d.best.combined, m.MATCHED_MIN)  # so only the date and length lock accepts it

    def test_greg_isenberg_hard_case_is_at_least_needs_review_when_the_length_is_off(self):
        d = m.decide(video("Building AI agents that actually work", "2026-03-17T15:00:00", 3700), GREG)
        self.assertEqual((d.status, d.method, d.best.episode_id), ("needs_review", "date_duration", 11))
        self.assertEqual(d.best.duration_diff_s, 165)

    def test_another_episode_the_same_day_and_length_blocks_the_lock(self):
        twin = prep(13, "A different show segment", "2026-03-17T08:00:00", 3500)
        d = m.decide(video("Building AI agents that actually work", "2026-03-17T15:00:00", 3540), [*GREG, twin])
        self.assertNotEqual(d.status, "matched")

    def test_an_episode_the_same_day_but_a_different_length_does_not_block_the_lock(self):
        other = prep(13, "A short bonus", "2026-03-17T08:00:00", 600)
        d = m.decide(video("Building AI agents that actually work", "2026-03-17T15:00:00", 3540), [*GREG, other])
        self.assertEqual((d.status, d.best.episode_id), ("matched", 11))


class OtherRules(unittest.TestCase):
    def test_a_clip_is_never_matched_to_the_full_episode(self):
        d = m.decide(video("Why PMs are suddenly valuable again | Tulsee Doshi", "2026-11-08T14:00:00", 420), LENNY)
        self.assertEqual((d.status, d.method), ("unmatched", "clip"))

    def test_a_close_second_candidate_needs_review(self):
        pair = [prep(1, "Weekly product growth review", "2026-05-02T10:00:00", 3000),
                prep(2, "Weekly product growth review", "2026-05-02T10:30:00", 3000)]
        d = m.decide(video("Weekly product growth review", "2026-05-02T12:00:00", 3000), pair)
        self.assertEqual(d.status, "needs_review")
        self.assertLess(d.margin, m.MARGIN_MIN)

    def test_no_episodes_is_unmatched(self):
        d = m.decide(video("Anything at all", "2026-05-02T12:00:00", 3000), [])
        self.assertEqual((d.status, d.best), ("unmatched", None))

    def test_a_partly_agreeing_candidate_needs_review(self):
        eps = [prep(1, "Marketing agents explained", "2026-06-01T10:00:00", 3000)]
        d = m.decide(video("How marketing agents work in practice", "2026-06-01T10:00:00", 2500), eps)
        self.assertEqual((d.status, d.method), ("needs_review", "partial"))

    def test_nothing_close_is_unmatched(self):
        d = m.decide(video("Cooking pasta at home", "2026-11-14T10:00:00", 600), LENNY)
        self.assertEqual(d.status, "unmatched")

    def test_a_title_match_far_from_the_date_is_only_a_review(self):
        # same words, a year apart, no length: title 1.0 and date 0.0 give 0.625 combined
        eps = [prep(1, "Weekly product growth review", "2025-05-02T10:00:00", None)]
        d = m.decide(video("Weekly product growth review", "2026-05-02T10:00:00", None), eps)
        self.assertEqual(d.status, "needs_review")

    def test_no_duration_on_either_side_still_scores_fairly(self):
        eps = [prep(1, "Weekly product growth review", "2026-05-02T10:00:00", None)]
        d = m.decide(video("Weekly product growth review", "2026-05-02T10:00:00", 3000), eps)
        self.assertEqual(d.status, "matched")
        self.assertIsNone(d.best.duration_score)

    def test_a_non_latin_title_cannot_be_matched_by_score(self):
        eps = [prep(1, "फिगरिंग आउट", "2026-05-02T10:00:00", 3000)]
        d = m.decide(video("फिगरिंग आउट", "2026-05-02T10:00:00", 3000), eps)
        self.assertIsNone(d.best.title_score)
        self.assertNotEqual(d.method, "score")  # only the date and length lock can accept it

    def test_the_top_three_candidates_are_kept_in_order(self):
        d = m.decide(video("Why PMs are suddenly valuable again | Tulsee Doshi", "2026-11-08T14:00:00", 3500), LENNY)
        self.assertEqual(len(d.top), 3)
        self.assertEqual(d.top[0].episode_id, 2)
        self.assertGreaterEqual(d.top[0].combined, d.top[1].combined)

    def test_ties_break_on_the_episode_id_so_results_are_stable(self):
        pair = [prep(7, "Same words here", "2026-05-02T10:00:00", None),
                prep(5, "Same words here", "2026-05-02T10:00:00", None)]
        d = m.decide(video("Same words here", "2026-05-02T10:00:00", None), pair)
        self.assertEqual(d.best.episode_id, 5)
