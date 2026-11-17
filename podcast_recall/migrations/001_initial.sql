-- U1 schema. Shared tables: channels, videos. Everything else is per user.
-- Deleting a user row cascades to all of that user's rows (revoke relies on this).

CREATE TABLE channels (
    channel_id          TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    uploads_playlist_id TEXT,
    updated_at          TEXT NOT NULL
);

CREATE TABLE videos (
    video_id            TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    channel_id          TEXT REFERENCES channels(channel_id),
    published_at        TEXT,
    duration_s          INTEGER,
    description         TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'unavailable')),
    unavailable_reason  TEXT,
    is_live_or_upcoming INTEGER NOT NULL DEFAULT 0,
    last_fetched_at     TEXT NOT NULL
);

CREATE TABLE users (
    user_id               TEXT PRIMARY KEY,
    youtube_channel_id    TEXT NOT NULL,
    youtube_channel_title TEXT NOT NULL DEFAULT '',
    created_at            TEXT NOT NULL
);

CREATE TABLE library_items (
    user_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    video_id      TEXT NOT NULL REFERENCES videos(video_id),
    source        TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    PRIMARY KEY (user_id, video_id, source)
);
CREATE INDEX idx_library_items_user_source ON library_items (user_id, source);
CREATE INDEX idx_library_items_video ON library_items (video_id);

CREATE TABLE user_channels (
    user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL REFERENCES channels(channel_id),
    subscribed INTEGER NOT NULL DEFAULT 1,
    is_podcast INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, channel_id)
);

CREATE TABLE playlists (
    user_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    playlist_id  TEXT NOT NULL,
    title        TEXT NOT NULL DEFAULT '',
    refreshed_at TEXT NOT NULL,
    PRIMARY KEY (user_id, playlist_id)
);

CREATE TABLE sync_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    started_at      TEXT NOT NULL,
    finished_at     TEXT NOT NULL,
    result          TEXT NOT NULL CHECK (result IN ('ok', 'partial', 'failed')),
    reason          TEXT,
    counts_json     TEXT NOT NULL DEFAULT '{}',
    estimated_units INTEGER NOT NULL DEFAULT 0,
    error           TEXT
);
CREATE INDEX idx_sync_runs_user ON sync_runs (user_id, id);
