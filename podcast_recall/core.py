"""The public functions the CLI and (later) the web chat call.

These return result objects and raise typed errors. They never print. Every function takes
optional keyword arguments (`conn`, `client`, `token_store`, `now`, ...) so tests can inject
fakes; when they are omitted the real database, Keychain and YouTube client are used.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from contextlib import contextmanager, nullcontext

from podcast_recall import (
    answering,
    auth,
    evalrun,
    golden_check,
    indexer,
    jobs,
    oracle,
    paths,
    podcastindex,
    requests_store,
    resolve,
    resolve_store,
    retrieval,
    store,
    sync,
    transcribe_flow,
    transcripts,
)
from podcast_recall.errors import (
    ApiError,
    ConfigError,
    NotSignedIn,
    QuotaExceeded,
    SyncAlreadyRunning,
)
from podcast_recall.lock import SyncLock
from podcast_recall.models import (
    ChannelNeedingFeed,
    ChannelRow,
    FeedInfo,
    FetchResult,
    PurgeResult,
    ResolvedVideo,
    ResolveResult,
    RevokeResult,
    SignInResult,
    StatusResult,
    SyncResult,
)
from podcast_recall.youtube_client import BATCH_SIZE, GoogleYouTubeClient, YouTubeClient

OWNER = "owner"


# ---------------------------------------------------------------------------- helpers


def open_db():
    paths.ensure_data_home()
    return store.connect(paths.db_path(), paths.backup_dir())


class _Db:
    """Use the injected connection, or open (and close) the real one."""

    def __init__(self, conn) -> None:
        self._given = conn
        self.conn = conn

    def __enter__(self):
        if self.conn is None:
            self.conn = open_db()
        return self.conn

    def __exit__(self, *exc_info) -> None:
        if self._given is None and self.conn is not None:
            self.conn.close()


def _require_user(conn, user_id: str):
    auth.validate_user_id(user_id)
    row = store.get_user(conn, user_id)
    if row is None:
        raise NotSignedIn(
            f"No sign-in found for user '{user_id}'. Please sign in again: "
            f"podcast-recall auth --user {user_id}"
        )
    return row


def _client_for(user_id: str, token_store: auth.TokenStore | None) -> YouTubeClient:
    tokens = (token_store or auth.KeychainTokenStore()).get(user_id)
    if not tokens:
        raise NotSignedIn(
            f"No sign-in found for user '{user_id}'. Please sign in again: "
            f"podcast-recall auth --user {user_id}"
        )
    return GoogleYouTubeClient.from_credentials_json(tokens)


# ---------------------------------------------------------------------------- sign-in


def sign_in(
    user_id: str = OWNER,
    force: bool = False,
    *,
    conn=None,
    token_store: auth.TokenStore | None = None,
    run_flow: Callable[[], auth.FlowResult] | None = None,
    client_factory: Callable[[str], YouTubeClient] | None = None,
    now: Callable[[], str] = store.utc_now,
) -> SignInResult:
    """Sign in with Google, check the permission and the account, then save the token."""
    auth.validate_user_id(user_id)
    tokens = token_store or auth.KeychainTokenStore()
    with _Db(conn) as db:
        flow = (run_flow or auth.run_installed_flow)()
        auth.verify_flow_result(flow)
        client = (client_factory or GoogleYouTubeClient.from_credentials_json)(flow.credentials_json)
        me = client.my_channel()
        existing = store.get_user(db, user_id)
        cleared = False
        if existing is not None and existing["youtube_channel_id"] != me.channel_id:
            if not force:
                raise ConfigError(
                    f"User '{user_id}' is linked to the YouTube channel "
                    f"'{existing['youtube_channel_title']}', but this sign-in is for "
                    f"'{me.title}'. Use --force to replace it (this clears the saved library "
                    f"for '{user_id}'), or choose another name with --user."
                )
            store.clear_user_data(db, user_id)
            cleared = True
        replaced = tokens.get(user_id) is not None
        tokens.save(user_id, flow.credentials_json)
        store.upsert_user(db, user_id, me.channel_id, me.title, now())
    return SignInResult(user_id, me.channel_id, me.title, replaced, cleared)


# ---------------------------------------------------------------------------- sync and fetch


def sync_library(
    user_id: str = OWNER,
    on_progress: Callable[[dict], None] | None = None,
    *,
    conn=None,
    client: YouTubeClient | None = None,
    token_store: auth.TokenStore | None = None,
    now: Callable[[], str] = store.utc_now,
    refresh_days: int | None = None,
    use_lock: bool = True,
) -> SyncResult:
    """Sync playlists, Liked videos and marked channels. One sync at a time per user."""
    auth.validate_user_id(user_id)
    days = refresh_days if refresh_days is not None else paths.video_refresh_days()
    with _Db(conn) as db:
        _require_user(db, user_id)
        lock = SyncLock(paths.lock_path(user_id)) if use_lock else nullcontext()
        with lock:
            api = client or _client_for(user_id, token_store)
            return sync.run_sync(db, api, user_id, on_progress, now=now, refresh_days=days)


def fetch_videos(
    video_ids: Iterable[str],
    user_id: str = OWNER,
    on_progress: Callable[[dict], None] | None = None,
    *,
    conn=None,
    client: YouTubeClient | None = None,
    token_store: auth.TokenStore | None = None,
    now: Callable[[], str] = store.utc_now,
) -> FetchResult:
    """Fetch details for any video IDs into the shared `videos` table. Never touches a user's
    library. IDs YouTube does not return are stored as `unavailable`."""
    ids = list(dict.fromkeys(video_ids))
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        api = client or _client_for(user_id, token_store)
        before = dict(api.calls)
        fetched = 0
        unavailable: list[tuple[str, str]] = []
        done_chunks = 0
        reason = None
        last: Exception | None = None
        chunks = [ids[i:i + BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]
        for chunk in chunks:
            try:
                infos = api.get_videos(chunk)
            except (QuotaExceeded, ApiError) as exc:
                last, reason = exc, str(exc)
                break
            missing = store.save_videos(db, chunk, infos, now())
            fetched += len(infos)
            unavailable += [(i, store.UNAVAILABLE_REASON) for i in missing]
            done_chunks += 1
            if on_progress:
                on_progress({"stage": "fetch", "done": done_chunks, "total": len(chunks)})
        if last is not None and done_chunks == 0:
            raise last
        delta = {k: v - before.get(k, 0) for k, v in api.calls.items() if v - before.get(k, 0)}
        return FetchResult(
            requested=len(ids),
            fetched=fetched,
            unavailable=unavailable,
            calls=delta,
            estimated_units=sum(delta.values()),
            partial=last is not None,
            reason=reason,
        )


# ---------------------------------------------------------------------------- channels


def list_channels(
    user_id: str = OWNER,
    marked_only: bool = False,
    refresh: bool = False,
    *,
    conn=None,
    client: YouTubeClient | None = None,
    token_store: auth.TokenStore | None = None,
    now: Callable[[], str] = store.utc_now,
) -> list[ChannelRow]:
    """Subscribed channels (marked first). Fetches the subscription list from YouTube when none
    is stored yet, or when `refresh` is true."""
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        rows = store.channel_rows(db, user_id)
        if refresh or not rows:
            api = client or _client_for(user_id, token_store)
            store.apply_subscriptions(db, user_id, api.list_subscriptions(), now())
            rows = store.channel_rows(db, user_id)
        return [r for r in rows if r.is_podcast] if marked_only else rows


def set_podcast_channel(
    user_id: str, channel_id: str, is_podcast: bool, *, conn=None
) -> ChannelRow:
    """Mark or unmark a subscribed channel as a podcast. Takes effect at the next sync."""
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        row = store.get_user_channel(db, user_id, channel_id)
        if row is None or not row["subscribed"]:
            raise ConfigError(
                f"Channel {channel_id} is not in your subscriptions. Run "
                "`podcast-recall channels list --refresh` and use an ID from that list."
            )
        store.set_podcast_flag(db, user_id, channel_id, is_podcast)
        for channel in store.channel_rows(db, user_id):
            if channel.channel_id == channel_id:
                return channel
    raise ConfigError(f"Channel {channel_id} could not be found.")  # pragma: no cover


# ---------------------------------------------------------------------------- status, revoke, purge


def get_status(user_id: str = OWNER, *, conn=None) -> StatusResult:
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        user = _require_user(db, user_id)
        last = store.last_sync_run(db, user_id)
        unique, per_source, unavailable = store.library_counts(db, user_id)
        return StatusResult(
            user_id=user_id,
            channel_title=user["youtube_channel_title"],
            last_run=last,
            unique_videos=unique,
            per_source=per_source,
            unavailable_in_library=unavailable,
            last_run_units=last["estimated_units"] if last else None,
        )


def revoke(
    user_id: str = OWNER,
    *,
    conn=None,
    token_store: auth.TokenStore | None = None,
    http_post: Callable[[str, dict], int] | None = None,
) -> RevokeResult:
    """Delete the user's token and per-user rows, and tell Google to revoke the grant. Local
    deletion happens even if the Google call fails (offline)."""
    auth.validate_user_id(user_id)
    tokens = token_store or auth.KeychainTokenStore()
    with _Db(conn) as db:
        user = store.get_user(db, user_id)
        credentials = tokens.get(user_id)
        if user is None and credentials is None:
            raise NotSignedIn(f"No sign-in found for user '{user_id}'. Nothing to revoke.")
        warnings: list[str] = []
        google_ok = False
        if credentials:
            google_ok = (
                auth.revoke_at_google(credentials, http_post)
                if http_post
                else auth.revoke_at_google(credentials)
            )
            if not google_ok:
                warnings.append(
                    "Google could not be told to revoke access (offline, or already revoked). "
                    "Remove it yourself at https://myaccount.google.com/connections."
                )
        else:
            warnings.append("No saved sign-in was found, so there was nothing to revoke at Google.")
        store.delete_user(db, user_id)
        try:
            tokens.delete(user_id)
        except ConfigError as exc:
            warnings.append(f"{exc} Delete the 'podcast-recall' entry in Keychain Access yourself.")
    return RevokeResult(google_ok, warnings)


def purge_stale_videos(
    max_age_days: int | None = None, *, conn=None, now: Callable[[], str] = store.utc_now
):
    """Delete shared video rows not refreshed within `max_age_days` that no other table refers
    to. Rows that something still refers to are kept and counted."""
    days = max_age_days if max_age_days is not None else paths.video_refresh_days()
    if days < 1:
        raise ConfigError("The age limit must be at least 1 day.")
    with _Db(conn) as db:
        deleted, kept = store.purge(db, store.cutoff(now(), days))
    return PurgeResult(deleted, kept)


# ---------------------------------------------------------------------------- U2: episode resolver


def _pi_client(pi_client: podcastindex.PodcastIndexClient | None) -> podcastindex.PodcastIndexClient:
    return pi_client or podcastindex.PodcastIndexClient(podcastindex.load_credentials())


def resolvable_library_videos(user_id: str = OWNER, *, conn=None) -> list[str]:
    """Video IDs in the user's library that have details (not deleted or private)."""
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        return resolve_store.library_video_ids(db, user_id)


