-- Week 3 schema: what was asked, how it was received, and what the user saved. Private data per
-- decision D10: every table belongs to a user and is removed when the user is revoked.
-- The question text lives here and never in log files (decision D19).

CREATE TABLE answer_requests (
    request_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    asked_at          TEXT NOT NULL,
    question          TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('answered', 'not_found', 'premise_corrected')),
    model             TEXT NOT NULL DEFAULT '',
    latency_ms        INTEGER NOT NULL DEFAULT 0,
    chunk_ids_json    TEXT NOT NULL DEFAULT '[]',
    claims_kept       INTEGER NOT NULL DEFAULT 0,
    claims_dropped    INTEGER NOT NULL DEFAULT 0,
    drop_reasons_json TEXT NOT NULL DEFAULT '[]',
    answer_json       TEXT NOT NULL
);
CREATE INDEX idx_answer_requests_user ON answer_requests (user_id, asked_at);

CREATE TABLE feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  INTEGER NOT NULL REFERENCES answer_requests(request_id) ON DELETE CASCADE,
    thumbs      INTEGER NOT NULL CHECK (thumbs IN (-1, 1)),
    note        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_feedback_request ON feedback (request_id);

-- A finding keeps its own copy of the question and answer, so it survives on its own.
CREATE TABLE findings (
    finding_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    request_id  INTEGER,
    question    TEXT NOT NULL,
    answer_json TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    saved_at    TEXT NOT NULL
);
CREATE INDEX idx_findings_user ON findings (user_id, saved_at);
