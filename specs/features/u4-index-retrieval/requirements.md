# U4: Index and Retrieval, Requirements (v2, 2026-11-18)

Branch: `feature/u4-index-retrieval` (from `main` after U3 was merged). Depends on U3 (`transcripts` table and JSON files) and U2/U1 (which episodes and videos are in a user's library). Source: requirements doc section 1.5 (U4), adapted. Decisions: D7 (core library, web chat and CLI), D10 (shared episodes, per-user library), D11 (languages), D16 (Whisper models). v2 adds the PM's answers to the 24 pre-build questions (all recommendations accepted), listed at the end and recorded as D17.

## What done looks like
- Every `ok` transcript is split into overlapping chunks of about 60 to 90 seconds, and each chunk is searchable by keyword and by meaning.
- `search_episodes(query, filters)` returns the best chunks with the episode, show, start and end time, the text, a YouTube link that opens at that moment, and the scores that produced the ranking.
- A user only ever gets results from episodes in **their own** library (requirement R2 of the rubric).
- The index is rebuilt incrementally, safely, and from nothing, and a changed transcript or changed chunking settings are noticed automatically.
- Retrieval quality is measured on a small hand-made set of about 20 questions with known answers (a "probe set"), against the target recall@5 of 85%. U4 is done when retrieval works and recall@5 is **measured**. If it is below 85%, one tuning round is allowed inside U4 (chunking or fusion settings); anything beyond that waits for Week 4. The real gate is the Week 2 golden set.
- Cost: $0. Everything runs on the Mac. Nothing leaves it except calls to Ollama on `127.0.0.1`.

## What the real data looks like (measured 2026-11-18 on the 16 seed transcripts)
- 206,000 words in total, 59 to 142 minutes each. At about 200 words per chunk that is **about 1,000 chunks**. This is small, so no heavy search infrastructure is needed.
- Segments are 2 to 6 seconds on average. Whisper segments reach 30 seconds. Publisher segments reach 28 seconds.
- Only 6 of the 12 publisher transcripts have speaker labels, and they are anonymous (`SPEAKER_00`, `SPEAKER_01`). Whisper transcripts have none.
- Segments sometimes overlap by up to 1.6 seconds (16 pairs in the seed set).
- Four transcripts (Raj Shamani) are Whisper turbo output: Hindi words in Latin letters mixed with English.

## How it works

### Chunking
1. Read the transcript's segments in time order. Only transcripts with status `ok` are indexed (`needs_review` ones are skipped until accepted).
2. Fill a chunk with whole segments until it holds about **120 seconds** (a segment is never cut; the length is a setting). Start the next chunk about **24 seconds** before the previous one ended, so a sentence on a boundary appears in both.
3. Each chunk stores: chunk ID, episode ID, chunk number, `start_s` (first segment start), `end_s` (last segment end), the text, the word count, the speaker label **only if one label covers more than half of the chunk's words** (otherwise none), the chunking version, and a hash of the source transcript.
4. Chunking is a pure function: same transcript and settings, same chunks. Segments are first sorted by start time and used as they are (overlaps are kept). Speaker labels are never part of the text that is indexed or embedded.
5. The stored chunking version combines the rules version (`CHUNKING_VERSION`) with the chunk length and overlap, so changing the rules or either setting makes the next build re-index every episode.

### Index (hybrid search)
- **Keyword:** SQLite FTS5 over the chunk text (BM25 ranking).
- **Meaning:** an embedding for each chunk from `nomic-embed-text` through Ollama, stored with `sqlite-vec`. Chunks use the `search_document:` prefix and queries the `search_query:` prefix, as the model expects.
- The embedding model name and vector size are stored. A different model means re-embedding.
- **Fusion:** take the top 30 from each method and combine them by reciprocal rank fusion (constant 60).
- **No reranker in U4** (Q10). One is added only if recall@5 on the probe set falls short, and then the choice goes in `decisions.md`.
- **If `sqlite-vec` cannot be loaded**, keyword search still works and the vector half is skipped with a visible warning.

### Search
`search_episodes(query, user_id, filters, limit)` returns hits, best first.
- **Scope:** only episodes that have a `matched` result for a video in this user's library. For development and validation, an explicit list of videos (the seed file) can be given instead (`--seed`); the same `matched`-only rule and filters apply, but library membership is not required (found during validation on 2026-11-18: the seed episodes are not all in the PM's YouTube library). `needs_review` and `unmatched` results are excluded.
- **Query text:** all words are plain words. Text in double quotes is an exact phrase. No raw operators (`AND`, `OR`, `*`, `NEAR`) are passed to FTS5.
- **Candidates:** 30 from each method. If the per-episode cap then leaves fewer than `limit` results, the candidate lists are widened (doubling, up to 480) so one long episode cannot starve the rest.
- **How many:** `limit` defaults to 8 and is at most 50. At most **3 chunks per episode** are returned by default (`per_episode` can change it), so one long episode does not fill the list.
- **Filters:** show, date range (`since`, `until`, by episode publish date), and specific episode IDs. A show is matched by name: a case-insensitive part of the show's title. If it matches more than one show, the search stops with an error that lists them. "Platform" is always YouTube in v1. "Played status" is ignored (D4).
- **Each hit:** chunk ID, episode ID, show, episode title, `start_s`, `end_s`, text, speaker, a YouTube link of the form `https://youtu.be/<video id>?t=<chunk start in whole seconds>`, and the scores (keyword rank, vector rank, fused score, rerank score if any).
- **Empty or weak results are returned as they are.** Deciding when to say "I don't know" belongs to U6.

