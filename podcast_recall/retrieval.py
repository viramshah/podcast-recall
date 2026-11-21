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

from podcast_recall import jobs, paths, vectors
from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.models import SearchHit, SearchResult

CANDIDATES = 30  # taken from each method before they are combined
MAX_CANDIDATES = 480  # the most taken when the per-episode cap leaves too few results
RRF_CONSTANT = 60
SEMANTIC_WEIGHT = 1.0  # how much the meaning ranking counts against the keyword ranking
INTRO_SECONDS = 180.0  # chunks starting before this are an episode's opening (teaser and host summary)
INTRO_WEIGHT = 1.0  # the factor applied to an opening chunk's score; 1.0 changes nothing
MIN_EPISODES_LENGTH_FACTOR = 4  # openings are only demoted in episodes at least this many times longer
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


def library_episode_ids(
    conn: sqlite3.Connection, user_id: str, video_ids: Sequence[str] | None = None
) -> list[int]:
    """Episodes with a `matched` result for a video in this user's library. With `video_ids`, that
    explicit list of videos is used instead of the library (for example the seed list)."""
    if video_ids is not None:
        return jobs.matched_episode_ids(conn, list(video_ids))
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
    video_ids: Sequence[str] | None = None,
) -> int:
    """Fill the temporary `_scope` table with the chunk IDs the user may see. Returns the count."""
    episodes = library_episode_ids(conn, user_id, video_ids)
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


def keyword_search(conn: sqlite3.Connection, expression: str, k: int = CANDIDATES) -> list[int]:
    rows = conn.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? "
        "AND rowid IN (SELECT chunk_id FROM _scope) ORDER BY rank LIMIT ?",
        (expression, k),
    )
    return [r[0] for r in rows]


def vector_search(
    conn: sqlite3.Connection, query_vector: Sequence[float], k: int = CANDIDATES
) -> list[tuple[int, float]]:
    """The nearest chunks inside the scope as (chunk id, cosine distance), nearest first. It always
    returns its nearest neighbours however far away they are; judging "too far" is U6's job."""
    rows = conn.execute(
        f"SELECT rowid, distance FROM {vectors.TABLE} WHERE embedding MATCH ? AND k = ? "
        "AND rowid IN (SELECT chunk_id FROM _scope) ORDER BY distance",
        (vectors.encode(query_vector), k),
    )
    return [(r[0], r[1]) for r in rows]