def find_feed_candidates(
    channel_id: str,
    limit: int = 5,
    *,
    conn=None,
    pi_client: podcastindex.PodcastIndexClient | None = None,
) -> list[FeedInfo]:
    """Podcast feeds that might belong to a YouTube channel, found by the channel's title."""
    with _Db(conn) as db:
        return resolve.find_feed_candidates(db, _pi_client(pi_client), channel_id, limit)


def set_channel_feed(
    channel_id: str,
    feed_ref: str,
    *,
    conn=None,
    pi_client: podcastindex.PodcastIndexClient | None = None,
    now: Callable[[], str] = store.utc_now,
) -> FeedInfo | None:
    """Record a channel's feed: `none`, a Podcast Index feed ID or a feed URL."""
    wants_none = feed_ref.strip().lower() == "none"
    with _Db(conn) as db:
        client = None if wants_none else _pi_client(pi_client)
        return resolve.set_channel_feed(db, client, channel_id, feed_ref, now())


def channels_needing_feed(video_ids, *, conn=None) -> list[ChannelNeedingFeed]:
    with _Db(conn) as db:
        return resolve.channels_needing_feed(db, list(video_ids))


def resolve_videos(
    video_ids,
    *,
    conn=None,
    pi_client: podcastindex.PodcastIndexClient | None = None,
    now: Callable[[], str] = store.utc_now,
    refresh: bool = True,
    full_refresh: bool = False,
) -> ResolveResult:
    """Match videos to feed episodes. See `resolve.resolve_videos` for the rules."""
    client = pi_client
    if client is None and refresh:
        client = podcastindex.PodcastIndexClient(podcastindex.load_credentials())
    with _Db(conn) as db:
        return resolve.resolve_videos(
            db, client, list(video_ids), now(), refresh=refresh, full_refresh=full_refresh
        )


