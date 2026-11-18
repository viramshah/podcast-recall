# U3: Ingest and Transcribe, Validation (v2, 2026-11-17)

Run these yourself before merging. They use the 20 seed episodes after U2 has matched them (16 `matched`, 4 not). Whisper needs the model downloaded once (done in Week 0). For long runs, keep the Mac awake with `caffeinate -i`.

## Automated
1. `make test` passes, including the crash-recovery, retry, one-worker, redirect-refusal, publisher-parsing and fallback tests.
2. `make lint` is clean.

## Manual
| # | Step | Expected |
|---|---|---|
| 1 | Before the full run, transcribe one hand-picked 5-minute section with the small model and with one larger model (`scripts/transcribe_test.py --model ...`), and compare both against what you hear | You can see which model is accurate enough for exact quotes. Record the choice and why in `decisions.md` |
| 2 | Run `scripts/compare_transcripts.py` on a Lenny's episode (publisher transcript versus Whisper) and judge the disagreement table by listening | You can decide whether publisher transcripts are accurate and precise enough (D13). Record the result |
| 3 | Transcribe 5 minutes of one Raj Shamani episode with Whisper and read it | You can judge the language handling (D11). Record the result and whether those episodes stay in the golden set |
| 4 | `podcast-recall transcribe run --seed --limit 2` | Two episodes finish. `transcribe status` shows them. No audio files remain |
| 5 | Start `transcribe run --seed`, stop it with Ctrl+C during a Whisper episode, then run it again | The job restarts cleanly. No duplicate transcript and no half-written file. The attempt count did not go up |
| 6 | Start two `transcribe run` commands at the same time | The second exits with a clear message that a worker is already running |
| 7 | `caffeinate -i uv run podcast-recall transcribe run --seed` for the rest | Every seed episode whose expected outcome is `matched` (16) ends as `done`, or its failure is explained and fixed. Total time is noted and reasonable |
| 8 | `podcast-recall transcribe status --seed` | Counts of transcripts `ok` and `needs_review`, jobs by state, the reason for each failed job, 4 videos `not_indexable`, and the disk used |
| 9 | Look at which seed episodes used the publisher transcript and which used Whisper | Lenny's episodes mostly `publisher`. Raj Shamani's all `whisper`. Greg Isenberg's a mix. For each `publisher` one, no audio was downloaded |
| 10 | For 5 episodes (at least 2 publisher and 2 Whisper), use `transcribe show <episode_id> --at mm:ss` at 3 times each and compare with the audio | Words match what is said, and the time is within about 15 seconds for publisher transcripts and about 2 seconds for Whisper |
| 11 | Look at the flags on all transcripts | Each `needs_review` transcript is explained. Use `transcribe accept` for the ones you judge fine, or `transcribe retry <id> --whisper` for the others |
| 12 | Point one episode's stored transcript link at a broken URL (on a copy of the database) and run | It falls back to Whisper and records the reason |
| 13 | Check that the 4 `n` seed rows were never downloaded | `transcribe status` lists them as `not_indexable`. No audio, raw file or transcript exists for them |
| 14 | Search the repo, the logs and the database for secrets, and `git status` for transcript or audio files | No secrets. Audio and transcripts are not tracked by git |
| 15 | (D16) On a copy of the data folder, run `transcribe retry <Raj Shamani id> --whisper` with the default small model, then `transcribe run --seed` | Small is stopped at the time limit or flagged, then the episode is retried with turbo. The result is `ok`, its model is `whisper-large-v3-turbo`, its flags include `retried_with_larger_model`, and the reason explains why. Takes about an hour |

## Record the results
- The Whisper model chosen and why, the real-time factor measured on the full run, and any episodes that failed checks, in `results.md` and `decisions.md`.
- Whether the Hindi or Hinglish episodes stay in the golden set (D11).
- The comparison of a publisher transcript with Whisper, and whether D13 stands.
- The final quality thresholds, after seeing real flags (D15).

## Exit gate
All fifteen manual steps pass and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, and merge.
