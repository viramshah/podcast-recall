"""Command line: a thin wrapper over `core.py`.

Results go to standard output. Progress, warnings and errors go to standard error.
Exit codes: 0 success, 1 error, 2 partial, 3 sign-in needed.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime

from podcast_recall import (
    agreement,
    answering,
    answers,
    core,
    evalrun,
    golden,
    ids,
    indexer,
    logging_setup,
    oracle,
    paths,
    schemas,
)
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


def cmd_findings_list(args) -> int:
    rows = core.list_findings(args.user)
    if not rows:
        print("No findings saved yet. Save one from the web chat (Save finding).")
        return EXIT_OK
    for row in rows:
        note = f"  note: {row['note']}" if row["note"] else ""
        print(f"{row['finding_id']:>4}  {row['saved_at'][:10]}  {row['question'][:90]}{note}")
    return EXIT_OK


def cmd_findings_show(args) -> int:
    from podcast_recall import exporter

    items = [i for i in core.finding_items(args.user) if i.finding_id == args.id]
    if not items:
        raise ConfigError(f"There is no finding {args.id} for this user.")
    print(exporter.render_markdown(items), end="")
    return EXIT_OK


def cmd_findings_note(args) -> int:
    core.update_finding_note(args.id, args.text, args.user)
    print(f"Updated the note on finding {args.id}.")
    return EXIT_OK


def cmd_findings_delete(args) -> int:
    core.delete_finding(args.id, args.user)
    print(f"Deleted finding {args.id}. Files you already exported keep their copy until you export again.")
    return EXIT_OK


def cmd_findings_export(args) -> int:
    if args.since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since):
        raise ConfigError("--since must look like 2026-11-26.")
    if args.format == "notes":
        result, count = core.export_findings_to_notes(args.user, since=args.since, show=args.show)
        print(f"{result.capitalize()} the Apple Notes note with {count} finding(s). It reaches your iPhone through iCloud.")
        return EXIT_OK
    path, count = core.export_findings(
        args.format, args.user, since=args.since, show=args.show, out=args.out, force=args.force
    )
    print(f"Wrote {count} finding(s) to {path}")
    print("This file holds your questions and short transcript quotes; keep it private.")
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
    if result.outcomes:
        print("Run `podcast-recall index build` to make the new transcripts searchable.")
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


# ---------------------------------------------------------------------------- index and search


def _index_progress(event: dict) -> None:
    if event["stage"] == "start":
        _err(f"[{event['position']}/{event['total']}] {event['title']} ...")
    else:
        _err(f"    {event['chunks']} chunks")


def cmd_index_build(args) -> int:
    video_ids = _target_ids(args) if args.seed is not None else None
    result = core.build_index(video_ids, rebuild=args.rebuild, on_progress=_index_progress)
    print(
        f"Indexed {result.indexed} episode(s), {result.chunks} chunks. "
        f"Already up to date: {result.up_to_date}. Removed: {result.removed}. "
        f"Meaning search: {'on' if result.vectors_used else 'off'}."
    )
    for warning in result.warnings:
        print(f"Warning: {warning}")
    return EXIT_PARTIAL if result.warnings else EXIT_OK


def cmd_index_status(args) -> int:
    video_ids = _target_ids(args) if args.seed is not None else None
    s = core.index_status(video_ids)
    print(f"Episodes indexed: {s.episodes_indexed}, chunks: {s.chunks}")
    print(f"Waiting to be indexed: {s.waiting}")
    print(f"Episodes without meaning vectors: {s.without_vectors}")
    print(
        f"Chunks: about {paths.chunk_seconds():g} s with {paths.chunk_overlap_seconds():g} s overlap "
        f"(version {s.chunking_version}), embedding model: {s.embed_model}"
    )
    print(f"Vector search available: {'yes' if s.vectors_available else 'no'} ({s.vector_rows} vectors)")
    return EXIT_PARTIAL if (s.waiting or s.without_vectors) else EXIT_OK


def cmd_search(args) -> int:
    video_ids = _target_ids(args) if args.seed is not None else None
    result = core.search_episodes(
        args.query, args.user, show=args.show, since=args.since, until=args.until,
        video_ids=video_ids, limit=args.limit,
    )
    for warning in result.warnings:
        _err(f"Warning: {warning}")
    if not result.hits:
        print("No results.")
        return EXIT_OK
    for number, hit in enumerate(result.hits, 1):
        speaker = f" [{hit.speaker}]" if hit.speaker else ""
        print(f"{number}. {hit.show}: {hit.title}")
        print(f"   {_mmss(hit.start_s)} to {_mmss(hit.end_s)}{speaker}")
        snippet = hit.text if len(hit.text) <= 300 else hit.text[:300].rsplit(" ", 1)[0] + " ..."
        print(f"   {snippet}")
        if hit.url:
            print(f"   {hit.url}")
        if args.explain:
            distance = "-" if hit.vector_distance is None else f"{hit.vector_distance:.3f}"
            print(
                f"   chunk {hit.chunk_id}  score {hit.score:.4f}  keyword rank "
                f"{hit.keyword_rank or '-'}  meaning rank {hit.vector_rank or '-'}  "
                f"meaning distance {distance}"
            )
    return EXIT_OK


# ---------------------------------------------------------------------------- evaluation


GOLDEN_PATH = "data/golden/golden_v0.csv"
LIBRARY_PATH = "data/golden/eval_library.csv"
SHEET_PATH = "data/golden/labelling_sheet.csv"


def _golden_and_library(args):
    return golden.load_golden(args.golden), golden.load_library(args.library)


def cmd_eval_run(args) -> int:
    items, library = _golden_and_library(args)
    raw = answers.load_answers(args.answers) if args.answers else None
    grades = core.run_eval(
        items, library, answers=raw, use_oracle=args.oracle, fabricate=args.fabricate, split=args.split
    )
    print(evalrun.format_summary(evalrun.summarize(grades)))
    failing = [g for g in grades if not g.passed]
    for grade in failing[:15]:
        print(f"\n{grade.item_id} ({grade.type}) failed: {', '.join(grade.rules_failed)}")
        for failure in grade.failures[:3]:
            print(f"  {failure.rule} [{failure.severity}]: {failure.reason}")
    if len(failing) > 15:
        print(f"\n... and {len(failing) - 15} more (see the scorecard file)")
    if args.out:
        evalrun.write_scorecard(args.out, grades)
        print(f"\nWrote {args.out}")
    return EXIT_PARTIAL if failing else EXIT_OK


def cmd_eval_answer(args) -> int:
    import json
    from datetime import UTC

    items, library = _golden_and_library(args)

    def progress(position: int, total: int, item_id: str, status: str, seconds: float) -> None:
        _err(f"[{position}/{total}] {item_id}: {status} ({seconds:.1f} s)")

    ids = [x.strip() for x in args.ids.split(",") if x.strip()] if args.ids else None
    count = len(core.choose_items(items, args.split, args.limit, ids))
    _err(f"Answering {count} questions; each can take up to a minute. Progress appears after each one.")
    services = None
    if args.check or args.unit_top is not None or args.premise_step:
        services = answering.AnswerServices(
            check=True if args.check else None, unit_top=args.unit_top, premise=True if args.premise_step else None
        )
        if args.premise_step:
            _err("Premise step on: a not-found answer to a question about what someone says gets a false-premise check.")
        if args.check:
            _err(f"Answer check on: answers by {paths.answer_model()}, checked by {paths.judge_model()}.")
        if args.unit_top:
            _err(f"Unit selection on: the model sees the {args.unit_top} best units plus their neighbours.")
    answers_by_id, results, latencies, grades = core.answer_golden(
        items, library, split=args.split, limit=args.limit, ids=ids, services=services, on_progress=progress
    )
    print(evalrun.format_answering(evalrun.summarize_answering(results, latencies)))
    print()
    print(evalrun.format_summary(evalrun.summarize(grades)))
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    card = args.out or f"evals/scorecards/answers_{args.split}_{stamp}.csv"
    evalrun.write_scorecard(card, grades)
    answers_path = card.rsplit(".", 1)[0] + ".answers.jsonl"
    with open(answers_path, "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(raw, ensure_ascii=False) + "\n" for item_id, raw in answers_by_id.items())
    chosen = core.choose_items(items, args.split, args.limit, ids)
    trace_path = card.rsplit(".", 1)[0] + ".trace.jsonl"
    with open(trace_path, "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(core.trace_record(item.id, result), ensure_ascii=False) + "\n" for item, result in zip(chosen, results, strict=True))
    print(f"\nWrote {card}, {answers_path} and {trace_path}")
    return EXIT_PARTIAL if any(not g.passed for g in grades) else EXIT_OK


def cmd_eval_diagnose(args) -> int:
    import json

    from podcast_recall import diagnosis

    items, library = _golden_and_library(args)
    answers_by_id = answers.load_answers(args.answers)
    trace_path = args.trace or args.answers.replace(".answers.jsonl", ".trace.jsonl")
    traces: dict[str, dict] = {}
    try:
        with open(trace_path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    record = json.loads(line)
                    traces[record["id"]] = record
    except FileNotFoundError:
        _err(f"No trace file at {trace_path}; causes that need the shown passages cannot be told.")
    grades, found = core.diagnose_run(items, library, answers_by_id, traces)
    print(diagnosis.format_diagnosis(found, len(grades)))
    if args.out:
        import csv

        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "type", "status", "cause", "detail"])
            writer.writerows([d.item_id, d.type, d.status, d.cause, d.detail] for d in found)
        print(f"\nWrote {args.out}")
    return EXIT_OK


def cmd_eval_abstain(args) -> int:
    from podcast_recall import abstention

    items, library = _golden_and_library(args)
    rows = core.abstention_scan(items, library, split=args.split, passages=args.passages)
    print(abstention.format_scan(rows))
    if args.out:
        import csv

        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "type", "best_distance", "hits"])
            writer.writerows([r.item_id, r.type, "" if r.best_distance is None else f"{r.best_distance:.4f}", r.hits] for r in rows)
        print(f"\nWrote {args.out}")
    return EXIT_OK


def cmd_eval_judge_sheet(args) -> int:
    from podcast_recall import judge_calibration as jc

    items, _library = _golden_and_library(args)
    rows = jc.collect_claims(args.answers, items)
    chosen = jc.sample(rows, args.count)
    jc.write_sheet(args.out, chosen)
    print(f"{len(rows)} claims in {len(args.answers)} run(s); {len(chosen)} written to {args.out}.")
    print("Fill in the two last columns for each row with yes, partly or no:")
    print("  human_supported: does the quote clearly say what the claim says?")
    print("  human_answers_question: does the claim directly answer what the question asks?")
    return EXIT_OK


def cmd_eval_grade_sheet(args) -> int:
    from podcast_recall import handgrade
    from podcast_recall import judge_calibration as jc
    from podcast_recall.answers import load_answers, parse_answer

    items, _library = _golden_and_library(args)
    rows = jc.collect_claims([args.answers], items)
    places: dict[str, tuple[str, str]] = {}
    source = jc.source_name(args.answers)
    for item_id, raw in load_answers(args.answers).items():
        for number, claim in enumerate(parse_answer(raw).claims, 1):
            if claim.citations:
                places[f"{source}:{item_id}#{number}"] = (claim.citations[0].show, claim.citations[0].title)
    rows = sorted(rows, key=lambda r: jc._key(r.claim_id))
    handgrade.write_sheet(args.out, rows, places)
    print(f"{len(rows)} claims from {len({r.question_id for r in rows})} answers written to {args.out}.")
    return EXIT_OK


def cmd_eval_grade_score(args) -> int:
    from podcast_recall import handgrade
    from podcast_recall import judge_calibration as jc

    items, _library = _golden_and_library(args)
    grades = handgrade.read_grades(args.sheet)
    result = handgrade.score(jc.collect_claims([args.answers], items), grades)
    print(f"Claims graded: {result.claims}; answers fully graded: {result.answers}"
          + (f" ({result.incomplete} more answers have ungraded claims and are left out)" if result.incomplete else ""))
    if result.answers:
        print(f"Answers passing R3 and R4: {result.passed}/{result.answers} = {result.passed / result.answers:.0%}")
        print(f"Answers with a Critical failure (R3 no or R4 no): {result.critical}/{result.answers} = {result.critical / result.answers:.0%}")
        print(f"Answers with a Major failure only (R3 partly, or a claim that does not answer): {result.major}")
    if result.claims:
        print(f"Claims: R3 yes {result.r3_yes}/{result.claims}, R4 yes {result.r4_yes}/{result.claims}, answers the question yes {result.answers_yes}/{result.claims}")
    return EXIT_OK


def cmd_eval_judge_agreement(args) -> int:
    from podcast_recall import judge_calibration as jc
    from podcast_recall import llm

    items, _library = _golden_and_library(args)
    human = jc.read_labels(args.sheet)
    rows = jc.collect_claims(args.answers, items)
    chat = llm.OllamaChat(model=paths.judge_model())
    _err(f"Asking {paths.judge_model()} about {len(human)} labelled claims.")
    machine = jc.run_judge(chat, rows, set(human))
    print(jc.format_report(jc.compare(human, machine)))
    if args.out:
        import csv

        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["claim_id", "human_supported", "human_answers", "judge_supported", "judge_answers"])
            for claim_id, (hs, ha) in sorted(human.items()):
                ms, ma = machine.get(claim_id, ("", ""))
                writer.writerow([claim_id, hs, ha, ms, ma])
        print(f"\nWrote {args.out}")
    return EXIT_OK


def cmd_eval_retrieval(args) -> int:
    items, library = _golden_and_library(args)
    services = indexer.IndexServices(use_vectors=not args.no_vectors)
    outcomes = core.eval_retrieval(
        items, library, split=args.split, diagnose=args.diagnose, intro_weight=args.intro_weight,
        intro_seconds=args.intro_seconds, services=services,
    )
    s = evalrun.retrieval_summary(outcomes)
    if args.intro_weight not in (None, 1.0):
        print(f"Opening chunks (first {args.intro_seconds or 180:g} s) weighted by {args.intro_weight:g}")
    print(f"Questions with a gold time (single-fact, who/when): {s['timed_n']}")
    print(f"Recall@5:  {s['recall_at_5']:.0%}   (target 85%)")
    print(f"Recall@10: {s['recall_at_10']:.0%}")
    print(f"MRR:       {s['mrr']:.2f}")
    for kind, row in s["by_type"].items():
        print(f"  {kind:<12} recall@5 {row['recall_at_5']:.0%} on {row['n']}")
    if s["synthesis_episode_recall"] is not None:
        print(f"Synthesis episode coverage in the top 5: {s['synthesis_episode_recall']:.0%} on {s['synthesis_n']}")
    print(f"Results from outside the library: {s['leaks']}   (must be 0)")
    if s["misses"]:
        print("Missed: " + ", ".join(s["misses"]))
    if args.diagnose:
        questions = {i.id: i for i in items}
        for outcome in outcomes:
            if outcome.id_missed:
                item = questions[outcome.item_id]
                gold = item.evidence[0]
                where = (
                    f"rank {outcome.deep_rank} of 50 with no per-episode cap (meaning distance "
                    f"{'n/a' if outcome.gold_distance is None else f'{outcome.gold_distance:.3f}'})"
                    if outcome.deep_rank else "not in the top 50 at all"
                )
                print(f"\n{outcome.item_id}: {item.question}")
                print(f"  the right chunk ({gold.video_id} at {golden.format_time(gold.start_s)}) is {where}")
                for hit in outcome.top:
                    distance = "-" if hit.vector_distance is None else f"{hit.vector_distance:.3f}"
                    print(f"    returned: {hit.title[:44]} at {golden.format_time(hit.start_s)} (distance {distance})")
    return EXIT_PARTIAL if s["leaks"] else EXIT_OK


def cmd_eval_check(args) -> int:
    items, library = _golden_and_library(args)
    problems = core.eval_check_golden(items, library)
    for problem in problems:
        print(f"[{problem.kind}] {problem.item_id}: {problem.message}")
    counts = golden.split_counts(items)
    print(f"\n{len(items)} questions. By type: {counts['type']}. By split: {counts['split']}.")
    errors = sum(1 for p in problems if p.kind == "error")
    print(f"{errors} error(s), {len(problems) - errors} warning(s).")
    return EXIT_ERROR if errors else (EXIT_PARTIAL if problems else EXIT_OK)


def cmd_eval_show(args) -> int:
    items, library = _golden_and_library(args)
    found = [i for i in items if i.id == args.item_id]
    if not found:
        _err(f"No question with the id '{args.item_id}'.")
        return EXIT_ERROR
    print(core.eval_show_item(found[0], library))
    return EXIT_OK


def cmd_eval_kappa(args) -> int:
    labels_a = (
        agreement.read_labels(args.labels_a) if args.labels_a
        else agreement.labels_from_golden(golden.load_golden(args.golden))
    )
    report = agreement.compare(labels_a, agreement.read_labels(args.labels_b))
    print(agreement.format_report(report))
    return EXIT_OK if report.meets_gate else EXIT_PARTIAL


def cmd_eval_sheet(args) -> int:
    chosen = agreement.sample_for_second_labeller(golden.load_golden(args.golden), args.count)
    agreement.write_labelling_sheet(args.out, chosen)
    print(f"Wrote {args.out} with {len(chosen)} questions (no gold answers).")
    return EXIT_OK


# ---------------------------------------------------------------------------- ask


def format_answer(response: schemas.AskResponse) -> str:
    answer = response.answer
    lines: list[str] = []
    if answer.status == "not_found":
        lines.append(answer.summary or "I couldn't find that in your podcasts.")
    else:
        if answer.status == "premise_corrected":
            lines.append("Note: the question assumes something the podcasts do not say.")
            if answer.summary:
                lines.append(f"  {answer.summary}" + ("  (not quoted)" if response.note_not_quoted else ""))
        for number, claim in enumerate(answer.claims, 1):
            for cite in claim.citations:
                lines.append(f'{number}. "{cite.quote}"')
                lines.append(f"   {cite.show}: {cite.title}, at {cite.time}")
                lines.append(f"   {cite.url}")
            lines.append(f"   AI summary (may say more than the quote): {claim.text}")
    if response.dropped:
        word = "statement was" if response.dropped == 1 else "statements were"
        lines.append(f"({response.dropped} {word} removed because its quote could not be verified.)")
    for warning in response.warnings:
        lines.append(f"Warning: {warning}")
    return "\n".join(lines)


def cmd_ask(args) -> int:
    video_ids = _target_ids(args) if args.seed is not None else None
    result = core.ask(
        args.question, args.user, show=args.show, since=args.since, until=args.until,
        video_ids=video_ids, record=not args.no_record,
    )
    response = schemas.ask_response(result)
    print(response.model_dump_json(indent=2) if args.json else format_answer(response))
    return EXIT_OK


def cmd_serve(args) -> int:
    import uvicorn

    from podcast_recall import web

    video_ids = _target_ids(args) if args.seed is not None else None
    app = web.create_app(user_id=args.user, port=args.port, video_ids=video_ids)
    if video_ids is not None:
        print(f"Answering from the seed file's {len(video_ids)} episodes, not your whole library.")
    print(f"Podcast Recall is at http://127.0.0.1:{args.port}  (this computer only; press Ctrl+C to stop)")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
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

    index = sub.add_parser("index", help="Build and inspect the search index.")
    isub = index.add_subparsers(dest="command", required=True)

    def iadd(name: str, func, help_text: str) -> argparse.ArgumentParser:
        sp = isub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(func=func)
        sp.add_argument("--seed", nargs="?", const=DEFAULT_SEED, default=None, metavar="FILE",
                        help=f"only the seed file's videos (default file: {DEFAULT_SEED})")
        sp.add_argument("--user", default=core.OWNER, help="local user name (default: owner)")
        return sp

    p = iadd("build", cmd_index_build, "Index new or changed transcripts for search.")
    p.add_argument("--rebuild", action="store_true", help="index every episode again")
    iadd("status", cmd_index_status, "Show how much is indexed and what is waiting.")

    p = add("search", cmd_search, "Search your library's transcripts.")
    p.add_argument("query", help="words to look for; put an exact phrase in double quotes")
    p.add_argument("--show", help="only this show (part of its name)")
    p.add_argument("--since", help="only episodes published on or after YYYY-MM-DD")
    p.add_argument("--until", help="only episodes published on or before YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=8, help="how many results (1 to 50, default 8)")
    p.add_argument("--seed", nargs="?", const=DEFAULT_SEED, default=None, metavar="FILE",
                   help=f"search the seed file's episodes instead of your library (default file: {DEFAULT_SEED})")
    p.add_argument("--explain", action="store_true", help="show the scores behind each result")

    evaluation = sub.add_parser("eval", help="Run the evaluation: golden set, rubric checks, kappa.")
    esub = evaluation.add_subparsers(dest="command", required=True)

    def eadd(name: str, func, help_text: str, files: bool = True) -> argparse.ArgumentParser:
        sp = esub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(func=func)
        sp.add_argument("--golden", default=GOLDEN_PATH, help=f"the golden set (default {GOLDEN_PATH})")
        if files:
            sp.add_argument("--library", default=LIBRARY_PATH,
                            help=f"the evaluation library (default {LIBRARY_PATH})")
        return sp

    p = eadd("run", cmd_eval_run, "Grade answers with the deterministic rubric checks (R1, R2, R5, R7).")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--answers", metavar="FILE", help="answers as JSON Lines, one per question id")
    source.add_argument("--oracle", action="store_true", help="grade perfect answers built from the golden set (must score 100%%)")
    source.add_argument("--fabricate", metavar="MODE", choices=oracle.FABRICATE_MODES,
                        help="grade deliberately wrong answers; modes: " + ", ".join(oracle.FABRICATE_MODES))
    p.add_argument("--split", choices=("all", "dev", "heldout"), default="all")
    p.add_argument("--out", metavar="FILE", help="write the per-question scorecard CSV here")
    p = eadd("answer", cmd_eval_answer, "Answer the golden questions with the real system and grade them.")
    p.add_argument("--split", choices=("all", "dev", "heldout"), default="dev",
                   help="which questions (default dev; the held-out split is never used for tuning)")
    p.add_argument("--limit", type=int, default=None, help="only the first N questions (a quick trial)")
    p.add_argument("--ids", metavar="ID,ID,...", help="only these question ids (for re-testing a few failures)")
    p.add_argument("--unit-top", type=int, default=None, metavar="N",
                   help="show the model only the N best-matching units plus neighbours (E5; 0 = all)")
    p.add_argument("--premise-step", action="store_true",
                   help="E9: re-check not-found answers to questions about what someone says for a false premise")
    p.add_argument("--check", action="store_true",
                   help="run the second-model answer check (PODCAST_RECALL_JUDGE_MODEL) before grading")
    p.add_argument("--out", metavar="FILE", help="where to write the scorecard CSV")
    p = eadd("diagnose", cmd_eval_diagnose, "Explain why each failing golden question failed (from a saved answers run).")
    p.add_argument("--answers", required=True, metavar="FILE", help="the .answers.jsonl written by `eval answer`")
    p.add_argument("--trace", metavar="FILE", help="the .trace.jsonl (default: next to the answers file)")
    p.add_argument("--out", metavar="FILE", help="where to write the per-question causes as CSV")
    p = eadd("abstain", cmd_eval_abstain, "Can search distance alone separate answerable from unanswerable questions? (no model)")
    p.add_argument("--split", choices=("all", "dev", "heldout"), default="dev",
                   help="which questions (default dev; pick the threshold on dev only)")
    p.add_argument("--passages", type=int, default=None, help="how many results to search (default: the answer setting)")
    p.add_argument("--out", metavar="FILE", help="where to write the per-question distances as CSV")
    p = eadd("judge-sheet", cmd_eval_judge_sheet, "Write a sheet of claims for a person to label (to calibrate the judge model).")
    p.add_argument("--answers", action="append", required=True, metavar="FILE", help="an .answers.jsonl from `eval answer` (repeat for several runs)")
    p.add_argument("--count", type=int, default=60, help="how many claims to put on the sheet (default 60)")
    p.add_argument("--out", default="evals/judge_sheet.csv", help="where to write the sheet")
    p = eadd("grade-sheet", cmd_eval_grade_sheet, "Write a sheet of every claim in a run for a person to grade on R3 and R4.")
    p.add_argument("--answers", required=True, metavar="FILE", help="the .answers.jsonl from `eval answer`")
    p.add_argument("--out", required=True, metavar="FILE", help="where to write the sheet")
    p = eadd("grade-score", cmd_eval_grade_score, "Score a graded R3/R4 sheet.")
    p.add_argument("--answers", required=True, metavar="FILE", help="the same .answers.jsonl")
    p.add_argument("--sheet", required=True, metavar="FILE", help="the sheet with the grades filled in")
    p = eadd("judge-agreement", cmd_eval_judge_agreement, "Compare the judge model with a person's labels on the sheet.")
    p.add_argument("--sheet", required=True, metavar="FILE", help="the sheet with the human labels filled in")
    p.add_argument("--answers", action="append", required=True, metavar="FILE", help="the same .answers.jsonl files used for the sheet")
    p.add_argument("--out", metavar="FILE", help="where to write each claim's human and judge labels as CSV")
    p = eadd("retrieval", cmd_eval_retrieval, "Measure recall@5 on the golden questions.")
    p.add_argument("--split", choices=("all", "dev", "heldout"), default="all")
    p.add_argument("--no-vectors", action="store_true", help="keyword search only")
    p.add_argument("--diagnose", action="store_true",
                   help="for each miss, show where the right chunk ranks in a deeper search with no per-episode cap")
    p.add_argument("--intro-weight", type=float, default=None,
                   help="multiply the score of chunks from an episode's first minutes by this (default 1, no change)")
    p.add_argument("--intro-seconds", type=float, default=None,
                   help="what counts as an episode's opening, in seconds (default 180)")
    eadd("check", cmd_eval_check, "Check the golden set itself: evidence exists, absent answers are absent.")
    p = eadd("show", cmd_eval_show, "Show one question with the transcript text at its gold time.")
    p.add_argument("item_id")
    p = eadd("kappa", cmd_eval_kappa, "Compare two labellers' sheets (Cohen's kappa on question type).", files=False)
    p.add_argument("--labels-b", required=True, metavar="FILE", help="the second labeller's sheet")
    p.add_argument("--labels-a", metavar="FILE", help="the first labeller's sheet (default: the golden set)")
    p = eadd("sheet", cmd_eval_sheet, "Write the sheet the second labeller fills in (questions only).", files=False)
    p.add_argument("--out", default=SHEET_PATH, help=f"where to write it (default {SHEET_PATH})")
    p.add_argument("--count", type=int, default=20, help="how many questions (default 20)")

    p = add("ask", cmd_ask, "Ask a question and get an answer with verified citations.")
    p.add_argument("question", help="your question, in plain English")
    p.add_argument("--show", help="only this show (part of its name)")
    p.add_argument("--since", help="only episodes published on or after YYYY-MM-DD")
    p.add_argument("--until", help="only episodes published on or before YYYY-MM-DD")
    p.add_argument("--json", action="store_true", help="print the answer as JSON")
    p.add_argument("--no-record", action="store_true", help="do not store this question and answer")
    p.add_argument("--seed", nargs="?", const=DEFAULT_SEED, default=None, metavar="FILE",
                   help=f"answer from the seed file's episodes instead of your library (default file: {DEFAULT_SEED})")
    findings = sub.add_parser("findings", help="List, edit, delete and export saved findings.")
    fsub = findings.add_subparsers(dest="command", required=True)

    def fadd(name: str, func, help_text: str) -> argparse.ArgumentParser:
        sp = fsub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(func=func)
        sp.add_argument("--user", default=core.OWNER, help="local user name (default: owner)")
        return sp

    fadd("list", cmd_findings_list, "List saved findings, newest first.")
    p = fadd("show", cmd_findings_show, "Show one finding as it will be exported.")
    p.add_argument("id", type=int, help="the finding number from `findings list`")
    p = fadd("note", cmd_findings_note, "Change the note on a finding.")
    p.add_argument("id", type=int, help="the finding number")
    p.add_argument("text", help="the new note (use \"\" to clear it)")
    p = fadd("delete", cmd_findings_delete, "Delete a finding (the quotes and answer are never edited).")
    p.add_argument("id", type=int, help="the finding number")
    p = fadd("export", cmd_findings_export, "Write the findings to Markdown, HTML or Apple Notes.")
    p.add_argument("--format", choices=("md", "html", "notes"), default="md",
                   help="md (default), html (opens on a phone) or notes (Apple Notes, Mac only)")
    p.add_argument("--since", metavar="YYYY-MM-DD", help="only findings saved on or after this date")
    p.add_argument("--show", help="only findings that cite this show")
    p.add_argument("--out", metavar="FILE_OR_FOLDER",
                   help="where to write (default: ~/Documents/Podcast Recall exports/)")
    p.add_argument("--force", action="store_true", help="overwrite a file that Podcast Recall did not create")

    p = add("serve", cmd_serve, "Start the local web chat (this computer only).")
    p.add_argument("--port", type=int, default=8000, help="port to listen on (default 8000)")
    p.add_argument("--seed", nargs="?", const=DEFAULT_SEED, default=None, metavar="FILE",
                   help=f"answer from the seed file's episodes instead of your library (default file: {DEFAULT_SEED})")
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