def fuse(
    keyword: Sequence[int], semantic: Sequence[int], semantic_weight: float = SEMANTIC_WEIGHT
) -> list[tuple[int, float]]:
    """Reciprocal rank fusion: each list adds weight / (60 + rank). Best first, ties by keyword
    rank. The keyword list has weight 1 and the meaning list `semantic_weight`."""
    scores: dict[int, float] = {}
    for ranking, weight in ((keyword, 1.0), (semantic, semantic_weight)):
        for rank, chunk_id in enumerate(ranking, 1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (RRF_CONSTANT + rank)
    position = {c: i for i, c in enumerate(keyword)}
    return sorted(scores.items(), key=lambda kv: (-kv[1], position.get(kv[0], 10**9), kv[0]))


def demote_intro(
    conn: sqlite3.Connection,
    ranked: Sequence[tuple[int, float]],
    seconds: float,
    weight: float,
) -> list[tuple[int, float]]:
    """Multiply the score of chunks from an episode's opening by `weight` and re-sort.

    An episode opens with a teaser and a host summary of everything to come. Those chunks read like
    a table of contents and match almost any question about the episode, so they crowd out the
    passage that really answers it. Only chunks that start before `seconds` are touched, and only
    in episodes much longer than that (a short episode is mostly "opening"). A weight of 1 changes
    nothing; 0 pushes openings to the bottom.
    """
    if weight == 1.0 or seconds <= 0 or not ranked:
        return list(ranked)
    marks = ",".join("?" * len(ranked))
    info = {
        r["chunk_id"]: (r["start_s"], r["length"])
        for r in conn.execute(
            "SELECT c.chunk_id, c.start_s, "
            "(SELECT MAX(end_s) FROM chunks WHERE episode_id = c.episode_id) AS length "
            f"FROM chunks c WHERE c.chunk_id IN ({marks})",
            [c for c, _ in ranked],
        )
    }
    order = {c: i for i, (c, _score) in enumerate(ranked)}
    adjusted = []
    for chunk_id, score in ranked:
        start, length = info.get(chunk_id, (None, None))
        if start is not None and start < seconds and (length or 0) >= MIN_EPISODES_LENGTH_FACTOR * seconds:
            score *= weight
        adjusted.append((chunk_id, score))
    return sorted(adjusted, key=lambda kv: (-kv[1], order[kv[0]]))


# ---------------------------------------------------------------------------- the entry point


def youtube_link(video_id: str, start_s: float) -> str:
    return f"https://youtu.be/{video_id}?t={int(start_s)}"


def _link_video(
    conn: sqlite3.Connection, user_id: str, episode_id: int, video_ids: Sequence[str] | None
) -> str | None:
    """A video of this episode that the user may open: from the explicit list, else the library."""
    if video_ids is not None:
        allowed = set(video_ids)
        rows = conn.execute(
            "SELECT video_id FROM episode_matches WHERE status = 'matched' AND episode_id = ? "
            "ORDER BY video_id",
            (episode_id,),
        )
        return next((r[0] for r in rows if r[0] in allowed), None)
    row = conn.execute(
        "SELECT m.video_id FROM episode_matches m JOIN library_items li "
        "ON li.video_id = m.video_id WHERE li.user_id = ? AND m.status = 'matched' "
        "AND m.episode_id = ? ORDER BY m.video_id LIMIT 1",
        (user_id, episode_id),
    ).fetchone()
    return row[0] if row else None


def _build_hits(
    conn: sqlite3.Connection,
    ranked: Sequence[tuple[int, float]],
    keyword: Sequence[int],
    semantic: Sequence[tuple[int, float]],
    *,
    user_id: str,
    video_ids: Sequence[str] | None,
    limit: int,
    per_episode: int,
) -> list[SearchHit]:
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
            video_for[episode_id] = _link_video(conn, user_id, episode_id, video_ids)
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
    return hits


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
    video_ids: Sequence[str] | None = None,
    limit: int = DEFAULT_LIMIT,
    per_episode: int = DEFAULT_PER_EPISODE,
    use_vectors: bool = True,
    semantic_weight: float | None = None,
    intro_weight: float | None = None,
    intro_seconds: float | None = None,
) -> SearchResult:
    """Search the user's library, or, with `video_ids`, exactly those videos' episodes instead."""
    if not 1 <= limit <= MAX_LIMIT:
        raise ConfigError(f"limit must be between 1 and {MAX_LIMIT}.")
    if per_episode < 1:
        raise ConfigError("per_episode must be at least 1.")
    weight = SEMANTIC_WEIGHT if semantic_weight is None else semantic_weight
    if weight < 0:
        raise ConfigError("semantic_weight cannot be negative.")
    intro_w = paths.intro_weight() if intro_weight is None else intro_weight
    intro_s = INTRO_SECONDS if intro_seconds is None else intro_seconds
    if intro_w < 0 or intro_s < 0:
        raise ConfigError("intro_weight and intro_seconds cannot be negative.")
    phrases, words = parse_query(query)
    expression = fts_expression(phrases, words)
    if expression is None:
        raise ConfigError("The search text has no words to look for.")
    warnings: list[str] = []
    scope_size = build_scope(
        conn, user_id, show=show, since=since, until=until, episode_ids=episode_ids,
        video_ids=video_ids,
    )
    if scope_size == 0:
        return SearchResult([], False, warnings)

    query_vector: list[float] | None = None
    if use_vectors:
        if not vectors.load(conn) or not vectors.table_exists(conn):
            warnings.append("Meaning search is not available yet (run `index build`). Using keywords only.")
        else:
            try:
                query_vector = embedder.embed_query(embedding_text(query))
            except (ApiError, ConfigError) as exc:
                warnings.append(f"Meaning search is unavailable ({exc}). Using keywords only.")

    # Take a few candidates from each method. If the per-episode cap then leaves too few results
    # (one episode filling the lists), take more, up to a fixed ceiling.
    k = CANDIDATES
    while True:
        keyword = keyword_search(conn, expression, k)
        semantic = vector_search(conn, query_vector, k) if query_vector is not None else []
        hits = _build_hits(
            conn, demote_intro(conn, fuse(keyword, [c for c, _ in semantic], weight), intro_s, intro_w),
            keyword, semantic,
            user_id=user_id, video_ids=video_ids, limit=limit, per_episode=per_episode,
        )
        exhausted = len(keyword) < k and (query_vector is None or len(semantic) < k)
        if len(hits) >= limit or exhausted or k >= MAX_CANDIDATES:
            break
        k = min(k * 2, MAX_CANDIDATES)
    return SearchResult(hits, query_vector is not None, warnings)


def get_chunk(conn: sqlite3.Connection, chunk_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
