# U2: Episode Resolver, Validation (v2, 2026-11-17)

Run these yourself before merging. They use `data/seed_episodes.csv` (20 episodes), already loaded into the database by U1's `fetch`. U2 needs your Podcast Index credentials (`source ~/.podcast-recall/podcastindex.env` or the file in the data folder).

## Automated
1. `make test` passes, including the matcher tests with the Muse pair, Greg Isenberg's hard case, a clip, and a non-Latin title.
2. `make lint` is clean.

## Manual, on the 20 seed episodes
| # | Step | Expected |
|---|---|---|
| 1 | `podcast-recall fetch data/seed_episodes.csv` | All 20 videos stored with title, channel, date and duration |
| 2 | `podcast-recall resolve feeds --seed` and choose a feed for each channel (about 7 shows) | Candidates are shown for each channel. The right feed is among them for Lenny's, Greg Isenberg and Raj Shamani. Choose "none" for the three video-only channels and for Dan Martell unless you find his feed |
| 3 | `podcast-recall resolve run --seed` | Prints counts per status, one line for each result that is not `matched`, no crash, and writes `data/seed_resolver_check.csv`. The first run makes one episode-list call per feed |
| 4 | `podcast-recall resolve review --seed` | Lists every `needs_review` and `unmatched` result with the best candidate and the score breakdown, and any channel still waiting for a feed |
| 5 | Open `data/seed_resolver_check.csv` and mark `correct (y/n)` for each row by opening the YouTube video and the feed episode side by side | At least 19 of 20 correct, where "correct" follows the seed rule in the requirements. **Zero wrong results with status `matched`** |
| 6 | Look at the rows marked `n` in the seed file | The three video-only channels are `no_feed`. Dan Martell is `no_feed` or `unmatched`. None is `matched` |
| 7 | Run `podcast-recall resolve run --seed` again | No duplicate rows, `since` used for the refresh (the output shows the calls), and anything you confirmed with `resolve confirm` is unchanged |
| 8 | Run `podcast-recall resolve confirm <video_id> <episode_id>` on one result, then `resolve run --seed` | The confirmed result stays `matched` and `reviewed` |
| 9 | Look at the stored duration difference for 5 matched episodes | The values are plausible (seconds to a few minutes) |
| 10 | Search the repo, the data folder's logs and the database for your Podcast Index key and secret | No matches |

## Record the results
- Write the final thresholds and weights, the 19-of-20 result and every disagreement in `results.md` and `decisions.md` (D14).
- If fewer than 19 of 20 are correct, do not merge. List each wrong or missed case, decide whether it is a matcher fix or a data problem, and fix it.

## Exit gate
Steps 1 to 10 pass and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, and merge.
