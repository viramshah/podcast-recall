# U1: YouTube Library Connector, Validation (v2, 2026-11-17)

Run these yourself before merging.

## Automated
1. `make test` passes with zero failures.
2. `make lint` (ruff) is clean.

## Manual, against your real account
| # | Step | Expected |
|---|---|---|
| 1 | `podcast-recall auth` and sign in with your Google account | Browser consent shows only "View your YouTube account"; CLI prints success |
| 2 | Check Keychain Access for the Podcast Recall entry | Entry exists; no token files in the repo folder |
| 3 | `podcast-recall channels list`, then `channels mark <id>` for 2-3 podcast channels | Channels are listed; marked ones show as podcast |
| 4 | `podcast-recall sync` and time it | Prints counts for playlists, Liked videos, podcast-channel uploads and estimated quota units; under 2 minutes for a library of about 200 subscriptions, 20 playlists and 2,000 items |
| 5 | `podcast-recall status` | Counts match what you see in YouTube (spot-check 5 subscriptions, one playlist and your Liked videos) |
| 6 | `podcast-recall sync` again | Under 1 minute; no duplicate rows; no `videos.list` calls for unchanged videos |
| 7 | Add one video to a test playlist, remove another, then `sync` | Library shows exactly one added and one removed; nothing else changes |
| 8 | Add a private or deleted video to a test playlist, then `sync` | It is skipped and counted, with no crash |
| 9 | `podcast-recall fetch data/seed_episodes.csv` | All 20 seed videos return title, channel, date and duration, including episodes not in your library |
| 10 | `podcast-recall revoke` | Keychain entry gone; database has no rows for the user; the app no longer appears under your Google account's third-party access |
| 11 | Run `sync` after revoke | Clear "please sign in again" message, no crash |
| 12 | Search the repo and logs for your refresh token or client secret | No matches |

## Exit gate
All twelve manual steps pass and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, and merge.
