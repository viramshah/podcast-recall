# U2: Episode Resolver, Requirements (v2, 2026-11-17)

Branch: `feature/u2-episode-resolver`. Depends on U1 (`videos` and `channels` tables, `fetch`). Source: requirements doc section 1.5 (U2), adapted for YouTube-first. Decisions: D2 (no-feed videos are "not indexable" for now), D10 (shared episode data), D11 (languages), D13 (publisher transcripts first). v2 adds the answers from the pre-build ambiguity review, listed at the end.

## What done looks like
- For every YouTube video in a user's library (or the seed list), the resolver finds the matching episode in the podcast's feed, or says clearly that it could not.
- Every result has a status (`matched`, `needs_review`, `unmatched` or `no_feed`), a combined score, the per-signal scores and the reason. Nothing fails silently.
- A matched episode gives U3 what it needs: audio URL, transcript link (D13), episode GUID, title, publish date and duration.
- **Week 1 target:** at least 95% of the 20 seed episodes are correctly resolved (19 of 20), checked by hand. **A wrong result with status `matched` is a defect to fix, not one of the allowed misses**, because it would cite the wrong audio.
- **What "correct" means for the seed list.** The expected outcome comes from the `has_rss` column of `data/seed_episodes.csv`. A `y` row is correct when it is `matched` to the right feed episode. An `n` row is correct when it is **not** `matched`: `no_feed` if its channel has no feed, or `unmatched` if its channel has a feed but the episode is not in it. With 16 `y` rows, one missed `y` row still leaves 19 of 20 correct, but leaves fewer episodes for U3.
- The 100-episode hand check from the requirements doc is a Week 4 task.

## What the probe taught us (see `notes.md`)
- `episodes/byfeedid?id=<feed id>&max=1000` returns the whole feed, newest first, in one call. No paging. `since=<epoch seconds>` returns only newer episodes. `before` does nothing. The feed's `episodeCount` is unreliable.
- Titles differ between YouTube and the feed: guest names and episode codes after a pipe, different bracketed text, capitalisation, a trailing word, curly quotes, punctuation. Example: "The rise of Muse: ..." versus "Meta's Muse: How we launched ...".
- A title can share very little: Greg Isenberg's "Building AI agents that actually work" (2026-03-17) is "AI Agents Full Course 59 Minutes (for beginners)" in the feed. Only "AI agents" is shared (a title signal of 0.4), so date and length are the real evidence.
- Searching Podcast Index by show name returns lookalikes ("Lenny's Daily Podcast").
- Publish dates fell on the same calendar day in every verified case. Durations were whole seconds.

## Scope
1. **Choose a feed once per channel.** `resolve feeds` walks through the YouTube channels that have videos to resolve and no feed decision yet. For each, it searches Podcast Index by the channel's title and shows up to 5 candidates (title, author, feed URL, episode count, last update, language). The PM picks one, pastes a feed URL or Podcast Index ID, chooses "none", or skips. The choice is stored for the channel and reused for every video from it. `resolve set-feed <channel_id> <feed URL | feed ID | none>` does the same without prompts.
2. **Fetch a feed's episodes.** The first time, one call with `max=1000`. Later, one call with `since` set to the newest stored publish date. `resolve run` refreshes each feed it needs once per run (skip with `--no-refresh`; re-fetch everything with `--full-refresh`). If the first fetch returns 1,000 episodes, the feed is flagged `truncated`, because older episodes may be missing, and a warning is shown.
3. **Match each video to an episode** with the rules in "Matching rules" below. Every episode of the feed is scored, not only those near the publish date.
4. **Store the result** in `episode_matches`: status, method, reason, combined score, the three signal scores, the duration difference in seconds (YouTube minus feed, kept for later drift tracking), the margin over the second-best candidate, the top 3 candidates, and a `reviewed` flag.
5. **Commands:**
   - `resolve feeds [--seed [FILE]]`: interactive feed choice.
   - `resolve set-feed <channel_id> <feed URL | feed ID | none>`.
   - `resolve run [--seed [FILE]] [--no-refresh] [--full-refresh]`: resolve and print a summary.
   - `resolve review [--seed [FILE]]`: list `needs_review` and `unmatched` results that nobody has reviewed, and channels still waiting for a feed choice.
   - `resolve confirm <video_id> <episode_id>`: the PM says this episode is right (status `matched`, `reviewed`).
   - `resolve reject <video_id>`: the PM says there is no episode (status `unmatched`, `reviewed`).
   - Without `--seed`, commands work on the videos in the signed-in user's library (`--user`, default `owner`). With `--seed`, they work on the video IDs in the seed file (default `data/seed_episodes.csv`), which must already have been loaded with `fetch`. Nothing in U2 needs a YouTube sign-in except choosing the library.
6. **Core functions** (`core.py`, no printing): `find_feed_candidates`, `set_channel_feed`, `channels_needing_feed`, `resolve_videos`, `confirm_match`, `reject_match`, `list_review_items` and `write_seed_check`.
7. **Credentials.** `PODCASTINDEX_KEY` and `PODCASTINDEX_SECRET` come from the environment. If either is missing, the CLI reads `<data folder>/podcastindex.env` (lines like `export NAME=value`). A file readable by group or others is refused with a message to run `chmod 600`. Environment variables win over the file. The values are never logged, printed or stored in the database.
8. **Seed check file.** `resolve run --seed` also writes `data/seed_resolver_check.csv`, one row per seed video: video ID, YouTube title, date and duration, status, method, score, episode ID, episode title, date and duration, duration difference, the expected outcome from the seed file's `has_rss` column, `auto_check` (`agrees` or `disagrees` with that expectation), and an empty `correct (y/n)` column for the PM.
9. **Summary output.** `resolve run` prints counts per status, then one line for each result that is not `matched` (video title, best episode, score and the three signal scores), then the channels waiting for a feed choice, the videos skipped because they are unavailable or missing, and the Podcast Index calls made.

