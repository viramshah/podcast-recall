# U3: Ingest and Transcribe, Requirements (v2, 2026-11-17)

Branch: `feature/u3-ingest-transcribe` (start it from `main` after U2 is merged). Depends on U2 (`episodes`, `feeds` and `episode_matches` tables). Source: requirements doc section 1.5 (U3), adapted. Decisions: D10 (shared episode data), D11 (languages), D13 (publisher transcript first, Whisper as the fallback), D15 (transcript quality thresholds). v2 adds the answers from the pre-build ambiguity review, listed at the end.

## What done looks like
- Every episode that U2 matched gets a transcript with timestamps, stored locally and shared by all users (D10).
- The transcript comes from the **publisher's own transcript file when one exists and passes the checks**, and from **local Whisper on the publisher's audio otherwise** (D13).
- Work runs from a queue that survives crashes and restarts. Re-running never repeats finished work and never leaves a half-written result.
- Every failure is retried, then reported with a reason. Nothing fails silently, and a transcript that looks wrong is flagged and kept out of search until a human accepts it.
- **Week 1 target:** every seed episode whose expected outcome is `matched` (16 of the 20) ends with a transcript that is `ok`, or its problem is explained and fixed.
- Cost: $0. Whisper's speed was measured in Week 0 at about 0.14 to 0.24 seconds of compute per second of audio with the small model, so a 1-hour episode takes about 8 to 15 minutes.

## How a transcript is made (one job per episode)
1. **Publisher first.** Unless the job is forced to Whisper, look at the episode's stored transcript links (`transcript_url` and the `transcripts` list from U2). Pick a supported one, download it, parse it, check it. If it passes, save it with `source = publisher`. No audio is downloaded.
2. **Whisper fallback.** If there is no supported link, or the download, the parsing or a check fails (the reason is recorded), download the audio, check it with `ffprobe`, run Whisper, check the result, and save it with `source = whisper`.
3. **Save** the transcript file and its database row, then finish the job.

