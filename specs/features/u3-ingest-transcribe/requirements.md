# U3: Ingest and Transcribe, Requirements (v1, 2026-11-17)

Branch: `feature/u3-ingest-transcribe`. Depends on U2 (`episodes` table with audio URLs and matched videos). Source: requirements doc section 1.5 (U3), adapted. Decisions: D10 (shared episode data), D11 (languages).

## What done looks like
- For each episode that U2 matched, the app downloads the publisher's public audio and transcribes it locally with **word-level timestamps**.
- Work runs from a queue that survives crashes and restarts. Re-running never repeats finished work and never leaves half-finished results.
- Failures are retried, then reported. Nothing fails silently.
- Transcripts are cached and shared across users (D10).
- **Week 1 target:** all 20 seed episodes that have a feed (15 at the moment) have transcripts, spot-checked against the audio.
- Cost: $0. Transcribing 1 hour of audio overnight is acceptable. Measured in Week 0: about 0.14 to 0.24 seconds of compute per second of audio with the small model.

## Scope
1. **Queue.** A `jobs` table with one row per episode and a state: `queued`, `downloading`, `transcribing`, `done` or `failed`. Each job records attempts, last error and timestamps. `not_indexable` is **not** a job state: it is worked out from U2's `episode_matches` (a video with status `no_feed` or `unmatched`, or `needs_review` that has not been confirmed) and shown by `transcribe status`.
   **Who enqueues.** `transcribe run` first enqueues every episode that has a match with status `matched`, or `needs_review` with `reviewed = 1` (confirmed by the PM with `resolve confirm`), and that has no job yet. It never enqueues anything else. It never re-enqueues a `done` job.
2. **Download.** Fetch the audio URL from the feed. Check the response is audio and store the file under `<data folder>/audio/` (`~/.podcast-recall/audio/`, outside the repo; see D12). Limits: maximum file size 600 MB, connect timeout 15 seconds, total time 30 minutes, at most 5 redirects. Only `http` and `https` URLs. **After every redirect, refuse addresses that point to this Mac or a private network** (loopback such as `127.0.0.1` and `localhost`, link-local, and private ranges), so a malicious feed cannot make the app call Ollama or another local service.
3. **Transcribe.** Use `mlx-whisper` with word timestamps. Run one transcription at a time, so it never competes with Ollama for memory on a 16GB Mac.
4. **Store the result.** One JSON file per episode under `<data folder>/transcripts/` (`~/.podcast-recall/transcripts/`) with: episode ID, model name and version, detected language, audio duration, and a list of segments, each with words (text, start, end). Also a `transcripts` row pointing to the file, with status and quality flags.
5. **Quality checks** on every transcript, recorded as flags: transcript length within about 2% of the audio duration, a plausible number of words per minute, no long silent gaps in timestamps, and the detected language. A failed check marks the transcript `needs_review` instead of silently trusting it.
6. **Retry.** Up to 3 attempts with backoff. After that, the job is `failed` with the error visible in `status`.
7. **Audio retention.** After a successful transcript, delete the audio file by default to save disk space (about 40 MB per hour). A flag keeps the audio for debugging.
8. **CLI commands:** `transcribe run [--limit N] [--overnight]`, `transcribe status`, `transcribe retry <episode_id>` and `transcribe show <episode_id> [--at mm:ss]` (prints the words near a time, for spot-checking).
9. **Core functions** (`core.py`, no printing): `enqueue_episodes(episode_ids)`, `run_queue(limit)` and `get_transcript(episode_id)`.

## Edge cases
- `no_feed`, `unmatched` and unconfirmed `needs_review` videos: never enqueued. They show as `not_indexable` in `transcribe status` (D2), worked out from U2's table, with no job row.
- Audio URL gone (404) or behind a login: mark `failed` with a clear reason.
- Very long episodes (3 hours or more): allowed, but flagged, because they take longer.
- Mac sleeps or the process is killed mid-job: on restart the job returns to `queued` and starts again cleanly.
- Disk nearly full: stop with a clear message before starting a download.
- Two copies of the same episode matched from different videos: transcribe once.

## Publisher transcripts first, Whisper as the fallback (decision D13, decided 2026-11-17)
The Podcast Index probe on 2026-11-17 found that many publishers supply their own transcript file: 351 of 371 Lenny's episodes (95%), 196 of 396 Startup Ideas episodes (49%), and none of the 649 Figuring Out episodes. The approach:
- Before downloading audio, check the episode's `transcriptUrl`. If there is one, download that file (a `.vtt` file of timed text chunks) and store it as the episode's transcript, with `source = publisher`. Skip the audio download and Whisper.
- If there is no transcript link, or it fails to download or to parse, fall back to audio and Whisper, with `source = whisper`.
- Publisher transcripts have timed chunks, not per-word times. Record the timing detail (`chunk` or `word`) on each transcript so later units know what precision they have.
- Download rules are the same as for audio: only `http` and `https`, refuse private addresses after redirects, a size limit and a timeout.
- Quality checks for a publisher transcript: it is not empty, its last cue ends within 5% of the feed's stated duration, and its words per minute fall in a plausible range. A failed check falls back to Whisper and records why.
- During validation, compare one publisher transcript with a Whisper transcript of the same 5-minute section (`scripts/compare_transcripts.py`): word accuracy on exact quotes, and how far the timings differ. If publisher transcripts prove too inaccurate or too coarse, revisit D13.
Build both paths. The download rules, the job queue, retries and the stored fields are the same for both, and every transcript records its `source` (`publisher` or `whisper`) and its timing detail (`chunk` or `word`).

## Risks to check in Week 1
- **Language (D11).** As far as I know, Raj Shamani's "Figuring Out" podcast (4 of the 20 seed episodes) is largely in Hindi or Hinglish. The small English-tuned setup may transcribe it poorly, and the embedding model used for search is English-focused. Transcribe 5 minutes of one of those episodes early and judge the quality before deciding whether they stay in the golden set.
- **Model size.** The small Whisper model was tested in Week 0. The quote check later needs transcripts accurate enough to fuzzy-match at 0.90. Compare the small model with a larger one on one hand-checked 5-minute clip before transcribing all 20.
- **No speaker names.** Whisper does not say who is speaking. Speaker labels are out of scope for v1, so the later rubric check on speaker attribution (R4) will depend on names stated in the transcript itself. Record this as a known limit.

## Out of scope
- Speaker identification (diarization).
- Transcribing videos with no feed (D2). Reconsidered in Week 1 only if you decide to allow audio download from YouTube.
- Chunking, embeddings and search (U4).
- Offset correction between the feed audio and the YouTube video (v2). U3 records durations so the gap can be measured.

## Data stored
Shared tables (D10): `jobs` and `transcripts`. Transcript JSON files live outside git. Audio files are temporary.

## Open questions for Claude Code to raise before coding
- How to keep exactly one transcription running at a time, including after a crash.
- Which Whisper model files to download and where they are cached.
- How to detect and handle audio that Whisper cannot read.
