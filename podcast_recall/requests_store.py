"""Storing what was asked, the feedback given, and the findings saved (migration 005).

Everything belongs to a user. The question text is kept here, in the private database, and never
in log files (decision D19).
"""

from __future__ import annotations

import json
import sqlite3

from podcast_recall.answers import Answer, answer_to_dict
from podcast_recall.errors import ConfigError


def log_request(
    conn: sqlite3.Connection,
    user_id: str,
    question: str,
    answer: Answer,
    dropped: list,
    chunk_ids: list[int],
    model: str,
    latency_ms: int,
    now: str,
) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO answer_requests (user_id, asked_at, question, status, model, latency_ms, "
            "chunk_ids_json, claims_kept, claims_dropped, drop_reasons_json, answer_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id, now, question, answer.status, model, latency_ms, json.dumps(chunk_ids),
                len(answer.claims), len(dropped), json.dumps([d.reason for d in dropped]),
                json.dumps(answer_to_dict(answer)),
            ),
        )
    return int(cursor.lastrowid)


def get_request(conn: sqlite3.Connection, request_id: int, user_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM answer_requests WHERE request_id = ? AND user_id = ?", (request_id, user_id)
    ).fetchone()
    if row is None:
        raise ConfigError(f"There is no request {request_id} for this user.")
    return row


def add_feedback(
    conn: sqlite3.Connection, request_id: int, user_id: str, thumbs: int, note: str, now: str
) -> int:
    if thumbs not in (-1, 1):
        raise ConfigError("thumbs must be 1 (up) or -1 (down).")
    get_request(conn, request_id, user_id)
    with conn:
        cursor = conn.execute(
            "INSERT INTO feedback (request_id, thumbs, note, created_at) VALUES (?, ?, ?, ?)",
            (request_id, thumbs, note.strip()[:500], now),
        )
    return int(cursor.lastrowid)


def add_finding(conn: sqlite3.Connection, request_id: int, user_id: str, note: str, now: str) -> int:
    row = get_request(conn, request_id, user_id)
    if row["status"] == "not_found":
        raise ConfigError("There is nothing to save: that question was not found in your podcasts.")
    with conn:
        cursor = conn.execute(
            "INSERT INTO findings (user_id, request_id, question, answer_json, note, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, request_id, row["question"], row["answer_json"], note.strip()[:1000], now),
        )
    return int(cursor.lastrowid)


def list_findings(conn: sqlite3.Connection, user_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM findings WHERE user_id = ? ORDER BY saved_at DESC, finding_id DESC", (user_id,)
    ).fetchall()


def get_finding(conn: sqlite3.Connection, finding_id: int, user_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM findings WHERE finding_id = ? AND user_id = ?", (finding_id, user_id)
    ).fetchone()
    if row is None:
        raise ConfigError(f"There is no finding {finding_id} for this user.")
    return row


def delete_finding(conn: sqlite3.Connection, finding_id: int, user_id: str) -> None:
    get_finding(conn, finding_id, user_id)
    with conn:
        conn.execute("DELETE FROM findings WHERE finding_id = ? AND user_id = ?", (finding_id, user_id))


def update_finding_note(conn: sqlite3.Connection, finding_id: int, user_id: str, note: str) -> None:
    get_finding(conn, finding_id, user_id)
    with conn:
        conn.execute(
            "UPDATE findings SET note = ? WHERE finding_id = ? AND user_id = ?",
            (note.strip()[:1000], finding_id, user_id),
        )
