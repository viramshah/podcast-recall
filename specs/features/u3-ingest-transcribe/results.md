# U3: Ingest and Transcribe, Validation Results

Recorded 2026-11-17 against the PM's real seed list. Spec: `validation.md` (v2). Automated: 248 tests pass, lint clean.

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
| 10 | Spot-check words and times | Partly | One publisher episode (12:30, "9 Stages of AI Agent Adoption"): exact match. Four more to do |
| 11 | Flags on all transcripts | Passed | No `needs_review`, so no flag evidence for D15 |
| 12 | Broken link falls back to Whisper | Pending | |
| 13 | The 4 non-matches never downloaded | Passed | 16 transcript files, none for the 4 non-matches, audio folder empty |
| 14 | Secrets and git check | Pending | |

## Findings
- **Whisper small cannot be trusted on Hindi/Hinglish audio.** It looped, and one episode stayed "transcribing" for 45+ minutes. Turbo fixed it.
- **A real design gap:** no per-episode time limit and no automatic switch to a better model. Tracked as D16.
- **The process was suspended once** (Ctrl+Z instead of Ctrl+C) and held the lock, so the next run was refused. It needed `kill -9`. The lock worked as designed.
- **D15 thresholds are untested:** no Whisper transcript on real data was flagged, so nothing was learned about where the limits should sit.

## Open items
- Steps 10 (four more), 12 and 14.
- Listen to 14:37 to 15:00 of FO433 (the repeated "eat" and the garbled tail).
- Decide D16 (time limit, and small versus turbo per episode).
- D15 stays provisional.
- Write `docs/Week1c_U3_Explained.md` when U3 is closed.
