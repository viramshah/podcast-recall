# U2: Episode Resolver, Validation Results

Recorded 2026-11-17 against the PM's real seed list and the real Podcast Index. Spec: `validation.md` (v2).

Automated: `make test` 206 passed and `make lint` "All checks passed" (run 2026-11-17 with the project's own `.venv`).

## The first seed run
20 videos resolved: 15 `matched`, 2 `unmatched`, 3 `no_feed`, 0 `needs_review`. Four Podcast Index calls in total (one per feed): Lenny's 371 episodes, Figuring Out 649, Startup Ideas 396, and Dan Martell's feed 0 new.

| # | Step | Result | Evidence |
|---|---|---|---|
| 1 | `fetch` the 20 seed videos | Passed | 20 requested, 20 fetched, 0 unavailable, 1 quota unit |
| 2 | Choose a feed per channel | Passed | Dan Martell chosen interactively (feed 8032617). The other channels set with `resolve set-feed` after pasted commands disturbed the prompts: Lenny's, Greg Isenberg, Raj Shamani and Raj Shamani Clips to their feeds, and Saeem Khan, Sandeep Swadia and Tristen O'Brien to "none" |
| 3 | `resolve run --seed` | Passed | Summary above. Wrote `data/seed_resolver_check.csv` with 20 rows |
| 4 | `resolve review --seed` | Passed | Listed the 2 `unmatched` results with their top 3 candidates and score breakdown |
| 5 | Mark `correct (y/n)` by hand | Done, evidence-based (see "Hand-check evidence") | All 20 rows marked `y` in `data/seed_resolver_check.csv`: 16 matched to the right episode, 4 correctly not matched. The assistant could not watch the videos, so a quick spot-check by the PM is still welcome |
| 6 | Rows marked `n` | Passed | The three video-only channels are `no_feed`. Dan Martell is `unmatched`. None is `matched` |
| 7 | Run again | Passed | After the clip URL was replaced and the seed list reloaded: 4 Podcast Index calls (one per feed), every feed "0 new episode(s)", no duplicate results. The seed check file was rewritten with 20 rows |
| 8 | Confirm one result and run again | Pending | |
| 9 | Duration differences for matched episodes | Passed | All 16 matches have a difference of 0 or 1 second (six at 0, ten at 1) |
| 10 | Search for the Podcast Index key and secret | Passed | The real 20-character key and 40-character secret were searched for (without printing them) in the working tree, tracked files, all of git history, the logs, the database and the backups: found nowhere |

## All 20 results
| Status | Method | YouTube title (short) | Feed episode | Date | Length diff |
|---|---|---|---|---|---|
| matched | score | Why every company now needs to think... Josh Woodward | same title, other guest bracket | 2026-10-11 | 1 s |
| matched | date_duration | 84 minutes of enterprise sales alpha, Jen Abel | How to close $100K+ enterprise deals, step by step | 2026-08-23 | 0 s |
| matched | score | Meta's Muse: Inside the launch... | Meta's Muse: How we launched... | 2026-11-15 | 1 s |
| matched | score | Why PMs are suddenly valuable again | same | 2026-11-08 | 0 s |
| matched | score | Inside the black box of AI | same | 2026-10-18 | 1 s |
| matched | date_duration | How to find product-market fit (but, actually), Rob Snyder | An 86-minute guide to finding PMF | 2026-10-25 | 1 s |
| matched | score | Why Your Communication Makes People Ignore You | same, with guest and episode code | 2026-11-14 | 1 s |
| **unmatched** | clip | Will America Ever Pay Back Its $40 Trillion Debt? Gita Gopinath, Raj Shamani Clips | (best candidate: FO585, Ex-IMF Chief Economist) | | 5,632 s shorter |
| matched | date_duration | Why AI Will Replace These Jobs, Sachin Puri | Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employees | 2026-11-17 | 1 s |
| matched | score | Diet Expert: Weight Loss... | same | 2025-11-15 | 1 s |
| no_feed | | Saeem Khan, Sandeep Swadia, Tristen O'Brien | | | |
| unmatched | none | How to Build an AI Agent for Every Part of Your Life (Dan Martell) | none close (best: an old Escape Velocity episode) | | |
| matched | date_duration | Building AI Agents that actually work (Full Course) | AI Agents Full Course 59 Minutes (for beginners) | 2026-03-17 | 1 s |
| matched | score | AI Agents are too good at marketing now | same | 2026-11-09 | 0 s |
| matched | date_duration | Use Grok Bot Better Than 99% of People (Full Course) | I'm Obsessed With Grok Bot. Here's Why | 2026-11-11 | 1 s |
| matched | date_duration | $100M ARR Founder: The Next Big AI Opportunity | Stop building AI wrappers. Start building agent harnesses. | 2026-10-28 | 0 s |
| matched | score | The $1M+ Solo Grok Bot Business (Full Course) | same | 2026-11-02 | 0 s |
| matched | score | The 9 Stages of AI Agent Adoption, Explained | same | 2026-10-21 | 0 s |

(Method for the unmatched and matched rows is from the run. The `method` column was added to the check file afterwards, so it appears in the next run.)

## Findings
- **The date-and-length rule works on real data.** Six videos have YouTube titles that differ from the feed titles (Jen Abel, Rob Snyder, Sachin Puri, Greg Isenberg's March episode, the Grok Bot episode and the "$100M ARR Founder" video). All were matched correctly because the date was the same and the length differed by 0 or 1 second. This also settled two doubts from earlier: the Rob Snyder and "agent harnesses" URLs were the right videos under different YouTube titles.
- **YouTube and feed lengths agree to the second** for these shows. The "within 2% or 30 s" closeness for the date-and-length rule is much looser than needed for them. Shows that insert ads may differ more.
- **The clip rule worked.** The Gita Gopinath video is a short clip from the "Raj Shamani Clips" channel, 5,632 seconds shorter than the full episode. The resolver found the right episode (FO585) as the best candidate and still refused to match it. The seed row had been marked `y`, which was a mistake in the seed list: the URL points to a clip, not the full episode.
- **Dan Martell** has no current feed containing the October 2026 video, so `unmatched` is the correct result for a row the seed list marks `n`.
- **Seed list score:** the automatic check agrees on 19 of 20. The one disagreement is the Gita Gopinath row, caused by the clip URL.

## Second seed run (after replacing the clip URL)
The Gita Gopinath row now points to the full episode (`dNIef2fGLQY`, on the main Raj Shamani channel).

- Result: **16 matched, 0 needs_review, 1 unmatched (Dan Martell), 3 no_feed.**
- **The automatic check agrees with the seed list on all 20 rows.**
- Methods: 9 matched by score (the titles agree) and 7 by date and length (the YouTube title differs from the feed title).
- The new Gita Gopinath row matched by date and length with a 1 second difference. Its YouTube title ("How Money Is Created: Central Banks, Money Printing & Inflation ...") differs from the feed title ("Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisis | Gita Gopinath | FO585"), so it is one of the seven that need a human eye.
- Matched length differences: 0 s (six videos) and 1 s (ten videos).

## Hand-check evidence (2026-11-17)
Checked by comparing the YouTube video page title, the guest, episode codes, dates and lengths with the matched feed episode. The video pages did not show channel, date or duration, so lengths come from U1 (YouTube API) and the feed.

| Video | YouTube title says | Feed episode | Verdict |
|---|---|---|---|
| `dNIef2fGLQY` | "How Money Is Created: Central Banks, Money Printing & Inflation \| Gita Gopinath \| **FO585** Raj Shamani" | "Ex-IMF Chief Economist ... \| Gita Gopinath \| **FO585** Raj Shamani" | Same guest and same episode code. Right |
| `8ol3j7o1U7o` | "Why AI Will Replace These Jobs ... \| Sachin Puri \| **FO589** Raj Shamani" | "Billion-Dollar Tech CEO ... \| Sachin Puri \| **FO589** Raj Shamani" | Same guest and same episode code. Right |
| `YS9In813jJ0` | "84 minutes of enterprise sales alpha \| Jen Abel" | "How to close $100K+ enterprise deals, step by step \| Jen Abel" (1:24:57) | Same guest, same day, "84 minutes" fits 1:24:57. Right |
| `19qrLchbQEc` | "How to find product-market fit (but, actually) \| Rob Snyder (Author, The Power of Pull)" | "An 86-minute guide to finding PMF \| Rob Snyder (Author, The Power of Pull)" | Same guest and same bracket text, same day. Right |
| `eA9Zf2-qYYM` | "Building AI Agents that actually work (Full Course)" | "AI Agents Full Course 59 Minutes (for beginners)" | Both say AI agents and full course, same day, 1 s apart. Right |
| `st61aKW8P5A` | "$100M ARR Founder: The Next Big AI Opportunity" | "Stop building AI wrappers. Start building agent harnesses." | An earlier web search described this video as a founder interview about agent harnesses, same day, 0 s apart. Right, with less title evidence than the others |
| `1cWZ7Ekff6E` | "Use Grok Bot Better Than 99% of People (Full Course)" | "I'm Obsessed With Grok Bot. Here's Why" | Same topic, same day, 1 s apart. Right, with less title evidence |

The nine matches by score have near-identical titles, the same day and lengths within 1 second.

## Open items
- Step 8: run `resolve confirm` on one result and run `resolve run --seed` again (needs the PM's terminal, because the assistant cannot open the database). The command is in the hand-over message.
- Optional: spot-check the two date-and-length rows with the least title evidence (`st61aKW8P5A` and `1cWZ7Ekff6E`) by listening to the first minute.
- Fixed during this check: `resolve run --seed` no longer erases the hand-marked `correct (y/n)` column when it rewrites the file.
