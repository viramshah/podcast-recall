# Week 2: Evaluation First, Validation (v2, 2026-11-18)

## Automated
1. `make test` passes, including checker, loader, kappa, oracle and fabricator tests.
2. `make lint` is clean.

## Manual
| # | Step | Expected |
|---|---|---|
| 1 | Read the rubric (v1.0) and apply it by hand to the six worked examples | You reach the same verdicts the rubric gives |
| 2 | Review the 60 drafted questions: keep, edit or replace each, and write at least 20 of your own from memory | Every item has a question, gold answer, evidence and type that you agree with |
| 3 | `podcast-recall eval check` (and `eval show <id>` to read the transcript at an item's gold time) | Every gold quote is found in its transcript near the gold time. Every unanswerable and false-premise item reports no hits, or you rewrite it |
| 4 | Give the second labeller the labelling sheet for 20 items (questions only) | They return a completed sheet in about an hour |
| 5 | `podcast-recall eval kappa` on the two label sets | Kappa on question type is at least 0.7. Episode and time agreement are reported. If below 0.7, rewrite the ambiguous items and repeat |
| 6 | `podcast-recall eval run` with the oracle answerer | 100% grounded accuracy, 0% hallucination |
| 7 | `podcast-recall eval run` with the fabricator | Fabricated citations fail R1, outside-library citations fail R2, and every failure shows its reason |
| 8 | `podcast-recall eval retrieval` on the dev split | Recall@5 and MRR reported by question type, with the misses listed |
| 9 | Compare the retrieval number with the earlier probe (75%) | The two are in the same range, or the difference is explained |
| 10 | Check that the held-out items are marked and not used in any tuning or reported dev number | The dev and held-out splits are separate in every report |
| 11 | `git status` and a search for secrets | No audio, transcript or database files tracked. No secrets |

## Record the results
Kappa, per-type retrieval recall, any items rewritten and why, the final rubric choices (D5), and the second labeller in `decisions.md` (D6).

## Exit gate
Kappa at least 0.7 on 20 items, the checkers pass their tests with the oracle at 100% and the fabricator failing, and golden set v0 is signed off by the PM. Then update `decisions.md` and the roadmap, write `docs/Week2_Explained.md`, and merge.
