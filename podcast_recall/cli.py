"""Command line: a thin wrapper over `core.py`.

Results go to standard output. Progress, warnings and errors go to standard error.
Exit codes: 0 success, 1 error, 2 partial, 3 sign-in needed.
"""

from __future__ import annotations

import argparse
import sys

from podcast_recall import core, ids, logging_setup, paths
from podcast_recall.errors import NotSignedIn, PodcastRecallError
from podcast_recall.models import FetchResult, SyncResult

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


# ---------------------------------------------------------------------------- parser


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
