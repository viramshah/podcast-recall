# Podcast Recall: PM Execution Plan (YouTube-first)

Source: `Podcast_Recall_Requirements.docx` v0.2 (Nov 16, 2026). This plan turns it into steps a semi-technical PM can run with Claude Code as the builder.

Owner: Viram Shah. Pace: about 8-10 hrs/week for 6 weeks plus Week 0.

## 0. How to read this plan

- **PM-owned** steps need your judgment and cannot be delegated to the agent: decisions, rubric, golden-set labels, testers.
- **Claude Code** steps are builds. You write the spec, Claude Code implements it, you review the diff and run the verification.
- Every week ends with an **exit gate**. Do not start the next week until it passes.
- The eval gate (90% grounded, 2% hallucination) is never lowered. Scope shrinks instead.

## 1. Changes from the requirements doc (your answers)

| Your input | Effect on the plan |
|---|---|
| You have **YouTube Premium, not Spotify Premium** | Spotify Dev Mode needs Premium, so **Spotify moves to v1.1**. v1 is YouTube-only. U1 builds the YouTube connector first. |
| Claude Code builds | Each unit gets a spec, plan and validation file under `specs/features/`. |
| Apple Silicon, 16GB+ Mac, Claude Desktop | Assumptions hold. 16GB is tight for a 14B model, so default to 7-9B models (see Week 0). |

Consequences of YouTube-first (**decide in Week 0**, see Decisions D1-D4):

1. YouTube Premium gives no API benefit. It removes ads and enables downloads in the app only. The Data API is free regardless (10,000 quota units/day).
2. The YouTube Data API **does not expose watch history**, and Watch Later is not readable. The library is **subscriptions + your own playlists + Liked videos**.
3. YouTube's API gives **no transcripts** for videos you do not own. The requirements doc's answer is the publisher's RSS audio via Podcast Index. That works for shows that publish an RSS feed. **Video-only shows have no RSS.** They need another route (D2).
4. "Dual links" (YouTube + Spotify) becomes YouTube links only in v1.
5. The OAuth consent screen in Testing mode **expires refresh tokens after 7 days**. Plan for re-auth, or publish the app (D3).

