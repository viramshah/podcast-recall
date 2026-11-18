# U3: Ingest and Transcribe, Validation Results

Recorded 2026-11-17 against the PM's real seed list. Spec: `validation.md` (v2). Automated: 261 tests pass (248 plus 13 for D16), lint clean.

## Outcome so far
16 matched seed episodes, **16 transcripts ready**, 0 queued, 0 failed, 0 `needs_review`. 4 videos not indexable (the non-matches). Transcripts take 9 MB. The audio folder is empty.

| Source | Model | Language | Status | Episodes |
|---|---|---|---|---|
| publisher | publisher:vtt | en | ok | 12 (all of Lenny's and Greg Isenberg's) |
| whisper | mlx-community/whisper-large-v3-turbo | en | ok | 4 (all Raj Shamani) |

## Steps
| # | Step | Result | Evidence |
|---|---|---|---|
| 1 | Small versus a larger model on a 5-minute section | Passed, for a different reason than planned | Small loops on Hindi/Hinglish audio (see D11); turbo is readable. English comparison not needed: no English episode needed Whisper |
| 2 | Publisher versus Whisper on a Lenny's episode | Partly | 0.95 similar and cue starts within 2 s (D13). The listening check of the disagreement table is still the PM's |
| 3 | 5 minutes of Raj Shamani with Whisper | Passed | Small: garbled and a repetition loop. Turbo: clean. Recorded in D11 |
| 4 | `run --seed --limit 2` | Passed | 2 episodes from the publisher, no audio folder created |
| 5 | Ctrl+C during Whisper, then run again | Passed | Job back in the queue, 0 attempts used, no audio left, later "Recovered after a crash: 1" |
| 6 | Two runs at once | Passed | Second run refused (message reworded to say "transcribe run") |
| 7 | Full seed run | Passed | All 16 `ok`. Turbo run of the 4 Raj Shamani episodes took about an hour |
| 8 | `status --seed` | Passed | 16 ready, 0 queued, 4 not indexable |
| 9 | Publisher or Whisper per episode | Passed | Lenny's and Greg all publisher (Greg was expected to be a mix), Raj Shamani all Whisper |
| 10 | Spot-check words and times | Passed | PM spot-checked 5 episodes (publisher and Whisper, including Raj Shamani): words matched and timing was within the targets. First check (12:30, "9 Stages of AI Agent Adoption") was an exact match |
| 11 | Flags on all transcripts | Passed | No `needs_review`, so no flag evidence for D15 |
| 12 | Broken link falls back to Whisper | Passed | PM ran it on a copy of the data folder: fell back to Whisper with the reason recorded (first real run of small on a full English episode) |
| 13 | The 4 non-matches never downloaded | Passed | 16 transcript files, none for the 4 non-matches, audio folder empty |
| 14 | Secrets and git check | Passed | No audio, transcript, database, `.env` or client-secret file is tracked. The real Podcast Index key appears nowhere in git history. The only data file matching the search (`data/podcastindex_probe.json`) holds public feed data with no credentials; drop it before ever making the repo public |
| 15 | (D16) Time limit and larger-model retry on real audio | Pending | Covered by 13 automated tests; real run optional, about an hour |

## Findings
- **Whisper small cannot be trusted on Hindi/Hinglish audio.** It looped, and one episode stayed "transcribing" for 45+ minutes. Turbo fixed it.
- **A real design gap:** no per-episode time limit and no automatic switch to a better model. Tracked as D16.
- **The process was suspended once** (Ctrl+Z instead of Ctrl+C) and held the lock, so the next run was refused. It needed `kill -9`. The lock worked as designed.
- **D15 thresholds are untested:** no Whisper transcript on real data was flagged, so nothing was learned about where the limits should sit.

## Open items
- Step 15 (optional real run of D16).
- Listen to 14:37 to 15:00 of FO433 (the repeated "eat" and the garbled tail).
- D16 decided and built (time limit, retry with turbo). See `decisions.md`.
- D15 stays provisional.
- `docs/Week1c_U3_Explained.md` written.
