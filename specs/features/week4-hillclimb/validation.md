# Week 4: Validation (v2)

Run yourself before merging; Ollama running with the answer model, the judge model and `nomic-embed-text`.

| # | Step | Expected |
|---|---|---|
| 1 | `make test && make lint` | Passes |
| 2 | `eval diagnose` on the dev run | A table of causes per failing question; counts add up to the number of failures |
| 3 | `eval check` on the 120-question set | Evidence found, absent answers absent, split ratio and show balance within limits |
| 4 | `eval judge-sheet`, label your share, `eval judge-agreement` | Agreement and kappa reported; at or above the bar in Q8, or R3/R4 flagged for hand grading |
| 5 | `eval retrieval` on the 120 questions | recall@5, MRR and leaks (0) recorded; the change since Week 3 stated |
| 6 | `eval answer --split dev` | Scorecard with all five rules; zero R1/R2 failures |
| 7 | Gate run 1 (dev), run 2 (held-out), run 3 (fresh 20 PM questions), version frozen | Each at least 90% grounded and at most 2% critical |
| 8 | Compare the median time with the working target | Recorded, with the decision on the final target |
| 9 | Check logs and `git status` | No question or transcript text in logs; no data, answers files or secrets tracked |

Record everything in `results.md` and `decisions.md`; write `docs/Week4_Explained.md`; then merge.
