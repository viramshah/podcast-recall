# U1: YouTube Library Connector, Validation

Run these yourself before merging.

## Automated
1. `make test` passes with zero failures.
2. `ruff check .` is clean.

## Manual, against your real account
| # | Step | Expected |
|---|---|---|
| 1 | `podcast-recall auth` and sign in with your Google account | Browser consent shows only "View your YouTube account"; CLI prints success |
| 2 | Check Keychain Access for the Podcast Recall entry | Entry exists; no token files in the repo folder |
| 3 | `podcast-recall sync` and time it | Under 2 minutes; prints counts of subscriptions, playlists, videos, and estimated quota units |
| 4 | `podcast-recall status` | Counts match what you see in YouTube (spot-check 5 subscriptions and one playlist) |
| 5 | `podcast-recall sync` again | Completes faster; no duplicate rows; quota use lower than the first run |
| 6 | Subscribe to one new channel, then `sync` | New channel appears, others unchanged |
| 7 | `podcast-recall revoke` | Keychain entry gone; database has no rows for the user |
| 8 | Run `sync` after revoke | Clear "please sign in again" message, no crash |
| 9 | Search the repo and logs for your refresh token or client secret | No matches |

## Exit gate
All nine manual steps pass and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, and merge.
