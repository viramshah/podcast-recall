"""Search the chunks: keyword (FTS5) and meaning (sqlite-vec), combined, limited to one user's
library (decisions D17, questions 10 to 20).

Scope comes first. The set of chunks a user may see is built from their library and the filters,
and both searches run only inside it, so a chunk from outside the library can never rank.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from podcast_recall import vectors
from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.models import SearchHit, SearchResult

CANDIDATES = 30  # taken from each method before they are combined
RRF_CONSTANT = 60
DEFAULT_LIMIT = 8
MAX_LIMIT = 50
DEFAULT_PER_EPISODE = 3
MAX_QUERY_CHARS = 1000

_WORD = re.compile(r"\w+(?:'\w+)?", re.UNICODE)
_QUOTED = re.compile(r'"([^"]+)"')
STOPWORDS = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have", "how", "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to", "was", "were", "what", "when", "where", "which", "who", "why", "will", "with", "you", "your"]
)


# ---------------------------------------------------------------------------- the query


def parse_query(text: str) -> tuple[list[list[str]], list[str]]:
    """Split a query into exact phrases (balanced double quotes) and plain words. Nothing is ever
    passed on as search syntax, so `AND`, `*`, brackets and stray quotes are just words."""
    text = text[:MAX_QUERY_CHARS]
    phrases = [_WORD.findall(m.lower()) for m in _QUOTED.findall(text)]
    phrases = [p for p in phrases if p]
    rest = _QUOTED.sub(" ", text).replace('"', " ")
    words = _WORD.findall(rest.lower())
    useful = [w for w in words if w not in STOPWORDS]
    return phrases, useful or words


def fts_expression(phrases: Sequence[Sequence[str]], words: Sequence[str]) -> str | None:
    terms = [f'"{" ".join(p)}"' for p in phrases] + [f'"{w}"' for w in words]
    return " OR ".join(terms) if terms else None


def embedding_text(text: str) -> str:
    return " ".join(_QUOTED.sub(r"\1", text).replace('"', " ").split())[:MAX_QUERY_CHARS]


# ---------------------------------------------------------------------------- scope and filters


def _date_epoch(value: str, *, end_of_day: bool) -> int:
    try:
        day = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        raise ConfigError(f"'{value}' is not a date. Use YYYY-MM-DD.") from None
    return int((day + timedelta(days=1)).timestamp()) - 1 if end_of_day else int(day.timestamp())


def library_episode_ids(conn: sqlite3.Connection, user_id: str) -> list[int]:
    """Episodes with a `matched` result for a video in this user's library."""
    rows = conn.execute(
        "SELECT DISTINCT m.episode_id FROM episode_matches m "
        "JOIN library_items li ON li.video_id = m.video_id "
        "WHERE li.user_id = ? AND m.status = 'matched' AND m.episode_id IS NOT NULL",
        (user_id,),
    )
    return [r[0] for r in rows]


def resolve_show(conn: sqlite3.Connection, text: str, episode_ids: Sequence[int]) -> int:
    """The feed whose title contains `text` (ignoring case), among the user's shows."""
    marks = ",".join("?" * len(episode_ids)) or "NULL"
    shows = conn.execute(
        "SELECT DISTINCT f.feed_id, f.title FROM feeds f JOIN episodes e ON e.feed_id = f.feed_id "
        f"WHERE e.episode_id IN ({marks}) ORDER BY f.title",
        list(episode_ids),
    ).fetchall()
    found = [s for s in shows if text.strip().lower() in s["title"].lower()]
    if len(found) == 1:
        return found[0]["feed_id"]
    names = ", ".join(s["title"] for s in (found or shows)) or "none yet"
    if not found:
        raise ConfigError(f"No show in your library matches '{text}'. Your shows: {names}")
    raise ConfigError(f"'{text}' matches more than one show: {names}. Use more of the name.")


def build_scope(
    conn: sqlite3.Connection,
    user_id: str,
    *,
    show: str | None,
    since: str | None,
    until: str | None,
    episode_ids: Sequence[int] | None,
) -> int:
    """Fill the temporary `_scope` table with the chunk IDs the user may see. Returns the count."""
    episodes = library_episode_ids(conn, user_id)
    if episode_ids is not None:
        wanted = set(episode_ids)
        episodes = [e for e in episodes if e in wanted]
    feed_id = resolve_show(conn, show, episodes) if show else None
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS _scope (chunk_id INTEGER PRIMARY KEY)")
    conn.execute("DELETE FROM _scope")
    if not episodes:
        return 0
    marks = ",".join("?" * len(episodes))
    sql = (
        "INSERT INTO _scope (chunk_id) SELECT c.chunk_id FROM chunks c "
        f"JOIN episodes e ON e.episode_id = c.episode_id WHERE c.episode_id IN ({marks})"
    )
    args: list = list(episodes)
    if feed_id is not None:
        sql += " AND e.feed_id = ?"
        args.append(feed_id)
    if since:
        sql += " AND e.published >= ?"
        args.append(_date_epoch(since, end_of_day=False))
    if until:
        sql += " AND e.published <= ?"
        args.append(_date_epoch(until, end_of_day=True))
    conn.execute(sql, args)
    return conn.execute("SELECT COUNT(*) FROM _scope").fetchone()[0]


# ---------------------------------------------------------------------------- the two searches


