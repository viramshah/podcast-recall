"""The vector half of the index, using the sqlite-vec extension.

The extension is optional: if it cannot be loaded, keyword search still works and the vector
half is skipped with a warning (decision D17, question 12). The vector table is created here,
not in a migration, because it needs the extension and a size that depends on the model.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

TABLE = "chunk_vectors"


def load(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec into this connection. Returns False if that is not possible."""
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)
        return True
    except (ImportError, AttributeError, sqlite3.OperationalError):
        return False


def encode(vector: Sequence[float]) -> bytes:
    import sqlite_vec

    return sqlite_vec.serialize_float32(list(vector))


def table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLE,)
    ).fetchone()
    return row is not None


def _meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM index_meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def ensure_table(conn: sqlite3.Connection, dimensions: int) -> bool:
    """Make sure the vector table exists with this size. Returns True if it had to be created
    again (a different size), in which case every stored vector is gone and every episode must be
    embedded again."""
    recreated = False
    existing = _meta(conn, "embed_dim")
    if table_exists(conn) and existing is not None and int(existing) != dimensions:
        conn.execute(f"DROP TABLE {TABLE}")
        recreated = True
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {TABLE} "
        f"USING vec0(embedding float[{int(dimensions)}] distance_metric=cosine)"
    )
    with conn:
        conn.execute(
            "INSERT INTO index_meta (key, value) VALUES ('embed_dim', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(int(dimensions)),),
        )
        if recreated:
            conn.execute("UPDATE index_state SET embedded = 0")
    return recreated


def row_count(conn: sqlite3.Connection) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] if table_exists(conn) else 0
