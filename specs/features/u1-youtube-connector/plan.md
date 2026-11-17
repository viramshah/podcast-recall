# U1: YouTube Library Connector, Plan

## Approach
1. Project skeleton: Python 3.12, `uv`, package `podcast_recall/`, `pytest`, `ruff`, and a `make test` target.
2. `auth.py`: Google OAuth installed-app flow using `google-auth-oauthlib`. Read `client_secret.json` from a path given by an env var. Store the refresh token in macOS Keychain (via `keyring`).
3. `youtube_client.py`: thin wrapper over the YouTube Data API with pagination, retry with backoff, and a quota counter. No calls from anywhere else.
4. `sync.py`: first sync pulls everything; later syncs use stored etags and the newest `publishedAt` per source to fetch only changes. Idempotent: running twice makes no duplicates.
5. `store.py`: SQLite access and migrations.
6. `cli.py`: commands `auth`, `sync`, `status`, `revoke`.
7. Unit tests with the API mocked. One manual integration test against your real account.

## Constraints
- No secrets in code, logs, test fixtures or git. `client_secret.json` and token files are in `.gitignore`.
- Only the read-only scope. Fail if a broader scope is requested.
- Every API call goes through `youtube_client.py`.

## Review checklist (PM)
- [ ] No tokens or secrets in the diff or logs
- [ ] Scope string is exactly `youtube.readonly`
- [ ] Running `sync` twice gives identical row counts
- [ ] `revoke` leaves no rows and no Keychain entry for that user
- [ ] Tests fail if you break pagination or incremental logic
- [ ] Nothing was added beyond the spec (no Spotify, no transcripts)
