# U4: Index and Retrieval, Validation (v2, 2026-11-18)

Run these yourself before merging, on the 16 seed transcripts. Ollama must be running with `nomic-embed-text` pulled.

## Automated
1. `make test` passes, including the chunker, incremental-index, crash, scoping, filter and FTS5-safety tests.
2. `make lint` is clean.

## Manual
| # | Step | Expected |
|---|---|---|
| 1 | `podcast-recall index build --seed` | All 16 episodes indexed, about 1,000 chunks, time noted |
| 2 | Run it again | Nothing new is indexed, and it finishes in seconds |
| 3 | `podcast-recall index status` | Episodes, chunks, model and chunking version shown. Nothing waiting |
| 4 | `podcast-recall search "<a topic you know is in one episode>" --explain` | The right episode is in the top 5. Times and link shown |
| 5 | Open the link of 5 hits (at least 2 publisher and 2 Whisper, one Raj Shamani) | The video opens within about 15 seconds of the words |
| 6 | Search for an exact phrase you remember hearing, then for the same idea in different words | The phrase finds it by keyword. The paraphrase finds it by meaning |
| 7 | Search with symbols: `AI agents AND (harness*)`, then `"agent harness"` with quotes, then a single unbalanced quote | No error in any. The quoted search finds that exact phrase |
| 8 | Filter by show, then by date range, then both. Also use a show name that matches two shows (for example a single common word) | Results come only from those episodes. An ambiguous name stops with an error listing the matches |
| 8b | Search for a topic discussed at length in one episode | At most 3 chunks from that episode appear by default, and other episodes fill the rest |
| 9 | Stop Ollama, run `index build --rebuild` on a copy of the data folder | Fails with a clear message. Keyword search of stored chunks still works |
| 10 | Kill an index build with Ctrl+C partway, then run it again | Finishes cleanly. No duplicate or half-indexed episode |
| 11 | Run the probe set script (about 20 questions, 2 to 3 from Raj Shamani episodes) | Recall@5 reported against the 85% target, with the misses listed. If below, one tuning round, then record the result |
| 12 | Search for something that is in none of the episodes | Weak, unrelated results are returned as they are, with low scores. No crash |
| 13 | Check logs for transcript text and for query text | None. Only chunk IDs, counts, scores and the query's length |
| 14 | `git status` and a search for secrets | No audio, transcript or database files tracked. No secrets |

## Record the results
Recall@5 and the misses, the time to build, the chunking and rerank choices and why, whether the Hinglish episodes retrieve worse than the others, and any change to the spec.

## Exit gate
All fifteen manual steps pass and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, write `docs/Week1d_U4_Explained.md`, and merge.
