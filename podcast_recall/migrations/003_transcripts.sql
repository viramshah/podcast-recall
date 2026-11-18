-- U3 schema: the transcription queue and the transcripts it produces.
-- Shared data (decision D10). Both tables point to `episodes`, so U1's purge never removes a
-- video whose episode has a transcript or a job.

CREATE TABLE jobs (
    episode_id    INTEGER PRIMARY KEY REFERENCES episodes(episode_id),
    state         TEXT NOT NULL CHECK (state IN
                  ('queued', 'fetching', 'downloading', 'transcribing', 'done', 'failed')),
    attempts      INTEGER NOT NULL DEFAULT 0,
    force_whisper INTEGER NOT NULL DEFAULT 0,
    not_before    TEXT,
    last_error    TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    started_at    TEXT,
    finished_at   TEXT
);
CREATE INDEX idx_jobs_state ON jobs (state);

CREATE TABLE transcripts (
    episode_id       INTEGER PRIMARY KEY REFERENCES episodes(episode_id),
    path             TEXT NOT NULL,
    raw_path         TEXT,
    source           TEXT NOT NULL CHECK (source IN ('publisher', 'whisper')),
    timing_detail    TEXT NOT NULL CHECK (timing_detail IN ('chunk', 'word')),
    model            TEXT NOT NULL DEFAULT '',
    language         TEXT NOT NULL DEFAULT '',
    audio_duration_s INTEGER,
    transcript_end_s REAL,
    word_count       INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL CHECK (status IN ('ok', 'needs_review')),
    flags_json       TEXT NOT NULL DEFAULT '[]',
    publisher_url    TEXT,
    fallback_reason  TEXT,
    created_at       TEXT NOT NULL
);
CREATE INDEX idx_transcripts_status ON transcripts (status);
