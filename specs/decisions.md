# Podcast Recall: Decision Log

Status values: Open, Decided. Fill in "Decision" and "Date" as you go in Week 0. Recommendations come from `plan.md` section 2.

| ID | Question | Options | Recommendation | Status | Decision | Date |
|---|---|---|---|---|---|---|
| D1 | Spotify in v1? | (a) Defer to v1.1. (b) Borrow a Premium account for the app owner. | (a) Defer | **Decided** | (a) Defer to v1.1. v1 is YouTube-only; no Spotify Premium. | 2026-11-17 |
| D2 | Video-only YouTube podcasts with no RSS feed | (a) Mark "not indexable". (b) `yt-dlp` audio plus local transcription, personal use only. | (a) for testers; (b) only for your own library, after checking YouTube ToS | **Interim** | (a) for now: no-feed videos are "not indexable". 3 of the 20 seed episodes are kept as video-only tests. Revisit in Week 1 after reading YouTube ToS and Qualtrics rules. | 2026-11-17 |
| D3 | OAuth app status | (a) Testing mode: up to 100 named test users, weekly re-auth. (b) Publish: needs Google verification. | (a) for MVP | **Decided** | (a) Testing mode. Google Cloud project is already set up this way; tell testers they must sign in again about weekly. | 2026-11-17 |
| D4 | "Heard" status (YouTube has no resume_point) | (a) Ignore in v1. (b) Google Takeout watch-history upload. | (a); revisit after Week 3 | **Interim** | (a) Ignore "heard" status in v1. Revisit after Week 3. | 2026-11-17 |
| D5 | Rubric thresholds | Quote match 0.90; timestamp window +/-15 s; "Partly supported" fails an answer | Accept the proposals unless the Week 2 pilot disagrees | **Decided (provisional)** | Accepted 2026-11-18: 0.90 word similarity, 15 seconds either side, "Partly" fails an answer. Provisional until the Week 2 pilot and the first real answers. | 2026-11-18 |
| D6 | Who second-labels 30 golden items (20 in Week 2) | A tester, colleague or friend who listens | Name a person before Week 2; about 3 hrs | **Decided; human labels outstanding** | Jainam second-labels 20 items (decided 2026-11-18). On 2026-11-20, to move forward, the Week 2 gate was met provisionally with model stand-ins: three cold model readers agreed with the gold on question type (kappa 1.00). Jainam has not labelled the sheet. Revisit before testers join (Week 6) or before results are quoted outside the project. | 2026-11-18 |
| D7 | Front end | (a) Ask IT for an MCP exception. (b) Personal machine and account. (c) Local web chat plus CLI on the same core code. | (c) | **Decided** | (c) Local web chat (FastAPI, localhost) plus a CLI over a shared core library. MCP is deferred to an optional thin adapter. | 2026-11-16 |
| D8 | How testers reach the app | (a) Cloudflare Tunnel plus Cloudflare Access (login by email). (b) Testers run it on their own Macs. (c) Screen-share sessions only. | Decide by Week 4, after asking IT whether exposing a service from the work Mac is allowed. Never expose without login. | Open | | |
| D9 | What counts as the YouTube library | (a) Playlists + Liked + recent uploads of channels you mark "podcast". (b) Playlists and Liked only. (c) Everything from every subscription. | (a) | **Decided** | (a) Sync all playlists and Liked videos, plus the latest 50 uploads of channels the user marks as podcast. Subscribed channels are stored but not synced unless marked. | 2026-11-17 |
| D10 | How user data is stored | (a) One database: shared episodes and transcripts, per-user library. (b) Fully separate data per user. | (a) | **Decided** | (a) Episodes and transcripts are stored once and reused. Tokens, library lists, podcast-channel flags and saved findings are per user. "Delete my data" removes the user's tokens and per-user rows; public episode data may stay. This softens the requirements doc's "no transcripts shared between users" to "never exposed or exported to other users". | 2026-11-17 |
| D11 | Which languages are in scope for v1 | (a) English only for the 90% gate. (b) Include Hindi and Hinglish episodes. | (a) for the gate. Check transcript quality on a Raj Shamani episode in Week 1 and decide whether those 4 seed episodes stay in the golden set. | Open | | |
| D12 | Where runtime data lives | (a) One folder outside the repo, `~/.podcast-recall/`. (b) Inside the repo's `data/` (git-ignored). | (a) | **Decided** | (a) `~/.podcast-recall/` (override with `PODCAST_RECALL_HOME`), permissions 700, holding the database, logs, audio, transcripts and lock files. The repo's `data/` keeps only the seed list. | 2026-11-17 |
| D14 | Matching rule values for U2 | Starting values: weights 0.5, 0.3 and 0.2; matched at 0.85 with a 0.15 margin; review at 0.60; lock closeness 2% or 30 s | Tune on the seed run, then record | **Decided (provisional)** | Starting values kept after the first seed run: 15 of 15 `y` rows with a real episode matched correctly, and YouTube and feed lengths differed by only 0 to 1 second for every match. The lock closeness (2% or 30 s) is far looser than what was observed. Revisit with shows that insert ads. | 2026-11-17 |
| D15 | Transcript quality thresholds for U3 | Starting values: publisher transcript ends within 85% to 105% of the feed duration; 80 to 260 words per minute; Whisper silent gaps over 120 s; language compared with the feed | Tune on the seed run, then record | Open | | |
| D13 | Where transcripts come from | (a) Always run Whisper on the audio. (b) Use the publisher's transcript file when one exists, and run Whisper otherwise. | (b), after comparing one publisher transcript with Whisper on the same 5 minutes | **Decided** | (b) Publisher transcript first, Whisper as the fallback. Decided by the PM before the side-by-side comparison was run, so the comparison stays as a check during U3 validation. | 2026-11-17 |
| D16 | Whisper time limit and larger-model retry | (a) Manual choice of model. (b) Time limit plus an automatic retry with the larger model. | (b) | **Decided** | (b) Whisper runs as a separate process with a limit of half the audio length plus 5 minutes (at least 10). A timeout or a flagged transcript is retried once with `whisper-large-v3-turbo`. Evidence: small looped on Hindi/Hinglish audio, turbo transcribed it cleanly (D11). Built and tested with fakes; the real-audio check (validation step 15) is optional. | 2026-11-17 |
| D17 | U4 retrieval design | The 24 questions in `features/u4-index-retrieval/requirements.md` | All recommendations | **Decided; chunk size tuned 2026-11-18 (120 s / 24 s); recall@5 75% vs 85% target, reranker open for Week 4** | See the numbered list at the end of the U4 requirements. Main points: 75 s chunks with 15 s overlap, hybrid FTS5 plus `sqlite-vec` with fusion, no reranker in U4, `nomic-embed-text`, library-scoped results, at most 3 chunks per episode, U4 done when recall@5 is measured on a probe set | 2026-11-18 |
| D18 | Week 2 evaluation design | The 24 questions in `features/week2-eval/requirements.md` | All recommendations | **Decided; two items met with stand-ins (2026-11-20)** | See the numbered list at the end of the Week 2 requirements. The second labeller and the PM-written third of the questions were done by model stand-ins (author `pm_proxy` for the questions), so the human confirmation of both is outstanding. Main points: deterministic checkers first, no LLM this week, explicit answer format with a status field, 60-question golden set over the 16 seed episodes (11 in the evaluation library), 20 held out, kappa on question type | 2026-11-18 |

