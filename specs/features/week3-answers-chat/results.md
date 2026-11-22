# Week 3 results (answers, citation verifier, web chat, CLI)

Status: **complete.** Manual validation steps were reported done by Viram on 2026-11-22 (details of each result were not sent to the assistant).

## Automated checks
- Full test suite: 528 passed. `ruff check .`: clean.
- Tests use a fake model and fake embedder. They cover passage units, prompt and injection defence, the model client, the quote builder, reply interpretation, the verifier, the answering path, storage and revoke cascade, schema files, web safety (Host, Origin, token, transcript window), the CLI and `eval answer`.

## Baseline scorecard (dev split, 40 questions, qwen2.5:7b-instruct, 4 passages)
Deterministic rules only (R1, R2, R5, R7). The judge rules (R3, R4, R6) are not built, so these numbers can only get worse.

| | Run 1 (baseline, per-passage unit numbers fixed, before the two fixes) | Run 2 (after the two fixes) |
|---|---|---|
| Grounded accuracy | 25/40 = 62% | 27/40 = 68% |
| Critical failures | 0 | 0 |
| R1 / R2 failures | 0 | 0 |
| Statuses | answered 15, not_found 17, premise_corrected 8 | answered 19, not_found 21 |
| Claims removed by the verifier | 15 (13 "not consecutive") | 1 (R1) |
| R7 timestamp within 15 s | 6/20 = 30% | 7/20 = 35% |
| Synthesis episode coverage | 39% | 44% |
| Median / p90 time | 31.9 s / 76.3 s | 23.9 s / 60.6 s |
| Failures by rule | R5 15 | R5 13 |

By type, run 2: single_fact 10/13, synthesis 6/9, who_when 3/7, unanswerable 5/5, not_in_library 3/3, false_premise 0/3.
Files: `evals/scorecards/answers_dev_20261122-0336.csv` (run 1), `answers_dev_20261122-0959.csv` (run 2). The held-out split has not been used.

### What the numbers say
- **The safety property holds:** zero R1/R2 failures and zero critical failures across 80 answers. No fabricated citation reached the output.
- **Every remaining failure is R5**: the system refuses a question it could have answered (about 10 of 32 answerable questions) or fails to correct a false premise (0/3). Likely main cause: retrieval. About a third of answerable questions have no gold chunk in the top 4 passages (Week 2: recall@5 was 70%), so the model cannot answer them. Not yet confirmed per question; run `eval retrieval --diagnose --split dev` and compare with the `not_found` ids.
- **False premise regressed** when the premise rule was narrowed (2/3 to 0/3). The 7B model does not use `premise_corrected` reliably either way.
- **R7 is low (35%)** partly because gold times mark where a topic starts and the model cites a later unit in the same discussion; the quotes spot-checked were on topic.
- **Claims that cite real text but do not answer the question exist** (for example a Google Flow claim on a NotebookLM question). Only the R3 judge can score this.

## Latency
Median 24 s (run 2) to 32 s (run 1) at 4 passages, p90 60 to 76 s, target median under 15 s: **not met**. Cold start and early questions were 50 to 95 s. Reading about 58 tokens/s, writing about 4 tokens/s (cold, tiny sample). Details and options in D19.

## Gate (from requirements.md)
| Gate item | Result |
|---|---|
| Web chat: cited answer + working link | **Met** (answer, thumbs buttons; link and remaining manual steps reported done by Viram, 2026-11-22) |
| CLI: cited answer + working link | **Met** (seed episodes; reported done by Viram) |
| Baseline scorecard, zero R1/R2 failures | **Met** (run 1 and run 2) |
| Median latency vs 15 s | **Measured, target not met** (24 s) |
| `llama3.1:8b` speed measured | Reported done by Viram; the figure was not sent to the assistant, so it is not recorded here. Add it. |
| No question or transcript text in log files | Reported done by Viram |
| Revoke test removes requests, feedback, findings | Reported done by Viram; automated test passes |
| Bad Origin / missing token refused | Reported done by Viram; automated test passes |
| Ollama stopped: plain message | Reported done by Viram; automated test passes |

No accuracy target applies in Week 3; the 90% gate is Week 4.

## Week 4 list from this week
1. Confirm whether refusals come from retrieval (diagnose by question), then fix retrieval first (opening-chunk weight, query wording such as "free trial" vs "pilot", reranker).
2. A reliable false-premise path (a separate check step or a stronger model).
3. Build the R3/R4/R6 judge so the score reflects whether claims answer the question.
4. Latency: passage count, passage length, model size, or a relaxed local target.
5. Decide the default passage count (4 vs 8).