### Keeping the index current
- `index build` is run by hand. `transcribe run` prints a reminder when it has produced new transcripts (automatic indexing can come with U5).
- `index build` finds transcripts that are `ok` and not indexed, or whose hash or chunking version changed, and indexes only those. It can run again at any time.
- A re-index of one episode replaces its chunks in one database transaction, so a crash never leaves half an episode.
- One index run at a time (file lock, like U3).
- Ollama is called only on a loopback address, with a 60-second timeout per batch of 16 chunks and at most 3 attempts per batch. If it is not running or the model is missing, the run stops with a clear message and nothing half-written remains. Keyword search still works for chunks already stored.
- Changing `CHUNKING_VERSION` or the embedding model causes a re-index of the affected episodes on the next build.
- Logs hold chunk IDs, scores, counts and timings only. Never transcript text, and never the query text (log its length).

### Commands
- `podcast-recall index build [--seed [FILE]] [--rebuild]`: build or update. `--rebuild` rebuilds everything.
- `podcast-recall index status`: episodes and chunks indexed, episodes waiting, model and chunking version, any problems.
- `podcast-recall search "query" [--show NAME] [--since DATE] [--until DATE] [--limit N] [--explain] [--user NAME]`: print hits with times and links. `--explain` shows the scores.
- Exit codes as before: 0 ok, 2 partial, 1 error.

### Core functions (`core.py`, no printing)
`build_index`, `index_status`, `search_episodes`, `get_chunk`. (`get_transcript` already exists from U3.)

## Data stored (migration 004, shared data per D10)
- `chunks`: chunk ID, episode ID, chunk number, start, end, text, word count, speaker, chunking version, transcript hash, created time.
- `chunks_fts`: the FTS5 table over chunk text.
- `chunk_vectors`: the `sqlite-vec` table of embeddings, plus the embedding model name and size.
- `index_state`: per episode, the hash and versions indexed and the time. This is how "up to date" is decided.
- Per-user scope is not stored in the index. It is decided at search time from the user's library (D10).

