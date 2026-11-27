# Podcast Recall

A local app that answers questions from your YouTube podcast library with verified quotes,
timestamps and links. This README covers the U1 YouTube connector. The product plan is in
`specs/`.

## Setup

```bash
uv sync
```

Create a Google Cloud OAuth client of type "Desktop app", enable the YouTube Data API v3, and
save the downloaded file as `~/.podcast-recall/client_secret.json` (or point `CLIENT_SECRET_PATH`
at it). Keep it out of the repo.

## Settings

Settings come only from environment variables.

| Variable | Default | Meaning |
|---|---|---|
| `PODCAST_RECALL_HOME` | `~/.podcast-recall` | Data folder: database, logs, backups, locks (later: audio and transcripts). Permissions 700. |
| `CLIENT_SECRET_PATH` | `~/.podcast-recall/client_secret.json` | Google OAuth client file. |
| `PODCAST_RECALL_VIDEO_REFRESH_DAYS` | `30` | Stored video details older than this are fetched again during `sync`. |
| `PODCASTINDEX_KEY`, `PODCASTINDEX_SECRET` | none | Podcast Index credentials for `resolve`. If unset, they are read from `<data folder>/podcastindex.env` (lines like `export PODCASTINDEX_KEY=...`, permissions 600). |
| `PODCAST_RECALL_WHISPER_MODEL` | `mlx-community/whisper-small-mlx` | Whisper model used when an episode has no usable publisher transcript. |
| `PODCAST_RECALL_WHISPER_LANGUAGE` | detect | Force a language (for example `hi`) instead of detecting it. |
| `PODCAST_RECALL_WHISPER_FALLBACK_MODEL` | `mlx-community/whisper-large-v3-turbo` | Larger model tried once when a Whisper run takes too long (half the audio length plus 5 minutes, at least 10) or its transcript is flagged. `none` turns the retry off. |
| `PODCAST_RECALL_EMBED_MODEL` | `nomic-embed-text` | Ollama model used to turn transcript chunks and questions into vectors for meaning search. Pull it once with `ollama pull nomic-embed-text`. |
| `PODCAST_RECALL_OLLAMA_URL` | `http://127.0.0.1:11434` | Where Ollama listens. Only a loopback address is accepted. |
| `PODCAST_RECALL_CHUNK_SECONDS` | `120` | Target length of a search chunk (15 to 300). Changing it makes the next `index build` redo every episode. Used for tuning. |
| `PODCAST_RECALL_CHUNK_OVERLAP_SECONDS` | 20% of the chunk length (`24`) | How far each chunk reaches back into the one before (0 to half the chunk length). |
| `PODCAST_RECALL_INTRO_WEIGHT` | `1` (no change) | Multiplies the search score of chunks from an episode's first 3 minutes (the teaser and host summary), which can crowd out the real answer. 0.5 helped on the dev questions but was not confirmed on the held-out ones, so it is off by default. |
| `PODCAST_RECALL_ANSWER_MODEL` | `qwen2.5:7b-instruct` | Ollama model that writes answers. Pull it once with `ollama pull qwen2.5:7b-instruct`. |
| `PODCAST_RECALL_ANSWER_TIMEOUT_S` | `120` | How long to wait for the model before retrying once and then giving up with a plain message. |
| `PODCAST_RECALL_PASSAGES` | `8` | How many search results (passages) the model is shown for each question. |
| `PODCAST_RECALL_UNIT_TOP` | `0` (off) | Experiment: show the answering model only this many best-matching units (plus their neighbours) from the retrieved passages instead of every unit. Smaller prompt, faster, easier to point at the right unit. Needs the embedding model at question time. |
| `PODCAST_RECALL_EXPORT_DIR` | `~/Documents/Podcast Recall exports` | Where `findings export` writes files (mode 600). Exports hold your questions and short transcript quotes; revoking your account does not delete files already exported. |
| `PODCAST_RECALL_PREMISE_STEP` | off | Experiment: when the answer is "not found" and the question is about what someone says ("Why does X say ...?"), one more model call checks whether the passages contradict what the question assumes and, if so, answers with a correction. Only runs after a "not found". |
| `PODCAST_RECALL_ANSWER_CHECK` | off | Set to `1` to have a second model check every answer before it is shown: each claim must be clearly supported by its quote and must answer the question, otherwise it is dropped (and the answer becomes "not found" if none is left). Adds one model call per answer. |
| `PODCAST_RECALL_JUDGE_MODEL` | `llama3.1:8b` | The model that does that check (a different family from the answer model). Pull it with `ollama pull llama3.1:8b`. |

