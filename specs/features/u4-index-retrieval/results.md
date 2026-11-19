# U4: Index and Retrieval, Validation Results

Recorded 2026-11-18 against the PM's real seed transcripts and local Ollama (`nomic-embed-text`). Spec: `validation.md` (v2). Automated: 342 tests pass, lint clean.

## The first build
16 episodes, **1,156 chunks**, 1,156 vectors. Chunks per episode ranged from 31 (a 31-minute episode) to 144 (a 142-minute one). A second build indexed nothing ("Already up to date: 16").

## Steps
| # | Step | Result | Evidence |
|---|---|---|---|
| 1 | `index build --seed` | Passed | 16 episodes, 1,156 chunks, meaning search on |
| 2 | Run it again | Passed | 0 indexed, 16 up to date |
| 3 | `index status` | Passed | 16 indexed, 0 waiting, 0 without vectors, 1,156 vectors |
| 4 | Search for a known topic | Passed, after a fix | First try (no `--seed`) returned only the Meta Muse episode: search is limited to the PM's YouTube library and the seed episodes are not all in it. After adding `--seed`: the passage "forget the modes and toggles. Just like one prompt box" (Josh Woodward) was result 2 (chunk 243); keyword rank 2, meaning rank 1, distance 0.305. 8 results from 4 episodes |
| 5 | Links open at the right time | Passed | PM confirmed |
| 6 | Exact phrase, then paraphrase | Passed | PM confirmed |
| 7 | Symbols in the query | Passed | PM confirmed |
| 8 | Show, date and ambiguous-show filters | Passed | PM confirmed |
| 9 | Ollama stopped | Passed | PM confirmed: clear message and exit code 1 on `index build`; `search` falls back to keywords with a warning |
| 10 | Ctrl+C during a build | Passed | PM confirmed: a later build finished the rest, no duplicates |
| 11 | Probe set recall@5 | **Measured: 75%, below the 85% target** | After the tuning round (default now 120 s / 24 s). Confirmed on the real index: 724 chunks, recall@5 75%, MRR 0.60, Raj Shamani 83% on 6 questions. See "Probe set results" below |
| 12 | A query that matches nothing | Passed | PM confirmed: weak results, no crash |
| 13 | No transcript or query text in logs | Passed | PM confirmed |
| 14 | Git and secrets check | Passed | PM confirmed |

## Probe set results (20 questions: 10 `claude` confirmed by the PM, 10 `claude2` drafted from other passages; 6 are Raj Shamani)
| Setting | Recall@5 | MRR |
|---|---|---|
| First 10 questions, keyword + meaning, cap 3 | 90% (after the scoring fix) | 0.59 |
| First 10, keyword only | 70% | 0.57 |
| First 10, cap 5 or 10 | 80% | 0.59 |
| **All 20, keyword + meaning, cap 3, equal weight** | **70%** (target 85%) | 0.51 |
| All 20, meaning weight 1.5 / 2 / 3 / 5 | 65% / 60% / 60% / 65% | 0.48 to 0.50 |
| Raj Shamani only (6 questions) | 67% | |

- The first 10 questions were too few: 90% did not hold up on 20.
- **A scoring flaw was found and fixed:** answer times were rounded down to a whole second, so a chunk starting a fraction after that second was wrongly counted as a miss. Scoring now allows 2 seconds of slack. It had understated recall.
- **An early explanation was wrong:** the per-episode cap was suspected for the first miss. Raising it did not help and hurt another question, so 3 stays.
- **A heavier meaning weight does not help.** Equal weight stays.
- **Chunk length experiment (20 questions, on a copy of the data, equal weight, cap 3):** 30 s / 8 s overlap gives 35% (3,184 chunks, MRR 0.31); 45 s / 10 s gives 55% (1,988 chunks, MRR 0.42); 75 s / 15 s gives 70% (1,156 chunks, MRR 0.51), and reproduces the real index exactly, which confirms the method. Smaller chunks are clearly worse: short snippets carry too little context for the meaning embedding, and the questions are about ideas. Larger sizes are next.
- **Larger chunks, same 20 questions (on a copy):** recall@5 / MRR / Raj only: 100 s 70% / 0.56 / 83%; 110 s 75% / 0.52 / 83%; 120 s 75% / 0.60 / 83%; **125 s 85% / 0.76 / 83%**; 130 s 75% / 0.58 / 83%; 140 s 75% / 0.62 / 83%; 150 s 70% / 0.58 / 83%. The 125 s result is a lucky outlier: its neighbours all score 75%. The real finding is a plateau from about 100 to 150 s that is modestly better than 75 s (recall 70 to 75% against 70%, MRR about 0.56 to 0.62 against 0.51, Raj Shamani 83% against 67%). **No chunk size reaches 85%.**
- **Decision:** the default is now 120 s with 24 s overlap (the middle of the plateau). It halves the chunk count (724 against 1,156). Tuned on 20 questions, so provisional until the Week 2 golden set. The reranker is the remaining lever, planned for the Week 4 hill-climb ("tune chunking, reranking, prompts").
- **The six misses (20 questions):** the right chunk ranks 12th, 10th, 26th, 36th and 41st for five of them, and is not in the top 50 for one. One (salt and blood pressure) is a near miss: the returned chunks are the neighbours of the right one in the same conversation. The seed library is almost all about AI agents, so queries that mention agents face many near-duplicates.
- **Next levers:** smaller chunks (chunk length and overlap are now settings), then a reranker over the top 50 (the spec allows it once recall falls short; it needs its own decision).

## Findings
- **Scope worked as designed and exposed a tooling gap.** A normal search covers only the user's library (rubric R2). The seed episodes were matched from the seed file, not from the library, so most were invisible. Added `search --seed` (and the probe script uses the seed list by default). Same `matched`-only rule and filters apply.
- **A real flaw found while reading the output:** the per-episode cap was applied after only 30 candidates per method, so one dominant episode could leave a short result list (3 results instead of 8). Fixed by widening the candidate lists (doubling, up to 480). A test that fails with the fix switched off proves it.
- **Meaning distance separates relevant from loose matches on this data:** about 0.30 to 0.33 for the relevant chunks, about 0.39 to 0.41 for loosely related ones. A starting guess of 0.35 for U6's "I don't know" threshold; to be tuned on the Week 2 golden set.
- **Two chunks can tie** on the fused score (one found by keyword first, one by meaning first). Ties go to keyword order.

## Exit gate
U4's gate (decision D17, question 4) is that retrieval works and recall@5 is **measured** on the probe set, with one tuning round allowed if below 85%. Measured: **75% at the tuned default**, from 70% before tuning. The 85% target is **not met**. The remaining lever is a reranker, deferred to the Week 4 hill-climb, where the 120-question golden set can judge it. All 14 manual steps and the automated checks passed.

## Open items
- Week 2 and 4: re-measure recall@5 on the real golden set, and decide the reranker.
- Check the 10 `claude2` answer times (questions 11 to 20), especially the three Raj Shamani ones (11, 17, 18), by opening the links. A wrong time would make that question a false miss.
- U6: cite the exact sentence's time inside a chunk, not the chunk's start (chunks are now 120 s).
- Raj Shamani retrieval quality (D11, D17) is judged by probe questions 1 to 3.
- `docs/Week1d_U4_Explained.md` written.
