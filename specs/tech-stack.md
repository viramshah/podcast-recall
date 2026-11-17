# Podcast Recall: Tech Stack (locked for v1)

Change an entry only by editing this file and recording why in `decisions.md`.

| Layer | Choice | Cost | Why |
|---|---|---|---|
| Language and tooling | Python 3.12, `uv`, `pytest`, `ruff` | $0 | Fits the ML libraries and FastAPI |
| Transcription | `mlx-whisper` (fallback `whisper.cpp`), local, word timestamps | $0 | Runs on Apple Silicon; timestamps power citations |
| Embeddings | `nomic-embed-text` via Ollama (or a `bge` model via sentence-transformers) | $0 | Local, small |
| Reranker | Open reranker model, local | $0 | Improves recall@5 |
| Answer LLM | One 7-9B instruct model via Ollama | $0 | Sized for 16GB RAM |
| Judge LLM | A model from a different family than the answer model | $0 | Reduces self-preference bias |
| Storage and search | SQLite, FTS5, `sqlite-vec` | $0 | One file, no server |
| Core library | Plain Python package: `sync_library`, `search_episodes`, `ask`, `get_transcript`, `save_finding`, `export_findings` | $0 | One implementation shared by the web chat, CLI and eval harness (D7) |
| Web chat | FastAPI + uvicorn, one static HTML page, bound to `127.0.0.1` | $0 | Replaces the MCP client; testers need a browser only |
| CLI | `podcast-recall` command (`auth`, `sync`, `ask`, `status`, `revoke`) | $0 | Development and eval use |
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
- `search.list` is never called, because it costs 100 YouTube quota units per call.
- No secrets in code, logs or git.
- No Spotify or other platform content is sent to an LLM.
- Exports hold short quotes plus links, never full transcripts.
