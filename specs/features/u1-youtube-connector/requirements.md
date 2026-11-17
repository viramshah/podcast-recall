# U1: YouTube Library Connector, Requirements (v4, 2026-11-17)

Branch: `feature/u1-youtube-connector`. Source: requirements doc section 1.5 (U1), adapted for YouTube-first and the web-chat front end (see `../../plan.md`). Decisions: D9 (library scope), D10 (shared episode data) and D12 (data location), all in `../../decisions.md`. v3 added the answers from the first ambiguity review. v4 fixes the contradictions found in the second pass.

## What done looks like
- A user signs in with Google (OAuth, read-only). The owner uses the Desktop-app flow. Token storage sits behind a small interface so the Week 6 web sign-in for testers can plug in without changing sync.
- The core library exposes `sync_library`, `fetch_videos`, `list_channels`, `set_podcast_channel`, `revoke` and `purge_stale_videos`. They return result objects and raise typed errors. They never print. The CLI is a thin wrapper, and the web chat will call the same functions.
- **The library (D9)** is: every video in the playlists the user **owns**, every video in Liked videos, and the uploads of channels the user has marked as "podcast". The API does not return playlists that belong to other people, even if the user saved them. State this limit in the CLI help.
- **Podcast-channel uploads are cumulative.** Each sync checks the latest 50 uploads of each marked channel and adds any that are new. Items do not drop out when newer uploads arrive. A sync **never removes** items from a channel source. They are removed only when the channel is unmarked or unsubscribed.
- **A video can be in several sources** (Liked, a playlist, a podcast channel). There is one library item per user, video and source. A video leaves the library only when no source contains it. `status` counts unique videos and also shows a count per source, using playlist titles.
- **Re-sync is incremental:** list the video IDs in each source every time, compare with what is stored, and fetch details only for new IDs and for stored videos not refreshed within the refresh age (default 30 days).
- **Safe removal (playlists and Liked videos):** items are removed from a source only after that source's complete listing succeeded. If listing fails or stops partway, nothing is removed from that source, and the run is marked `partial`.
- **Unmarked or unsubscribed channels:** unmarking a channel removes its `channel:<id>` library items at the next sync. A channel is treated as unsubscribed only after the complete subscription listing succeeded and no longer contains it. Its `subscribed` flag turns off and its items are removed, the same as unmarking. Shared `videos` and `channels` rows are never deleted by a sync.
- **Revoke** asks for confirmation (or `--yes`). It deletes the user's tokens and all per-user rows (`users`, `library_items`, `user_channels`, `playlists` and `sync_runs`), and calls Google's revoke endpoint. If the Google call fails (for example offline), the local deletion still happens and a warning tells the user to remove access at https://myaccount.google.com/connections.
- **Sync time target:** first sync no more than 250 API calls and 120 seconds, and a repeat sync no more than 150 calls and 60 seconds, on a library of about 200 subscriptions, 20 playlists, 2,000 playlist items and 10 podcast channels, with no stored video older than the refresh age. A mocked API runs instantly, so the benchmark test simulates 300 ms per call and asserts the call count and the computed time. Also record the size and sync time of the real account.
- **Identity:** `user_id` is a short local name matching `[a-z0-9_-]` and at most 32 characters. Every command except `purge` takes `--user <name>` (default `owner`). The read-only scope cannot read an email address, so the signed-in account is identified by its **YouTube channel ID and title**, read with `channels.list(mine=true)` and stored on the user row. One YouTube channel per `user_id`: signing in again for an existing user replaces the token, and a different channel ID is refused unless `--force` is given. An account with several channels (brand accounts) uses whichever channel was authorized at sign-in.
- **Sign-in rules:** always request offline access with `prompt=consent`, so Google returns a refresh token every time (refuse if none comes back). After sign-in, check the scope Google actually granted. It must be exactly `https://www.googleapis.com/auth/youtube.readonly`. If it is anything else, refuse and discard the token.
- After a revoke, `sync` for that user says "no sign-in found, please sign in again".

