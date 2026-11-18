# Podcast Recall: Roadmap

Pace: about 8-10 hrs/week. The 90% grounded and 2% hallucination gate is never lowered. Scope shrinks instead. Details are in `plan.md`.

- [x] **Week 0: Setup (closed 2026-11-17; open items: measure llama3.1:8b speed (qwen2.5:7b is about 21 tokens/s), confirm 3 unverified feed episodes and 2 video URLs, D5 and D6 are Week 2 decisions).** Tools, local models, Whisper test, YouTube and Podcast Index keys, local chat hello world, 20 seed episodes, decisions D1-D7. Gate: every key works and the local chat page gets an Ollama reply.
- [x] **Week 1a: U1 YouTube connector (done 2026-11-17).** Gate met: steps 1-16 of the manual validation passed on the real account, 108 automated tests pass, lint clean. Step 17 (real API samples) deferred. See `features/u1-youtube-connector/results.md` and `docs/Week1_Explained.md`.
- [ ] **Week 1b: U2 episode resolver and U3 ingest and transcribe.** Gate: resolver at least 95% correct on the 20 seed episodes (15 expected `matched`), and transcripts for every matched seed episode. Status: U2 merged and validated (see `docs/Week1b_U2_Explained.md`); U3 built (261 tests) and validated on the seed list: 16 of 16 transcripts, spot-checks passed. Left: the optional step 15. See `docs/Week1c_U3_Explained.md` and `specs/features/u3-ingest-transcribe/results.md`.
- [ ] **Week 2: Eval first.** Rubric v1.0, deterministic checkers, golden set v0 (60 questions). Gate: kappa at least 0.7 on 20 double-labelled items.
- [ ] **Week 3: U4 index and retrieval, U6 answers and verifier, U5 core API with web chat and CLI.** Gate: end-to-end demo in the local web chat, baseline scorecard.
- [ ] **Week 4: Hill-climb.** Golden set to 120, judge calibration. Gate: at least 90% grounded and at most 2% hallucination, three consecutive runs.
- [ ] **Week 5: U7 exports.** Gate: findings open on a phone with working links.
- [ ] **Week 6: Testers.** Tester access per D8 (Cloudflare Tunnel with Access login, or local installs), Web application OAuth client, up to 4 testers, their questions added. Gate: still at least 90%.

## v1.1 backlog
- Spotify connector and dual links
- Notion export (if cut)
- Full-history upload from Google Takeout
- MCP adapter over the core library (only if Qualtrics policy allows)

## v2 backlog
- Apple Podcasts, YouTube Music
- Per-episode timestamp offset correction
