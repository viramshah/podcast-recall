"""Score search against data/retrieval_probe.csv and report recall@5.

Usage:
    uv run python scripts/retrieval_probe.py [--probe FILE] [--user NAME] [--no-vectors] [--limit 10]

Needs the index built (`podcast-recall index build --seed`) and, unless --no-vectors, Ollama running.
By default the search covers the seed file's episodes (the probe questions are about those); use
--library to search your own YouTube library instead.
Run it with and without --no-vectors to see what meaning search adds.
"""

import argparse
import sys

from podcast_recall import core, ids, indexer, paths, probe
from podcast_recall.errors import PodcastRecallError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", default="data/retrieval_probe.csv")
    parser.add_argument("--user", default=core.OWNER)
    parser.add_argument("--no-vectors", action="store_true", help="keyword search only")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--semantic-weight", type=float, default=None,
                        help="weight of the meaning ranking against keywords (default 1.0, equal)")
    parser.add_argument("--per-episode", type=int, default=3,
                        help="most chunks taken from one episode (default 3, the app's default)")
    parser.add_argument("--seed", default="data/seed_episodes.csv",
                        help="search the episodes of this seed file (default)")
    parser.add_argument("--library", action="store_true",
                        help="search your YouTube library instead of the seed file")
    args = parser.parse_args()

    rows = probe.load_probe(args.probe)
    scope = None if args.library else ids.load_ids([args.seed])[0]
    services = indexer.IndexServices(use_vectors=not args.no_vectors)
    conn = core.open_db()
    outcomes: list[probe.ProbeOutcome] = []
    problems = 0
    try:
        for row in rows:
            match = conn.execute(
                "SELECT episode_id FROM episode_matches WHERE video_id = ? AND status = 'matched'",
                (row.video_id,),
            ).fetchone()
            if match is None:
                print(f"SKIPPED {row.video_id}: no matched episode for this video")
                problems += 1
                continue
            result = core.search_episodes(
                row.question, args.user, video_ids=scope, limit=args.limit,
                per_episode=args.per_episode, semantic_weight=args.semantic_weight,
                services=services, conn=conn,
            )
            for warning in result.warnings[:1]:
                print(f"warning: {warning}")
            outcome = probe.ProbeOutcome(
                row, probe.gold_rank(result.hits, match[0], row.gold_s), result.hits
            )
            if outcome.rank is None or outcome.rank > 5:
                # where would the right chunk rank with no per-episode cap and a deep list?
                deep = core.search_episodes(
                    row.question, args.user, video_ids=scope, limit=50, per_episode=50,
                    semantic_weight=args.semantic_weight, services=services, conn=conn,
                )
                outcome.deep_rank = probe.gold_rank(deep.hits, match[0], row.gold_s)
                gold_hit = next((h for h in deep.hits if probe.holds_gold(h, match[0], row.gold_s)), None)
                outcome.gold_distance = gold_hit.vector_distance if gold_hit else None
            outcomes.append(outcome)
    finally:
        conn.close()

    print(f"\n{'#':>2}  {'rank':>4}  {'@5':<3} {'who':<6} {'tag':<4} question")
    for number, o in enumerate(outcomes, 1):
        rank = o.rank if o.rank else "-"
        ok = "yes" if o.rank and o.rank <= 5 else "NO"
        print(f"{number:>2}  {rank!s:>4}  {ok:<3} {o.row.author:<6} {o.row.tag:<4} {o.row.question[:70]}")

    print(f"\nSettings: chunks {paths.chunk_seconds():g} s / {paths.chunk_overlap_seconds():g} s overlap, "
          f"per-episode cap {args.per_episode}, meaning weight "
          f"{1.0 if args.semantic_weight is None else args.semantic_weight}, limit {args.limit}, "
          f"{'keyword only' if args.no_vectors else 'keyword + meaning'}")
    print(f"Questions scored: {len(outcomes)}" + (f" ({problems} skipped)" if problems else ""))
    print(f"Recall@5:  {probe.recall_at(outcomes, 5):.0%}   (target 85%)")
    print(f"Recall@10: {probe.recall_at(outcomes, 10):.0%}")
    print(f"MRR:       {probe.mean_reciprocal_rank(outcomes):.2f}")
    raj = [o for o in outcomes if o.row.tag == "raj"]
    if raj:
        print(f"Raj Shamani episodes only: recall@5 {probe.recall_at(raj, 5):.0%} on {len(raj)} questions")
    for o in outcomes:
        if o.rank is None or o.rank > 5:
            print(f"\nMISS: {o.row.question}")
            where = (f"rank {o.deep_rank} of 50 with no per-episode cap (meaning distance "
                     f"{o.gold_distance if o.gold_distance is None else round(o.gold_distance, 3)})"
                     if o.deep_rank else "not in the top 50 at all")
            print(f"  the right chunk ({o.row.video_id} at {o.row.gold_s:.0f}s) is {where}")
            print("  what came back instead:")
            for hit in o.top[:3]:
                print(f"    {hit.title[:50]} at {hit.start_s:.0f}s  distance {hit.vector_distance}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PodcastRecallError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
