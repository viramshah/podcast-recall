# Week 4: Plan (v2)

Build order (each step ends with tests, a results line and a commit-sized change; all questions in `requirements.md` are decided (D20)):

1. **Store the evidence.** `eval answer` saves retrieved chunk ids and the model's raw reply per question (private, git-ignored). New migration only if needed.
2. **`eval diagnose`.** Join answers, retrieved chunks and golden evidence; classify each failing question (not retrieved, not shown, model refused or mis-cited, gold questionable); print counts.
3. **Run the diagnosis on dev**, write the cause table into `results.md`, and let it set the order of steps 4 to 7.
4. **Retrieval experiments** (one at a time, dev only): opening weight, keyword expansion, passage count and cap, then reranker only if justified. Each logged.
5. **Judge.** `judge.py` for R3, R4, R6 with a JSON schema, a calibration sheet generator (`eval judge-sheet`), an agreement report (`eval judge-agreement`), and `eval run` extended to include the judge rules.
6. **Answer quality.** False-premise examples in the prompt, then the check step if needed; answer-model comparison; passage count.
7. **Golden set to 120.** Write and verify 60 new questions; keep the split rule; `eval check` passes.
8. **Speed decision** from the numbers; update the target in the decision log.
9. **Gate runs** (frozen version): dev, held-out, fresh 20 PM questions.
10. **Docs:** `results.md`, decisions, roadmap, `docs/Week4_Explained.md`.

Constraints carried from Week 3: no new dependencies without asking; question text only in the private database; guard test bans the `.search(` pattern in package source; line length 100; fake model and embedder in tests.