## Notes per decision

### D1: Spotify
- Record here your reading of Spotify's Developer Policy clause on AI models (Week 0 step 0.9).
- Reading: _TBD_

### D2: Video-only shows
- After building the seed list, count how many of the 20 episodes have RSS: _TBD_ / 20. If under 15, revisit before Week 1 ends.
- YouTube ToS reading for audio download: _TBD_

### D3: OAuth
- Testing mode caps at 100 test users and expires refresh tokens after 7 days. Tell testers.

### D4: Heard status
- Revisit after Week 3: how much of your real listening do saved items cover? _TBD_

### D5: Rubric
- Final values after the Week 2 pilot: match threshold _TBD_, window _TBD_, "Partly" fails _TBD_.

### D6: Second labeller
- Name: _TBD_

### D7: Front end (decided 2026-11-16)
- Why: Claude Code returned "not allowed by enterprise policy" when adding an MCP server, so no Claude client can call the product's tools.
- What changes: U5 becomes a core library with a local web chat and a CLI. The six functions (`sync_library`, `search_episodes`, `ask`, `get_transcript`, `save_finding`, `export_findings`) and their JSON schemas stay. The answer model stays on Ollama. Claude is not used in the product.
- What stays: retrieval, citations, the verifier, the eval harness and the rubric.
- Deferred: an MCP adapter, only if Qualtrics policy changes. It would be a thin wrapper over the same functions.
- Cost: a small web UI to build and test (citation cards, thumbs up/down, save finding), and testers need a way in (D8).