def confirm_match(
    video_id: str, episode_id: int, *, conn=None, now: Callable[[], str] = store.utc_now
) -> ResolvedVideo:
    with _Db(conn) as db:
        return resolve.confirm_match(db, video_id, episode_id, now())


def reject_match(
    video_id: str, *, conn=None, now: Callable[[], str] = store.utc_now
) -> ResolvedVideo:
    with _Db(conn) as db:
        return resolve.reject_match(db, video_id, now())


def list_review_items(video_ids, *, conn=None) -> list[dict]:
    with _Db(conn) as db:
        return resolve.list_review_items(db, list(video_ids))


def write_seed_check(seed_file, out_path, *, conn=None) -> int:
    """Write the seed check CSV (one row per seed video) and return the number of rows."""
    with _Db(conn) as db:
        return resolve.write_seed_check(db, seed_file, out_path)


# ---------------------------------------------------------------------------- transcripts (U3)


@contextmanager
def _one_run_only(lock_path, what: str):
    """Hold a file lock for the whole run. A second run is refused with a message about `what`."""
    lock = SyncLock(lock_path)
    try:
        lock.__enter__()
    except SyncAlreadyRunning:
        raise SyncAlreadyRunning(
            f"Another {what} is already working. Wait for it to finish, then try again."
        ) from None
    try:
        yield
    finally:
        lock.__exit__(None, None, None)


