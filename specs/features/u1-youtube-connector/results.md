# U1: YouTube Library Connector, Validation Results

Recorded 2026-11-17 against the PM's real account. Spec: `validation.md` (v4).

Automated: `make test` 107 passed (pytest). `make lint`: All checks passed (ruff 0.17.5). `make test`: 108 passed after the log-folder permission fix.

| # | Step | Result | Evidence |
|---|---|---|---|
| 1 | `auth` | Passed | Printed `Signed in as YouTube channel 'Viram Shah'`. Consent URL showed only the `youtube.readonly` scope. |
| 2 | `auth` again | Passed | Printed "The saved sign-in was replaced." Keychain entry count not checked by hand yet. |
| 3 | Data folder and database permissions | Passed | `~/.podcast-recall` is `drwx------`; database, lock file and `client_secret.json` are `-rw-------`. The first run tightened the folder from 755 to 700 and warned. |
| 4 | `channels list`, `mark`, `--marked` | Passed (output not pasted for `--marked`) | Subscriptions were fetched before any sync. Lenny's Podcast, Greg Isenberg and Raj Shamani were marked and synced as `channel:` sources. |
| 5 | `sync` first run | Passed | 6.3 s, 20 quota units. Liked 166 found, 150 added, 16 unavailable skipped. Three channels 50 each. 300 video details in 7 batches. |
| 6 | `status` | Passed (only the last line was pasted) | After a fresh sync: `Unavailable: 0 in library, 16 skipped in last sync`. An earlier status showed an empty library only because it ran right after revoke and re-sign-in. |
| 7 | `sync` again | Passed | `videos.list: 0`, nothing added, 13 quota units. |
| 8 | Add and remove a playlist item | Passed (removal) | Test playlist `found 3, added 0, removed 1` after removing a video on YouTube. The add run was not pasted. |
| 9 | Deleted or private playlist item | Covered by real data | 16 unavailable videos in Liked were skipped and counted with no crash. Also covered by an automated test. |
| 10 | `fetch data/seed_episodes.csv` | Passed | 20 requested, 20 fetched, 0 unavailable, exit code 0, 1 quota unit. `status` unchanged after fetch is still to be confirmed. |
| 11 | Two syncs at once | Passed (reported by the PM, output not recorded) | Also covered by an automated test. |
| 12 | Interrupted sync | Passed (reported by the PM, output not recorded) | Also covered by an automated test of a killed process freeing the lock. |
| 13 | `revoke` without `--yes` | Reported done by the PM, output not recorded | |
| 14 | `revoke --yes` | Reported done by the PM, output not recorded | The shared `videos` table was kept by design, which matches the database still being large afterwards. |
| 15 | `sync` after revoke | Reported done by the PM, output not recorded | |
| 16 | Search repo and logs for secrets | Passed | `grep` for `ya29.`, `1//0` and `GOCSPX` over the logs, code, scripts, specs, docs, README, Makefile and pyproject printed nothing. |
| 17 | Save scrubbed real API response samples | Deferred by the PM (2026-11-17) | Test fixtures stay hand-written. See Known limits. |

## Findings
- None of the seed shows' channels were subscribed at first, so those episodes entered through Liked videos. After subscribing, they also arrive through `channel:` sources. Only subscribed channels can be marked (D9). Decide whether v1.1 should allow marking any channel by ID.
- Liked videos contained 16 deleted or private videos. They are now handled.
- The `logs` folder was created with permissions 755. Fixed: the folder is now 700 and the log file 600.

## Known limits
- Test fixtures for the YouTube client are hand-written, not copied from real responses (step 17 deferred). Real syncs of 166 Liked videos, three channels and a playlist worked against live YouTube, so the shapes in use today are right. The tests would not catch Google changing a response shape later. Revisit if a sync starts failing with an unexpected-response error, or before U1 is reused for testers.
- The Google email address cannot be read with the read-only scope. Accounts are identified by YouTube channel ID and title.
- Only subscribed channels can be marked as podcasts (D9). Marking any channel by ID is a possible v1.1 change.

## Exit gate
Met on 2026-11-17, with step 17 deferred. Steps 11 to 15 were reported done by the PM without recorded output.