## Commands

All commands except `purge` take `--user <name>` (default `owner`).

```bash
uv run podcast-recall auth                 # sign in with Google (read-only)
uv run podcast-recall channels list        # your subscriptions (fetched on first use)
uv run podcast-recall channels mark <id>   # treat a channel as a podcast
uv run podcast-recall sync                 # playlists, Liked videos, marked channels
uv run podcast-recall status
uv run podcast-recall fetch data/seed_episodes.csv
uv run podcast-recall revoke               # asks for confirmation (--yes to skip)
uv run podcast-recall purge --days 30
```

Exit codes: 0 success, 1 error, 2 partial result or something needs attention, 3 sign-in needed.

### Matching videos to podcast episodes (U2)

```bash
uv run podcast-recall fetch data/seed_episodes.csv     # load the seed videos first
uv run podcast-recall resolve feeds --seed             # choose a podcast feed for each channel
uv run podcast-recall resolve run --seed               # match videos to episodes, write data/seed_resolver_check.csv
uv run podcast-recall resolve review --seed            # results that need a human look
uv run podcast-recall resolve confirm <video_id> <episode_id>
uv run podcast-recall resolve reject <video_id>
uv run podcast-recall resolve set-feed <channel_id> <feed URL | feed ID | none>
```

Without `--seed`, `resolve` works on the videos in your library. Results you confirm or reject are
never overwritten by a later `resolve run`.

Limit: the YouTube API only returns playlists you own. Playlists that belong to other people are
not included, even if you saved them.

### Getting transcripts (U3)

```
uv run podcast-recall transcribe run --seed            # publisher transcript first, Whisper as fallback
uv run podcast-recall transcribe status --seed         # counts, needs_review, failures, disk use
uv run podcast-recall transcribe show <episode_id> --at 12:30   # text around a time
uv run podcast-recall transcribe accept <episode_id>   # mark a needs_review transcript as ok
uv run podcast-recall transcribe retry <episode_id> [--whisper]
```

Only `matched` episodes are transcribed. Audio is deleted after success (`--keep-audio` keeps it).
Exit codes: 0 all done, 2 some need review, failed or are waiting to retry, 1 error. For a long run
on a laptop, prefix with `caffeinate -i` so the Mac does not sleep.

### Searching transcripts (U4)

```
uv run podcast-recall index build --seed               # split transcripts into chunks and index them
uv run podcast-recall index status --seed              # what is indexed and what is waiting
uv run podcast-recall search "agent harness"           # best matches in YOUR library, with time and a link
uv run podcast-recall search "agent harness" --seed    # the same, over the seed file's episodes instead
uv run podcast-recall search '"exact phrase"' --show lenny --since 2026-10-01 --explain
```

