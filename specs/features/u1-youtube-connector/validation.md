# U1: YouTube Library Connector, Validation (v4, 2026-11-17)

Run these yourself before merging.

## Automated
1. `make test` passes with zero failures. It includes the simulated-latency benchmark (first sync at most 250 calls and 120 simulated seconds; repeat at most 150 calls and 60), the interrupted-listing test (nothing removed), the multiple-sources test, the placeholder test, the scope, refresh-token and different-channel tests, the purge-protection test and the log-redaction test.
2. `make lint` (ruff) is clean.

## Manual, against your real account
| # | Step | Expected |
|---|---|---|
| 1 | `podcast-recall auth --user owner` and sign in with your Google account | Browser consent shows only "View your YouTube account"; CLI prints success and your YouTube channel title (not an email) |
| 2 | Run `podcast-recall auth --user owner` a second time | The token is replaced; there is still exactly one `podcast-recall` entry for `youtube:owner` in Keychain Access |
| 3 | Check Keychain Access for the `podcast-recall` entry (account `youtube:owner`), and look in `~/.podcast-recall/` | Entry exists; no token files in the repo or the data folder; the folder is 700 and the database 600 |
| 4 | `podcast-recall channels list` (before any sync), then `channels mark <channel_id>` for 2-3 podcast channels, then `channels list --marked` | The list is fetched from YouTube even though you have not synced; marked ones show as podcast; the filtered list shows only those |
| 5 | `podcast-recall sync` and time it | Prints, per source, items found, added and removed, a line of API calls per method and the estimated quota units. Write down your account's size and the time taken |
| 6 | `podcast-recall status` | Shows your channel title, last sync, unique videos, a count per source with playlist titles, and unavailable videos. Counts match YouTube (spot-check 5 subscriptions, one playlist and your Liked videos) |
| 7 | `podcast-recall sync` again | Under 1 minute; no duplicate rows; the output shows `videos.list: 0` for unchanged videos |
| 8 | On the YouTube website (the app has no write access), add one video to a test playlist and remove another, then `sync` | Library shows exactly one added and one removed; nothing else changes |
| 9 | **Only if one exists:** if one of your playlists already contains a "Deleted video" or "Private video" row, run `sync` | It is skipped and counted, with no crash. You cannot create one on demand, so the automated placeholder test covers this otherwise |
| 10 | `podcast-recall fetch data/seed_episodes.csv`, then `echo $?` | All 20 seed videos return title, channel, date and duration, including episodes not in your library. They do not appear in the library counts in `status`. Exit code is 0, or 2 if some were unavailable |
| 11 | Start `sync` in one terminal and, while it runs, start `sync` in a second | The second exits with a clear "a sync is already running" message |
| 12 | Start `sync`, stop it with Ctrl+C partway, then run `sync` again | The second run completes normally with no stuck lock and no missing or duplicate rows |
| 13 | `podcast-recall revoke` without `--yes` | It asks for confirmation. Answer no, and nothing changes |
| 14 | `podcast-recall revoke --yes` | Keychain entry gone; the `users`, `library_items`, `user_channels`, `playlists` and `sync_runs` tables have no rows for the user (shared `videos` and `channels` rows stay, by design); the app no longer appears at https://myaccount.google.com/connections |
| 15 | Run `sync` after revoke, then `echo $?` | Clear "no sign-in found, please sign in again" message, exit code 3, no crash |
| 16 | Search the repo, the data folder's log files and your terminal history for your refresh token or client secret | No matches |
| 17 | Save one scrubbed sample of each API response type the code reads (IDs and text replaced with fake values) | The sample files exist for the test fixtures, with no real data in them |

## Exit gate
All seventeen manual steps pass (step 9 only if applicable) and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, and merge.