## Edge cases
- A transcript with `needs_review` or no transcript: not indexed, and not returned.
- An episode removed from every library: its chunks stay (shared data) but are never returned for a user who does not have it.
- Two videos for one episode (a clip and a full episode cannot both match, but two uploads can): one hit per chunk, using the link of a video in the user's library.
- A query with only stop words, an empty query or very long text: a clear message or truncation.
- Special characters in a query (`AND`, `*`, parentheses, unbalanced quotes) must not break FTS5 syntax. They are plain words. Only a balanced pair of double quotes makes a phrase.
- Ollama busy or slow: bounded retries with timeouts, then fail the run with the reason.
- Text in two scripts or languages in one chunk (Hinglish): indexed as it is.

## Out of scope
- Writing answers, citations to the sentence level, the citation verifier (U6).
- The web chat and the final CLI `ask` command (U5).
- The evaluation harness and the golden set (Week 2).
- Speaker diarization or naming speakers.
- Played status, other platforms, and per-episode timestamp offset correction (v2 backlog).
- Query rewriting, multi-hop search and conversation memory.

## Known risks
- **Embeddings are English-focused.** The four Raj Shamani transcripts are English with Hindi words in Latin letters. Meaning search may be weaker there. The keyword half still works. The probe set includes 2 to 3 questions from those episodes as evidence for D11, and a multilingual embedding model is revisited if they retrieve badly.
- **No reranker yet.** Ollama does not serve rerankers, and the options (a PyTorch model of about 2 GB, or the answer model as a slow reranker) are not worth their cost until the probe set shows a recall gap.
- **Chunk size was tuned on 20 questions.** The first guess of 75 s was changed to 120 s with a 24 s overlap after an experiment (see `results.md`): short chunks scored far worse, 100 to 150 s formed a plateau, and one apparent peak at 125 s was luck. Week 4 will re-tune on the golden set, so chunking is versioned and re-runnable. A chunk this long means a link opens up to about two minutes before the answer, so U6 must cite the exact sentence's time inside the chunk, not the chunk's start.
- **YouTube and podcast audio can differ.** Intros, ads or cuts could shift times. On the seed list lengths matched to within 1 second, so links should open at the right place. A per-episode offset correction is a v2 item.
- **Retrieval is judged on a small probe set until Week 2.** The 85% target is only meaningful on the real golden set.

## Settings (environment variables, documented in the README)
`PODCAST_RECALL_EMBED_MODEL` (default `nomic-embed-text`) and `PODCAST_RECALL_OLLAMA_URL` (default `http://127.0.0.1:11434`; a non-loopback address is refused).

## Decisions made in the pre-build review (2026-11-18, all recommendations accepted)
1. Build U4 now with its own probe set; the golden set stays in Week 2.
2. Probe set: the PM writes 10 questions from episodes they know, the assistant drafts 10 from the transcripts, and the PM verifies the answer times.
3. The probe set includes 2 to 3 questions from the Raj Shamani episodes.
4. U4 is done when retrieval works and recall@5 is measured on the probe set against 85%. One tuning round is allowed if below.
5. Chunks were 75 seconds with 15 seconds of overlap (changed to 120 s and 24 s on 2026-11-18, see Known risks).
6. Whole segments only.
7. Speaker label stored only when one label covers more than half the chunk, and never embedded.
8. Segments are sorted by start time and overlaps are kept.
9. Only `ok` transcripts are indexed.
10. No reranker in U4.
11. `nomic-embed-text`; revisit a multilingual model if Raj Shamani probe questions retrieve badly.
12. `sqlite-vec`, with keyword-only search as a fallback.
13. Top 30 from each method, reciprocal rank fusion with constant 60.
14. Plain words; double quotes mean an exact phrase; no raw operators.
15. Default 8 results, at most 50.
16. At most 3 chunks per episode by default.
17. Filters: show, date range, episode IDs. Platform fixed, played status ignored.
18. Show filter by name part, with an error listing the matches if more than one.
19. Link: `youtu.be/<id>?t=<chunk start>`.
20. Only `matched` episodes in the user's library.
21. Manual `index build`; `transcribe run` prints a reminder.
22. Ollama on loopback only, 60 s per batch of 16, up to 3 attempts.
23. Log chunk IDs, scores and counts only.
24. A stored version number triggers re-indexing when the chunk rules or model change.
