# U2: Podcast Index probe results

Probe run on 2026-11-17 with `scripts/probe_podcastindex.py` against the three confirmed seed feeds. Raw summary: `data/podcastindex_probe.json` (public podcast data only).

## What the API does

| Question | Answer | Evidence |
|---|---|---|
| How do I find a feed's ID? | `GET /podcasts/byfeedurl?url=<feed URL>` returns `feed.id`, title, `episodeCount`, language | Worked for all 3 feeds |
| How do I list episodes? | `GET /episodes/byfeedid?id=<id>&max=N`. `/episodes/byfeedurl` returns the identical episodes | `same_guids_as_byfeedid: true` for all 3 |
| Is there paging? | **No.** One call with `max=1000` returned the whole feed: Lenny's 371, Startup Ideas 396, Figuring Out 649. `max=5000` returned the same counts | Returned counts |
| What is the real cap on `max`? | Unknown. The largest feed (649) is below 1,000, so we have not seen it truncate | Untested above 649 |
| Sort order? | Newest first, always | `order: newest first` for every call |
| `since=<epoch seconds>`? | Works as "published after". Returned 9, 21 and 26 episodes, exactly the number newer than the cut-off, newest first | `returned == expected_if_filtering_newer_only` |
| `before=<epoch seconds>`? | **Not supported.** The full list came back unchanged | Returned 371, 396 and 649 |
| Is `episodeCount` on the feed reliable? | **No.** Lenny's said 370 but 371 were returned; Figuring Out said 638 but 649 were returned. Only Startup Ideas matched | `matches_feed_episodeCount` |
| Speed? | 0.25 to 0.92 seconds per call, including the full-feed fetch | `seconds` in the JSON |
| Duplicate GUIDs? | None | `duplicate_guids: 0` |

## Fields on each episode
`id`, `guid`, `title`, `description`, `datePublished` (epoch seconds, UTC), `datePublishedPretty`, `dateCrawled`, `duration`, `enclosureUrl`, `enclosureType`, `enclosureLength`, `episodeType`, `episode`, `season`, `explicit`, `image`, `link`, `chaptersUrl`, `transcriptUrl`, `transcripts`, `feedId`, `feedUrl`, `feedImage`, `feedItunesId`, `feedItunesType`, `feedLanguage`, `feedDead`, `feedDuplicateOf`, `podcastGuid`.

- **`duration`:** a whole number of seconds in every episode of all three feeds (types: all `int`, no zeros). Other feeds may use text like `01:00:00` or 0, so the matcher still handles both.
- **`enclosureUrl`:** the audio file. `audio/mpeg` in the seed episodes. Lenny's goes through a redirect (`pscrb.fm`), so U3's redirect safety rules apply.
- **`transcriptUrl` and `transcripts`:** present as fields. Whether these three publishers fill them in is not yet known (see open items).
- **Dates:** `datePublished` is a UTC time. In every verified case it fell on the same calendar day as the date in the seed list.

## Seed episodes found by title
| Show | Episode | Found? | Feed date | Duration (s) | Notes |
|---|---|---|---|---|---|
| Lenny's | Josh Woodward / "lab team" | Yes, position 5 | 2026-10-11 | 3731 | Guest brackets differ from YouTube's title |
| Lenny's | Jen Abel / enterprise deals | Yes, position 12 | 2026-08-23 | 5097 | Feed title: "How to close $100K+ enterprise deals, step by step" |
| Startup Ideas | "AI Agents are too good at marketing now" | Yes, position 2 | 2026-11-09 | 3120 | YouTube title lacks "now" |
| Startup Ideas | "Building AI agents that actually work" (March) | **Found by date only** | 2026-03-17 | 3535 | Feed title is "AI Agents Full Course 59 Minutes (for beginners)". The two titles share almost no words. Confirm using the stored YouTube duration |
| Figuring Out | "Why Your Communication Makes People Ignore You..." | Yes, position 1 | 2026-11-14 | 8542 | Episode FO588, 2 h 22 min |
| Figuring Out | "Diet Expert..." | **Yes, position 156** | 2025-11-15 | 4296 | Episode FO433. The seed list said `n`; corrected to `y` |

## Publisher transcripts (follow-up probe, same day)
| Show | Episodes with a transcript link | Format of the sample |
|---|---|---|
| Lenny's Podcast | **351 of 371 (95%)** | `.vtt` file hosted by Substack |
| Startup Ideas (Greg Isenberg) | **196 of 396 (49%)** | `.vtt` file hosted by Flightcast |
| Figuring Out (Raj Shamani) | **0 of 649** | none |

- The `.vtt` format holds text in timed chunks (cues), not per-word times. That is accurate enough for a citation within about 15 seconds, but coarser than Whisper's word-level times.
- Where a transcript exists, U3 could download it instead of running Whisper. Where none exists (all Raj Shamani episodes, which are also the Hindi and Hinglish ones in decision D11), Whisper is still needed.
- This is proposed as decision D13 and is not yet adopted.

## Greg Isenberg, 2026-03-17: a hard matching case
The feed has three episodes within 7 days: "My OpenClaw setup that finally works" (03-19), "AI Agents Full Course 59 Minutes (for beginners)" (03-17, 3535 s) and "Autoresearch clearly explained" (03-11). The YouTube title "Building AI agents that actually work" shares almost no words with any of them. The date and the topic point to the 03-17 episode. Only the length can confirm it, and the length is already stored in the database by U1.

## What this changes
- **No paging code is needed.** Fetch a feed once, store the episodes, refresh with `since`. This is simpler than the spec assumed. U2 requirements and plan are updated.
- **Old videos are reachable**: a year-old episode (position 156) was found without any date filter.
- **Titles need normalising** (case, curly quotes, punctuation, guest and episode-code suffixes after a pipe). The title examples are listed in `requirements.md`.
- The seed list's `y` count was 15. With Diet Expert corrected it is 16, and Greg Isenberg's March episode is unresolved.

## Open items
1. **Publisher transcripts.** Answered above (95%, 49% and 0%). Open: decision D13 on whether U3 uses them, and a side-by-side check of one publisher transcript against Whisper.
2. **Greg Isenberg "Building AI agents that actually work" (2026-03-17).** Probable match found by date. Confirm by comparing the stored YouTube duration of video `eA9Zf2-qYYM` with 3535 s.
3. **Feeds above 1,000 episodes.** Untested. If one turns up, test the cap and fall back to the RSS file if needed.
4. **Dan Martell's feed.** Two candidate feeds are still unverified.
