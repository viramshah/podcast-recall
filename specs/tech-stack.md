# Podcast Recall: Tech Stack (locked for v1)

Change an entry only by editing this file and recording why in `decisions.md`.

| Layer | Choice | Cost | Why |
|---|---|---|---|
| Language and tooling | Python 3.12, `uv`, `pytest`, `ruff` | $0 | Fits the ML libraries and FastAPI |
| Transcription | The publisher's transcript file when one exists (D13), otherwise `mlx-whisper` (fallback `whisper.cpp`), local, word timestamps | $0 | Saves hours of compute for episodes that have one; timestamps power citations |
| Embeddings | `nomic-embed-text` via Ollama (or a `bge` model via sentence-transformers) | $0 | Local, small |
| Reranker | Open reranker model, local | $0 | Improves recall@5 |
| Answer LLM | One 7-9B instruct model via Ollama | $0 | Sized for 16GB RAM |
| Judge LLM | A model from a different family than the answer model | $0 | Reduces self-preference bias |
| Storage and search | SQLite, FTS5, `sqlite-vec` | $0 | One file, no server |
| Core library | Plain Python package: `sync_library`, `fetch_videos`, `list_channels`, `set_podcast_channel`, `revoke`, `purge_stale_videos`, `search_episodes`, `ask`, `get_transcript`, `save_finding`, `export_findings` | $0 | One implementation shared by the web chat, CLI and eval harness (D7) |
| Web chat | FastAPI + uvicorn, one static HTML page, bound to `127.0.0.1` | $0 | Replaces the MCP client; testers need a browser only |
| CLI | `podcast-recall` command (`auth`, `sync`, `status`, `revoke`, `channels`, `fetch`, `purge`, `resolve`, `transcribe`, `ask`) | $0 | Development and eval use |
| Platform data | YouTube Data API v3 (read-only, free quota), Podcast Index API (free key) | $0 | |
| Auth storage | macOS Keychain via `keyring` | $0 | Tokens never in files |
| Export | Markdown, Google Docs API, Apple Notes (AppleScript), Notion API | $0 | Notion is the first cut if time runs short |
| Tester access | Cloudflare Tunnel plus Cloudflare Access (free), **pending D8** and an IT check | $0 | Web chat needs login before it is exposed |
| CI and evals | GitHub Actions for unit tests and deterministic checks; local `make eval` for LLM-judged runs | $0 | |

## Deferred
- Spotify Web API (v1.1).
- MCP adapter over the core library (only if Qualtrics policy allows; see D7).

## Rules
- Only the `youtube.readonly` OAuth scope.
- The web chat binds to `127.0.0.1` and is never exposed to a network without login in front.
- Claude and other hosted LLMs are not used in the product. The answer and judge models run in Ollama.
- Episodes and transcripts are stored once and shared (public publisher content). Tokens, library lists, podcast-channel flags and findings are per user and carry a `user_id` (D10).
- `search.list` is never called. It is not needed, and Google's quota page gives it its own small daily allowance (checked twice on 2026-11-17; an earlier version of this file wrongly said 100 units per call).
- Podcast Index credentials come from the environment variables `PODCASTINDEX_KEY` and `PODCASTINDEX_SECRET`, optionally loaded from `~/.podcast-recall/podcastindex.env` (permissions 600). They are not stored in Keychain, and are never logged or committed. Google OAuth tokens are stored in Keychain.
- Database changes are numbered SQL migration files in `podcast_recall/migrations/`, tracked by a `schema_version` table. Each unit adds its own.
- Downloads from feeds refuse loopback, link-local and private addresses, including after redirects.
- All runtime data (database, logs, audio, transcripts, lock files) lives in one folder, `~/.podcast-recall/` (override with `PODCAST_RECALL_HOME`), permissions 700, and never in the repo (D12). The repo's `data/` holds only the seed list and other small files that are safe to commit.
- SQLite runs in WAL mode with foreign keys on and a 5-second busy timeout. Timestamps are UTC ISO-8601 text.
- Logs never contain tokens, authorization headers, client secrets or email addresses, and a test enforces this.
- Packaging: flat `podcast_recall/` package at the repo root, entry point `podcast_recall.cli:main`, `uv.lock` committed, ruff with line length 100.
- Settings come only from environment variables, listed in the README: `PODCAST_RECALL_HOME`, `CLIENT_SECRET_PATH`, `PODCAST_RECALL_VIDEO_REFRESH_DAYS` (default 30), and the Podcast Index credentials.
- The Google sign-in uses only the read-only scope, so it cannot read an email address. An account is identified by its YouTube channel ID and title.
- Locks use the operating system's file lock, and database backups use SQLite's backup feature.
- No secrets in code, logs or git.
- No Spotify or other platform content is sent to an LLM.
- Exports hold short quotes plus links, never full transcripts.
