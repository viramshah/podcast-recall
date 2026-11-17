"""The sync algorithm. See specs/features/u1-youtube-connector/requirements.md ("Sync order").

Order: subscriptions, playlists, your channel (Liked videos), uploads playlists of marked
channels, then the video IDs of every source, then video details, then apply additions and
removals source by source.

Safety rules:
- Items are removed from a playlist or Liked source only when that source's complete listing
  succeeded. A failed listing removes nothing.
- Channel sources only ever gain items. They lose them when the channel is unmarked or
  unsubscribed.
- A video leaves the library only when no source contains it (one library item per source).
- Deleted and private videos are detected because `videos.list` returns nothing for them.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from podcast_recall import store
from podcast_recall.errors import ApiError, NotSignedIn, QuotaExceeded
from podcast_recall.models import SourceResult, SyncResult
from podcast_recall.youtube_client import BATCH_SIZE, YouTubeClient

CHANNEL_UPLOAD_WINDOW = 50


def _chunks(items: Sequence, size: int):
    for start in range(0, len(items), size):
        yield list(items[start:start + size])


def run_sync(
    conn,
    client: YouTubeClient,
    user_id: str,
    on_progress: Callable[[dict], None] | None = None,
    *,
    now: Callable[[], str] = store.utc_now,
    refresh_days: int = 30,
) -> SyncResult:
    started = now()
    calls_before = dict(client.calls)
    results: dict[str, SourceResult] = {}
    errors: list[str] = []
    state: dict = {"stop": None, "last": None, "ok": False}

    def sr(source: str) -> SourceResult:
        if source not in results:
            results[source] = SourceResult(source=source, label=source)
        return results[source]

    def emit(event: dict) -> None:
        if on_progress:
            on_progress(event)

    def api(label: str, fn: Callable):
        """Run one API step. QuotaExceeded stops all further API work; ApiError only fails this
        step. NotSignedIn propagates."""
        if state["stop"]:
            return False, None
        try:
            value = fn()
            state["ok"] = True
            return True, value
        except QuotaExceeded as exc:
            state["stop"] = "YouTube quota exceeded"
            state["last"] = exc
            errors.append(f"{label}: {exc}")
        except ApiError as exc:
            state["last"] = exc
            errors.append(f"{label}: {exc}")
        return False, None

    def finish(result: str, reason: str | None, error: str | None) -> tuple[dict, int, int | None]:
        delta = {k: v - calls_before.get(k, 0) for k, v in client.calls.items()}
        delta = {k: v for k, v in delta.items() if v}
        units = sum(delta.values())
        for res in results.values():
            res.label = store.source_label(conn, user_id, res.source)
        counts = {
            "sources": [vars(r) for r in results.values()],
            "calls": delta,
            "videos_fetched": fetched,
        }
        run_id = store.record_sync_run(
            conn, user_id, started, now(), result, reason, counts, units, error
        )
        return delta, units, run_id

    fetched = 0
    try:
        # 1. Subscriptions: only a COMPLETE listing may change `subscribed` flags.
        ok, subs = api("subscriptions", client.list_subscriptions)
        if ok:
            store.apply_subscriptions(conn, user_id, subs, now())

        # 2. Playlists you own (titles refreshed; vanished playlists lose their items).
        ok, playlists = api("playlists", client.list_playlists)
        if ok:
            for source, count in store.apply_playlists(conn, user_id, playlists, now()).items():
                sr(source).removed += count

        # 3. Your own channel gives the Liked videos playlist.
        ok, me = api("your channel", client.my_channel)
        likes_id = me.likes_playlist_id if ok else None

        # Uploads playlist IDs for channels marked as podcast (cached on the channel row).
        marked = store.effective_podcast_channels(conn, user_id)
        missing = [c.channel_id for c in marked if not c.uploads_playlist_id]
        for chunk in _chunks(missing, BATCH_SIZE):
            ok, infos = api("channel details", lambda c=chunk: client.get_channels(c))
            if ok:
                store.save_channel_infos(conn, infos, now())
        marked = store.effective_podcast_channels(conn, user_id)

        # Items of channels that are no longer marked or subscribed go away.
        for source, count in store.remove_inactive_channel_items(conn, user_id).items():
            sr(source).removed += count

        # 4. List the video IDs of every source.
        plan: list[tuple[str, str, Callable[[], list[str]]]] = []
        for p in store.list_playlists(conn, user_id):
            plan.append((f"playlist:{p.playlist_id}", "playlist",
                         lambda pid=p.playlist_id: client.list_playlist_video_ids(pid)))
        if likes_id:
            plan.append(("liked", "liked", lambda: client.list_playlist_video_ids(likes_id)))
        for c in marked:
            if c.uploads_playlist_id:
                plan.append((f"channel:{c.channel_id}", "channel",
                             lambda u=c.uploads_playlist_id: client.list_playlist_video_ids(
                                 u, max_items=CHANNEL_UPLOAD_WINDOW)))
        listings: dict[str, tuple[str, list[str]]] = {}
        for source, kind, fetch in plan:
            res = sr(source)
            ok, ids = api(f"listing {source}", fetch)
            if ok:
                listings[source] = (kind, list(dict.fromkeys(ids)))
            else:
                res.complete = False
                res.error = state["stop"] or (errors[-1] if errors else "listing failed")
                emit({"stage": "source", "source": source, "complete": False, "error": res.error})

        # 5. Details for IDs that are new or older than the refresh age.
        all_ids = list(dict.fromkeys(i for _kind, ids in listings.values() for i in ids))
        need = store.videos_needing_fetch(conn, all_ids, store.cutoff(now(), refresh_days))
        for chunk in _chunks(need, BATCH_SIZE):
            ok, infos = api("video details", lambda c=chunk: client.get_videos(c))
            if ok:
                store.save_videos(conn, chunk, infos, now())
                fetched += len(infos)

        # 6. Apply additions and removals, one transaction per source.
        status_map = store.video_status_map(conn, all_ids)
        for source, (kind, ids) in listings.items():
            res = sr(source)
            stored = store.library_video_ids(conn, user_id, source)
            add = [i for i in ids if i not in stored and status_map.get(i) == "ok"]
            remove = (stored - set(ids)) if kind != "channel" else set()
            store.apply_source(conn, user_id, source, add, remove, now())
            res.found = len(ids)
            res.added = len(add)
            res.removed += len(remove)
            res.skipped_unavailable = sum(1 for i in ids if status_map.get(i) == "unavailable")
            res.deferred = sum(1 for i in ids if i not in status_map)
            emit({"stage": "source", "source": source, "complete": True, "found": res.found,
                  "added": res.added, "removed": res.removed,
                  "skipped_unavailable": res.skipped_unavailable})
    except NotSignedIn as exc:
        finish("partial" if state["ok"] else "failed", "sign-in expired or revoked", str(exc))
        raise

    deferred = sum(r.deferred for r in results.values())
    problems = list(dict.fromkeys(errors))
    if state["stop"]:
        problems.insert(0, state["stop"])
    if deferred:
        problems.append(f"{deferred} videos could not be fetched yet and will be retried next sync")
    if problems and not state["ok"]:
        reason = "; ".join(problems)
        finish("failed", reason, reason)
        raise state["last"] or ApiError(reason)
    status = "partial" if problems else "ok"
    reason = "; ".join(problems) if problems else None
    delta, units, run_id = finish(status, reason, None)
    return SyncResult(
        user_id=user_id,
        status=status,
        reason=reason,
        sources=list(results.values()),
        calls=delta,
        estimated_units=units,
        videos_fetched=fetched,
        warnings=problems,
        started_at=started,
        finished_at=now(),
        run_id=run_id,
    )
