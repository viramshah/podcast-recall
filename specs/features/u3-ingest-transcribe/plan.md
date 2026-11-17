# U3: Ingest and Transcribe, Plan (v1, 2026-11-17)

## Approach
1. **Dependencies.** Reuse `mlx-whisper` (already in `pyproject.toml`) and the HTTP client added in U2. Use `ffprobe` (from the installed `ffmpeg`) to read audio duration, as `scripts/transcribe_test.py` does.
2. **`jobs.py`.** The queue on SQLite: add, claim, update state, retry with backoff, and recover jobs left in `downloading` or `transcribing` after a crash by returning them to `queued`. A lock file ensures only one worker runs.
3. **`download.py`.** Download with the limits in the requirements (600 MB, 15 s connect, 30 min total, 5 redirects), check the content type, write to a temporary name and rename on success. Delete partial files on failure. Resolve the host after each redirect and refuse loopback, link-local and private addresses.
3b. **`publisher.py`.** Decided in D13. Downloads an episode's publisher transcript (a `.vtt` file, using the same download safety rules), parses its timed cues into the same structure Whisper produces (with `chunk` timing detail), and runs the publisher-transcript quality checks. Pure parsing functions, no database access. If anything fails, the caller falls back to Whisper.
4. **`transcribe.py`.** Wraps `mlx-whisper` (model name from configuration) and returns a structure of segments and words. Starts from `scripts/transcribe_test.py`, but the output format is new: that script writes a flat word list, while U3 stores segments that each contain words. No database access.
5. **`quality.py`.** Pure functions for the quality checks (duration match, words per minute, gaps, language). Easy to unit test.
6. **`transcripts.py`.** Writes the JSON file atomically, then the `transcripts` row. Reads for `get_transcript`.
7. **`store.py`.** Add `jobs` and `transcripts` tables, with a migration.
8. **`core.py` and `cli.py`.** Core functions as listed in the requirements. The CLI only calls them. `transcribe run --overnight` runs until the queue is empty and prints a summary.
9. **Tests.** Queue tests (crash recovery, retries, one worker), quality-check tests, and download tests with a local fake server (404, wrong content type, oversized file). A very short real audio clip tests the Whisper wrapper end to end.

## Constraints
- No secrets in code, logs or git. Audio and transcripts live in the data folder (`~/.podcast-recall/audio/` and `transcripts/`, D12), outside the repo. Use the path helper from U1 (`paths.py`).
- One transcription at a time. Never run it in parallel with another job.
- Download only `http` and `https` URLs. Never run downloaded content as code.
- Write results atomically (temporary name, then rename), so a crash never leaves a half-written transcript that looks finished.
- `core.py` has no user-facing printing.

## Review checklist (PM)
- [ ] Killing the process mid-job and restarting resumes cleanly with no duplicate or half-finished transcript
- [ ] Only one worker can run at a time
- [ ] Failed jobs show the reason in `transcribe status`, after 3 attempts
- [ ] Every transcript has per-word start and end times, model name, language and duration
- [ ] Quality flags are stored, and a failed check marks `needs_review` instead of passing silently
- [ ] Audio is deleted after success unless the keep flag is set
- [ ] Unmatched, no-feed and unconfirmed `needs_review` videos are never downloaded, and appear as `not_indexable` without a job row
- [ ] A download that redirects to `localhost` or a private address is refused (tested with a fake server)
- [ ] An episode with a transcript link uses the publisher transcript, downloads no audio and records `source = publisher`
- [ ] A missing, broken or implausible transcript file falls back to Whisper and records why
- [ ] Every transcript records its source and its timing detail (`chunk` or `word`)
- [ ] No secrets or full transcripts in git or logs
- [ ] Nothing added beyond the spec (no chunking, no search, no diarization)
