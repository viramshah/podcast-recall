# U4: Index and Retrieval, Plan (v2, 2026-11-18)

## Approach
1. **`chunker.py`.** Pure function from segments to chunks (target 75 s, overlap 15 s, never splits a segment). Tested on short synthetic transcripts and on real shapes (overlapping segments, 30 s Whisper segments, a transcript with no speakers).
2. **Migration `004_index.sql`.** `chunks`, `chunks_fts` (FTS5, content table), `chunk_vectors` (`sqlite-vec`), `index_state`. A guard so that a database without the extension still opens and keyword search still works.
3. **`embeddings.py`.** An Ollama client for `/api/embed` with batching, timeouts, bounded retries, the document and query prefixes, and a check that Ollama's address is loopback. Injectable, so no test needs Ollama.
4. **`indexer.py`.** Find transcripts to index (status `ok`, hash or version changed), chunk, embed, and replace one episode's rows in one transaction. One run at a time through the file lock.
5. **`retrieval.py`.** Query cleaning (plain words, balanced double quotes as a phrase), keyword search, vector search, reciprocal rank fusion, library scoping, filters (show by name, dates, episodes), the per-episode cap, hit building with the YouTube link. No reranker.
6. **`core.py` and `cli.py`.** `build_index`, `index_status`, `search_episodes`, `get_chunk`; `index build|status` and `search`. The CLI only calls core. Progress goes to standard error.
7. **Probe set.** `data/retrieval_probe.csv`: about 20 questions (10 from the PM, 10 drafted by the assistant, 2 to 3 of them from Raj Shamani episodes), each with the episode and the time where the answer is, verified by the PM. A script reports recall@5 and the rank of the gold chunk. This is U4's own check until the Week 2 golden set exists.
8. **Tests.** Chunker rules; index up to date and incremental; crash mid-episode leaves the old chunks; changed hash or version triggers re-index; FTS5 query safety; scoping (a user never sees another user's episode, and never an episode outside their library); filters; fusion order; Ollama down; deterministic output with a fake embedder; end-to-end through the CLI with a fake Ollama.
9. **README and tech stack.** Settings, commands, new dependency `sqlite-vec` (added with `uv add sqlite-vec`, run by the PM), the embedding model (`ollama pull nomic-embed-text`), and the decision that U4 has no reranker. `transcribe run` prints a reminder to run `index build`.

## Constraints
- No secrets in code, logs or git. No transcript text in logs: log chunk IDs, scores and counts only.
- Ollama is called only on loopback, through one module, with a 60 s timeout per batch of 16 and at most 3 attempts.
- No query text and no transcript text in logs.
- Database changes only through numbered migrations.
- `core.py` has no printing.
- U1, U2 and U3 are not changed, except `core.py` and `cli.py` additions and the migration.

## Review checklist (PM)
- [ ] Only `ok` transcripts are indexed, and `transcribe accept` makes a flagged one indexable on the next build
- [ ] Running `index build` twice indexes nothing the second time
- [ ] Killing a build mid-episode leaves no half-indexed episode and the next build finishes it
- [ ] Changing the chunking version or the embedding model triggers a re-index
- [ ] A search never returns an episode outside the signed-in user's library
- [ ] Quotes, `AND`, `*` and other symbols in a query do not cause errors
- [ ] Every hit has episode, show, start and end, text and a link that opens at the right moment (checked by hand on 5 hits)
- [ ] Filters by show and date work and can be combined
- [ ] With Ollama stopped, `index build` fails clearly and keyword search of stored chunks still works
- [ ] Recall@5 on the probe set meets the target, or the gap is explained
- [ ] No transcript text in logs, and nothing added beyond the spec (no answers, no verifier, no web page)
