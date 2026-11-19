"""Build and update the search index from `ok` transcripts.

Each episode is replaced in one database transaction, so a crash never leaves half an episode.
Embeddings are fetched before anything is written, so a failure (for example Ollama stopped)
leaves the previous chunks of that episode untouched.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable, Collection
from dataclasses import dataclass, field

from podcast_recall import chunker, embeddings, paths, transcripts, vectors
from podcast_recall.models import BuildResult, IndexStatus

NO_VECTORS_WARNING = (
    "The sqlite-vec extension could not be loaded, so only keyword search is available. "
    "Run `uv sync` to install it."
)


class Embedder:  # the interface the indexer and the search rely on
    model: str

    def embed_documents(self, texts):  # pragma: no cover - interface only
        raise NotImplementedError

    def embed_query(self, text):  # pragma: no cover - interface only
        raise NotImplementedError


@dataclass
class IndexServices:
    embedder: Embedder | None = None
    use_vectors: bool = True
    _default: Embedder | None = field(default=None, repr=False)

    def get_embedder(self) -> Embedder:
        if self.embedder is not None:
            return self.embedder
        if self._default is None:
            self._default = embeddings.OllamaEmbedder()
        return self._default


def file_hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ok_transcripts(conn: sqlite3.Connection, only: Collection[int] | None):
    rows = conn.execute(
        "SELECT t.episode_id, t.path, e.title FROM transcripts t "
        "JOIN episodes e ON e.episode_id = t.episode_id WHERE t.status = 'ok' ORDER BY t.episode_id"
    ).fetchall()
    return [r for r in rows if only is None or r["episode_id"] in only]


def _states(conn: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    return {r["episode_id"]: r for r in conn.execute("SELECT * FROM index_state")}


def episodes_to_index(
    conn: sqlite3.Connection,
    only: Collection[int] | None,
    *,
    rebuild: bool,
    embed_model: str | None,
    vectors_ok: bool,
) -> tuple[list[sqlite3.Row], int]:
    """The `ok` transcripts that need (re)indexing, and how many are already current."""
    states = _states(conn)
    work, current = [], 0
    for row in _ok_transcripts(conn, only):
        state = states.get(row["episode_id"])
        path = paths.data_home() / row["path"]
        stale = rebuild or state is None or not path.is_file()
        if not stale:
            stale = (
                state["chunking_version"] != chunker.current_version()
                or state["transcript_hash"] != file_hash(path)
                or (vectors_ok and (not state["embedded"] or state["embed_model"] != embed_model))
            )
        if stale:
            work.append(row)
        else:
            current += 1
    return work, current


def remove_episode(conn: sqlite3.Connection, episode_id: int, vectors_loaded: bool) -> None:
    ids = [r[0] for r in conn.execute("SELECT chunk_id FROM chunks WHERE episode_id = ?", (episode_id,))]
    with conn:
        if vectors_loaded and vectors.table_exists(conn):
            conn.executemany(f"DELETE FROM {vectors.TABLE} WHERE rowid = ?", [(i,) for i in ids])
        conn.execute("DELETE FROM chunks WHERE episode_id = ?", (episode_id,))
        conn.execute("DELETE FROM index_state WHERE episode_id = ?", (episode_id,))


def _stale_removals(conn: sqlite3.Connection, only: Collection[int] | None) -> list[int]:
    ok_ids = {r["episode_id"] for r in _ok_transcripts(conn, None)}
    return [e for e in _states(conn) if e not in ok_ids and (only is None or e in only)]


def index_episode(
    conn: sqlite3.Connection,
    episode_id: int,
    path_text: str,
    *,
    embedder: Embedder | None,
    vectors_loaded: bool,
    now: str,
) -> int:
    """Replace one episode's chunks (and vectors) in one transaction. Returns the chunk count."""
    path = paths.data_home() / path_text
    digest = file_hash(path)
    transcript = transcripts.load_transcript(conn, episode_id)
    drafts = chunker.chunk_segments(transcript.segments) if transcript else []
    vecs = None
    if embedder is not None and drafts:
        vecs = embedder.embed_documents([d.text for d in drafts])  # may raise; nothing written yet
        vectors.ensure_table(conn, len(vecs[0]))
    old_ids = [r[0] for r in conn.execute("SELECT chunk_id FROM chunks WHERE episode_id = ?", (episode_id,))]
    with conn:
        if vectors_loaded and vectors.table_exists(conn) and old_ids:
            conn.executemany(f"DELETE FROM {vectors.TABLE} WHERE rowid = ?", [(i,) for i in old_ids])
        conn.execute("DELETE FROM chunks WHERE episode_id = ?", (episode_id,))
        for position, draft in enumerate(drafts):
            cursor = conn.execute(
                "INSERT INTO chunks (episode_id, chunk_no, start_s, end_s, text, word_count, speaker) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (episode_id, draft.chunk_no, draft.start_s, draft.end_s, draft.text,
                 draft.word_count, draft.speaker),
            )
            if vecs is not None:
                conn.execute(
                    f"INSERT INTO {vectors.TABLE} (rowid, embedding) VALUES (?, ?)",
                    (cursor.lastrowid, vectors.encode(vecs[position])),
                )
        conn.execute(
            "INSERT INTO index_state (episode_id, transcript_hash, chunking_version, embed_model, "
            "embedded, chunk_count, indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(episode_id) DO UPDATE SET transcript_hash = excluded.transcript_hash, "
            "chunking_version = excluded.chunking_version, embed_model = excluded.embed_model, "
            "embedded = excluded.embedded, chunk_count = excluded.chunk_count, "
            "indexed_at = excluded.indexed_at",
            (episode_id, digest, chunker.current_version(),
             embedder.model if vecs is not None and embedder else None,
             int(vecs is not None), len(drafts), now),
        )
    return len(drafts)