Run `index build` after `transcribe run` (and after `transcribe accept`). It is safe to run again: only
new or changed transcripts are indexed. Search combines keyword and meaning matching and only returns
episodes in your own library (or, with `--seed`, exactly the seed file's episodes, which may not be in your YouTube library). Words are plain words; text in double quotes is an exact phrase. Without
Ollama running, `index build` stops with a clear message and `search` falls back to keywords.
`--explain` shows the scores, including the meaning distance (0 is identical; larger is further away).

### Evaluation (Week 2)

```
uv run podcast-recall eval check                       # golden set: evidence exists, absent answers are absent
uv run podcast-recall eval show q01                    # one question with the transcript text at its gold time
uv run podcast-recall eval run --oracle                # perfect answers built from the golden set: must score 100%
uv run podcast-recall eval run --fabricate invented_quote   # deliberately wrong answers: must fail
uv run podcast-recall eval run --answers answers.jsonl --out evals/scorecards/run.csv
uv run podcast-recall eval retrieval                   # recall@5 on the golden questions
uv run podcast-recall eval retrieval --diagnose        # ...and for each miss, where the right chunk really ranks
uv run podcast-recall eval retrieval --split dev --intro-weight 0.25   # try demoting an episode's opening minutes
uv run podcast-recall eval sheet                       # the sheet for the second labeller (questions only)
uv run podcast-recall eval kappa --labels-b filled.csv # agreement with the second labeller
```

The golden set is `data/golden/golden_v0.csv` and the evaluation library `data/golden/eval_library.csv`
(change them with `--golden` and `--library`). Answers are JSON Lines, one per question id, in the format
in `podcast_recall/answers.py`. `eval run` checks the deterministic rubric rules only (R1 the quote is real,
R2 the source is in the library, R5 abstention, R7 timestamp). The model-judged rules (R3, R4, R6) come later,
and the scorecard says so. Exit code 2 means some answers failed.

### Asking questions (Week 3)

```
uv run podcast-recall ask "What do the guests say about hiring?"   # cited answer in the terminal
uv run podcast-recall ask "..." --show lenny --since 2026-01-01    # limit by show or date
uv run podcast-recall ask "..." --json                             # the same response the web chat gets
uv run podcast-recall ask "..." --no-record                        # do not store the question
uv run podcast-recall serve                                        # local web chat (prints the address)
uv run podcast-recall eval answer --split dev                      # answer the golden questions, print a scorecard
uv run podcast-recall eval answer --split dev --ids p01,sf09 --check --unit-top 12 --premise-step   # a few questions, with the answer check and unit selection
uv run podcast-recall eval judge-sheet --answers RUN.answers.jsonl --count 60   # claims for a person to label
uv run podcast-recall eval judge-agreement --sheet evals/judge_sheet.csv --answers RUN.answers.jsonl   # judge vs the person's labels
uv run podcast-recall eval abstain --split dev                    # can search distance alone say "not found"?
uv run podcast-recall findings list   # saved findings, newest first
uv run podcast-recall findings export --format html   # md (default), html (opens on a phone) or notes (Apple Notes, Mac only); files go to ~/Documents/Podcast Recall exports/
uv run podcast-recall findings note 1 "for the deck"; uv run podcast-recall findings delete 1
uv run podcast-recall eval diagnose --answers evals/scorecards/RUN.answers.jsonl   # why each failing question failed
uv run podcast-recall eval grade-sheet --answers RUN.answers.jsonl --out evals/grade_sheet_RUN.csv   # every claim of a run, for a person to grade R3, R4 and answers-the-question
uv run podcast-recall eval grade-score --answers RUN.answers.jsonl --sheet evals/grade_sheet_RUN.csv   # scores the graded sheet (any R3 no or R4 no is Critical; partly is Major)
```

Every answer is checked before you see it: the model only points at numbered passages, the code copies
the quote and time from the transcript, and a verifier re-runs rules R1 and R2 and removes anything that
fails. If nothing survives you get "I couldn't find that in your podcasts." The web chat listens on
127.0.0.1 only and needs the per-run token that the page carries. Questions are stored in your private
database (never in log files). `eval answer` also prints median latency against the 15 s target, and
saves a private `.trace.jsonl` next to the scorecard (the passages shown, the model's raw reply, what the
verifier removed) for `eval diagnose`; trace and answers files hold transcript text and are git-ignored.
Ollama must be running, with the embedding model and the answer model pulled.

## Tests

```bash
make test    # pytest
make lint    # ruff
```
