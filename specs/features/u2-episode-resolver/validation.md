# U2: Episode Resolver, Validation (v1, 2026-11-17)

Run these yourself before merging. They use `data/seed_episodes.csv` (20 episodes) loaded with U1's `fetch` command.

## Automated
1. `make test` passes, including the matcher tests with the Lenny's "Muse" title mismatch and a clip-versus-episode case.
2. `make lint` is clean.

## Manual, on the 20 seed episodes
| # | Step | Expected |
|---|---|---|
| 1 | `podcast-recall fetch data/seed_episodes.csv` | All 20 videos stored with title, channel, date and duration |
| 2 | `podcast-recall resolve feeds` and choose a feed for each of the 7 channels | Candidates are shown for each channel. Choose the correct feed, or "none" for channels with no feed |
| 3 | `podcast-recall resolve run --seed` | Prints counts of `matched`, `needs_review`, `unmatched` and `no_feed`. No crash |
| 4 | `podcast-recall resolve review` | Lists every `needs_review` and `unmatched` video with the best candidate and the score breakdown |
| 5 | Open `data/seed_resolver_check.csv` (the tool writes one row per video) and mark each match correct or wrong by opening the YouTube video and the feed episode side by side | At least 19 of 20 correct. **Zero wrong results with status `matched`** |
| 6 | Check the no-feed rows (the video-only tests marked `n` in the seed list) | Each has status `no_feed`. None has a guessed episode |
| 7 | Run `resolve run --seed` again | No duplicate rows. A match you confirmed with `resolve confirm` is unchanged |
| 8 | Look at the stored duration difference for 5 matched episodes | The values are plausible (usually seconds to a few minutes) and recorded for later drift tracking |
| 9 | Search the repo and logs for your Podcast Index key and secret | No matches |

## Record the results
- Write the final thresholds and weights, and the 19-of-20 result, in `decisions.md`.
- If fewer than 19 of 20 are correct, do not merge. List each wrong or missed case, decide whether it is a matcher fix or a data problem, and fix it.

## Exit gate
Steps 1 to 9 pass and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, and merge.