def build_index(
    conn: sqlite3.Connection,
    services: IndexServices,
    *,
    now: Callable[[], str],
    only_episode_ids: Collection[int] | None = None,
    rebuild: bool = False,
    on_progress: Callable[[dict], None] | None = None,
) -> BuildResult:
    warnings: list[str] = []
    vectors_loaded = vectors.load(conn) if services.use_vectors else False
    if services.use_vectors and not vectors_loaded:
        warnings.append(NO_VECTORS_WARNING)
    embedder = services.get_embedder() if vectors_loaded else None
    model = embedder.model if embedder else None

    removed_ids = _stale_removals(conn, only_episode_ids)
    for episode_id in removed_ids:
        remove_episode(conn, episode_id, vectors_loaded)

    work, current = episodes_to_index(
        conn, only_episode_ids, rebuild=rebuild, embed_model=model, vectors_ok=vectors_loaded
    )
    chunk_total = 0
    for position, row in enumerate(work, 1):
        if on_progress:
            on_progress({"stage": "start", "position": position, "total": len(work),
                         "episode_id": row["episode_id"], "title": row["title"]})
        count = index_episode(
            conn, row["episode_id"], row["path"], embedder=embedder,
            vectors_loaded=vectors_loaded, now=now(),
        )
        chunk_total += count
        if on_progress:
            on_progress({"stage": "done", "episode_id": row["episode_id"],
                         "title": row["title"], "chunks": count})
    return BuildResult(len(work), chunk_total, current, len(removed_ids), vectors_loaded, warnings)


def index_status(
    conn: sqlite3.Connection, embed_model: str, only: Collection[int] | None = None
) -> IndexStatus:
    vectors_available = vectors.load(conn)
    work, _current = episodes_to_index(
        conn, only, rebuild=False, embed_model=embed_model, vectors_ok=vectors_available
    )
    states = [s for s in _states(conn).values() if only is None or s["episode_id"] in only]
    return IndexStatus(
        episodes_indexed=len(states),
        chunks=sum(s["chunk_count"] for s in states),
        waiting=len(work),
        without_vectors=sum(1 for s in states if not s["embedded"]),
        chunking_version=chunker.current_version(),
        embed_model=embed_model,
        vectors_available=vectors_available,
        vector_rows=vectors.row_count(conn) if vectors_available else 0,
    )
