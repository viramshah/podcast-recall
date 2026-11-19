"""Test answerers that prove the harness works (decision D18, question 21).

The **oracle** builds a perfect answer from a golden item and the real transcript, so it must score
100%. The **fabricator** answers wrongly in one chosen way, so each way must fail the right rule.
Neither uses a model.
"""

from __future__ import annotations

from podcast_recall import golden
from podcast_recall.answers import (
    MAX_QUOTE_SENTENCES,
    Answer,
    Citation,
    Claim,
    answer_to_dict,
    link_for,
    sentence_count,
)
from podcast_recall.checkers import EvalContext, expected_status
from podcast_recall.errors import ConfigError
from podcast_recall.golden import GoldenItem

FABRICATE_MODES = (
    "invented_quote",  # right episode and time, but the quote is made up (fails R1)
    "outside_library",  # a real quote from an episode that is not in the library (fails R2)
    "wrong_time",  # a real quote cited at the wrong time (fails R1, and R7)
    "invents_answer",  # answers a question that should get "not found" (fails R5)
    "uncited_claim",  # a claim with no citation (fails R1)
    "refuses",  # says "not found" to everything (fails R5 on answerable questions)
)

INVENTED = "The guest firmly declared that the moon landing was scheduled for next Tuesday."


def _trim_to_sentences(text: str, limit: int = MAX_QUOTE_SENTENCES) -> str:
    import re

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    return " ".join(sentences[:limit])


def real_quote(ctx: EvalContext, episode_id: int, at_s: float) -> tuple[str, float]:
    """A real quote of at most 2 sentences from the segment at `at_s`, and that segment's start."""
    transcript = ctx.transcript_for(episode_id)
    if transcript is None or not transcript.segments:
        raise ConfigError(f"No transcript for episode {episode_id}.")
    segments = sorted(transcript.segments, key=lambda s: s.start)
    chosen = next((s for s in segments if s.start <= at_s < s.end), None)
    if chosen is None:
        chosen = min(segments, key=lambda s: abs(s.start - at_s))
    index = segments.index(chosen)
    text = chosen.text
    while sentence_count(text) < MAX_QUOTE_SENTENCES and index + 1 < len(segments):
        index += 1
        text = f"{text} {segments[index].text}"
    return _trim_to_sentences(text), chosen.start


def _citation(ctx: EvalContext, video_id: str, episode_id: int, quote: str, start_s: float) -> Citation:
    show, title = ctx.episode_label(episode_id)
    return Citation(video_id, episode_id, show, title, quote, start_s, link_for(video_id, start_s))


def oracle_answer(item: GoldenItem, ctx: EvalContext) -> Answer:
    status = expected_status(item)
    if status != "answered":
        return Answer(status, (), item.gold_answer)
    claims = []
    for evidence in item.evidence:
        episode_id = ctx.video_to_episode[evidence.video_id]
        quote, start = real_quote(ctx, episode_id, evidence.start_s)
        claims.append(
            Claim(item.gold_answer, (_citation(ctx, evidence.video_id, episode_id, quote, start),))
        )
        if item.type != golden.SYNTHESIS:
            break
    return Answer("answered", tuple(claims), item.gold_answer)


def fabricated_answer(item: GoldenItem, ctx: EvalContext, mode: str) -> Answer:
    if mode not in FABRICATE_MODES:
        raise ConfigError(f"Unknown fabrication mode '{mode}'. Use one of: {', '.join(FABRICATE_MODES)}")
    if mode == "refuses":
        return Answer("not_found", (), "")
    if mode == "invents_answer":
        if item.answerable:
            return oracle_answer(item, ctx)  # nothing to fabricate for a question that has an answer
        episode_id = min(ctx.library_episode_ids)
        video_id = next(v for v, e in ctx.video_to_episode.items() if e == episode_id)
        cite = _citation(ctx, video_id, episode_id, INVENTED, 60.0)
        return Answer("answered", (Claim("An invented answer.", (cite,)),), "An invented answer.")
    if not item.evidence:
        return oracle_answer(item, ctx)  # these modes only change answers that cite evidence
    base = oracle_answer(item, ctx)
    if base.status != "answered":
        return base
    claims = []
    for claim in base.claims:
        citation = claim.citations[0]
        if mode == "invented_quote":
            changed = Citation(citation.video_id, citation.episode_id, citation.show, citation.title,
                               INVENTED, citation.start_s, citation.url)
            claims.append(Claim(claim.text, (changed,)))
        elif mode == "wrong_time":
            moved = citation.start_s + 600.0
            changed = Citation(citation.video_id, citation.episode_id, citation.show, citation.title,
                               citation.quote, moved, link_for(citation.video_id, moved))
            claims.append(Claim(claim.text, (changed,)))
        elif mode == "uncited_claim":
            claims.append(Claim(claim.text, ()))
        else:  # outside_library
            outside = sorted(set(ctx.video_to_episode.values()) - ctx.library_episode_ids)
            if not outside:
                raise ConfigError("Every indexed episode is in the library, so there is none to cite outside it.")
            episode_id = outside[0]
            video_id = next(v for v, e in ctx.video_to_episode.items() if e == episode_id)
            quote, start = real_quote(ctx, episode_id, 600.0)
            claims.append(Claim(claim.text, (_citation(ctx, video_id, episode_id, quote, start),)))
    return Answer("answered", tuple(claims), base.summary)


def answers_for(items, ctx: EvalContext, *, oracle: bool, mode: str | None = None) -> dict[str, dict]:
    """Raw answers (as they would be read from a file) for every golden item."""
    out = {}
    for item in items:
        answer = oracle_answer(item, ctx) if oracle else fabricated_answer(item, ctx, mode or "")
        out[item.id] = {"id": item.id, **answer_to_dict(answer)}
    return out