def episode_ids_for_videos(video_ids, *, conn=None) -> list[int]:
    """Matched episodes for these videos (used to limit a run to the seed list or a library)."""
    with _Db(conn) as db:
        return jobs.matched_episode_ids(db, list(video_ids))


def run_transcribe(
    video_ids=None,
    *,
    limit: int | None = None,
    keep_audio: bool = False,
    on_progress=None,
    services: transcribe_flow.Services | None = None,
    conn=None,
    now: Callable[[], str] = store.utc_now,
):
    """Enqueue matched episodes and process the queue. `video_ids` limits the work to those
    videos' episodes. Only one run at a time (a file lock)."""
    with _one_run_only(paths.transcribe_lock_path(), "transcribe run"), _Db(conn) as db:
        only = None if video_ids is None else set(jobs.matched_episode_ids(db, list(video_ids)))
        return transcribe_flow.run_queue(
            db, services or transcribe_flow.Services(), now=now, limit=limit,
            only_episode_ids=only, keep_audio=keep_audio, on_progress=on_progress,
        )


def transcribe_status(video_ids=None, *, conn=None, now: Callable[[], str] = store.utc_now):
    with _Db(conn) as db:
        if video_ids is None:
            return transcribe_flow.build_status(db, now())
        ids = list(video_ids)
        return transcribe_flow.build_status(
            db, now(), set(jobs.matched_episode_ids(db, ids)), ids
        )


def retry_transcript(
    episode_id: int, force_whisper: bool = False, *, conn=None, now: Callable[[], str] = store.utc_now
) -> None:
    with _Db(conn) as db:
        jobs.retry(db, episode_id, force_whisper, now())


def accept_transcript(episode_id: int, *, conn=None) -> None:
    with _Db(conn) as db:
        transcripts.accept(db, episode_id)


def get_transcript(episode_id: int, *, conn=None):
    """The stored transcript (the contract with U4), or None."""
    with _Db(conn) as db:
        return transcripts.load_transcript(db, episode_id)


