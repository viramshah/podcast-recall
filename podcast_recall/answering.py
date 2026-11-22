"""Answer a question from the user's podcasts, with citations that are real (decision D19).

question -> search -> number the passages -> ask the local model -> turn its pointers into quotes
         -> verify R1 + R2 -> answer, or "not found" -> log

The model never writes a quote. It points at numbered units and the code copies their text, so a
quote is always word for word and its time is the unit's start. What this does not prove is that
the quote supports the claim written next to it: that is R3, the judge's job in Week 4.
"""

from __future__ import annotations

import dataclasses
import re
import sqlite3
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from podcast_recall import (
    checkers,
    evalrun,
    indexer,
    llm,
    paths,
    prompting,
    retrieval,
    transcripts,
    units,
    verifier,
)
from podcast_recall.answers import (
    MAX_QUOTE_WORDS,
    Answer,
    Citation,
    Claim,
    link_for,
)
from podcast_recall.errors import ConfigError
from podcast_recall.prompting import MAX_SOURCES, MAX_UNITS_PER_SOURCE, STATUSES, Passage
from podcast_recall.units import Unit
from podcast_recall.verifier import NOT_FOUND_TEXT, Dropped

MAX_QUESTION_CHARS = 1000
PER_EPISODE = 3
QUOTE_SPAN_S = 12.0  # only units that start this soon after the first one join a quote (R1's window is 15 s)
MODEL_ATTEMPTS = 2


@dataclass
class AnswerServices:
    index: indexer.IndexServices = field(default_factory=indexer.IndexServices)
    chat: object | None = None  # something with `chat_json(system, user, schema)`; real Ollama by default
    _default: object | None = field(default=None, repr=False)

    def get_chat(self):
        if self.chat is not None:
            return self.chat
        if self._default is None:
            self._default = llm.OllamaChat()
        return self._default


@dataclass
class AskResult:
    answer: Answer
    dropped: list[Dropped] = field(default_factory=list)
    uncited_note: bool = False
    chunk_ids: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    model: str = ""
    latency_ms: int = 0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    request_id: int | None = None


# ---------------------------------------------------------------------------- the quote


