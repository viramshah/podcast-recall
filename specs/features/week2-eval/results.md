# Week 2: Evaluation First, Results (in progress)

Recorded 2026-11-18. Spec: `validation.md` (v2). Automated: 433 tests pass, lint clean.

## Built
Answer format, golden set loader, checkers R1, R2, R5 and R7, oracle and fabricator (six modes), scorecard, kappa, golden-set checks, and the `eval` commands (`run`, `retrieval`, `check`, `show`, `kappa`, `sheet`).

## Golden set v0 (drafted by the assistant, awaiting the PM's review)
- `data/golden/golden_v0.csv`: 60 questions. Type counts match the plan exactly: 20 single-fact, 13 synthesis, 10 who/when, 7 unanswerable, 5 false premise, 5 not-in-library. Split: 40 dev, 20 held out (7, 4, 3, 2, 2, 2 by type). 17 of 60 are tagged `raj` (28%).
- `data/golden/eval_library.csv`: 11 library episodes. `data/golden/held_out_episodes.csv`: the 5 indexed-but-not-in-the-library episodes (D18, question 17).
- `data/golden/review_v0.md`: the review sheet (question, gold answer, transcript text and link at each gold time).
- Every gold time was checked against the transcript text. Five anchors were corrected during drafting (a repeated cold-open line, an answer starting earlier than the phrase). Four unanswerable questions were replaced after a concept search found overlaps (hiring, stage fright, seed round, a note-taking app). The unanswerable and false-premise questions carry concept phrases in `key_points`, and none of those phrases appear together in any indexed chunk (checked offline against the transcript files).

## Not yet done
| # | Step | Status |
|---|---|---|
| 1 | Read the rubric and apply it by hand | Rubric v1.0 written (`rubric.md`, with worked examples). PM to read it and confirm they would grade the same way |
| 2 | Review the 60 drafted questions and write at least 20 of your own | Pending (PM) |
| 3 | `eval check` | **Passed**: 60 questions, 0 errors, 0 warnings |
| 4 | Second labeller labels 20 items | Pending: Jainam (D6 decided 2026-11-18). Sheet and instructions written |
| 5 | `eval kappa` at least 0.7 | Pending |
| 6 | `eval run --oracle` scores 100% on the real golden set | **Passed** (after the oracle fix): 60/60 = 100%, 0 critical, R7 30/30 |
| 7 | `eval run --fabricate ...` fails as expected | Partly: `invented_quote` run by the PM scored 17/60 = 28%, 43 critical (every answerable question fails, the 17 unanswerable-type ones pass). The other five modes are covered by automated tests; the PM can run them |
| 8 | `eval retrieval` baseline | Pending |
| 9 | Compare with the 75% probe result | Pending |
| 10 | Held-out items are kept separate | Pending |
| 11 | Git and secrets check | Pending |

## Findings so far
- **`eval check` on the real database: clean.** 60 questions, 0 errors, 0 warnings.
- **The first oracle run scored 92%, not 100%.** Five R1 failures, all caused by the oracle itself: it built quotes by adding segments until it had two sentences, and the AI Agents Full Course transcript has no punctuation, so it ran on for up to 2,390 words (14 minutes). Two more quotes ran slightly past the 15 second window. Fixed: the oracle stays inside the window and under 60 words, and the answer format now caps a quote at 60 words as well as 2 sentences. A regression test uses a transcript without punctuation. The fabricator run behaved correctly (28% accuracy, 72% critical, only the unanswerable-type questions pass).