## Sync order
1. List all subscriptions (complete listing), then update each user's `subscribed` flags only if the listing succeeded.
2. List the user's playlists and store their IDs and titles.
3. Read the user's channel (`channels.list(mine=true)`) for the Liked-videos playlist ID, and the uploads playlist ID of each marked channel (cached on the `channels` row).
4. List the video IDs of every source.
5. Apply additions and removals per source, following the safe-removal rule.
6. Fetch details with `videos.list` for new or stale IDs, and store them. Create or update a `channels` row for each video's channel from the video metadata, so every video has a channel row even if the user is not subscribed to it.

## Scope
- OAuth 2.0 for a Desktop app, scope `https://www.googleapis.com/auth/youtube.readonly` only.
- Read calls allowed: `channels.list`, `subscriptions.list` (`mine=true`), `playlists.list` (`mine=true`), `playlistItems.list`, and `videos.list` (batches of 50, only for new or stale IDs).
- **Never** call `search.list`. It is not needed, and Google gives it its own small daily allowance.
- Store per video: video ID, title, channel ID, published date (UTC), duration in whole seconds, description (first 500 characters), `status` (`ok` or `unavailable`) with a reason, a flag for live or upcoming videos, and `last_fetched_at`.
- Duration comes from `videos.list` (an ISO 8601 text such as `PT1H2M3S`, converted to seconds). Playlist calls do not return it. U2 needs it to match episodes to feeds.
- Live, upcoming and premiere videos are stored with duration 0 and the flag set. Shorts are not filtered in v1.
- Store per library item: user, video, source (`playlist:<id>`, `liked`, or `channel:<id>`), first-seen time.
- **Placeholders:** a deleted or private video in a playlist is detected because `videos.list` returns nothing for its ID. Do not match on title text, which is localised. Such videos are skipped, counted and reported.
- **`fetch_videos`** fetches metadata for any list of IDs, whether or not they are in a user's library. It writes only to the shared `videos` and `channels` tables and never to `library_items`, so seed videos do not appear in a user's library and are never removed by a sync. An ID that returns nothing is recorded as `unavailable` with a reason, not dropped silently. It needs a signed-in user for API access.
- **`fetch` command input:** a CSV with a `youtube_url` column, a text file, or bare IDs. It understands watch URLs, `youtu.be` links, shorts and embed URLs, ignores `&t=` and `&list=`, removes duplicates and reports lines it could not parse. Exit code 0 if everything was fetched, 2 if some IDs were unavailable or unparsable, 1 on error.
- **Channels:** only subscribed channels can be marked in v1. `channels list` shows title, channel ID and whether it is marked, with marked channels first and then alphabetical, and `--marked` shows only marked ones. If no subscriptions are stored yet, or when `--refresh` is given, `channels list` first fetches the subscription list from YouTube. `channels mark` and `unmark` take the channel ID shown in the list.
- **CLI commands:** `auth`, `sync`, `status`, `revoke`, `channels list [--marked] [--refresh]`, `channels mark <channel_id>`, `channels unmark <channel_id>`, `fetch <csv, file or ids>` and `purge [--days N]`. All except `purge` take `--user`.
- **Terminal output:** results go to standard output. Progress, warnings and errors go to standard error.
- **`sync` output:** for each source, the items found, added and removed, plus a line of API calls made per method (for example `videos.list: 0`) and the estimated quota units. **`status`** shows the signed-in channel title, the last sync run (time, result and counts), unique videos, a count per source (playlist titles, liked, channel names), unavailable videos and the units used in the last run.
- **Result and exit-code mapping:** a run that completed is `ok` (exit 0). A run that saved some work but stopped early is `partial` (exit 2) and is **returned** as a result with a reason. If nothing could be saved, the matching typed error is raised, a `failed` run is recorded and the CLI exits 1 (exit 3 for `NotSignedIn`).
- **Typed errors** (raised only when nothing could be done): `NotSignedIn`, `QuotaExceeded` (exceeded before any call succeeded), `ApiError` and `ConfigError` (for example a missing client secret file).
- **Settings come only from environment variables**, documented in the README: `PODCAST_RECALL_HOME` (data folder), `CLIENT_SECRET_PATH`, and `PODCAST_RECALL_VIDEO_REFRESH_DAYS` (default 30).
- **Progress:** core functions take an optional `on_progress` callback. The CLI prints one line per source as it finishes.
- **Retries:** up to 5 attempts at 1, 2, 4, 8 and 16 seconds with jitter, only for network errors, HTTP 5xx and 429. Other 4xx errors are not retried. Requests are sequential with a 30-second timeout.
- **Quota:** estimate units per run (each list call costs 1 unit) and log them. A hard stop on HTTP 403 `quotaExceeded`. A persistent per-day counter is not required (the quota resets at midnight Pacific time).
- **One sync at a time per user**, using an operating-system file lock (`flock`) in the data folder, which is released automatically if the process dies. A second sync exits with a clear message.
- **Logging:** log files go in `<data folder>/logs/` with rotation (5 files of 1 MB). Never log tokens, authorization headers, client secrets, URLs containing tokens or email addresses. A redaction filter and a test enforce this.

