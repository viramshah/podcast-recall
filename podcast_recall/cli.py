"""Command line: a thin wrapper over `core.py`.

Results go to standard output. Progress, warnings and errors go to standard error.
Exit codes: 0 success, 1 error, 2 partial, 3 sign-in needed.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from podcast_recall import core, ids, logging_setup, paths
from podcast_recall.errors import ApiError, ConfigError, NotSignedIn, PodcastRecallError
from podcast_recall.models import FeedInfo, FetchResult, ResolveResult, SyncResult

EXIT_OK, EXIT_ERROR, EXIT_PARTIAL, EXIT_SIGN_IN = 0, 1, 2, 3

PLAYLIST_NOTE = (
    "Limit: the YouTube API only returns playlists you own. Playlists that belong to other "
    "people are not included, even if you saved them."
)


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _confirm(question: str) -> bool:
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _progress(event: dict) -> None:
    if event.get("stage") == "source":
        if event.get("complete"):
            _err(
                f"  {event['source']}: found {event['found']}, added {event['added']}, "
                f"removed {event['removed']}"
            )
        else:
            _err(f"  {event['source']}: NOT COMPLETE ({event.get('error')})")
    elif event.get("stage") == "fetch":
        _err(f"  fetched batch {event['done']} of {event['total']}")


def format_sync(result: SyncResult) -> str:
    lines = [f"Sync for '{result.user_id}': {result.status.upper()}"]
    for r in result.sources:
        if r.complete:
            extra = f", skipped {r.skipped_unavailable} unavailable" if r.skipped_unavailable else ""
            extra += f", {r.deferred} to retry" if r.deferred else ""
            lines.append(
                f"  {r.label}: found {r.found}, added {r.added}, removed {r.removed}{extra}"
            )
        else:
            lines.append(f"  {r.label}: NOT COMPLETE, nothing removed ({r.error})")
    calls = ", ".join(f"{m}: {n}" for m, n in sorted(result.calls.items())) or "none"
    lines.append(f"API calls: {calls}")
    if "videos.list" not in result.calls:
        lines.append("videos.list: 0")
    lines.append(f"Estimated quota units: {result.estimated_units}")
    lines.append(f"Video details fetched: {result.videos_fetched}")
    if result.reason:
        lines.append(f"Reason: {result.reason}")
    return "\n".join(lines)


def format_fetch(result: FetchResult) -> str:
    lines = [
        (
            f"Requested {result.requested}, fetched {result.fetched}, "
            f"unavailable {len(result.unavailable)}"
        )
    ]
    for video_id, why in result.unavailable:
        lines.append(f"  unavailable: {video_id} ({why})")
    for text in result.unparsed:
        lines.append(f"  could not read: {text}")
    calls = ", ".join(f"{m}: {n}" for m, n in sorted(result.calls.items())) or "none"
    lines.append(f"API calls: {calls}; estimated quota units: {result.estimated_units}")
    if result.partial:
        lines.append(f"Stopped early: {result.reason}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------- commands


def cmd_auth(args) -> int:
    result = core.sign_in(args.user, force=args.force)
    print(f"Signed in as YouTube channel '{result.channel_title}' (user '{result.user_id}').")
    if result.token_replaced:
        print("The saved sign-in was replaced.")
    if result.library_cleared:
        print("The saved library for this user was cleared because the channel changed.")
    return EXIT_OK


def cmd_sync(args) -> int:
    result = core.sync_library(args.user, on_progress=_progress)
    print(format_sync(result))
    return EXIT_PARTIAL if result.partial else EXIT_OK


def cmd_status(args) -> int:
    s = core.get_status(args.user)
    print(f"User '{s.user_id}', YouTube channel: {s.channel_title}")
    if s.last_run:
        r = s.last_run
        print(f"Last sync: {r['finished_at']} ({r['result']}), {r['estimated_units']} quota units")
        if r.get("reason"):
            print(f"  reason: {r['reason']}")
    else:
        print("Last sync: never")
    print(f"Unique videos in library: {s.unique_videos}")
    for label, count in s.per_source:
        print(f"  {label}: {count}")
    skipped = 0
    if s.last_run:
        skipped = sum(x.get("skipped_unavailable", 0) for x in s.last_run["counts"].get("sources", []))
    print(f"Unavailable: {s.unavailable_in_library} in library, {skipped} skipped in last sync")
    return EXIT_OK


def cmd_revoke(args) -> int:
    if not args.yes and not _confirm(
        f"This deletes the saved sign-in and all library data for '{args.user}' and revokes "
        "access at Google. Continue?"
    ):
        print("Nothing changed.")
        return EXIT_OK
    result = core.revoke(args.user)
    print("Access revoked at Google." if result.google_revoked else "Local data deleted.")
    for warning in result.warnings:
        _err(f"Warning: {warning}")
    return EXIT_OK


def cmd_channels_list(args) -> int:
    rows = core.list_channels(args.user, marked_only=args.marked, refresh=args.refresh)
    if not rows:
        print("No channels to show.")
    for row in rows:
        print(f"{'[podcast]' if row.is_podcast else '         '}  {row.channel_id}  {row.title}")
    return EXIT_OK


def cmd_channels_mark(args) -> int:
    row = core.set_podcast_channel(args.user, args.channel_id, args.command == "mark")
    state = "marked as podcast" if row.is_podcast else "no longer marked"
    print(f"{row.title} ({row.channel_id}) {state}. This takes effect at the next sync.")
    return EXIT_OK


def cmd_fetch(args) -> int:
    video_ids, unparsed = ids.load_ids(args.inputs)
    if not video_ids:
        _err("No video IDs found in the input.")
        return EXIT_ERROR
    result = core.fetch_videos(video_ids, args.user, on_progress=_progress)
    result.unparsed = unparsed
    print(format_fetch(result))
    return EXIT_PARTIAL if (result.partial or result.unavailable or unparsed) else EXIT_OK


def cmd_purge(args) -> int:
    result = core.purge_stale_videos(args.days)
    print(f"Deleted {result.deleted} stale videos, kept {result.kept} that are still referenced.")
    return EXIT_OK


# ---------------------------------------------------------------------------- resolve

DEFAULT_SEED = "data/seed_episodes.csv"
SEED_CHECK_PATH = "data/seed_resolver_check.csv"


def _ask(question: str) -> str:
    try:
        return input(question).strip()
    except EOFError:
        return "s"  # no terminal: skip


def _target_ids(args) -> list[str]:
    """The seed file's videos with --seed, otherwise the signed-in user's library."""
    if args.seed is not None:
        found, _unparsed = ids.load_ids([args.seed])
        return found
    return core.resolvable_library_videos(args.user)


def _score_text(score, title, date, duration) -> str:
    def f(value) -> str:
        return "n/a" if value is None else f"{value:.2f}"

    return f"score {f(score)} (title {f(title)}, date {f(date)}, length {f(duration)})"


def format_feed(number: int, feed: FeedInfo) -> str:
    updated = datetime.fromtimestamp(feed.last_update).strftime("%Y-%m-%d") if feed.last_update else "?"
    return (
        f"  {number}. {feed.title} | by {feed.author or 'unknown'} | "
        f"{feed.episode_count if feed.episode_count is not None else '?'} episodes | "
        f"updated {updated} | {feed.language or '?'} | {feed.url}"
    )


def format_resolve(result: ResolveResult) -> str:
    c = result.counts
    lines = [
        (
            f"Resolved {len(result.videos)} videos: matched {c['matched']}, needs_review "
            f"{c['needs_review']}, unmatched {c['unmatched']}, no_feed {c['no_feed']}"
        )
    ]
    for v in result.videos:
        if v.status in ("needs_review", "unmatched"):
            target = f" -> {v.episode_title} (episode {v.episode_id})" if v.episode_id else ""
            lines.append(
                f"  {v.status}: {v.video_title}{target}: "
                f"{_score_text(v.score, v.title_score, v.date_score, v.duration_score)}; {v.reason}"
            )
    if result.waiting:
        lines.append("Channels waiting for a feed choice (run `resolve feeds`):")
        for ch in result.waiting:
            lines.append(f"  {ch.title} ({ch.channel_id}): {ch.video_count} video(s)")
    if result.unavailable:
        lines.append(f"Skipped {len(result.unavailable)} unavailable video(s).")
    if result.missing:
        lines.append(f"{len(result.missing)} video(s) are not in the database yet (run `fetch` first).")
    if result.kept_reviewed:
        lines.append(f"Kept {result.kept_reviewed} result(s) you already reviewed.")
    for feed_id, new, truncated in result.feeds_refreshed:
        lines.append(f"Feed {feed_id}: {new} new episode(s){' (list may be truncated)' if truncated else ''}")
    calls = ", ".join(f"{m}: {n}" for m, n in sorted(result.calls.items())) or "none"
    lines.append(f"Podcast Index calls: {calls}")
    for warning in result.warnings:
        lines.append(f"Warning: {warning}")
    return "\n".join(lines)


def cmd_resolve_feeds(args) -> int:
    waiting = core.channels_needing_feed(_target_ids(args))
    if not waiting:
        print("Every channel already has a feed choice.")
        return EXIT_OK
    skipped = 0
    for channel in waiting:
        print(f"\nChannel: {channel.title} ({channel.channel_id}), {channel.video_count} video(s)")
        for title in channel.sample_titles:
            print(f"  for example: {title}")
        candidates = core.find_feed_candidates(channel.channel_id)
        if not candidates:
            print("  No feeds were found under that name.")
        for number, feed in enumerate(candidates, 1):
            print(format_feed(number, feed))
        while True:
            answer = _ask("Pick a number, 'u' for a feed URL or ID, 'n' for no feed, 's' to skip: ").lower()
            if answer == "s":
                skipped += 1
                break
            if answer == "n":
                core.set_channel_feed(channel.channel_id, "none")
                print("  Saved: no feed for this channel.")
                break
            if answer == "u":
                ref = _ask("Feed URL or Podcast Index ID: ")
                if not ref:
                    continue
                try:
                    feed = core.set_channel_feed(channel.channel_id, ref)
                except (ConfigError, ApiError) as exc:
                    _err(f"  {exc}")
                    continue
                print(f"  Saved: {feed.title if feed else 'no feed'}")
                break
            if answer.isdigit() and 1 <= int(answer) <= len(candidates):
                feed = core.set_channel_feed(channel.channel_id, str(candidates[int(answer) - 1].feed_id))
                print(f"  Saved: {feed.title if feed else 'no feed'}")
                break
            print("  Please choose one of the options.")
    return EXIT_PARTIAL if skipped else EXIT_OK


def cmd_resolve_set_feed(args) -> int:
    feed = core.set_channel_feed(args.channel_id, args.feed)
    print(f"Saved: {feed.title}" if feed else "Saved: no feed for this channel.")
    return EXIT_OK


def cmd_resolve_run(args) -> int:
    video_ids = _target_ids(args)
    result = core.resolve_videos(
        video_ids, refresh=not args.no_refresh, full_refresh=args.full_refresh
    )
    print(format_resolve(result))
    if args.seed is not None:
        rows = core.write_seed_check(args.seed, SEED_CHECK_PATH)
        print(f"Wrote {SEED_CHECK_PATH} ({rows} rows)")
    attention = result.partial or result.counts["needs_review"] or result.waiting or result.missing
    return EXIT_PARTIAL if attention else EXIT_OK


def cmd_resolve_review(args) -> int:
    video_ids = _target_ids(args)
    items = core.list_review_items(video_ids)
    waiting = core.channels_needing_feed(video_ids)
    if not items and not waiting:
        print("Nothing to review.")
        return EXIT_OK
    for item in items:
        print(f"{item['status']}: {item['video_title']} ({item['video_id']})")
        print(f"  {_score_text(item['score'], item['title_score'], item['date_score'], item['duration_score'])}; "
              f"{item['reason']}")
        for rank, cand in enumerate(item["candidates"], 1):
            print(f"  {rank}. episode {cand['episode_id']}: {cand['title']} "
                  f"(score {cand['combined']:.2f})")
    for ch in waiting:
        print(f"Waiting for a feed choice: {ch.title} ({ch.channel_id}), {ch.video_count} video(s)")
    return EXIT_OK


def cmd_resolve_confirm(args) -> int:
    v = core.confirm_match(args.video_id, args.episode_id)
    print(f"Confirmed: {v.video_title} -> {v.episode_title}")
    return EXIT_OK


def cmd_resolve_reject(args) -> int:
    v = core.reject_match(args.video_id)
    print(f"Rejected: {v.video_title} has no matching episode.")
    return EXIT_OK


# ---------------------------------------------------------------------------- parser


# ---------------------------------------------------------------------------- transcribe


def _mmss(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"


def _parse_at(text: str) -> float:
    parts = [float(p) for p in text.split(":")]
    if not 1 <= len(parts) <= 3:
        raise ConfigError("Use --at as seconds, mm:ss or h:mm:ss.")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def _transcribe_progress(event: dict) -> None:
    stage = event["stage"]
    if stage == "start":
        _err(f"[{event['position']}/{event['total']}] {event['title']} ...")
    elif stage == "done":
        extra = f" ({event['fallback_reason']})" if event.get("fallback_reason") else ""
        flags = f" flags: {', '.join(event['flags'])}" if event["flags"] else ""
        _err(f"    {event['source']}, {event['status']}{flags}{extra}")
    elif stage == "failed":
        _err(f"    failed ({event['state']}): {event['error']}")


def cmd_transcribe_run(args) -> int:
    video_ids = _target_ids(args) if args.seed is not None else None
    result = core.run_transcribe(
        video_ids, limit=args.limit, keep_audio=args.keep_audio, on_progress=_transcribe_progress
    )
    publisher_n = sum(1 for o in result.outcomes if o.source == "publisher")
    review = [o for o in result.outcomes if o.status == "needs_review"]
    print(
        f"Transcribed {len(result.outcomes)} episode(s): {publisher_n} from the publisher, "
        f"{len(result.outcomes) - publisher_n} with Whisper. "
        f"New jobs: {result.enqueued}. Recovered after a crash: {result.recovered}."
    )
    for o in review:
        print(f"  needs review: {o.episode_id} {o.title} ({', '.join(o.flags)})")
    for episode_id, title, error in result.failures:
        print(f"  failed: {episode_id} {title}: {error}")
    if result.waiting:
        print(f"{result.waiting} job(s) are waiting to retry. Run this again in a few minutes.")
    return EXIT_PARTIAL if (review or result.failures or result.waiting) else EXIT_OK


def cmd_transcribe_status(args) -> int:
    video_ids = _target_ids(args) if args.seed is not None else None
    s = core.transcribe_status(video_ids)
    print(f"Matched episodes: {s.matched_episodes}")
    print(f"Transcripts ready: {s.transcripts_ok}")
    print(f"Queued: {s.queued}, waiting to retry: {s.waiting}, running: {s.running}")
    print(f"Videos not indexable (no match yet): {s.not_indexable_videos}")
    print(f"Disk: audio {s.audio_bytes // 1_000_000} MB, transcripts {s.transcript_bytes // 1_000_000} MB")
    for episode_id, title, flags in s.needs_review:
        print(f"  needs review: {episode_id} {title} ({', '.join(flags)})")
    for episode_id, title, error in s.failed:
        print(f"  failed: {episode_id} {title}: {error}")
    for episode_id in s.missing_files:
        print(f"  missing transcript file: {episode_id}")
    return EXIT_PARTIAL if (s.needs_review or s.failed or s.missing_files) else EXIT_OK


def cmd_transcribe_retry(args) -> int:
    core.retry_transcript(args.episode_id, args.whisper)
    print(f"Episode {args.episode_id} is queued again. Run: podcast-recall transcribe run")
    return EXIT_OK


def cmd_transcribe_accept(args) -> int:
    core.accept_transcript(args.episode_id)
    print(f"Episode {args.episode_id} marked as reviewed (ok).")
    return EXIT_OK


def cmd_transcribe_show(args) -> int:
    at = _parse_at(args.at) if args.at else None
    shown = core.show_transcript(args.episode_id, at, args.window)
    t = shown.transcript
    print(
        f"Episode {t.episode_id}: {t.source} transcript, {t.timing_detail} timing, "
        f"model {t.model}, language {t.language}, status {t.status}"
        + (f", flags: {', '.join(t.flags)}" if t.flags else "")
    )
    if t.fallback_reason:
        print(f"Why not the publisher's: {t.fallback_reason}")
    print(f"{shown.total_segments} segments.")
    for start, _end, text in shown.text_before_and_after:
        print(f"[{_mmss(start)}] {text}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="podcast-recall",
        description="Sync your YouTube library for Podcast Recall. " + PLAYLIST_NOTE,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, func, help_text: str, user: bool = True) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(func=func)
        if user:
            sp.add_argument("--user", default=core.OWNER, help="local user name (default: owner)")
        return sp

    p = add("auth", cmd_auth, "Sign in with Google (read-only YouTube access).")
    p.add_argument("--force", action="store_true",
                   help="replace the account linked to this user (clears its saved library)")
    add("sync", cmd_sync, "Sync playlists, Liked videos and marked podcast channels. " + PLAYLIST_NOTE)
    add("status", cmd_status, "Show the signed-in channel, last sync and library counts.")
    p = add("revoke", cmd_revoke, "Delete the sign-in and saved data, and revoke access at Google.")
    p.add_argument("--yes", action="store_true", help="do not ask for confirmation")

    channels = sub.add_parser("channels", help="List subscribed channels and mark podcasts.")
    csub = channels.add_subparsers(dest="command", required=True)

    def cadd(name: str, func, help_text: str) -> argparse.ArgumentParser:
        sp = csub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(func=func)
        sp.add_argument("--user", default=core.OWNER, help="local user name (default: owner)")
        return sp

    p = cadd("list", cmd_channels_list, "List subscribed channels, marked ones first.")
    p.add_argument("--marked", action="store_true", help="only channels marked as podcast")
    p.add_argument("--refresh", action="store_true", help="fetch the subscription list again")
    for name in ("mark", "unmark"):
        p = cadd(name, cmd_channels_mark, f"{name.capitalize()} a subscribed channel as a podcast.")
        p.add_argument("channel_id", help="channel ID from `channels list`")

    p = add("fetch", cmd_fetch, "Fetch video details for IDs, URLs, a text file or a CSV "
                                "with a youtube_url column. Does not change your library.")
    p.add_argument("inputs", nargs="+", help="video IDs, URLs, or files")

    p = add("purge", cmd_purge, "Delete stale video rows that nothing refers to.", user=False)
    p.add_argument("--days", type=int, default=None,
                   help="age limit in days (default: PODCAST_RECALL_VIDEO_REFRESH_DAYS or 30)")
    resolve = sub.add_parser("resolve", help="Match YouTube videos to podcast episodes.")
    rsub = resolve.add_subparsers(dest="command", required=True)

    def radd(name: str, func, help_text: str, *, seed: bool = True, user: bool = True):
        sp = rsub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(func=func)
        if user:
            sp.add_argument("--user", default=core.OWNER, help="local user name (default: owner)")
        if seed:
            sp.add_argument("--seed", nargs="?", const=DEFAULT_SEED, default=None, metavar="FILE",
                            help=f"work on the seed file's videos (default file: {DEFAULT_SEED})")
        return sp

    radd("feeds", cmd_resolve_feeds, "Choose a podcast feed for each channel (asks questions).")
    p = radd("set-feed", cmd_resolve_set_feed, "Set a channel's feed without questions.",
             seed=False, user=False)
    p.add_argument("channel_id")
    p.add_argument("feed", help="a feed URL, a Podcast Index feed ID, or 'none'")
    p = radd("run", cmd_resolve_run, "Match videos to episodes and print a summary.")
    p.add_argument("--no-refresh", action="store_true", help="use the episodes already stored")
    p.add_argument("--full-refresh", action="store_true", help="fetch every episode again")
    radd("review", cmd_resolve_review, "List results that need a human look.")
    p = radd("confirm", cmd_resolve_confirm, "Say that an episode is right for a video.",
             seed=False, user=False)
    p.add_argument("video_id")
    p.add_argument("episode_id", type=int)
    p = radd("reject", cmd_resolve_reject, "Say that a video has no matching episode.",
             seed=False, user=False)
    p.add_argument("video_id")

    transcribe = sub.add_parser("transcribe", help="Get transcripts for matched episodes.")
    tsub = transcribe.add_subparsers(dest="command", required=True)

    def tadd(name: str, func, help_text: str) -> argparse.ArgumentParser:
        sp = tsub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(func=func)
        return sp

    def seed_args(sp) -> None:
        sp.add_argument("--seed", nargs="?", const=DEFAULT_SEED, default=None, metavar="FILE",
                        help=f"only the seed file's videos (default file: {DEFAULT_SEED})")
        sp.add_argument("--user", default=core.OWNER, help="local user name (default: owner)")

    p = tadd("run", cmd_transcribe_run, "Transcribe matched episodes (publisher first, then Whisper).")
    seed_args(p)
    p.add_argument("--limit", type=int, default=None, help="stop after this many episodes")
    p.add_argument("--keep-audio", action="store_true", help="do not delete downloaded audio")
    p = tadd("status", cmd_transcribe_status, "Show transcript counts and problems.")
    seed_args(p)
    p = tadd("retry", cmd_transcribe_retry, "Queue an episode again with fresh attempts.")
    p.add_argument("episode_id", type=int)
    p.add_argument("--whisper", action="store_true", help="skip the publisher transcript")
    p = tadd("accept", cmd_transcribe_accept, "Mark a needs_review transcript as ok.")
    p.add_argument("episode_id", type=int)
    p = tadd("show", cmd_transcribe_show, "Show a transcript's details and text near a time.")
    p.add_argument("episode_id", type=int)
    p.add_argument("--at", help="time as seconds, mm:ss or h:mm:ss")
    p.add_argument("--window", type=float, default=30.0, help="seconds either side (default 30)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths.ensure_data_home()
        logging_setup.setup_logging(paths.log_dir())
        return args.func(args)
    except NotSignedIn as exc:
        _err(str(exc))
        return EXIT_SIGN_IN
    except PodcastRecallError as exc:
        _err(f"Error: {exc}")
        return EXIT_ERROR
    except KeyboardInterrupt:
        _err("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