## Matching rules
All constants live in one block in `matcher.py`, so tuning on the seed list changes numbers, not logic.

**Title signal.** Lowercase, straight quotes, `&` as "and", accents removed, apostrophes dropped. Split into words, drop a short list of common English words (the, of, to, and so on), reduce each word lightly (`launched` to `launch`, `makes` to `make`, `labs` to `lab`), and keep the unique words. Score = the share of the **YouTube title's** words that appear in the feed title. Extra words in the feed title (guest names, episode codes) cost nothing. If the YouTube title has fewer than 2 words left (including non-Latin titles), the title signal is **missing**.

**Date signal.** The difference in days between the video's publish time and the episode's, both in UTC. 1.0 up to 1 day, falling in a straight line to 0 at 4 days.

**Duration signal.** The difference is YouTube minus feed, in seconds. Tolerance = the larger of 10% of the episode's length or 180 seconds. 1.0 within tolerance, falling in a straight line to 0 at three times the tolerance. If the YouTube video is shorter than half of the episode, the signal is 0 and the video is flagged as a probable clip. If either duration is 0 or missing, the signal is **missing**.

**Combined score.** Title 0.5, date 0.3, duration 0.2. When a signal is missing, the weights of the others are scaled to add up to 1.

**Decision, in this order.** The best candidate is the one with the highest combined score; the margin is its lead over the second best.
1. No episodes at all: `unmatched`.
2. A probable clip (the best candidate's duration signal is the clip flag): `unmatched`.
3. Combined 0.85 or more, title signal present, and a margin of at least 0.15: `matched` (method `score`). Combined 0.85 or more but a smaller margin: `needs_review`.
4. **Date and length lock.** The date signal is 0.9 or more, the duration signal is 0.9 or more, and no other episode has a date signal of 0.9 or more with a duration signal of 0.5 or more (or missing). Then the result is `matched` (method `date_duration`) if the duration difference is within the larger of 2% of the episode's length or 30 seconds, and `needs_review` otherwise. This is how the Greg Isenberg case above is resolved, with no help from the title.
5. Combined 0.60 or more: `needs_review`.
6. Otherwise: `unmatched`.
A channel whose feed is "none" gives `no_feed`. A channel with no feed decision gives no result; its videos are listed as waiting for a feed choice.

**These numbers are starting values.** The lock closeness (2% or 30 seconds) in particular is a guess, because YouTube and podcast audio often differ by ad breaks. Tune on the seed run, then record the final values and the reasons in `decisions.md` (D14).

## Edge cases
- Channel set to "none": `no_feed`, never a guessed episode.
- A video that is `unavailable` in U1 (no metadata): skipped and listed. A video not found in the database: listed as missing, with a hint to run `fetch`.
- The same episode uploaded twice to YouTube: each video has its own result, and both can point to the same episode.
- A feed with more than 1,000 episodes: flagged `truncated` when 1,000 come back. The cap is untested, so older episodes of such a feed may not be found.
- Podcast Index unavailable or rate-limited: retries with back-off, then the run is partial. Stored episodes are still used. If nothing could be done, the error is raised.
- A feed episode removed later: the stored episode and match are kept. U3 flags it when the audio cannot be downloaded.
- Re-running: results are recomputed for videos nobody reviewed. Results the PM confirmed or rejected are never overwritten.
- Changing a channel's feed: unreviewed results for that channel are recomputed at the next run.

## Out of scope
- Spotify matching (v1.1).
- Transcribing and downloading audio (U3).
- Per-episode timestamp offset correction (v2). U2 only stores the duration difference.
- Guessing a feed for a channel without a confirmed choice.
- Reading the RSS file directly (only if a feed turns out to exceed the Podcast Index limit).

## Data stored (migration 002)
Shared tables (D10):
- `feeds` (Podcast Index feed ID as the key, title, URL, author, language, reported episode count, `fetched_at`, newest stored publish time, `truncated`).
- `channel_feeds` (channel ID, feed ID or empty for "none", decided time).
- `episodes` (Podcast Index episode ID as the key, feed ID, GUID, title, publish time as epoch seconds, duration in seconds or empty, audio URL and type, transcript URL and the list of transcript entries, page link, fetched time).
- `episode_matches` (video ID as the key, episode ID or empty, status, method, reason, score, title, date and duration signals, duration difference, margin, top candidates as JSON, `reviewed`, resolved time).
Foreign keys point from `episode_matches` to `videos`, so U1's purge never deletes a matched video.

## Decisions made in the pre-build review (2026-11-17)
1. A channel with no feed decision gets no result and is reported as waiting, not stored as a fifth status.
2. Every episode of the feed is scored. Dates only affect the date signal, so a re-upload with a very different date can still reach `needs_review` through its title.
3. The episode ID used in commands is Podcast Index's numeric episode ID.
4. No new dependencies: the Podcast Index client uses the standard library, and fuzzy matching is a simple word-overlap rule.
5. One result per video. Many videos may share an episode.
6. The retry helper is shared with U1 (moved to `retry.py`).
7. Redaction now also covers `X-Auth-Key` and the two Podcast Index variables.
8. `resolve run` needs no YouTube sign-in with `--seed`.