## Edge cases the code must handle
- A playlist that is empty, or a library that is empty: succeed with zero items.
- Expired or revoked refresh token (Testing mode expires about weekly): stop with a clear "please sign in again" message and exit code 3, not a crash.
- Quota exceeded partway: stop gracefully, keep what was saved, return a `partial` result, exit code 2.
- A playlist deleted on YouTube: its items are removed at the next successful listing.
- A stored video that later becomes private or deleted: marked `unavailable` when it is refreshed.
- Running `sync` twice in a row: identical row counts, no duplicates.
- Interrupted sync (Ctrl+C or crash): no half-applied removals, the lock is released, and the next run recovers.
- Keychain locked or access denied: a clear error, not a crash.
- A video from a channel the user is not subscribed to: it still gets a `channels` row from the video metadata.

## Out of scope
- Spotify (v1.1).
- Watch history and Watch Later (not exposed by the API).
- Playlists owned by other people.
- Reading the Google email address (needs a permission beyond the read-only scope).
- Transcripts and RSS matching (U2 and U3).
- Any write access to the user's YouTube account.
- Web sign-in for testers (Week 6).

## Data stored locally (D12)
All runtime data lives in one folder, `~/.podcast-recall/`, which can be changed with `PODCAST_RECALL_HOME`. The folder has permissions 700 (if it already exists with looser permissions, tighten it and warn) and the database file 600. The repo's `data/` holds only the seed list and other small files that are safe to commit.

SQLite, one database file at `<data folder>/podcast_recall.db`. Settings: WAL mode, foreign keys on, 5-second busy timeout. Timestamps are UTC ISO-8601 text.
- **Shared tables:** `videos`, and `channels` (channel ID, title, cached uploads-playlist ID, last updated). `channels` holds every channel seen, from subscriptions or from video metadata.
- **Per-user tables:** `users` (user ID, YouTube channel ID and title, created time), `library_items`, `user_channels` (user, channel, `subscribed`, `is_podcast` default false), `playlists` (user, playlist ID, title, refreshed every sync) and `sync_runs` (user, start, end, result `ok`, `partial` or `failed`, counts, estimated units, error text).
- `schema_version` for migrations.

Every per-user row carries `user_id`. Migrations are forward-only numbered SQL files, each applied in a transaction at startup. Before an upgrade, back up the database with SQLite's own backup feature (not a plain file copy, which is unsafe while the database is open) and keep the three most recent backups. Later units add their own migration files.

Each `videos` row records `last_fetched_at`. `purge_stale_videos(max_age_days)` deletes shared video rows that have not been refreshed within the age limit and that **no other table refers to by foreign key**, and reports the rows it kept. U2 and U3 must declare their references to `videos` as foreign keys, so the purge protects them without U1 knowing about their tables. Revisit the age limit once the YouTube policy check (below) is done.

## Results
Core functions return result objects, for example a `SyncResult` with counts per source, calls per method, estimated units, the partial flag, the reason and warnings.

## PM tasks outside the code
- Read YouTube's API Services developer policies on how long API data may be stored and on deleting data after a user revokes access. I have not verified the exact rules, and an independent review said stored API data may need to be refreshed or deleted within about 30 days. Record what you find in `decisions.md` before testers join, and set the 30-day defaults to match.

## Left to the agent
Internal function names, file layout inside the package, SQL indexes and test names. Claude Code should still list anything else that is unclear before it writes code.
