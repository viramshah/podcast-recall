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
| 9 | Ollama stopped | Pending | |
| 10 | Ctrl+C during a build | Pending | |
| 11 | Probe set recall@5 | Pending | Needs the PM's 10 questions and a check of the 10 drafted answer times |
| 12 | A query that matches nothing | Passed | PM confirmed: weak results, no crash |
| 13 | No transcript or query text in logs | Pending | |
| 14 | Git and secrets check | Pending | |

## Findings
- **Scope worked as designed and exposed a tooling gap.** A normal search covers only the user's library (rubric R2). The seed episodes were matched from the seed file, not from the library, so most were invisible. Added `search --seed` (and the probe script uses the seed list by default). Same `matched`-only rule and filters apply.
- **A real flaw found while reading the output:** the per-episode cap was applied after only 30 candidates per method, so one dominant episode could leave a short result list (3 results instead of 8). Fixed by widening the candidate lists (doubling, up to 480). A test that fails with the fix switched off proves it.
- **Meaning distance separates relevant from loose matches on this data:** about 0.30 to 0.33 for the relevant chunks, about 0.39 to 0.41 for loosely related ones. A starting guess of 0.35 for U6's "I don't know" threshold; to be tuned on the Week 2 golden set.
- **Two chunks can tie** on the fused score (one found by keyword first, one by meaning first). Ties go to keyword order.

## Open items
- Steps 9, 10, 13 and 14, and the probe set (step 11).
- Raj Shamani retrieval quality (D11, D17) is judged by probe questions 1 to 3.
- Write `docs/Week1d_U4_Explained.md` when U4 is closed.
