# U1: YouTube Library Connector, Plan (v4, 2026-11-17)

## Approach
1. **Project set-up.** Python 3.12, `uv`. Change `pyproject.toml`: turn on packaging (`package = true`), set the package to `podcast_recall` at the repo root (flat layout), add the entry point `podcast-recall = podcast_recall.cli:main`, and add `pytest` and `ruff` as dev dependencies (ruff with line length 100). Add `keyring` as a dependency. Commit `uv.lock`. Add a `Makefile` with `test` and `lint` targets. Add a README section listing the settings (`PODCAST_RECALL_HOME`, `CLIENT_SECRET_PATH`, `PODCAST_RECALL_VIDEO_REFRESH_DAYS`).
2. **`podcast_recall/paths.py`.** Resolves the data folder (`PODCAST_RECALL_HOME`, default `~/.podcast-recall/`), creates it with permissions 700 (tightening and warning if it exists with looser ones), and gives paths for the database, logs, lock files and (later) audio and transcripts.
3. **`podcast_recall/models.py` and `errors.py`.** Result objects (`SyncResult`, `FetchResult`, channel rows) and the typed errors `NotSignedIn`, `QuotaExceeded`, `ApiError`, `ConfigError`. Typed errors are raised only when nothing could be done. Otherwise a `partial` result is returned.
4. **`podcast_recall/core.py`.** The public functions the web chat and CLI both call: `sync_library(user_id, on_progress=None)`, `fetch_videos(video_ids, user_id, on_progress=None)`, `list_channels(user_id, marked_only=False, refresh=False)`, `set_podcast_channel(user_id, channel_id, is_podcast)`, `revoke(user_id)` and `purge_stale_videos(max_age_days)`. No printing and no CLI logic.
5. **`auth.py`.** Google OAuth installed-app flow using `google-auth-oauthlib`, always requesting offline access with `prompt=consent`, and refusing if no refresh token returns. Checks the granted scope is exactly `youtube.readonly`. After sign-in, reads the user's own channel with `channels.list(mine=true)` and stores the channel ID and title on the user row. A different channel ID for an existing `user_id` is refused unless `--force`. Reads the client secret path from `CLIENT_SECRET_PATH` (default `~/.podcast-recall/client_secret.json`, matching the Week 0 scripts). Tokens go through a `TokenStore` interface with `get(user_id)`, `save(user_id, credentials_json)` and `delete(user_id)`. The Keychain implementation uses service `podcast-recall` and account `youtube:<user_id>`. An in-memory fake is used in tests. `revoke` also calls Google's revoke endpoint. `user_id` is validated against `[a-z0-9_-]{1,32}`.
6. **`youtube_client.py`.** The only place that calls the API. Pagination, retries (5 attempts, 1/2/4/8/16 s with jitter, only for network errors, 5xx and 429), a 30-second timeout, a per-method call counter, a quota estimate and a hard block on `search.list`. Defined behind a small interface so tests can use a fake client.
7. **`ids.py`.** Extracts video IDs from watch, `youtu.be`, shorts and embed URLs, ignoring `&t=` and `&list=`.
8. **`sync.py`.** Follows the sync order in the requirements: complete subscription listing first (updating `subscribed` flags only if it succeeded), then playlists (with titles), the user's channel and the uploads playlists of marked channels, then the video IDs of every source. For playlists and Liked videos, remove items only after that source's listing succeeded in full. Channel sources only add. Then call `videos.list` for IDs that are new or older than the refresh age. Detect placeholders by absence from the `videos.list` response, and skip and count them. Create or update a `channels` row from each video's metadata. Idempotent. Records a `sync_runs` row.
9. **`lock.py`.** An operating-system file lock (`flock`) per user in the data folder, so only one sync runs at a time and a crash never leaves a stuck lock.
10. **`store.py`.** SQLite access with WAL, foreign keys and a 5-second busy timeout. Migrations are forward-only numbered SQL files in `podcast_recall/migrations/`, each applied in a transaction at startup and tracked in `schema_version`. Before an upgrade, the database is backed up with SQLite's backup feature and the three most recent backups are kept. File permissions 600. `purge_stale_videos` deletes only rows that no foreign key refers to. U2 and U3 add their own migration files and declare foreign keys to `videos`.
11. **`logging_setup.py`.** Rotating log files (5 files of 1 MB) in the data folder, with a redaction filter that removes tokens, authorization headers, client secrets, URLs with tokens and email addresses. Results go to standard output, and progress, warnings and errors to standard error.
12. **`cli.py`.** Thin wrapper over `core.py` with the commands, output, `--user` option (all commands except `purge`) and exit codes in the requirements. `revoke` asks for confirmation unless `--yes`.
13. **Tests.** Unit tests use a fake `YouTubeClient` and sample JSON whose structure is copied from real API responses saved during the manual test, with every ID and text replaced by fake values, plus the in-memory `TokenStore`. Cases: placeholders, removed items, an item in several sources, an interrupted or failed listing (nothing removed), channel sources that never lose items during sync, unmarked and unsubscribed channels, an incomplete subscription listing (nobody unsubscribed), a video from an unsubscribed channel, quota exceeded partway (partial result) and before any call (typed error), an expired token, a wrong granted scope, a missing refresh token, a different channel for an existing user, a second sync at the same time, a killed sync releasing the lock, a purge that keeps a referenced video, log redaction, ID extraction from URLs, and the simulated-latency benchmark (300 ms per call; first sync at most 250 calls and 120 simulated seconds, repeat at most 150 calls and 60). One manual test against your real account.

