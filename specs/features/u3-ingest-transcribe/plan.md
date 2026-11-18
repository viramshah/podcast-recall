# U3: Ingest and Transcribe, Plan (v2, 2026-11-17)

## Approach
1. **Start from a merged U2.** Create `feature/u3-ingest-transcribe` from `main` after U2 is merged. U3 reads U2's `episodes` and `episode_matches`.
2. **No new dependencies.** `mlx-whisper` is already in `pyproject.toml`. Use `ffprobe` (from `ffmpeg`, already installed) through `subprocess`, as `scripts/transcribe_test.py` does. HTTP uses `urllib`, as in U2.
3. **`net.py`: safe downloads.** One place for every download. A custom redirect handler that checks the host at each hop (and refuses loopback, private, link-local, multicast and reserved addresses, and URLs with credentials), a redirect limit of 5, size limits, a time limit and streaming to a `.part` file with a running size count. The host-resolving function is injectable so tests use a fake resolver and a local fake server. Never logs full URLs with query strings.
4. **`publisher.py`.** Pick a supported transcript entry (VTT, SRT; by stored type, then extension), download it through `net.py`, parse the cues into the transcript structure, and keep the raw file. Pure parsing functions. Reuse the cue-parsing approach from `scripts/compare_transcripts.py`, extended for SRT, entities, merged duplicate cues and speakers.
5. **`audio.py`.** Disk-space check, the audio download through `net.py`, and the `ffprobe` check (audio stream present, duration above 0). The `ffprobe` call is injectable.
6. **`whisper_runner.py`.** Wraps `mlx-whisper` with the settings in the requirements, returning segments with words and the detected language. The Whisper call is injectable, so tests never load a model. One optional real-model test, skipped unless `mlx_whisper` is installed and `RUN_WHISPER_TEST=1`.
7. **`quality.py`.** Pure functions and one constants block for the checks and flags in the requirements.
8. **`transcripts.py`.** Build the transcript structure, write the JSON and raw files atomically (temporary name, then rename), write the `transcripts` row, and read a transcript back for `get_transcript` and `show`.
9. **`jobs.py`.** The queue: enqueue, choose due jobs in the required order, claim, record success or failure with the not-before times, crash recovery, and the `status` counts. The global lock reuses U1's `SyncLock` with a different file.
10. **`transcribe_flow.py`.** `process_job`: the publisher-first, Whisper-fallback logic from the requirements, with each step and each fallback reason recorded.
11. **Migration `003_transcripts.sql`** for `jobs` and `transcripts`, with foreign keys to `episodes`.
12. **`core.py` and `cli.py`.** The functions and commands in the requirements. The CLI only calls the core functions. Progress goes through a callback to standard error, results to standard output.
13. **README.** Document the two settings and the `caffeinate` tip.
14. **Tests.**
    - Publisher parsing with realistic VTT and SRT samples (multi-line cues, identifiers, `NOTE` blocks, tags, entities, speakers, repeated cues, backwards times, hours-less timestamps).
    - Quality checks, one test per rule and per flag.
    - `net.py`: a redirect to `localhost` or a private address is refused at the first and the second hop, credentials in a URL are refused, oversized and slow downloads are cut off, content types are handled.
    - Queue: order, attempts and not-before times, crash recovery (an exception mid-job, then a new run), one worker at a time, two videos sharing one episode, enqueue only `matched`.
    - Flow: publisher success downloads no audio; a missing or broken or implausible publisher file falls back with the reason recorded; Whisper success deletes the audio unless `--keep-audio`; a Whisper check failure gives `needs_review`; language mismatch is flagged; `retry --whisper` and `accept`.
    - Transcript file: atomic write, schema, `show` windows.
    - CLI: exit codes, filters, output. An end-to-end test through the real commands with a fake network and a fake Whisper.

## Constraints
- No secrets in code, logs or git. Audio and transcripts live in the data folder (D12), never in the repo. Use `paths.py`.
- Every download goes through `net.py`.
- One transcription at a time, enforced by the lock.
- Write results atomically so a crash never leaves a half-written transcript that looks finished.
- `core.py` has no printing.
- The matcher, the resolver and U1 are not changed by U3, except for the migration.

## Review checklist (PM)
- [ ] Killing the process mid-job and restarting resumes cleanly: no duplicate and no half-written file, and the attempt count is not used up by the crash
- [ ] Only one worker can run at a time, and a killed worker leaves no stuck lock
- [ ] Only `matched` episodes are enqueued, and `not_indexable` videos have no job row
- [ ] A failed job shows its reason in `transcribe status` after 3 attempts, and `retry` gives it a fresh start
- [ ] A download that redirects to `localhost` or a private address is refused at every hop, tested with a fake server
- [ ] An episode with a good transcript link uses the publisher transcript, downloads no audio and records `source = publisher` and `timing_detail = chunk`
- [ ] A missing, broken, implausible or unsupported publisher file falls back to Whisper and records the reason
- [ ] Every Whisper transcript has word times, and every transcript records its source, model, language, timing detail and duration
- [ ] A transcript that fails a Whisper check is stored as `needs_review` with its flags, and is not `ok` until `transcribe accept`
- [ ] The language is detected, not forced to English, and a mismatch with the feed language is flagged
- [ ] The raw publisher file is kept, and audio is deleted after success unless `--keep-audio`
- [ ] The transcript JSON matches the contract in the requirements
- [ ] No secrets or full transcripts in git or logs, and URLs with tokens are redacted in logs
- [ ] Nothing added beyond the spec (no chunking, no search, no diarization)
