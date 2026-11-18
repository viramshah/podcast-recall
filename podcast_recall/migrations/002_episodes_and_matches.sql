-- U2 schema: podcast feeds, their episodes, and the match of each YouTube video to an episode.
-- Everything here is shared data (decision D10). A channel's feed is NULL when the PM chose "none".

CREATE TABLE feeds (
    feed_id                INTEGER PRIMARY KEY,
    title                  TEXT NOT NULL DEFAULT '',
    url                    TEXT NOT NULL DEFAULT '',
    author                 TEXT NOT NULL DEFAULT '',
    language               TEXT NOT NULL DEFAULT '',
    episode_count_reported INTEGER,
    fetched_at             TEXT,
    newest_published       INTEGER,
    truncated              INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE channel_feeds (
    channel_id TEXT PRIMARY KEY REFERENCES channels(channel_id),
    feed_id    INTEGER REFERENCES feeds(feed_id),
    decided_at TEXT NOT NULL
);

CREATE TABLE episodes (
    episode_id       INTEGER PRIMARY KEY,
    feed_id          INTEGER NOT NULL REFERENCES feeds(feed_id),
    guid             TEXT NOT NULL DEFAULT '',
    title            TEXT NOT NULL DEFAULT '',
    published        INTEGER,
    duration_s       INTEGER,
    audio_url        TEXT NOT NULL DEFAULT '',
    audio_type       TEXT NOT NULL DEFAULT '',
    transcript_url   TEXT,
    transcripts_json TEXT NOT NULL DEFAULT '[]',
    link             TEXT NOT NULL DEFAULT '',
    fetched_at       TEXT NOT NULL
);
CREATE INDEX idx_episodes_feed ON episodes (feed_id, published);

CREATE TABLE episode_matches (
    video_id        TEXT PRIMARY KEY REFERENCES videos(video_id),
    episode_id      INTEGER REFERENCES episodes(episode_id),
    status          TEXT NOT NULL CHECK (status IN ('matched', 'needs_review', 'unmatched', 'no_feed')),
    method          TEXT NOT NULL DEFAULT '',
    reason          TEXT NOT NULL DEFAULT '',
    score           REAL,
    title_score     REAL,
    date_score      REAL,
    duration_score  REAL,
    duration_diff_s INTEGER,
    margin          REAL,
    candidates_json TEXT NOT NULL DEFAULT '[]',
    reviewed        INTEGER NOT NULL DEFAULT 0,
    resolved_at     TEXT NOT NULL
);
CREATE INDEX idx_episode_matches_status ON episode_matches (status);
CREATE INDEX idx_episode_matches_episode ON episode_matches (episode_id);
