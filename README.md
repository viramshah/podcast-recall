# Podcast Recall

A local app that answers questions from your YouTube podcast library with verified quotes,
timestamps and links. This README covers the U1 YouTube connector. The product plan is in
`specs/`.

## Setup

```bash
uv sync
```

Create a Google Cloud OAuth client of type "Desktop app", enable the YouTube Data API v3, and
save the downloaded file as `~/.podcast-recall/client_secret.json` (or point `CLIENT_SECRET_PATH`
at it). Keep it out of the repo.

## Settings

Settings come only from environment variables.

| Variable | Default | Meaning |
|---|---|---|
| `PODCAST_RECALL_HOME` | `~/.podcast-recall` | Data folder: database, logs, backups, locks (later: audio and transcripts). Permissions 700. |
| `CLIENT_SECRET_PATH` | `~/.podcast-recall/client_secret.json` | Google OAuth client file. |
| `PODCAST_RECALL_VIDEO_REFRESH_DAYS` | `30` | Stored video details older than this are fetched again during `sync`. |
| `PODCASTINDEX_KEY`, `PODCASTINDEX_SECRET` | none | Podcast Index credentials for `resolve`. If unset, they are read from `<data folder>/podcastindex.env` (lines like `export PODCASTINDEX_KEY=...`, permissions 600). |

## Commands

All commands except `purge` take `--user <name>` (default `owner`).

```bash
uv run podcast-recall auth                 # sign in with Google (read-only)
uv run podcast-recall channels list        # your subscriptions (fetched on first use)
uv run podcast-recall channels mark <id>   # treat a channel as a podcast
uv run podcast-recall sync                 # playlists, Liked videos, marked channels
uv run podcast-recall status
uv run podcast-recall fetch data/seed_episodes.csv
uv run podcast-recall revoke               # asks for confirmation (--yes to skip)
uv run podcast-recall purge --days 30
```

Exit codes: 0 success, 1 error, 2 partial result or something needs attention, 3 sign-in needed.

### Matching videos to podcast episodes (U2)

```bash
uv run podcast-recall fetch data/seed_episodes.csv     # load the seed videos first
uv run podcast-recall resolve feeds --seed             # choose a podcast feed for each channel
uv run podcast-recall resolve run --seed               # match videos to episodes, write data/seed_resolver_check.csv
uv run podcast-recall resolve review --seed            # results that need a human look
uv run podcast-recall resolve confirm <video_id> <episode_id>
uv run podcast-recall resolve reject <video_id>
uv run podcast-recall resolve set-feed <channel_id> <feed URL | feed ID | none>
```

Without `--seed`, `resolve` works on the videos in your library. Results you confirm or reject are
never overwritten by a later `resolve run`.

Limit: the YouTube API only returns playlists you own. Playlists that belong to other people are
not included, even if you saved them.

## Tests

```bash
make test    # pytest
make lint    # ruff
```