def show_transcript(episode_id: int, at: float | None = None, window: float = 30.0, *, conn=None):
    """A transcript plus, when `at` is given, the text around that second."""
    from podcast_recall.models import ShowResult

    transcript = get_transcript(episode_id, conn=conn)
    if transcript is None:
        raise ConfigError(f"Episode {episode_id} has no transcript yet.")
    segments = [] if at is None else transcripts.window_segments(transcript, at, window)
    return ShowResult(transcript, segments, len(transcript.segments))


# ---------------------------------------------------------------------------- index and search (U4)


def build_index(
    video_ids=None,
    *,
    rebuild: bool = False,
    on_progress=None,
    services: indexer.IndexServices | None = None,
    conn=None,
    now: Callable[[], str] = store.utc_now,
):
    """Index every `ok` transcript that is new or changed. `video_ids` limits the work to those
    videos' episodes. Only one run at a time (a file lock)."""
    with _one_run_only(paths.index_lock_path(), "index build"), _Db(conn) as db:
        only = None if video_ids is None else set(jobs.matched_episode_ids(db, list(video_ids)))
        return indexer.build_index(
            db, services or indexer.IndexServices(), now=now, only_episode_ids=only,
            rebuild=rebuild, on_progress=on_progress,
        )


def index_status(video_ids=None, *, conn=None):
    with _Db(conn) as db:
        only = None if video_ids is None else set(jobs.matched_episode_ids(db, list(video_ids)))
        return indexer.index_status(db, paths.embed_model(), only)


def search_episodes(
    query: str,
    user_id: str = OWNER,
    *,
    show: str | None = None,
    since: str | None = None,
    until: str | None = None,
    episode_ids=None,
    video_ids=None,
    limit: int = retrieval.DEFAULT_LIMIT,
    per_episode: int = retrieval.DEFAULT_PER_EPISODE,
    semantic_weight: float | None = None,
    services: indexer.IndexServices | None = None,
    conn=None,
):
    """The best chunks for a query, from this user's library only. With `video_ids` the search
    covers exactly those videos' episodes instead (used for the seed list and the probe set)."""
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        services = services or indexer.IndexServices()
        return retrieval.find(
            db, services.get_embedder(), query, user_id, show=show, since=since, until=until,
            episode_ids=episode_ids, video_ids=video_ids, limit=limit, per_episode=per_episode,
            use_vectors=services.use_vectors, semantic_weight=semantic_weight,
        )


def get_chunk(chunk_id: int, *, conn=None):
    with _Db(conn) as db:
        return retrieval.get_chunk(db, chunk_id)


# ---------------------------------------------------------------------------- evaluation (Week 2)


def run_eval(
    items,
    library_video_ids,
    *,
    answers: dict | None = None,
    use_oracle: bool = False,
    fabricate: str | None = None,
    split: str = "all",
    conn=None,
):
    """Grade answers with the deterministic rubric checks. The answers come from a file (already
    read), from the oracle (perfect answers built from the golden set), or from a fabricator."""
    with _Db(conn) as db:
        ctx = evalrun.build_context(db, library_video_ids)
        if answers is None:
            answers = oracle.answers_for(items, ctx, oracle=use_oracle, mode=fabricate)
        return evalrun.grade_all(items, answers, ctx, split)


def eval_retrieval(
    items,
    library_video_ids,
    *,
    split: str = "all",
    diagnose: bool = False,
    intro_weight: float | None = None,
    intro_seconds: float | None = None,
    services: indexer.IndexServices | None = None,
    conn=None,
):
    """Recall@5 and friends on the golden questions, searching the evaluation library. With
    `diagnose`, every miss is searched again, 50 deep with no per-episode cap."""
    chosen = [i for i in items if split == "all" or i.split == split]
    services = services or indexer.IndexServices()
    with _Db(conn) as db:
        ctx = evalrun.build_context(db, library_video_ids)
        embedder = services.get_embedder()

        def search(question: str):
            return retrieval.find(
                db, embedder, question, OWNER, video_ids=library_video_ids, limit=10,
                use_vectors=services.use_vectors, intro_weight=intro_weight, intro_seconds=intro_seconds,
            ).hits

        def deep_search(question: str):
            return retrieval.find(
                db, embedder, question, OWNER, video_ids=library_video_ids, limit=retrieval.MAX_LIMIT,
                per_episode=retrieval.MAX_LIMIT, use_vectors=services.use_vectors,
                intro_weight=intro_weight, intro_seconds=intro_seconds,
            ).hits

        return evalrun.retrieval_outcomes(chosen, ctx, search, deep_search if diagnose else None)