### D8: Tester access
- Ask Qualtrics IT whether exposing a local service from your work Mac through a tunnel is allowed: _TBD_
- A tunnel needs login in front (Cloudflare Access), and testers need a Web application OAuth client with a redirect URL: _TBD_
- Fallbacks: testers run it on their own Macs, or screen-share sessions.
- Copyright: if testers reach the app through a tunnel, the app must show short quotes plus links only and never serve full transcripts, as in the requirements doc's export rule: _TBD_

### D9: Library scope (decided 2026-11-17)
- Why: a subscription is a channel, not a video. Reading every upload of every subscribed channel could mean thousands of videos, slow syncs and heavy API quota use, and mostly non-podcast content.
- What this means: playlists and Liked videos sync in full. Subscribed channels are stored with an `is_podcast` flag (default off). Only marked channels have their latest 50 uploads synced.
- Consequence: a podcast you only subscribe to will not appear until you mark its channel as a podcast.
- Refined in the pre-build review: uploads of marked channels are cumulative (they do not drop out as newer ones arrive); only playlists you own are included (the API does not return other people's playlists); a video leaves the library only when no source contains it.

### D10: Shared episode data (decided 2026-11-17)
- Why: transcribing an episode is slow. Separate copies per user would repeat that work for every tester who has the same episode.
- What stays private: tokens, library lists, podcast-channel flags and saved findings. Episode transcripts come from public publisher feeds.
- To do: read YouTube's API developer policies on stored-data limits and deletion after revocation, and record the result here: _TBD_

### D11: Languages
- As far as I know, Raj Shamani's "Figuring Out" is largely Hindi or Hinglish, and 4 of the 20 seed episodes are from it. Verify by listening: _TBD_
- Check in Week 1 (U3 validation step 2): transcript quality on 5 minutes of one episode. 
  - Result (2026-11-17, PM, FO433 "Diet Expert", minutes 10 to 15): **Whisper small fails on this audio.** It detected Hindi, wrote garbled Devanagari, then looped on "how do you make your food" with zero-length segments. In the full run the same episode stayed in the transcribing state for 45+ minutes with no result.
  - **Whisper large-v3-turbo works.** Same clip: it detected English and wrote clean, readable text with Hindi words in Latin letters ("bajra jawari", "kachi sabzi"). Real speed about 0.24 of real time (the script's reported 1.118 included a 4 min 22 s model download). A short repeat of "eat" at about 14:38 and two garbled lines at the clip's cut-off were seen; to be checked by ear.
  - All four Raj Shamani seed episodes were then transcribed with turbo, all ended `ok` and language `en`, about 17,000 words each on average.

- The search embedding model (`nomic-embed-text`) is English-focused, so Hindi retrieval may be weak: _TBD_
- Decision after the check: keep those episodes in the golden set, move them to a separate experiment, or replace them: _TBD_

### D13: Transcript source
- Probe result (2026-11-17): publisher transcript links exist for 351 of 371 Lenny's episodes (95%), 196 of 396 Startup Ideas episodes (49%) and 0 of 649 Figuring Out episodes.
- For: saves hours of Whisper time, may be more accurate, and needs no audio download or storage for those episodes.
- Against: publisher files have timed chunks instead of per-word times, formats and quality vary by publisher, and a mix of two sources makes evaluation results harder to compare.
- Check (run by the PM on 2026-11-17, Lenny's "Muse" episode, minutes 10 to 15, Whisper small): 0.95 similar, 7.4% of words differ; every one of 92 publisher cue starts was within 2 s of Whisper's word times (worst 1.4 s); publisher cues averaged 2.9 s and were at most 6.7 s long; the publisher file has anonymous speaker labels (SPEAKER_00, SPEAKER_01). The publisher got names and jargon right where Whisper small did not ("Nat Friedman", "dogfooding"); Whisper kept filler words the publisher dropped. Whisper ran at about 0.05 of real time. The listening check of the disagreement table is still the PM's to do. Result: the evidence supports D13.
- Decision (2026-11-17, PM): publisher transcript first. Whisper is the fallback when an episode has no transcript link, or the file fails to download, parse or pass the quality checks.
- Consequences: U2 must keep each episode's transcript link. U3 builds both paths and records the `source` and the timing detail (`chunk` or `word`) of every transcript. Raj Shamani's episodes (no publisher transcripts) always go through Whisper. If the comparison shows publisher transcripts are too inaccurate or too coarse in timing, revisit this decision.

### D16: Whisper model per episode, and a time limit (opened 2026-11-17)
- Evidence: see D11. Small is fast and fine for clear English (0.05 of real time) but loops on Hindi and Hinglish. Turbo handles them at about 0.24 of real time.
- Used so far: the model is a single setting (`PODCAST_RECALL_WHISPER_MODEL`) applied to a whole run. The Raj Shamani episodes were run with turbo by setting it for one run.
- Gap found: nothing stops one looping episode from holding the queue for an hour. Needs a per-episode time limit, and probably "retry once with turbo when small is flagged or times out". Not built yet.
- Decision (2026-11-17, PM): build the recommended design. Small stays the default. Each Whisper run has a **time limit of half the audio length plus 5 minutes (never under 10 minutes)**, enforced by running Whisper as a separate process that can be stopped. If a run hits the limit, or its transcript is flagged `needs_review`, the episode is **retried once with the larger model** (`PODCAST_RECALL_WHISPER_FALLBACK_MODEL`, default `mlx-community/whisper-large-v3-turbo`, `none` turns this off). The transcript records the model actually used and why it was retried.

### D17: U4 retrieval
- Open checks: does `nomic-embed-text` retrieve the four Raj Shamani episodes as well as the others (D11)? Does recall@5 reach 85% on the probe set without a reranker? _TBD after U4 validation_
- Chunk size (2026-11-18): tested 30 to 150 s on a copy. Short chunks are much worse (30 s: 35%, 45 s: 55%); 100 to 150 s is a plateau of 70 to 75% recall with MRR 0.52 to 0.62; one 85% result at 125 s was a lucky outlier. Default changed from 75 s / 15 s to **120 s / 24 s**. Still below the 85% target: reranker deferred to the Week 4 hill-climb.
- Probe result (2026-11-18, 20 questions): recall@5 is 70% against the 85% target with keyword plus meaning search, cap 3 and equal weight. Keyword only is lower, and a heavier meaning weight does not help. Reranker decision: _open_, pending the chunk-size experiment. Details in `features/u4-index-retrieval/results.md`.
- Early evidence (2026-11-18): on the seed episodes, relevant chunks had a meaning distance of about 0.30 to 0.33 and loosely related ones about 0.39 to 0.41. Starting guess for U6's abstention threshold: 0.35, to be tuned on the Week 2 golden set.
