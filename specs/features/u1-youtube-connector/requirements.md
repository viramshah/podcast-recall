# U1: YouTube Library Connector, Requirements (v2, 2026-11-17)

Branch: `feature/u1-youtube-connector`. Source: requirements doc section 1.5 (U1), adapted for YouTube-first and the web-chat front end (see `../../plan.md`). Decisions: D9 (library scope) and D10 (shared episode data), both in `../../decisions.md`.

## What done looks like
- A user signs in with Google (OAuth, read-only). The owner uses the Desktop-app flow. Token storage sits behind a small interface so the Week 6 web sign-in for testers can plug in without changing sync.
- The core library exposes `sync_library(user_id)` and `fetch_videos(video_ids)`. The CLI is a thin wrapper over them. The web chat will call the same functions.
- The library is: every video in the user's playlists, every video in Liked videos, plus recent uploads (latest 50) for the channels the user has marked as "podcast". Subscribed channels are stored with a `is_podcast` flag, default false.
- Re-sync is incremental: list the IDs in each source every time, compare with what is stored, and fetch details only for new IDs.
- Items removed from a playlist or unliked are removed from that user's library. If a channel is unmarked as podcast, its `channel:<id>` library items are removed at the next sync. Shared `videos` and `channels` rows are never deleted by a sync.
- "Revoke access" deletes the user's tokens and library rows locally and also calls Google's revoke endpoint.
- Sync time target: first sync under 2 minutes and a repeat sync under 1 minute, on a library of about 200 subscriptions, 20 playlists, 2,000 playlist items and 10 podcast channels. Prove it with a benchmark test against a mocked API at that size. Also record the size and sync time of your real account, which may be smaller.
- Each user's tokens, library list and podcast-channel flags are separate. Episode data is shared (D10).
- `user_id` is a short local name chosen with `auth --user <name>` (default `owner`). The Google account email is stored as an attribute of the user. `revoke` deletes the user row. After a revoke, `sync` for that user says "no sign-in found, please sign in again".

## Scope
- OAuth 2.0 for a Desktop app, scope `https://www.googleapis.com/auth/youtube.readonly` only.
- Read calls allowed: `channels.list` (find the Liked and uploads playlist IDs), `subscriptions.list` (`mine=true`), `playlists.list` (`mine=true`), `playlistItems.list`, and `videos.list` (metadata, batches of 50, only for IDs not already stored).
- **Never** call `search.list`. It is not needed, and Google gives it its own small daily allowance.
- Store per video: video ID, title, channel ID and name, published date, duration, description snippet, last-fetched time. Duration comes from `videos.list`, because playlist calls do not return it. U2 needs it to match episodes to feeds.
- Store per library item: user, video, source (playlist ID, `liked`, or `channel:<id>`), first-seen time.
- `fetch_videos(video_ids)` fetches metadata for any list of IDs, whether or not they are in the user's library. It is used to load the 20 seed episodes in `data/seed_episodes.csv`. It writes only to the shared `videos` table and never to `library_items`, so seed videos do not appear in a user's library and are never removed by a sync. An ID that returns nothing (deleted, private or mistyped) is recorded as `unavailable` with a reason, not dropped silently.
- CLI commands: `auth`, `sync`, `status`, `revoke`, `channels list`, `channels mark <channel_id>`, `channels unmark <channel_id>`, `fetch <csv or ids>`.
- Estimate and log quota units used per sync.

## Edge cases the code must handle
- "Deleted video" and "Private video" placeholders in playlists: skip them and report the count.
- A playlist that is empty, or a library that is empty: succeed with zero items.
- Expired or revoked refresh token (Testing mode expires about weekly): stop with a clear "please sign in again" message, not a crash.
- Quota exceeded (HTTP 403 `quotaExceeded`): stop gracefully, keep what was saved, and mark the sync as partial.
- Running `sync` twice in a row: identical row counts, no duplicates.

## Out of scope
- Spotify (v1.1).
- Watch history and Watch Later (not exposed by the API).
- Transcripts and RSS matching (U2 and U3).
- Any write access to the user's YouTube account.
- Web sign-in for testers (Week 6).

## Data stored locally
SQLite, one database. Shared tables: `videos`, `channels`. Per-user tables: `users`, `library_items`, `user_channels` (holds the `is_podcast` flag). Every per-user row carries `user_id`. The schema is owned by this unit; later units add to it through numbered migration files (see the plan). Each `videos` row records `last_fetched_at`, and a `purge_stale_videos(max_age_days)` function can delete shared video metadata that has not been refreshed within the allowed time (see the PM task below).

## PM tasks outside the code
- Read YouTube's API Services developer policies on how long API data may be stored and on deleting data after a user revokes access. I have not verified the exact rules, and an independent review said stored API data may need to be refreshed or deleted within about 30 days. Record what you find in `decisions.md` before testers join, and set the `purge_stale_videos` default to match.

## Open questions for Claude Code to raise before coding
- Where the SQLite file lives and how migrations are handled.
- How progress is reported during a long sync.
- How the token storage interface should be shaped so web sign-in can replace the Desktop flow later.
