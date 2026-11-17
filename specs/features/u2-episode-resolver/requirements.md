# U2: Episode Resolver, Requirements (v1, 2026-11-17)

Branch: `feature/u2-episode-resolver`. Depends on U1 (`videos` table with title, date and duration; `fetch_videos`). Source: requirements doc section 1.5 (U2), adapted for YouTube-first. Decisions: D2 (no-feed videos are "not indexable" for now), D10 (shared episode data), D11 (languages).

## What done looks like
- For every YouTube video in the library (or the seed list), the resolver finds the matching episode in the publisher's RSS feed, or says clearly that it could not.
- Every match carries a confidence score and a status: `matched`, `needs_review`, `unmatched` or `no_feed`. Nothing fails silently.
- The matched episode gives U3 what it needs: audio URL, feed episode ID (GUID), feed title, publish date and duration.
- Both platform IDs are stored so links can be built later: the YouTube video ID, and (v1.1) the Spotify episode ID.
- **Week 1 target:** at least 95% of the 20 seed episodes are correctly resolved (19 of 20), checked by hand. **A wrong result with status `matched` counts as a defect to fix, not as one of the allowed misses**, because it would cite the wrong audio.
- **What "correct" means for the seed list.** The expected outcome comes from the `has_rss` column of `data/seed_episodes.csv`. A `y` row is correct when it is `matched` to the right feed episode. An `n` row is correct when it is **not** `matched`: `no_feed` if its channel has no feed, or `unmatched` if the channel has a feed but that episode is not in it (for example the Dan Martell row, and Greg Isenberg's March episode if it turns out not to be in its feed). With 15 `y` rows, one missed `y` row still leaves 19 of 20 correct, but it also leaves only 14 episodes for U3.
- The 100-episode hand check from the requirements doc is a Week 4 task.

## Why this is harder than it looks (learned in Week 0)
- Searching Podcast Index by show name returns lookalikes. "Lenny's Podcast" also returned "Lenny's Daily Podcast", a different show.
- Titles differ between YouTube and the feed. Example: YouTube "The rise of Muse: Inside the launch of the most successful consumer product this year" is "Meta's Muse: How we launched the most successful consumer product this year" in the feed.
- Some YouTube channels are clips, tutorials or re-uploads with no feed episode at all.
- Dates can differ by a day (time zones), and durations differ (ads, intros, trims).

## Scope
1. **Find the feed once per channel.** For each YouTube channel in the library, search Podcast Index for candidate feeds and show the top few. The PM confirms the right one (or "none") once. The choice is stored as the channel's feed and is reused for every later video from that channel.
2. **Match each video to an episode within that feed.** Fetch the feed's episodes around the video's publish date (Podcast Index episode endpoints `episodes/byfeedid` or `episodes/byfeedurl`, with a fallback to parsing the RSS). **Verified by the probe on 2026-11-17 (see `notes.md`):** there is no paging. `episodes/byfeedid?id=<feed id>&max=1000` returns the whole feed, newest first, for all three seed feeds (371, 396 and 649 episodes), and `episodes/byfeedurl` gives the same result. `since=<epoch seconds>` returns only newer episodes, newest first. `before` is **not** supported. The feed's `episodeCount` is not reliable: it was 1 and 11 lower than the real count. Fetch a feed's episodes once, keep them in the `episodes` table, and refresh later with `since` set to the newest stored publish date. Then score each candidate against the video on title similarity, publish-date closeness and duration closeness. Also keep each episode's `transcriptUrl` and `transcripts` entries, which U3 uses first (D13).
3. **Store the result** with the score, the status, the per-signal scores and the duration difference in seconds (used later to measure timestamp drift).
4. **Handle clips and non-episodes.** A video far shorter than every candidate, or with no candidate above the review threshold, is `unmatched`.
5. **CLI commands:** `resolve feeds` (choose feeds for channels), `resolve run [--seed]`, `resolve review` (list `needs_review` and `unmatched` items), `resolve confirm <video_id> <episode_id>` and `resolve reject <video_id>`. `resolve run --seed` also writes `data/seed_resolver_check.csv` with one row per seed video (video ID, title, best episode title, status, score, and an empty `correct (y/n)` column for the PM to fill in).
6. **Core functions** (`core.py`, no printing): `find_feed_candidates(channel_id)`, `set_channel_feed(channel_id, feed_id_or_none)`, `resolve_videos(video_ids)` and `confirm_match(video_id, episode_id)`.
7. **Credentials.** The Podcast Index key and secret come from the environment variables `PODCASTINDEX_KEY` and `PODCASTINDEX_SECRET`. The CLI also loads `~/.podcast-recall/podcastindex.env` if it exists, as in Week 0. The file must have permissions 600, and the values are never logged or printed.

## Starting thresholds (to be tuned on the seed list, not guessed)
| Status | Rule |
|---|---|
| `matched` | Combined score of 0.85 or higher, and the best candidate beats the second-best by a clear margin |
| `needs_review` | Score of 0.60 to 0.85, or two candidates that are close |
| `unmatched` | Below 0.60, or no candidates |
| `no_feed` | The channel's feed was set to "none" |

Signals and starting weights: title similarity 0.5, publish date within 2 days 0.3, duration within the larger of 10% or 3 minutes 0.2. Record the final values in `decisions.md` after the seed run.

**These starting values are untested and may not work.** With title worth 0.5, an episode whose title differs a lot (the Lenny's "Muse" example) cannot reach 0.85 on date and duration alone, because those two signals add up to only 0.5. Tuning must make seed pairs with different titles but matching date and duration reach a useful result: at least the correct episode as the top candidate, with status `matched` or `needs_review`. Record which, and why, in `decisions.md`.

**Missing duration.** Feeds give duration as seconds, as `HH:MM:SS` text, as 0, or not at all. Parse the first two forms. Treat 0 or missing as "no duration signal" and divide the weights among the signals that are available, so such feeds are not pushed down to `needs_review` for lack of data. In the three seed feeds, duration was always a whole number of seconds with no zeros, but other feeds may differ.

**What the probe showed about titles.** Feed titles differ from YouTube titles in ways the matcher must absorb: extra guest names and episode codes after a pipe (`... | Pooja Makhija | FO433 Raj Shamani`), different bracketed text (`(VP Google Labs)` versus `(Google Labs, Gemini, AI Studio)`), different capitalisation and a trailing word (`AI agents are too good at marketing` versus `AI Agents are too good at marketing now`), curly versus straight apostrophes (`Meta’s Muse`), and different punctuation (`Calories, Digestion, Sugar & Belly Fats` versus `calories , Digestion , Sugar 7 belly Fat`). Normalise case, quotes and punctuation, and judge similarity on how many of the YouTube title's words appear in the feed title, not on a strict whole-string match. Publish dates matched to the day in every verified case.

**A hard case that must pass.** Greg Isenberg's YouTube video `eA9Zf2-qYYM` is titled "Building AI agents that actually work" (2026-03-17). The feed episode that day is titled "AI Agents Full Course 59 Minutes (for beginners)" (3535 s). The two titles share almost no words. With the starting weights this pair scores at most 0.5 and would be `unmatched`. The tuned rule must classify it at least as `needs_review`, and as `matched` when the date is the same day, the duration agrees closely, and no other episode that day is a candidate. Use it as a unit test, together with the Lenny's "Muse" pair.

## Edge cases
- Channel with no feed (D2): mark `no_feed`, never try to guess an episode.
- The same episode uploaded twice to YouTube: both videos map to the same feed episode.
- A feed too large to download whole (the Lenny's feed is several MB as RSS): use the Podcast Index episode endpoint, not the RSS file. It returned all 649 episodes of the largest seed feed in under a second. Whether a feed with more than 1,000 episodes returns everything is untested (a request for 5,000 returned all 649, so the cap is unknown). For such a feed, fall back to reading the RSS file and record it in `decisions.md`.
- Podcast Index unavailable or rate-limited: stop with a clear message, keep earlier results.
- A feed episode removed later: keep the stored match, and flag it when U3 cannot download the audio.

## Out of scope
- Spotify matching (v1.1).
- Transcribing (U3).
- Per-episode timestamp offset correction (v2). U2 only stores the duration difference.
- Automatic guessing for channels without a confirmed feed.

## Data stored
Shared tables (D10): `feeds` (feed ID, title, URL), `channel_feeds` (channel to feed, or none), `episodes` (feed episode GUID, feed ID, title, publish date, duration, audio URL, transcript URL and type when the publisher supplies one) and `episode_matches` (video ID, episode ID, confidence, status, per-signal scores, duration difference, reviewed flag).

## Open questions for Claude Code to raise before coding
- Which fuzzy-matching library to use, and how titles are normalised (case, punctuation, guest-name suffixes after a pipe).
- How Podcast Index paging works for long feeds, and its rate limits.
- (Resolved) `needs_review` matches are not transcribed until the PM confirms them with `resolve confirm`. See U3 for the rule.
