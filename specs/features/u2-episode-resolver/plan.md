# U2: Episode Resolver, Plan (v2, 2026-11-17)

## Approach
0. **Probe (done 2026-11-17, results in `notes.md`).** Confirmed how Podcast Index returns episodes. The paging design follows from it: one call per feed, refresh with `since`.
1. **No new dependencies.** The Podcast Index client uses `urllib`, and matching uses plain word-overlap rules. This keeps the lockfile unchanged.
2. **`retry.py`.** Move `call_with_retries` and the retry delays out of `youtube_client.py`, which re-imports them so U1 behaviour and tests are unchanged.
3. **`podcastindex.py`.** The only place that calls Podcast Index. Signs requests (SHA-1 of key, secret and timestamp), takes an injectable transport so tests never touch the network, and has: `search_feeds`, `feed_by_url`, `feed_by_id` and `episodes(feed_id, since)`. Status 401 or 403 becomes `ConfigError`; 429, 5xx and network errors are retried and then become `ApiError`; a body with `status: "false"` becomes `ApiError`. Loads credentials from the environment or `<data folder>/podcastindex.env` (refusing a file that is readable by others). A short pause between calls. Counts calls. Never logs credentials.
4. **`matcher.py`.** Pure functions with no network or database: title, date and duration signals, the combined score and the decision rules in the requirements. All constants in one block. Episodes are prepared once (their words computed once) and scored against many videos.
5. **`resolve_store.py`.** SQL for feeds, channel feeds, episodes and matches, including upserts that never overwrite reviewed results.
6. **`resolve.py`.** The flows: feed candidates, setting a channel's feed, refreshing a feed, resolving a list of videos, confirming and rejecting, the review list, and the seed check file. Podcast Index failures make the run partial, not fatal, when stored episodes exist.
7. **Migration `002_episodes_and_matches.sql`.**
8. **`core.py` and `cli.py`.** Core functions as listed in the requirements. The CLI only calls them. `resolve feeds` prompts for choices through an injectable input function, so it can be tested.
9. **`logging_setup.py`.** Add `X-Auth-Key` and `PODCASTINDEX_KEY` or `PODCASTINDEX_SECRET` values to the redaction patterns.
10. **Tests.** Matcher tests with real pairs from the seed list (Muse, Greg Isenberg's hard case, Raj Shamani, Diet Expert, Jen Abel), clip-versus-episode, duplicate and close candidates, missing signals and a non-Latin title. Podcast Index tests with a fake transport (signing, errors, retries, credentials file rules, never logging secrets). Flow tests with a fake client and a real database (feed choice, refresh with `since`, truncation flag, no-feed, waiting channels, reviewed results kept, recompute after a feed change, unavailable videos, purge protection). CLI tests for exit codes and prompts.

## Constraints
- No secrets in code, logs, test fixtures or git.
- Podcast Index calls only through `podcastindex.py`.
- `matcher.py` has no network or database access.
- Never produce a result for a channel without a feed decision.
- Never overwrite a reviewed result.
- `core.py` has no printing.

## Review checklist (PM)
- [x] No Podcast Index key or secret in the diff, logs or database, and a test proves log redaction
- [x] A channel set to "none" always gives `no_feed`; a channel with no decision gives no result and is listed as waiting
- [x] `matched` by score needs a title signal, a combined score of 0.85 and a margin of 0.15; the lock rule needs the date, length and closeness conditions
- [x] The Lenny's Muse pair resolves to the correct episode as `matched`, and Greg Isenberg's hard case is at least `needs_review` in a unit test
- [x] A feed with no duration still scores fairly (weights are rescaled), and a non-Latin title cannot reach `matched` by score
- [x] A very short clip never matches a full episode
- [x] The three signal scores, the duration difference, the margin and the top 3 candidates are stored for every result
- [x] Re-running `resolve run` creates no duplicate rows and never overwrites a confirmed or rejected result
- [x] The first feed fetch uses one call, later fetches use `since`, and 1,000 returned episodes sets the `truncated` flag
- [x] A credentials file readable by others is refused
- [x] U1's purge still keeps videos that have a match
- [x] Nothing added beyond the spec (no Spotify, no audio download, no transcription)