## 2. Decisions to make in Week 0

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Spotify in v1? | (a) Defer to v1.1. (b) Borrow a Premium account for the app owner. | (a) Defer. Keeps $0 and the 5-user limit out of the critical path. |
| D2 | Video-only YouTube podcasts with no RSS | (a) Mark "not indexable" in v1. (b) Download audio with `yt-dlp` and transcribe locally, for personal use. | (a) for testers, (b) only for your own library. Check YouTube ToS wording first. Never fail silently. |
| D3 | OAuth app status | (a) Testing mode, up to 100 named test users, weekly re-auth. (b) Publish, which needs Google verification for sensitive scopes. | (a) for MVP. Add testers as test users. Put the weekly re-auth in the tester brief. |
| D4 | Heard-status | YouTube has no `resume_point`. Options: ignore "heard", or use a Google Takeout watch-history upload. | Ignore for v1. Revisit after Week 3 (the doc's open question). |
| D5 | Rubric thresholds | 0.90 quote match, +/-15 s window, "Partly" fails an answer | Accept the doc's proposals unless the Week 2 pilot says otherwise. |
| D6 | Who second-labels 30 golden items | A tester, a colleague, or a friend who listens | Pick a named person before Week 2. Needs about 3 hrs. |

## 3. Week 0: Setup (click-by-click)

Goal: every key works and you have a 20-episode seed list. Time: about 8 hrs.

### 0.1 Repo and constitution (PM-owned, then Claude Code)
1. Create a public GitHub repo named `podcast-recall`. Clone it.
2. Copy this plan and the requirements doc into `specs/`.
3. Write `specs/mission.md` (intent, north star, out of scope; copy from doc section 1.1).
4. Write `specs/tech-stack.md` (copy the doc's section 2.1 table, with Spotify marked "v1.1").
5. Write `specs/roadmap.md` (Weeks 1-6 from section 4 below).
6. Commit to `main`. From here, **each unit gets its own branch** (`feature/u1-youtube-connector`, and so on).

### 0.2 Install tooling (Terminal)
1. Install Homebrew from brew.sh if missing.
2. Run:
   ```bash
   brew install python@3.12 uv git gh ffmpeg yt-dlp ollama
   ```
3. Sign in to GitHub: `gh auth login`.
4. Start Ollama: `brew services start ollama` (or open the Ollama app).
5. Install Claude Code if not already installed, and open it in the repo folder.

### 0.3 Local models (Terminal)
Pick sizes for a 16GB Mac. Use model names that exist in the Ollama library when you run this (check `ollama.com/library`).
1. Answer model: pull one 7-9B instruct model, for example `ollama pull qwen2.5:7b-instruct`.
2. Judge model: pull one from a **different family** than the answer model, for example `ollama pull llama3.1:8b`.
3. Embeddings: `ollama pull nomic-embed-text`.
4. Test each: `ollama run <model> "Say hello in five words"`.
5. Close other heavy apps. Note the response speed. Under 10 tokens/s on the answer model means going smaller.

### 0.4 Transcription test
1. Ask Claude Code: "Create a uv project in `podcast-recall/`, install `mlx-whisper`, and write a script that transcribes a given audio file with word-level timestamps to JSON."
2. Download a 5-minute clip of any podcast and run the script.
3. **Pass:** the JSON has a start/end time per word, and a 1-hour episode would take an acceptable time (the doc allows overnight). Record the real-time factor.

### 0.5 Google Cloud and YouTube API (browser)
1. Go to console.cloud.google.com. Create a project named `podcast-recall`.
2. **APIs & Services > Library:** search "YouTube Data API v3" and click Enable.
3. **OAuth consent screen:** user type External, app name `Podcast Recall`, your email as support and developer contact.
4. **Scopes:** add `https://www.googleapis.com/auth/youtube.readonly` (read-only, per the doc).
5. **Test users:** add your own Google account (the one with YouTube Premium). Testers come in Week 6.
6. **Credentials > Create credentials > OAuth client ID:** application type **Desktop app**. Download the JSON as `client_secret.json`.
7. Store `client_secret.json` **outside the repo** (or in Keychain via Claude Code later). Add it to `.gitignore`.
8. **Pass (hello world):** a script lists your subscriptions (`subscriptions.list`, `mine=true`). Ask Claude Code to write it from this spec.

### 0.6 Podcast Index key (browser)
1. Go to api.podcastindex.org and sign up for a free key.
2. The API key and secret arrive by email. Store them in your password manager. Never commit them.
3. **Pass:** a signed request to `/search/byterm?q=huberman` returns feeds. Ask Claude Code to write the auth-header code (SHA-1 of key+secret+timestamp).

### 0.7 MCP hello world
1. Ask Claude Code: "Create a minimal MCP server using the official Python SDK with one tool, `ping`, over stdio."
2. Add it to Claude Desktop: **Settings > Developer > Edit Config**, then add the server under `mcpServers` with the `uv run` command.
3. Restart Claude Desktop. **Pass:** asking "use ping" returns the tool result.

### 0.8 Pick the 20 seed episodes (PM-owned)
1. Choose 20 episodes you have actually heard, from **5-8 shows**, across at least 2 topics.
2. Require that **at least 15 have an RSS feed** (check each show in Podcast Index). Include 2-3 video-only episodes to test D2.
3. Include 2 shows that run dynamic ads, to see timestamp drift early.
4. Save as `data/seed_episodes.csv` with columns: `youtube_url, show, title, date, has_rss (y/n), notes`.

### 0.9 Spotify policy and Spotify decision (PM-owned)
1. Read Spotify's Developer Policy and Terms (developer.spotify.com/policy), specifically the clause on AI models.
2. Record your reading in `specs/decisions.md` under D1. Given no Premium, this is a v1.1 item.

### 0.10 Week 0 exit gate
- [ ] Both Ollama models answer; embeddings model works
- [ ] Whisper transcript with word timestamps exists
- [ ] YouTube subscriptions list prints
- [ ] Podcast Index search returns feeds
- [ ] Claude Desktop calls your `ping` tool
- [ ] `seed_episodes.csv` has 20 rows
- [ ] D1-D6 recorded in `specs/decisions.md`

## 4. Weeks 1-6 (milestones)

Each unit uses the **unit loop** in section 5.

### Week 1: U1 (YouTube) + U2 resolver + U3 transcribe
- **Goal:** 20 seed episodes transcribed, each mapped to a canonical RSS episode.
- **PM actions:**
  1. Write specs for U1 (YouTube OAuth, subscriptions, playlists, tokens in macOS Keychain, incremental sync), U2 (Podcast Index lookup + title/date/duration match + stored confidence) and U3 (download, transcribe, queue, retry, cache). Copy the acceptance criteria from doc section 1.5.
  2. Hand-check the resolver output: open 20 matches and mark right or wrong in a CSV.
  3. Spot-check 5 transcripts against the audio.
- **Done when:** resolver is at least 95% correct on the 20 (the doc's U2 target is 95% on 100; the 100-episode check comes in Week 4), and 20 transcripts exist.

### Week 2: Eval first
- **Goal:** rubric v1.0 and golden set v0 (60 questions).
- **PM actions:**
  1. Finalise the rubric (D5). Update section 1.4 of the requirements doc.
  2. Write labelling instructions. Fields: question, gold answer, gold episode(s), gold start time, question type.
  3. Label 60 questions from the 20 seed episodes, using the doc's mix (single-fact, cross-episode, who/when, unanswerable, false premise, catalogue-not-library).
  4. Ask your second labeller (D6) to double-label 20 items. Compute Cohen's kappa (ask Claude Code for a script).
  5. Ask Claude Code to write the deterministic checkers (R1, R2, R5, R7) with unit tests.
- **Done when:** kappa is at least 0.7 on 20 items. If lower, rewrite ambiguous questions and re-label.

### Week 3: U4 + U6 + verifier + U5
- **Goal:** ask in Claude Desktop, get a cited answer and a link.
- **PM actions:** spec U4 (chunking, hybrid search, reranker), U6 (answer only from retrieved chunks, citation format, verifier) and U5 (the six MCP tools and their JSON schemas). Review each diff for the checklist in section 5.
- **Done when:** end-to-end demo works and a baseline scorecard exists.
- **Decide:** is the full-history upload needed (D4)?

### Week 4: Hill-climb to the gate
- **Goal:** at least 90% grounded and at most 2% hallucination, **three consecutive runs**.
- **PM actions:**
  1. Grow the golden set to 120.
  2. Calibrate the judge on 40 human-graded answers; if agreement is under 85%, grade R3 by hand.
  3. Keep an error-analysis log. Tag each failure: retrieval miss, chunking, prompt, abstention, judge error.
  4. Change **one thing per run** (chunking, reranker, prompt, abstention threshold) so you know what worked.
  5. Run the 100-episode resolver check (U2).
- **Done when:** three runs in a row clear every target in doc section 1.3. **If missed by end of Week 5, narrow scope. Do not lower the bar.**

### Week 5: Exports (+ Spotify only if D1 changed)
- **Goal:** a findings collection opens on your phone with working links.
- **PM actions:** spec U7. Build in the doc's order: Markdown, Google Doc, Apple Notes, Notion. Test links on iOS, Android and desktop. Test re-export for duplicates.
- **Cut line:** Notion goes to v1.1. YouTube `&t=` links are reliable, so link risk is lower than the doc assumed.
- **Done when:** exports open on a phone and links jump to the right moment.

### Week 6: Testers
- **Goal:** MVP with up to 4 testers, still at least 90% with their questions added.
- **PM actions:**
  1. Set up Cloudflare Tunnel (free) to your local MCP server.
  2. Add each tester's Google account as a test user (D3).
  3. Write the **tester brief**: what it does, what it cannot do (not indexable shows), Mac-must-be-on uptime, weekly re-auth, how to give thumbs up/down, how to run "delete my data".
  4. Onboard each tester live for 20 minutes. Confirm their library syncs in under 2 minutes.
  5. Add their real questions to the golden set. Re-run `make eval`.
  6. In week 6, send the one-question survey. Success is 3 of 4 testers asking 3 or more questions per week.
  7. Fill in the resume line with the real X, Y and Z.
- **Done when:** scorecard in the README shows at least 90% with tester questions included.

## 5. The unit loop (use for every unit U1-U8)

1. **Branch:** `git checkout -b feature/<unit>`.
2. **Spec (PM-owned, 20-30 min):** create `specs/features/<unit>/requirements.md` (what done looks like), `plan.md` (approach, constraints, out of scope) and `validation.md` (how you will verify). Take acceptance criteria from doc section 1.5.
3. **Clarify:** ask Claude Code to list ambiguities in the spec **before** coding. Answer them in the spec, not in chat.
4. **Implement:** in Claude Code, say "Read the spec folder for `<unit>` and `specs/tech-stack.md`. Implement it with unit tests. Do not change anything out of scope."
5. **Review the diff** (do not read all the code). Check:
   - Secrets or tokens in code or logs?
   - Does it match the spec's JSON schema and acceptance criteria?
   - Tests included, and do they fail when the code is broken?
   - Anything added that the spec did not ask for?
6. **Verify:** run the steps in `validation.md` yourself (unit tests, then the real data). Only then merge.
7. **Log:** record what changed in `specs/decisions.md` and update checkboxes in the roadmap.

## 6. Operations (after Week 6)

1. Ask Claude Code to create the nightly `launchd` job (sync, resolve, transcribe, log failures).
2. **Weekly 30-minute review (PM-owned):** each thumbs-down or verifier-blocked answer becomes a golden question, then a fix, then `make eval`. Ship only if the gate holds.
3. Re-run the full eval on any model, prompt or chunking change. Keep the scorecard history in the repo. A drop of more than 3 points blocks the release.

## 7. Risks the PM watches

| Risk | Signal | Response |
|---|---|---|
| Video-only shows are most of your library (D2) | Under 15 of 20 seed episodes have RSS | Rethink the transcript source before Week 1 ends |
| 16GB RAM too small for the models | Slow answers, swapping | Smaller models; run Whisper and Ollama at separate times |
| OAuth token expiry in Testing mode | Syncs fail after 7 days | Re-auth flow; weekly reminder in the tester brief |
| Judge is unreliable | Agreement under 85% | Grade R3 by hand; deterministic checks carry the gate |
| Timestamp drift from ads | R7 below 85% | Open links 10 s early; show the quote; offset correction in v2 |
| Scope creep | New asks mid-week | Add to `roadmap.md` v1.1; do not start without a spec |

## 8. Time estimate

| Phase | PM hours | Biggest PM tasks |
|---|---|---|
| Week 0 | 8 | Accounts, keys, seed list, decisions |
| Weeks 1-2 | 16-20 | Specs, resolver check, rubric, 60 labels |
| Weeks 3-4 | 16-20 | Specs, diff reviews, 60 more labels, judge calibration |
| Weeks 5-6 | 16-20 | Export testing on devices, tester onboarding |