def trim_quote(text: str) -> str:
    """At most 2 sentences and 60 words, from the start of the text."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    words = " ".join(sentences[:2]).split()
    return " ".join(words[:MAX_QUOTE_WORDS])


def build_quote(selected: Sequence[Unit]) -> tuple[str, float]:
    """The quote for a pointer: the cited units' own words, only those that start within 12 seconds
    of the first (so the quote stays inside the checker's 15 second window), trimmed to at most 2
    sentences and 60 words. Returns the quote and the first unit's start time."""
    first = selected[0]
    chosen = [u for u in selected if u.start_s - first.start_s <= QUOTE_SPAN_S]
    return trim_quote(" ".join(u.text for u in chosen)), first.start_s


# ---------------------------------------------------------------------------- reading the model's reply


def _runs(numbers: Sequence[int], owner: dict) -> list[list[int]]:
    """Split the cited unit numbers into runs of consecutive units inside one passage."""
    runs: list[list[int]] = []
    for n in sorted(set(numbers)):
        if runs and n == runs[-1][-1] + 1 and owner[n][0] is owner[runs[-1][0]][0]:
            runs[-1].append(n)
        else:
            runs.append([n])
    return runs


def interpret(
    data: dict,
    passages: dict[int, Passage],
    video_for: Callable[[int], str | None],
) -> tuple[str, str, list[Claim], list[Dropped]]:
    """Turn the model's JSON into (status, note, claims with real citations, dropped claims).
    A pointer that does not lead to a real unit drops that claim; nothing is ever invented."""
    status = data.get("status")
    if status not in STATUSES:
        raise llm.InvalidModelOutput("the reply has no valid status")
    raw_claims = data.get("claims")
    if not isinstance(raw_claims, list):
        raise llm.InvalidModelOutput("the reply has no list of claims")
    note = data.get("note") if isinstance(data.get("note"), str) else ""
    claims: list[Claim] = []
    dropped: list[Dropped] = []
    for raw in raw_claims:
        text = (raw.get("text") if isinstance(raw, dict) else None)
        text = text.strip() if isinstance(text, str) else ""
        if not text:
            dropped.append(Dropped("(empty)", "the claim had no text"))
            continue
        citations: list[Citation] = []
        reason = None
        for source in (raw.get("sources") if isinstance(raw.get("sources"), list) else []):
            found, reason = _citations(source, passages, video_for)
            citations.extend(found)
        if not citations:
            dropped.append(Dropped(text, reason or "the claim had no usable source"))
        else:
            claims.append(Claim(text[:400], tuple(citations)))
    return status, note, claims, dropped


def _citations(source, passages: dict[int, Passage], video_for) -> tuple[list[Citation], str | None]:
    """Unit numbers are unique across the prompt, so the units alone say which passage is meant.
    Units that are not next to each other (a common slip of small models) become separate citations,
    one per run; each quote is still the real transcript text."""
    if not isinstance(source, dict):
        return [], "a source was not an object"
    wanted = source.get("units")
    if not isinstance(wanted, list) or not wanted or not all(isinstance(n, int) for n in wanted):
        return [], "it pointed at no units"
    owner = {u.number: (p, u) for p in passages.values() for u in p.units}
    if any(n not in owner for n in wanted):
        return [], "it pointed at a unit that does not exist"
    found: list[Citation] = []
    reason = None
    for run in _runs(wanted, owner)[:MAX_SOURCES]:
        run = run[:MAX_UNITS_PER_SOURCE]
        passage = owner[run[0]][0]
        quote, start_s = build_quote([owner[n][1] for n in run])
        if not quote.strip():
            reason = "the cited units had no text"
            continue
        video_id = video_for(passage.hit.episode_id)
        if video_id is None:
            reason = "the episode has no video in the library"
            continue
        found.append(Citation(video_id, passage.hit.episode_id, passage.hit.show, passage.hit.title, quote,
                              start_s, link_for(video_id, start_s)))
    return found, (None if found else reason)


# ---------------------------------------------------------------------------- the path


def build_context(conn: sqlite3.Connection, user_id: str, video_ids: Sequence[str] | None) -> checkers.EvalContext:
    """What the verifier needs: the episodes the user may cite, and every matched video."""
    ctx = evalrun.build_context(conn, [])
    ctx.library_episode_ids = set(retrieval.library_episode_ids(conn, user_id, video_ids))
    return ctx


def answer_question(
    conn: sqlite3.Connection,
    services: AnswerServices,
    question: str,
    user_id: str,
    *,
    show: str | None = None,
    since: str | None = None,
    until: str | None = None,
    video_ids: Sequence[str] | None = None,
    passages: int | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> AskResult:
    started = clock()
    question = question.strip()
    if not question:
        raise ConfigError("Please type a question.")
    if len(question) > MAX_QUESTION_CHARS:
        raise ConfigError(f"The question is too long (the limit is {MAX_QUESTION_CHARS} characters).")
    count = passages or paths.passages()
    found = retrieval.find(
        conn, services.index.get_embedder(), question, user_id, show=show, since=since, until=until,
        video_ids=video_ids, limit=count, per_episode=PER_EPISODE, use_vectors=services.index.use_vectors,
    )
    result = AskResult(Answer("not_found", (), NOT_FOUND_TEXT), warnings=list(found.warnings))
    chat = services.get_chat()
    result.model = getattr(chat, "model", "")

    cache: dict[int, object] = {}
    numbered: dict[int, Passage] = {}
    unit_count = 0
    for hit in found.hits:
        if hit.episode_id not in cache:
            cache[hit.episode_id] = transcripts.load_transcript(conn, hit.episode_id)
        transcript = cache[hit.episode_id]
        if transcript is None:
            continue
        pieces = units.build_units(transcript.segments, hit.start_s, hit.end_s)
        if pieces:
            number = len(numbered) + 1
            pieces = [dataclasses.replace(u, number=u.number + unit_count) for u in pieces]
            unit_count += len(pieces)  # unit numbers run on across passages, so each is unique
            numbered[number] = Passage(number, hit, tuple(pieces))
    result.chunk_ids = [p.hit.chunk_id for p in numbered.values()]
    if not numbered:
        result.latency_ms = int((clock() - started) * 1000)
        return result

    video_cache: dict[int, str | None] = {}

    def video_for(episode_id: int) -> str | None:
        if episode_id not in video_cache:
            video_cache[episode_id] = retrieval.video_for_episode(conn, user_id, episode_id, video_ids)
        return video_cache[episode_id]

    message = prompting.build_user_message(question, list(numbered.values()))
    interpreted = None
    last_error: Exception | None = None
    for _attempt in range(MODEL_ATTEMPTS):
        try:
            reply = chat.chat_json(prompting.SYSTEM_PROMPT, message, prompting.ANSWER_SCHEMA)
            interpreted = interpret(reply.data, numbered, video_for)
            result.prompt_tokens, result.completion_tokens = reply.prompt_tokens, reply.completion_tokens
            break
        except llm.InvalidModelOutput as exc:
            last_error = exc
    if interpreted is None:
        result.warnings.append(f"The model's reply could not be used ({last_error}).")
        result.latency_ms = int((clock() - started) * 1000)
        return result

    status, note, claims, dropped = interpreted
    draft = Answer(status, tuple(claims), "")
    verified = verifier.verify(draft, build_context(conn, user_id, video_ids), note=note)
    result.answer = verified.answer
    result.dropped = dropped + verified.dropped
    result.uncited_note = verified.uncited_note
    result.latency_ms = int((clock() - started) * 1000)
    return result
