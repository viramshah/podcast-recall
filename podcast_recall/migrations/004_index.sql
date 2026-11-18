-- U4 schema: searchable chunks of transcripts. Shared data (decision D10); which user may see a
-- chunk is decided at search time from the user's library, never stored here.
-- The vector table (`chunk_vectors`) is created at run time by `vectors.py`, because it needs the
-- sqlite-vec extension and a vector size that depends on the embedding model.

CREATE TABLE chunks (
    chunk_id   INTEGER PRIMARY KEY AUTOINCREMENT,  -- ids are never reused, so a stale vector cannot attach to a new chunk
    episode_id INTEGER NOT NULL REFERENCES episodes(episode_id),
    chunk_no   INTEGER NOT NULL,
    start_s    REAL NOT NULL,
    end_s      REAL NOT NULL,
    text       TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    speaker    TEXT,
    UNIQUE (episode_id, chunk_no)
);
CREATE INDEX idx_chunks_episode ON chunks (episode_id, start_s);

CREATE VIRTUAL TABLE chunks_fts USING fts5(
    text, content = 'chunks', content_rowid = 'chunk_id', tokenize = 'porter unicode61'
);

CREATE TRIGGER chunks_after_insert AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts (rowid, text) VALUES (new.chunk_id, new.text);
END;

CREATE TRIGGER chunks_after_delete AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts (chunks_fts, rowid, text) VALUES ('delete', old.chunk_id, old.text);
END;

-- What each episode was indexed from. An episode is up to date when the transcript hash, the
-- chunking version and (when vectors are in use) the embedding model all match.
CREATE TABLE index_state (
    episode_id       INTEGER PRIMARY KEY REFERENCES episodes(episode_id),
    transcript_hash  TEXT NOT NULL,
    chunking_version INTEGER NOT NULL,
    embed_model      TEXT,
    embedded         INTEGER NOT NULL DEFAULT 0,
    chunk_count      INTEGER NOT NULL,
    indexed_at       TEXT NOT NULL
);

CREATE TABLE index_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
