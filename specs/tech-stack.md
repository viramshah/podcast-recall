# Podcast Recall: Tech Stack (locked for v1)

Change an entry only by editing this file and recording why in `decisions.md`.

| Layer | Choice | Cost | Why |
|---|---|---|---|
| Language and tooling | Python 3.12, `uv`, `pytest`, `ruff` | $0 | Fits the MCP SDK and ML libraries |
| Transcription | `mlx-whisper` (fallback `whisper.cpp`), local, word timestamps | $0 | Runs on Apple Silicon; timestamps power citations |
| Embeddings | `nomic-embed-text` via Ollama (or a `bge` model via sentence-transformers) | $0 | Local, small |
| Reranker | Open reranker model, local | $0 | Improves recall@5 |
| Answer LLM | One 7-9B instruct model via Ollama | $0 | Sized for 16GB RAM |
| Judge LLM | A model from a different family than the answer model | $0 | Reduces self-preference bias |
| Storage and search | SQLite, FTS5, `sqlite-vec` | $0 | One file, no server |
| MCP server | Official MCP Python SDK, stdio | $0 | Works in Claude Desktop |
| Platform data | YouTube Data API v3 (read-only, free quota), Podcast Index API (free key) | $0 | |
| Auth storage | macOS Keychain via `keyring` | $0 | Tokens never in files |
| Export | Markdown, Google Docs API, Apple Notes (AppleScript), Notion API | $0 | Notion is the first cut if time runs short |
| Tester access | Cloudflare Tunnel (free) | $0 | |
| CI and evals | GitHub Actions for unit tests and deterministic checks; local `make eval` for LLM-judged runs | $0 | |

## Deferred
- Spotify Web API (v1.1).

## Rules
- Only the `youtube.readonly` OAuth scope.
- No secrets in code, logs or git.
- No Spotify or other platform content is sent to an LLM.
- Exports hold short quotes plus links, never full transcripts.