def eval_check_golden(items, library_video_ids, *, conn=None):
    with _Db(conn) as db:
        ctx = evalrun.build_context(db, library_video_ids)
        return golden_check.check_all(db, items, ctx)


def eval_show_item(item, library_video_ids, *, conn=None) -> str:
    with _Db(conn) as db:
        ctx = evalrun.build_context(db, library_video_ids)
        return golden_check.show_item(item, ctx)


# ---------------------------------------------------------------------------- answers (Week 3)


def ask(
    question: str,
    user_id: str = OWNER,
    *,
    show: str | None = None,
    since: str | None = None,
    until: str | None = None,
    video_ids=None,
    record: bool = True,
    services: answering.AnswerServices | None = None,
    conn=None,
    now: Callable[[], str] = store.utc_now,
):
    """Answer a question from this user's podcasts. Every citation in the answer has been verified
    (R1 and R2). With `record`, the request is stored so it can get feedback and be saved."""
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        result = answering.answer_question(
            db, services or answering.AnswerServices(), question, user_id, show=show, since=since,
            until=until, video_ids=video_ids,
        )
        if record:
            result.request_id = requests_store.log_request(
                db, user_id, question.strip(), result.answer, result.dropped, result.chunk_ids,
                result.model, result.latency_ms, now(),
            )
        return result


def record_feedback(
    request_id: int, thumbs: int, note: str = "", user_id: str = OWNER, *, conn=None,
    now: Callable[[], str] = store.utc_now,
) -> int:
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        return requests_store.add_feedback(db, request_id, user_id, thumbs, note, now())


def save_finding(
    request_id: int, note: str = "", user_id: str = OWNER, *, conn=None,
    now: Callable[[], str] = store.utc_now,
) -> int:
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        return requests_store.add_finding(db, request_id, user_id, note, now())


def list_findings(user_id: str = OWNER, *, conn=None):
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        return requests_store.list_findings(db, user_id)


def delete_finding(finding_id: int, user_id: str = OWNER, *, conn=None) -> None:
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        requests_store.delete_finding(db, finding_id, user_id)


def update_finding_note(finding_id: int, note: str, user_id: str = OWNER, *, conn=None) -> None:
    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        requests_store.update_finding_note(db, finding_id, user_id, note)


def finding_items(user_id: str = OWNER, *, since: str | None = None, show: str | None = None, conn=None):
    """The saved findings, newest first, ready to export (the answer parsed, feedback and removed
    claims joined in)."""
    from podcast_recall import exporter

    auth.validate_user_id(user_id)
    with _Db(conn) as db:
        _require_user(db, user_id)
        return exporter.load_items(db, user_id, since=since, show=show)


def export_findings(
    fmt: str, user_id: str = OWNER, *, since: str | None = None, show: str | None = None,
    out: str | None = None, force: bool = False, conn=None,
):
    """Write the findings to a file. Returns (path, number of findings)."""
    from pathlib import Path

    from podcast_recall import exporter

    items = finding_items(user_id, since=since, show=show, conn=conn)
    text = exporter.render(items, fmt)
    target = Path(out).expanduser() if out else paths.export_dir() / exporter.file_name(fmt, since, show)
    if out and target.is_dir():
        target = target / exporter.file_name(fmt, since, show)
    return exporter.write_export(target, text, force=force), len(items)


def export_findings_to_notes(user_id: str = OWNER, *, since=None, show=None, conn=None, runner=None):
    """Create or update the one Apple Notes note. Returns ("created" or "updated", number of findings)."""
    from podcast_recall import applenotes, exporter

    items = finding_items(user_id, since=since, show=show, conn=conn)
    body = exporter.render_notes_html(items)
    result = applenotes.write_note(body, runner) if runner else applenotes.write_note(body)
    return result, len(items)


