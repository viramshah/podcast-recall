# Podcast Recall: Decision Log

Status values: Open, Decided. Fill in "Decision" and "Date" as you go in Week 0. Recommendations come from `plan.md` section 2.

| ID | Question | Options | Recommendation | Status | Decision | Date |
|---|---|---|---|---|---|---|
| D1 | Spotify in v1? | (a) Defer to v1.1. (b) Borrow a Premium account for the app owner. | (a) Defer | **Decided** | (a) Defer to v1.1. v1 is YouTube-only; no Spotify Premium. | 2026-11-17 |
| D2 | Video-only YouTube podcasts with no RSS feed | (a) Mark "not indexable". (b) `yt-dlp` audio plus local transcription, personal use only. | (a) for testers; (b) only for your own library, after checking YouTube ToS | **Interim** | (a) for now: no-feed videos are "not indexable". 3 of the 20 seed episodes are kept as video-only tests. Revisit in Week 1 after reading YouTube ToS and Qualtrics rules. | 2026-11-17 |
| D3 | OAuth app status | (a) Testing mode: up to 100 named test users, weekly re-auth. (b) Publish: needs Google verification. | (a) for MVP | **Decided** | (a) Testing mode. Google Cloud project is already set up this way; tell testers they must sign in again about weekly. | 2026-11-17 |
| D4 | "Heard" status (YouTube has no resume_point) | (a) Ignore in v1. (b) Google Takeout watch-history upload. | (a); revisit after Week 3 | **Interim** | (a) Ignore "heard" status in v1. Revisit after Week 3. | 2026-11-17 |
| D5 | Rubric thresholds | Quote match 0.90; timestamp window +/-15 s; "Partly supported" fails an answer | Accept the proposals unless the Week 2 pilot disagrees | Open | | |
| D6 | Who second-labels 30 golden items (20 in Week 2) | A tester, colleague or friend who listens | Name a person before Week 2; about 3 hrs | Open | | |
| D7 | Front end | (a) Ask IT for an MCP exception. (b) Personal machine and account. (c) Local web chat plus CLI on the same core code. | (c) | **Decided** | (c) Local web chat (FastAPI, localhost) plus a CLI over a shared core library. MCP is deferred to an optional thin adapter. | 2026-11-16 |
| D8 | How testers reach the app | (a) Cloudflare Tunnel plus Cloudflare Access (login by email). (b) Testers run it on their own Macs. (c) Screen-share sessions only. | Decide by Week 4, after asking IT whether exposing a service from the work Mac is allowed. Never expose without login. | Open | | |

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
