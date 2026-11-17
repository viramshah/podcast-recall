# U2: Episode Resolver, Plan (v1, 2026-11-17)

## Approach
0. **Probe first.** Before designing anything, write a small throwaway script that calls Podcast Index `episodes/byfeedid` and `episodes/byfeedurl` for the Lenny's, Greg Isenberg and Raj Shamani feeds. Record in `specs/features/u2-episode-resolver/notes.md`: the query parameters that exist, the sort order, the maximum result count, whether an older episode can be reached, and the exact fields and formats returned (especially duration and publish date). Design the paging from what this shows.
1. **Dependencies.** Add an HTTP client and a fuzzy-string library (for example `httpx` and `rapidfuzz`), and a feed parser only if the Podcast Index fallback is needed. Keep additions small and list them in the pull request.
2. **`podcastindex.py`.** The only place that calls Podcast Index. Signs requests (SHA-1 of key, secret and timestamp, as in `scripts/podcastindex_hello.py`), reads credentials from `PODCASTINDEX_KEY` and `PODCASTINDEX_SECRET`, fetches episodes using the paging the probe found, and handles rate limits and errors. Never logs credentials.
3. **`feeds.py`.** `find_feed_candidates(channel_id)` searches by channel name and returns the top candidates with feed title, URL and author so the PM can choose. `set_channel_feed(...)` stores the choice, including "none".
4. **`matcher.py`.** Pure functions (no network): normalise titles, compute the three signal scores, combine them and apply the thresholds. This is the part with the most unit tests.
5. **`resolve.py`.** For each video, load its channel's feed, fetch candidate episodes around the video's publish date, call the matcher, and write `episode_matches`.
6. **`store.py`.** Add the shared tables for feeds, channel feeds, episodes and matches, with a migration.
7. **`core.py` and `cli.py`.** Core functions as listed in the requirements. The CLI only calls them. `resolve feeds` shows candidates and asks for a choice.
8. **Tests.** Matcher tests with real examples from the seed list (including the Lenny's Muse title mismatch), clip-versus-episode cases, duplicate candidates, and date and duration edge cases. Podcast Index calls are mocked.

## Constraints
- No secrets in code, logs, test fixtures or git.
- Podcast Index calls only through `podcastindex.py`.
- The matcher has no network access and no database access, so it can be tested alone.
- Never auto-accept a match for a channel whose feed has not been confirmed.

## Review checklist (PM)
- [ ] No Podcast Index key or secret in the diff or logs
- [ ] A channel with feed "none" always produces `no_feed`, never a guessed episode
- [ ] `matched` requires the score and the margin over the second-best candidate
- [ ] The Lenny's "Muse" example resolves to the correct episode as the top candidate despite the different titles (status `matched` or `needs_review`; the result and the reason are recorded in `decisions.md`)
- [ ] A feed that reports no duration, or a duration of 0, still scores fairly (weights are renormalised)
- [ ] The probe notes (`notes.md`) exist, and the paging code matches them
- [ ] A very short clip does not match a full episode
- [ ] The score breakdown and duration difference are stored for each match
- [ ] Rerunning `resolve run` does not create duplicate rows and does not overwrite a PM-confirmed match
- [ ] Nothing added beyond the spec (no Spotify, no transcription)