def choose_items(items, split: str = "dev", limit: int | None = None, ids: Sequence[str] | None = None):
    """The golden questions a run covers: a split, optionally only some ids, optionally the first N."""
    chosen = [i for i in items if split == "all" or i.split == split]
    if ids:
        unknown = sorted(set(ids) - {i.id for i in items})
        if unknown:
            raise ConfigError("Unknown question id(s): " + ", ".join(unknown))
        wanted = set(ids)
        chosen = [i for i in items if i.id in wanted]  # an explicit id wins over the split
    if limit is not None:
        chosen = chosen[:limit]
    return chosen


def answer_golden(
    items,
    library_video_ids,
    *,
    split: str = "dev",
    limit: int | None = None,
    ids: Sequence[str] | None = None,
    services: answering.AnswerServices | None = None,
    on_progress=None,
    conn=None,
):
    """Ask the real answering system every golden question of a split, against the evaluation
    library. Nothing is stored in the request history. Returns (answers, results, latencies, grades)."""
    chosen = choose_items(items, split, limit, ids)
    services = services or answering.AnswerServices()
    answers_by_id: dict[str, dict] = {}
    results = []
    latencies: list[float] = []
    with _Db(conn) as db:
        ctx = evalrun.build_context(db, library_video_ids)
        for position, item in enumerate(chosen, 1):
            result = answering.answer_question(
                db, services, item.question, OWNER, video_ids=library_video_ids
            )
            results.append(result)
            latencies.append(result.latency_ms / 1000)
            from podcast_recall.answers import answer_to_dict

            answers_by_id[item.id] = {"id": item.id, **answer_to_dict(result.answer)}
            if on_progress:
                on_progress(position, len(chosen), item.id, result.answer.status, result.latency_ms / 1000)
        grades = evalrun.grade_all(chosen, answers_by_id, ctx, "all")
    return answers_by_id, results, latencies, grades


def trace_record(item_id: str, result) -> dict:
    """What one answered question leaves behind for diagnosis: the passages the model was shown,
    its raw reply and what the verifier removed. Private (it holds transcript text): git-ignored."""
    return {
        "id": item_id,
        "status": result.answer.status,
        "latency_ms": result.latency_ms,
        "model": result.model,
        "chunk_ids": list(result.chunk_ids),
        "raw_reply": result.raw_reply,
        "dropped": [{"claim": d.claim, "reason": d.reason} for d in result.dropped],
        "warnings": list(result.warnings),
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "units_total": result.units_total,
        "units_shown": result.units_shown,
        "premise_raw": result.premise_raw,
        "premise_ms": result.premise_ms,
        "check_model": result.check_model,
        "check_ms": result.check_ms,
        "check_raw": result.check_raw,
    }


def diagnose_run(items, library_video_ids, answers_by_id: dict, traces: dict, conn=None):
    """Grade the saved answers again and explain every failure. Returns (grades, diagnoses)."""
    from podcast_recall import diagnosis

    graded_items = [i for i in items if i.id in answers_by_id]
    with _Db(conn) as db:
        ctx = evalrun.build_context(db, library_video_ids)
        grades = evalrun.grade_all(graded_items, answers_by_id, ctx, "all")
        return grades, diagnosis.diagnose(db, graded_items, grades, traces, ctx)


def abstention_scan(items, library_video_ids, *, split: str = "dev", per_episode: int = 3, passages: int | None = None,
                    services: indexer.IndexServices | None = None, conn=None):
    """Search each golden question the way the answering path does; return the best meaning
    distance and the hit count per question. No answering model is used."""
    from podcast_recall import abstention

    chosen = choose_items(items, split)
    services = services or indexer.IndexServices()
    count = passages or paths.passages()
    best: dict[str, tuple[float | None, int]] = {}
    with _Db(conn) as db:
        embedder = services.get_embedder()
        for item in chosen:
            hits = retrieval.find(
                db, embedder, item.question, OWNER, video_ids=library_video_ids, limit=count,
                per_episode=per_episode, use_vectors=services.use_vectors,
            ).hits
            distances = [h.vector_distance for h in hits if h.vector_distance is not None]
            best[item.id] = (min(distances) if distances else None, len(hits))
    return abstention.scan_rows(chosen, best)