def keyword_search(conn: sqlite3.Connection, expression: str) -> list[int]:
    rows = conn.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? "
        "AND rowid IN (SELECT chunk_id FROM _scope) ORDER BY rank LIMIT ?",
        (expression, CANDIDATES),
    )
    return [r[0] for r in rows]


def vector_search(
    conn: sqlite3.Connection, query_vector: Sequence[float]
) -> list[tuple[int, float]]:
    """The nearest chunks inside the scope as (chunk id, cosine distance), nearest first. It always
    returns its nearest neighbours however far away they are; judging "too far" is U6's job."""
    rows = conn.execute(
        f"SELECT rowid, distance FROM {vectors.TABLE} WHERE embedding MATCH ? AND k = ? "
        "AND rowid IN (SELECT chunk_id FROM _scope) ORDER BY distance",
        (vectors.encode(query_vector), CANDIDATES),
    )
    return [(r[0], r[1]) for r in rows]


def fuse(keyword: Sequence[int], semantic: Sequence[int]) -> list[tuple[int, float]]:
    """Reciprocal rank fusion: each list adds 1 / (60 + rank). Best first, ties by keyword rank."""
    scores: dict[int, float] = {}
    for ranking in (keyword, semantic):
        for rank, chunk_id in enumerate(ranking, 1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_CONSTANT + rank)
    position = {c: i for i, c in enumerate(keyword)}
    return sorted(scores.items(), key=lambda kv: (-kv[1], position.get(kv[0], 10**9), kv[0]))


# ---------------------------------------------------------------------------- the entry point


def youtube_link(video_id: str, start_s: float) -> str:
    return f"https://youtu.be/{video_id}?t={int(start_s)}"


def find(
    conn: sqlite3.Connection,
    embedder,
    query: str,
    user_id: str,
    *,
    show: str | None = None,
    since: str | None = None,
    until: str | None = None,
    episode_ids: Sequence[int] | None = None,
    limit: int = DEFAULT_LIMIT,
    per_episode: int = DEFAULT_PER_EPISODE,
    use_vectors: bool = True,
) -> SearchResult:
    if not 1 <= limit <= MAX_LIMIT:
        raise ConfigError(f"limit must be between 1 and {MAX_LIMIT}.")
    if per_episode < 1:
        raise ConfigError("per_episode must be at least 1.")
    phrases, words = parse_query(query)
    expression = fts_expression(phrases, words)
    if expression is None:
        raise ConfigError("The search text has no words to look for.")
    warnings: list[str] = []
    scope_size = build_scope(
        conn, user_id, show=show, since=since, until=until, episode_ids=episode_ids
    )
    if scope_size == 0:
        return SearchResult([], False, warnings)

    keyword = keyword_search(conn, expression)

    semantic: list[tuple[int, float]] = []
    vectors_used = False
    if use_vectors:
        if not vectors.load(conn) or not vectors.table_exists(conn):
            warnings.append("Meaning search is not available yet (run `index build`). Using keywords only.")
        else:
            try:
                semantic = vector_search(conn, embedder.embed_query(embedding_text(query)))
                vectors_used = True
            except ApiError as exc:
                warnings.append(f"Meaning search is unavailable ({exc}). Using keywords only.")
            except ConfigError as exc:
                warnings.append(f"Meaning search is unavailable ({exc}). Using keywords only.")

    ranked = fuse(keyword, [c for c, _ in semantic])
    keyword_rank = {c: i for i, c in enumerate(keyword, 1)}
    vector_rank = {c: i for i, (c, _d) in enumerate(semantic, 1)}
    vector_distance = dict(semantic)

    hits: list[SearchHit] = []
    seen_per_episode: dict[int, int] = {}
    video_for: dict[int, str | None] = {}
    for chunk_id, score in ranked:
        row = conn.execute(
            "SELECT c.*, e.title AS episode_title, f.title AS show FROM chunks c "
            "JOIN episodes e ON e.episode_id = c.episode_id JOIN feeds f ON f.feed_id = e.feed_id "
            "WHERE c.chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if row is None:
            continue
        episode_id = row["episode_id"]
        if seen_per_episode.get(episode_id, 0) >= per_episode:
            continue
        seen_per_episode[episode_id] = seen_per_episode.get(episode_id, 0) + 1
        if episode_id not in video_for:
            link_row = conn.execute(
                "SELECT m.video_id FROM episode_matches m JOIN library_items li "
                "ON li.video_id = m.video_id WHERE li.user_id = ? AND m.status = 'matched' "
                "AND m.episode_id = ? ORDER BY m.video_id LIMIT 1",
                (user_id, episode_id),
            ).fetchone()
            video_for[episode_id] = link_row[0] if link_row else None
        video_id = video_for[episode_id]
        hits.append(
            SearchHit(
                chunk_id=chunk_id, episode_id=episode_id, show=row["show"],
                title=row["episode_title"], start_s=row["start_s"], end_s=row["end_s"],
                text=row["text"], speaker=row["speaker"],
                url=youtube_link(video_id, row["start_s"]) if video_id else None,
                keyword_rank=keyword_rank.get(chunk_id), vector_rank=vector_rank.get(chunk_id),
                vector_distance=vector_distance.get(chunk_id), score=score,
            )
        )
        if len(hits) >= limit:
            break
    return SearchResult(hits, vectors_used, warnings)


def get_chunk(conn: sqlite3.Connection, chunk_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