## Scope
### Queue
- A `jobs` table with one row per episode (not per video: two videos matched to one episode share one job).
- States: `queued`, `fetching` (publisher file), `downloading` (audio), `transcribing`, `done`, `failed`.
- **Who is enqueued.** `transcribe run` first enqueues every episode that has at least one `episode_matches` row with status `matched` and that has no job yet. (U2's `resolve confirm` sets the status to `matched`, so a confirmed result is included. Unreviewed `needs_review`, `unmatched` and `no_feed` results are never enqueued.) A `done` job is never enqueued again.
- **Which jobs run.** By default, every due job. `--seed [FILE]` limits the run to the episodes of the seed file's videos. `--user NAME` limits it to the episodes of that user's library. `--limit N` stops after N jobs.
- **Order.** Jobs with a usable publisher transcript first (they take seconds), then Whisper jobs, shortest episode first, so results arrive early. Ties go by episode ID.
- **Attempts.** Up to 3 per job. After a failed attempt the job goes back to `queued` with a not-before time (2 minutes after the first failure, 10 minutes after the second). A run ignores jobs that are not due and reports how many are waiting. After the third failure the job is `failed`. `transcribe retry` starts it again with a fresh set of attempts.
- **Crash recovery.** When a run starts, any job left in `fetching`, `downloading` or `transcribing` is returned to `queued` without using an attempt, and unfinished temporary files (`*.part`) are deleted.
- **One worker at a time**, using an operating-system file lock (`<data folder>/transcribe.lock`), released automatically if the process dies. A second run exits with a clear message. Whisper is never run in parallel with itself.

### Publisher transcripts (D13)
- **Supported formats in v1:** WebVTT (`.vtt`, type `text/vtt`) and SubRip (`.srt`, type `application/srt` or `application/x-subrip`). The format comes from the stored type, falling back to the file extension. JSON, HTML and plain-text transcripts are not used in v1 (they either lack timing or need extra work), and the episode falls through to Whisper.
- **Parsing.** Read the timed cues. Ignore `WEBVTT` headers, `NOTE`, `STYLE` and cue identifiers. Remove markup tags, decode HTML entities, collapse white space, skip empty cues, and merge consecutive cues with identical text. Keep the speaker label when a cue carries one (`<v SPEAKER_00>` or `<v Name>`). The publisher file checked on 2026-11-17 used anonymous labels such as `SPEAKER_00`, not names. Times may be `mm:ss.mmm` or `hh:mm:ss.mmm`. Cues must not run backwards in time, or the file fails the checks.
- **Keep the original file** next to the parsed transcript (`<data folder>/transcripts/raw/<episode_id>.vtt` or `.srt`), so a parsing problem can be reproduced.
- Publisher times line up with the publisher's own audio. Dynamic ad insertion can shift them for listeners, so the stored duration check (below) matters.

### Audio and Whisper
- **Download.** The episode's `audio_url` to `<data folder>/audio/<episode_id>.<ext>` (extension from the content type, default `.mp3`), via a temporary `.part` file renamed on success.
- **Accepted responses:** content type `audio/*`, `video/mp4`, `application/octet-stream` or `binary/octet-stream`. The real test is `ffprobe`: the file must have an audio stream and a duration above 0, otherwise the job fails with that reason.
- **Disk space.** Before downloading, require free space of at least the larger of 2 times the advertised file size or 500 MB. Otherwise stop with a clear message before downloading anything.
- **Whisper.** `mlx-whisper`, word timestamps on, `condition_on_previous_text` off (this reduces long repeated-text loops on long audio). The model comes from `PODCAST_RECALL_WHISPER_MODEL` (default `mlx-community/whisper-small-mlx`) and is recorded in every transcript. The **language is detected**, never forced to English, and recorded (D11). `PODCAST_RECALL_WHISPER_LANGUAGE` may force a language.
- **Retention.** Delete the audio after a successful transcript unless `--keep-audio` is given.

### Safety rules for every download (audio and transcript files)
- Only `http` and `https`, no credentials inside the URL, at most 5 redirects.
- **Check the host at every step, including after each redirect**, and refuse addresses that point to this Mac or a private network: loopback (`127.0.0.1`, `localhost`, `::1`), private ranges, link-local, multicast and reserved addresses. A host with no public address is refused.
- Limits: audio 600 MB, transcript file 20 MB, connect timeout 15 seconds, total time 30 minutes for audio and 2 minutes for a transcript file.
- Never run downloaded content as code.

### The transcript file (the contract with U4)
One JSON file per episode at `<data folder>/transcripts/<episode_id>.json`, written to a temporary name and renamed:
```json
{
  "episode_id": 62911913190,
  "source": "publisher",
  "timing_detail": "chunk",
  "model": "publisher:vtt",
  "language": "en",
  "audio_duration_s": 6067,
  "created_at": "2026-11-17T22:10:00Z",
  "segments": [
    {"start": 0.0, "end": 3.2, "text": "Welcome back to the show.", "speaker": "Lenny", "words": []}
  ]
}
```
- `source` is `publisher` or `whisper`. `timing_detail` is `chunk` (publisher cues) or `word` (Whisper).
- Every segment has `start`, `end` (seconds from the start of the episode) and `text`. Whisper segments also carry `words`, each with `text`, `start` and `end`. `speaker` appears only if the publisher file carried a label, which may be anonymous (`SPEAKER_00`) rather than a name.
- `language` is the Whisper-detected language, or the feed's language for a publisher transcript (a publisher file does not say).
- `audio_duration_s` is the feed's stated duration, or the measured audio length for Whisper.

### Quality checks (starting values, decision D15)
All numbers live in one constants block in `quality.py`.
- **Publisher transcript** (a failed check means fall back to Whisper and record the reason): not empty (at least 50 words); times never run backwards; the last cue ends between 85% and 105% of the feed's stated duration; between 80 and 260 words per minute.
- **Whisper transcript** (a failed check keeps the transcript but marks it `needs_review`): not empty; between 80 and 260 words per minute; the last segment ends at least 90% of the way through the measured audio; no silent gap longer than 120 seconds between segments; the detected language matches the feed's language (compared by its first part, `en`). 
- **Information only** (flagged, no effect on the status): an episode longer than 3 hours; a measured audio length that differs from the feed's stated duration by more than 2% (a sign of dynamic ads).
- Every transcript row stores its status (`ok` or `needs_review`) and the list of flags. U4 indexes only `ok` transcripts. `transcribe accept <episode_id>` marks a flagged transcript `ok` after the PM has looked at it, and `transcribe retry <episode_id> --whisper` redoes it with Whisper.

### Commands
- `transcribe run [--seed [FILE]] [--user NAME] [--limit N] [--keep-audio]`: enqueue, then process due jobs. Prints one line per job (position, title, source, audio length, time taken) and a summary. A Mac that goes to sleep stops the run, so for long runs use `caffeinate -i uv run podcast-recall transcribe run`.
- `transcribe status [--seed [FILE]]`: counts of matched episodes, transcripts `ok` and `needs_review`, jobs queued, waiting and failed, the reason for each failed job, how many videos are `not_indexable` (worked out from U2: no feed, unmatched or unreviewed), and disk space used by audio and transcripts.
- `transcribe retry <episode_id> [--whisper]`: a fresh set of attempts, optionally forced to Whisper.
- `transcribe accept <episode_id>`: mark a `needs_review` transcript `ok`.
- `transcribe show <episode_id> [--at mm:ss] [--window SECONDS]`: print the source, model, language, timing detail and flags, and the text within the window (default 30 seconds) around a time, for spot-checking.
- Exit codes: 0 everything finished; 2 some jobs failed, are waiting, or produced a transcript that needs review; 1 error.

### Core functions (`core.py`, no printing)
`enqueue_episodes`, `run_queue`, `get_transcript` (returns the contract above as objects), `transcribe_status`, `retry_job`, `accept_transcript` and `show_transcript`.

## Edge cases
- `no_feed`, `unmatched` and unreviewed `needs_review` videos: never enqueued. They are counted as `not_indexable` in `transcribe status`, worked out from U2, with no job row (D2).
- Audio URL gone (404) or behind a login: the attempt fails with that reason.
- A transcript link that is gone or unreadable: fall back to Whisper and record why.
- A feed that returns a different transcript later: the stored one is kept. `transcribe retry` replaces it.
- Mac sleeps or the process is killed mid-job: see crash recovery above.
- The stored transcript file is missing for a `done` job: `transcribe status` reports it, and `transcribe retry` rebuilds it.
- Two videos matched to one episode: one job, one transcript.
- Whisper cannot read the audio: the attempt fails with `ffprobe` or Whisper's reason.

## Out of scope
- Speaker identification (diarization). A publisher's speaker names are kept when present.
- Transcribing videos with no feed (D2).
- Chunking, embeddings and search (U4). U3 stores `segments`, and U4 decides how to cut them.
- Offset correction between the feed audio and the YouTube video (v2).
- Publisher transcripts in JSON, HTML or plain text.
- Scheduling a nightly run (Operations phase).

## Data stored (migration 003, shared data per D10)
- `jobs`: episode ID (key, points to `episodes`), state, attempts, `force_whisper`, not-before time, last error, created, updated, started and finished times.
- `transcripts`: episode ID (key, points to `episodes`), path to the JSON file, path to the raw publisher file, source, timing detail, model, language, audio duration, end time of the last segment, word count, status (`ok` or `needs_review`), flags as JSON, the publisher URL (provenance), and created time.
Transcript and audio files are in the data folder, outside git. Because both tables point to `episodes`, U1's purge never removes a video whose episode has a transcript.

## Settings (environment variables, documented in the README)
`PODCAST_RECALL_WHISPER_MODEL` (default `mlx-community/whisper-small-mlx`) and `PODCAST_RECALL_WHISPER_LANGUAGE` (default: detect).

## Known risks
- **Language (D11).** Raj Shamani's "Figuring Out" (5 of the 16 matched seed episodes) is, as far as I know, largely Hindi or Hinglish, and its feed offers no transcript, so it always goes through Whisper. Whisper auto-detects the language, and a mismatch with the feed's language is flagged. Transcribe 5 minutes of one of those episodes early and judge the result before deciding whether they stay in the golden set.
- **Model size.** The small model was tested in Week 0. Exact-quote checks later need accurate text. Compare it with a larger model on one hand-checked 5-minute clip before the full run.
- **Publisher transcript precision.** Measured on 2026-11-17: cues average about 3 seconds and every cue start was within 2 seconds of Whisper's word times, which is more than enough for a citation. D13 stays revisitable (see validation).
- **No speaker names from Whisper.** The later check on speaker attribution depends on names stated in the transcript itself.
- **Dynamic ads.** Publisher transcript times and the audio that listeners hear can drift apart. The duration flag shows where this is likely.

## Decisions made in the pre-build review (2026-11-17)
1. Enqueue only `matched` results. The earlier "`needs_review` with `reviewed = 1`" case cannot occur, because `resolve confirm` sets `matched`.
2. By default `transcribe run` covers every matched episode, with `--seed` and `--user` filters. There is no `--overnight` flag; use `--limit` to cap a run and `caffeinate` to keep the Mac awake.
3. Publisher transcripts run first, then Whisper jobs shortest first.
4. A failed publisher check falls back to Whisper automatically and records why. A failed Whisper check keeps the transcript as `needs_review`.
5. Whisper detects the language and never forces English. A mismatch with the feed language is flagged.
6. Only VTT and SRT are used from publishers in v1. The raw file is kept.
7. A `needs_review` transcript stays out of U4's index until `transcribe accept` or a retry with Whisper.
8. The small Whisper model is the default. The model is recorded per transcript. Changing it later does not retranscribe anything by itself.
9. The transcript JSON above is the contract with U4.
10. Corrections to v1: the seed count is 16 matched (not 15), 4 seed rows are `n` (not 5), and "a list of segments, each with words" became "segments, with words only for Whisper".
