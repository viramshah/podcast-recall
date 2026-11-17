# U1: YouTube Library Connector, Plan (v2, 2026-11-17)

## Approach
1. **Project set-up.** Python 3.12, `uv`. Change `pyproject.toml`: turn on packaging (`package = true`), add a `podcast-recall` command entry, and add `pytest` and `ruff` as dev dependencies. Add a `Makefile` with `test` and `lint` targets. Add `keyring` as a dependency.
2. **`podcast_recall/core.py`.** The public functions the web chat and CLI both call: `sync_library(user_id)`, `fetch_videos(video_ids)`, `list_channels(user_id)`, `set_podcast_channel(user_id, channel_id, is_podcast)`, `revoke(user_id)`. No printing and no CLI logic here.
3. **`auth.py`.** Google OAuth installed-app flow using `google-auth-oauthlib`. Reads the client secret path from `CLIENT_SECRET_PATH` (default `~/.podcast-recall/client_secret.json`, matching the Week 0 scripts). Tokens go through a `TokenStore` interface. The first implementation stores the refresh token in macOS Keychain (via `keyring`), keyed by user. `revoke` also calls Google's revoke endpoint. The user is identified by `user_id` (a local name, default `owner`), and the Google email is stored as an attribute.
4. **`youtube_client.py`.** The only place that calls the API. Pagination, retry with backoff, a quota counter, and a hard block on `search.list`.
5. **`sync.py`.** For each source (every playlist, Liked videos, and the latest 50 uploads of each podcast channel): list all video IDs, compare with stored library items, add new ones and remove missing ones, then call `videos.list` only for IDs not yet in the `videos` table. Skip deleted and private placeholders and count them. Idempotent.
6. **`store.py`.** SQLite access and migrations. Shared `videos` and `channels`; per-user `users`, `library_items`, `user_channels`. Migrations are numbered SQL files in `podcast_recall/migrations/`, applied in order and tracked in a `schema_version` table. U2 and U3 add their own migration files.
7. **`cli.py`.** Thin wrapper over `core.py` with the commands in the requirements.
8. **Tests.** Unit tests with the YouTube API mocked, including deleted and private placeholders, removed items, quota exceeded and an expired token. One manual test against your real account.

## Constraints
- No secrets in code, logs, test fixtures or git. `client_secret.json` and token files are in `.gitignore`.
- Only the read-only scope. Fail if a broader scope is requested.
- Every API call goes through `youtube_client.py`. `search.list` is never called.
- `core.py` has no user-facing printing, so the web chat can reuse it.
- Every per-user table has `user_id`, even though v1 starts with one user.

## Review checklist (PM)
- [ ] No tokens or secrets in the diff or logs
- [ ] Scope string is exactly `youtube.readonly`
- [ ] No call to `search.list` anywhere
- [ ] Running `sync` twice gives identical row counts, and the second run makes no `videos.list` calls for unchanged videos
- [ ] Removing a video from a playlist and syncing removes it from the library
- [ ] `revoke` leaves no rows and no Keychain entry for that user, and calls Google's revoke endpoint
- [ ] `sync_library` and `fetch_videos` live in `core.py`, and the CLI only calls them
- [ ] Tests fail if you break pagination, the ID comparison or placeholder handling
- [ ] Nothing was added beyond the spec (no Spotify, no transcripts, no web sign-in)
