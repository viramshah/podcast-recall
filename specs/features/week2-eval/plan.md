# Week 2: Evaluation First, Plan (v2, 2026-11-18)

## Approach
1. **Rubric v1.0.** Finalise `specs/features/week2-eval/rubric.md` from requirements doc section 1.4: every check, threshold and term defined, with worked examples (a passing and a failing answer for each rule). Record D5 in `decisions.md`.
2. **Answer and citation format.** A small module `podcast_recall/answers.py`: dataclasses and a JSON loader and validator for the format in the requirements. This is the contract U6 will produce.
3. **Golden set format and loader.** `podcast_recall/golden.py`: read `data/golden/golden_v0.csv`, validate every field (ids unique, types valid, evidence parses, split valid), and expose items. Errors name the row.
4. **Evaluation library.** `data/golden/eval_library.csv` (video IDs). A function returns the episodes in scope, reusing U4's explicit-scope search.
5. **Golden set helpers.** `podcast_recall/golden_check.py`, run as `eval check` and `eval show <id>`: for answerable items, confirm the gold time exists in the transcript, the episode is in the library, and print the transcript text at that time for the PM to read; for unanswerable and false-premise items, search every indexed chunk for the question's key terms and report any hits; for not-in-library items, confirm the episode is indexed but not in the library. Also `eval sheet`, which writes the second labeller's sheet (questions only, no gold answers, a fixed stratified sample of 20).
6. **Deterministic checkers.** `podcast_recall/checkers.py`: R1, R2, R5, R7 as pure functions, each returning pass or fail with a reason. Text normalisation and token matching in one place.
7. **Test answerers.** `podcast_recall/oracle.py`: an oracle (builds a perfect answer from the gold item and the real transcript) and a fabricator with several modes (invented quote, cites outside the library, wrong time, invents an answer, uncited claim), to prove the harness scores the oracle 100% and each fabrication as a failure of the right rule. Available as `eval run --oracle` and `eval run --fabricate MODE`.
8. **Scorecard and harness.** `podcast_recall/evalrun.py`: run checkers over answers, compute accuracy, hallucination rate, per-type and per-rule results, write the CSV. `eval run`, `eval retrieval`, `eval kappa` in the CLI.
9. **Kappa.** `podcast_recall/agreement.py`: Cohen's kappa for two label lists, plus percentage agreement for episode and time.
10. **Candidate questions.** The assistant drafts 60 candidates from the real transcripts into the labelling sheet. The PM reviews, edits, rewrites some from memory, and signs off.
11. **Tests.** Every checker on passing and failing cases (exact quote, light paraphrase just above and below 0.90, wrong episode, quote outside the window, quote from another episode, empty quote). Loader errors. Kappa against hand-worked examples (including perfect and chance-level agreement). Oracle scores 100% and fabricator fails. Retrieval metrics on a fake index.
12. **README and tech stack.** Commands, file locations, and the scoring definitions.

## Constraints
- No LLM calls this week.
- No transcript text in logs; scorecards hold short quotes only.
- `core.py` has no printing. U1 to U4 are not changed except for additions to `core.py` and `cli.py`.
- Every threshold is a named constant in one place.
- The held-out split is never used for tuning (rule written into the rubric).

## Review checklist (PM)
- [ ] The rubric reads clearly enough that someone else would grade the same way
- [ ] Every golden item has a gold answer, gold evidence and a type, and the gold quotes are verified against the transcripts
- [ ] Unanswerable and false-premise items were checked against the transcripts and are truly absent
- [ ] At least a third of the questions were written or rewritten by the PM
- [ ] The second labeller labelled 20 items without seeing the gold answers, and kappa is at least 0.7
- [ ] The oracle scores 100% and the fabricator fails every fabricated-citation case
- [ ] Each checker's failure message says why
- [ ] Retrieval recall@5 is measured on the golden set and recorded
- [ ] Nothing was added beyond the spec (no judge, no answer model, no HTML scorecard)
