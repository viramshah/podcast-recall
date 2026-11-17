# U1: YouTube Library Connector, Requirements

Branch: `feature/u1-youtube-connector`. Source: requirements doc section 1.5 (U1), adapted for YouTube-first (see `../../plan.md`).

## What done looks like
- A user signs in with Google (OAuth, read-only) and the app stores their library locally: subscriptions, their playlists, and Liked videos.
- Tokens are stored in the macOS Keychain, never in files or logs.
- Re-sync is incremental: only new or changed items are fetched after the first run.
- A tester's library syncs in under 2 minutes.
- "Revoke access" removes that user's tokens and all their stored library data.
- Each user's data is isolated from other users' data.

## Scope
- OAuth 2.0 for a Desktop app, scope `https://www.googleapis.com/auth/youtube.readonly` only.
- Read: `subscriptions.list` (`mine=true`), `playlists.list` (`mine=true`), `playlistItems.list`, and the Liked videos playlist.
- Store per video: video ID, title, channel ID and name, published date, duration, playlist or subscription source, last-synced time.
- Handle the expired refresh token (Testing mode, 7 days) with a clear "please sign in again" message, not a crash.
- Respect the API quota (10,000 units/day by default). Log estimated units used per sync.

## Out of scope
- Spotify (v1.1).
- Watch history and Watch Later (not exposed by the API).
- Transcripts, RSS matching (U2 and U3).
- Any write access to the user's YouTube account.

## Data stored locally
SQLite tables: `users`, `channels`, `videos`, `library_items` (user, video, source, synced_at). Schema owned by this unit; later units add to it.

## Open questions for Claude Code to raise before coding
- Where the SQLite file lives and how per-user isolation is implemented (separate file per user vs user_id column).
- How to detect "changed" items for incremental sync (use `etag` and `publishedAt`).
