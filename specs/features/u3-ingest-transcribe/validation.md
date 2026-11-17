# U3: Ingest and Transcribe, Validation (v1, 2026-11-17)

Run these yourself before merging. They use the 20 seed episodes after U2 has matched them.

## Automated
1. `make test` passes, including the crash-recovery, retry and download-failure tests.
2. `make lint` is clean.

## Manual
| # | Step | Expected |
|---|---|---|
| 1 | Before the full run, transcribe one hand-picked 5-minute section with the small model and with one larger model, and compare both against what you hear | You can see which model is accurate enough for exact quotes. Record the choice and why in `decisions.md` |
| 2 | Transcribe 5 minutes of one Raj Shamani episode | You can judge whether the language handling (D11) is acceptable. Record the result in `decisions.md` |
| 3 | `podcast-recall transcribe run --limit 2` | Two episodes finish. `transcribe status` shows them as `done`. Audio files are deleted |
| 4 | Start `transcribe run`, then stop it with Ctrl+C mid-episode, then run it again | The job restarts cleanly. No duplicate transcript. No half-written file |
| 5 | Start two `transcribe run` commands at the same time | The second exits with a clear message that a worker is already running |
| 6 | `podcast-recall transcribe run --overnight` for the remaining matched seed episodes | Every seed episode whose expected outcome is `matched` (the 15 `y` rows) ends as `done`, or its failure is explained and fixed. Total time is noted and reasonable |
| 7 | `podcast-recall transcribe status` | Counts by state. Any `failed` job shows its reason |
| 8 | For 5 episodes, use `transcribe show <episode_id> --at mm:ss` at 3 different times and compare with the audio | Words match what is said, and the timestamp is within about 2 seconds of the real position |
| 9 | Check the quality flags for all transcripts | Each transcript's length is within about 2% of the audio duration. Any flagged transcript is explained |
| 10 | Check that the 5 `n` seed rows were never downloaded | `transcribe status` lists them as `not_indexable` (worked out from U2, no job row). No audio or transcript exists for them |
| 11 | Search the repo and logs for secrets, and `git status` for transcript or audio files | No secrets. Audio and transcripts are not tracked by git |

## Record the results
- The Whisper model chosen, the real-time factor measured on the full run, and any episodes that failed quality checks, in `decisions.md`.
- Whether the Hindi or Hinglish episodes stay in the golden set (D11).
- The comparison of a publisher transcript with Whisper on the same 5-minute section, and the decision on D13.

## Exit gate
All eleven manual steps pass and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, and merge.
