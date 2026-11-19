"""Score search against data/retrieval_probe.csv and report recall@5.

Usage:
    uv run python scripts/retrieval_probe.py [--probe FILE] [--user NAME] [--no-vectors] [--limit 10]

Needs the index built (`podcast-recall index build --seed`) and, unless --no-vectors, Ollama running.
By default the search covers the seed file's episodes (the probe questions are about those); use
--library to search your own YouTube library instead.
Run it with and without --no-vectors to see what meaning search adds.
"""

import argparse

from podcast_recall import core, ids, indexer, probe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", default="data/retrieval_probe.csv")
    parser.add_argument("--user", default=core.OWNER)
    parser.add_argument("--no-vectors", action="store_true", help="keyword search only")
    parser.add_argument("--limit", type=int, default=10)
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
                row.question, args.user, video_ids=scope, limit=args.limit, services=services,
                conn=conn,
            )
            for warning in result.warnings[:1]:
                print(f"warning: {warning}")
            outcomes.append(
                probe.ProbeOutcome(row, probe.gold_rank(result.hits, match[0], row.gold_s), result.hits)
            )
    finally:
        conn.close()

    print(f"\n{'#':>2}  {'rank':>4}  {'@5':<3} {'who':<6} {'tag':<4} question")
    for number, o in enumerate(outcomes, 1):
        rank = o.rank if o.rank else "-"
        ok = "yes" if o.rank and o.rank <= 5 else "NO"
        print(f"{number:>2}  {rank!s:>4}  {ok:<3} {o.row.author:<6} {o.row.tag:<4} {o.row.question[:70]}")

    print(f"\nQuestions scored: {len(outcomes)}" + (f" ({problems} skipped)" if problems else ""))
    print(f"Recall@5:  {probe.recall_at(outcomes, 5):.0%}   (target 85%)")
    print(f"Recall@10: {probe.recall_at(outcomes, 10):.0%}")
    print(f"MRR:       {probe.mean_reciprocal_rank(outcomes):.2f}")
    raj = [o for o in outcomes if o.row.tag == "raj"]
    if raj:
        print(f"Raj Shamani episodes only: recall@5 {probe.recall_at(raj, 5):.0%} on {len(raj)} questions")
    for o in outcomes:
        if o.rank is None or o.rank > 5:
            print(f"\nMISS: {o.row.question}")
            print(f"  expected {o.row.video_id} at {o.row.gold_s:.0f}s; top results:")
            for hit in o.top[:3]:
                print(f"    {hit.title[:50]} at {hit.start_s:.0f}s  distance {hit.vector_distance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
