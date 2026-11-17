# Podcast Recall: Roadmap

Pace: about 8-10 hrs/week. The 90% grounded and 2% hallucination gate is never lowered. Scope shrinks instead. Details are in `plan.md`.

- [ ] **Week 0: Setup.** Tools, local models, Whisper test, YouTube and Podcast Index keys, local chat hello world, 20 seed episodes, decisions D1-D7. Gate: every key works and the local chat page gets an Ollama reply.
- [ ] **Week 1: U1 YouTube connector, U2 resolver, U3 transcribe.** Gate: resolver at least 95% on the 20 seed episodes.
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
