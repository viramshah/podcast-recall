# U2: Episode Resolver, Requirements (v1, 2026-11-17)

Branch: `feature/u2-episode-resolver`. Depends on U1 (`videos` table with title, date and duration; `fetch_videos`). Source: requirements doc section 1.5 (U2), adapted for YouTube-first. Decisions: D2 (no-feed videos are "not indexable" for now), D10 (shared episode data), D11 (languages).

## What done looks like
- For every YouTube video in the library (or the seed list), the resolver finds the matching episode in the publisher's RSS feed, or says clearly that it could not.
- Every match carries a confidence score and a status: `matched`, `needs_review`, `unmatched` or `no_feed`. Nothing fails silently.
- The matched episode gives U3 what it needs: audio URL, feed episode ID (GUID), feed title, publish date and duration.
- Both platform IDs are stored so links can be built later: the YouTube video ID, and (v1.1) the Spotify episode ID.
- **Week 1 target:** at least 95% of the 20 seed episodes are correctly resolved (19 of 20), checked by hand. **A wrong result with status `matched` counts as a defect to fix, not as one of the allowed misses**, because it would cite the wrong audio.
- The 100-episode hand check from the requirements doc is a Week 4 task.

## Why this is harder than it looks (learned in Week 0)
- Searching Podcast Index by show name returns lookalikes. "Lenny's Podcast" also returned "Lenny's Daily Podcast", a different show.
- Titles differ between YouTube and the feed. Example: YouTube "The rise of Muse: Inside the launch of the most successful consumer product this year" is "Meta's Muse: How we launched the most successful consumer product this year" in the feed.
- Some YouTube channels are clips, tutorials or re-uploads with no feed episode at all.
- Dates can differ by a day (time zones), and durations differ (ads, intros, trims).

## Scope
1. **Find the feed once per channel.** For each YouTube channel in the library, search Podcast Index for candidate feeds and show the top few. The PM confirms the right one (or "none") once. The choice is stored as the channel's feed and is reused for every later video from that channel.
2. **Match each video to an episode within that feed.** Fetch recent episodes of the feed (Podcast Index episode endpoints, with a fallback to parsing the RSS), then score each candidate against the video on title similarity, publish-date closeness and duration closeness.
3. **Store the result** with the score, the status, the per-signal scores and the duration difference in seconds (used later to measure timestamp drift).
4. **Handle clips and non-episodes.** A video far shorter than every candidate, or with no candidate above the review threshold, is `unmatched`.
5. **CLI commands:** `resolve feeds` (choose feeds for channels), `resolve run [--seed]`, `resolve review` (list `needs_review` and `unmatched` items), `resolve confirm <video_id> <episode_id>` and `resolve reject <video_id>`. `resolve run --seed` also writes `data/seed_resolver_check.csv` with one row per seed video (video ID, title, best episode title, status, score, and an empty `correct (y/n)` column for the PM to fill in).
6. **Core functions** (`core.py`, no printing): `find_feed_candidates(channel_id)`, `set_channel_feed(channel_id, feed_id_or_none)`, `resolve_videos(video_ids)` and `confirm_match(video_id, episode_id)`.

## Starting thresholds (to be tuned on the seed list, not guessed)
| Status | Rule |
|---|---|
| `matched` | Combined score of 0.85 or higher, and the best candidate beats the second-best by a clear margin |
| `needs_review` | Score of 0.60 to 0.85, or two candidates that are close |
| `unmatched` | Below 0.60, or no candidates |
| `no_feed` | The channel's feed was set to "none" |

Signals and starting weights: title similarity 0.5, publish date within 2 days 0.3, duration within the larger of 10% or 3 minutes 0.2. Record the final values in `decisions.md` after the seed run.

## Edge cases
- Channel with no feed (D2): mark `no_feed`, never try to guess an episode.
- The same episode uploaded twice to YouTube: both videos map to the same feed episode.
- A feed too large to download whole (the Lenny's feed is several MB): do not load the whole feed. Use the episode endpoints and page by date.
- Podcast Index unavailable or rate-limited: stop with a clear message, keep earlier results.
- A feed episode removed later: keep the stored match, and flag it when U3 cannot download the audio.

## Out of scope
- Spotify matching (v1.1).
- Transcribing (U3).
- Per-episode timestamp offset correction (v2). U2 only stores the duration difference.
- Automatic guessing for channels without a confirmed feed.

## Data stored
Shared tables (D10): `feeds` (feed ID, title, URL), `channel_feeds` (channel to feed, or none), `episodes` (feed episode GUID, feed ID, title, publish date, duration, audio URL) and `episode_matches` (video ID, episode ID, confidence, status, per-signal scores, duration difference, reviewed flag).

## Open questions for Claude Code to raise before coding
- Which fuzzy-matching library to use, and how titles are normalised (case, punctuation, guest-name suffixes after a pipe).
- How Podcast Index paging works for long feeds, and its rate limits.
- Whether `needs_review` results should block U3 or let it proceed.