## Constraints
- No secrets in code, logs, test fixtures or git. `client_secret.json` and token files are in `.gitignore`.
- Only the read-only scope. Refuse any other granted scope.
- Every API call goes through `youtube_client.py`. `search.list` is never called.
- `core.py` has no user-facing printing, so the web chat can reuse it.
- Every per-user table has `user_id`, even though v1 starts with one user.
- Items are removed from a playlist or Liked source only after its complete listing succeeded. Channel sources are never trimmed by sync.
- All runtime data lives in the data folder (D12), never in the repo.
- Settings come only from environment variables.

## Review checklist (PM)
- [ ] No tokens or secrets in the diff or logs, and a test proves log redaction
- [ ] Scope string is exactly `youtube.readonly`, and a wrong granted scope is refused
- [ ] The account is identified by channel ID and title, with no attempt to read an email address
- [ ] No call to `search.list` anywhere
- [ ] Running `sync` twice gives identical row counts, and the second run makes no `videos.list` calls for unchanged videos
- [ ] A listing that fails partway removes nothing, and the run is marked `partial`
- [ ] Channel sources are never trimmed by sync, only by unmark or unsubscribe, and nobody is unsubscribed after an incomplete subscription listing
- [ ] A video in two sources stays in the library when one source drops it
- [ ] Removing a video from a playlist and syncing removes it from the library
- [ ] A video from an unsubscribed channel still has a `channels` row
- [ ] Placeholders are detected because `videos.list` returned nothing, not by title text
- [ ] `channels list` fetches subscriptions when none are stored, and with `--refresh`
- [ ] `revoke` asks for confirmation, leaves no per-user rows (including `playlists` and `sync_runs`) and no Keychain entry, and calls Google's revoke endpoint. A failed Google call still deletes local data and warns
- [ ] `sync_library` and `fetch_videos` live in `core.py`, and the CLI only calls them
- [ ] Partial results are returned and typed errors are raised only when nothing could be done, with exit codes 0, 1, 2 and 3 as specified
- [ ] Database and data folder permissions are 600 and 700, and the data folder is outside the repo
- [ ] Tests fail if you break pagination, the ID comparison, placeholder handling, the safe-removal rule or the purge protection
- [ ] Nothing was added beyond the spec (no Spotify, no transcripts, no web sign-in)
