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
    embeddings,
    evalrun,
    indexer,
    judge,
    llm,
    paths,
    premise,
    prompting,
    retrieval,
    transcripts,
    units,
    unitselect,
    verifier,
)
from podcast_recall.answers import (
    MAX_QUOTE_WORDS,
    Answer,
    Citation,
    Claim,
    link_for,
)
from podcast_recall.errors import ApiError, ConfigError
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
    check: bool | None = None  # run the second-model answer check; None means the environment setting
    unit_top: int | None = None  # keep only this many best units (E5); None means the environment setting
    premise: bool | None = None  # check `not_found` answers for a false premise (E9); None means the environment
    judge: object | None = None  # the checker's model client; a real Ollama judge model by default
    _default: object | None = field(default=None, repr=False)
    _default_judge: object | None = field(default=None, repr=False)

    def get_chat(self):
        if self.chat is not None:
            return self.chat
        if self._default is None:
            self._default = llm.OllamaChat()
        return self._default

    def checking(self) -> bool:
        return paths.answer_check_enabled() if self.check is None else self.check

    def premise_step(self) -> bool:
        return paths.premise_step_enabled() if self.premise is None else self.premise

    def unit_limit(self) -> int:
        return paths.unit_top() if self.unit_top is None else self.unit_top

    def get_judge(self):
        if self.judge is not None:
            return self.judge
        if self._default_judge is None:
            self._default_judge = llm.OllamaChat(model=paths.judge_model())
        return self._default_judge


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
    raw_reply: dict | None = None  # the model's JSON reply as received (private; for diagnosis)
    check_raw: dict | None = None  # the answer checker's verdicts, when the check ran
    check_model: str = ""
    check_ms: int = 0
    units_total: int = 0  # units in the retrieved passages
    units_shown: int = 0  # units the model was shown (fewer when the unit selection is on)
    premise_raw: dict | None = None  # the premise check's reply, when that step ran
    premise_ms: int = 0


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
    result.units_total = sum(len(p.units) for p in numbered.values())
    result.units_shown = result.units_total
    top = services.unit_limit()
    if numbered and top > 0:
        try:
            reduced = unitselect.select_units(question, list(numbered.values()), services.index.get_embedder(), top)
            numbered = {p.number: p for p in reduced}
            result.units_shown = sum(len(p.units) for p in reduced)
        except (embeddings.EmbeddingUnavailable, ApiError) as exc:
            result.warnings.append(f"Unit selection was skipped ({exc}); the model saw every unit.")
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
            result.raw_reply = reply.data
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
    if (
        result.answer.status == "not_found"
        and services.premise_step()
        and premise.looks_attributed(question)
    ):
        _run_premise_step(result, services, question, numbered, video_for, build_context(conn, user_id, video_ids), clock)
    if services.checking() and result.answer.claims and result.answer.status in ("answered", "premise_corrected"):
        _run_check(result, services, question, clock)
    result.latency_ms = int((clock() - started) * 1000)
    return result


def _run_premise_step(result: AskResult, services: AnswerServices, question: str, numbered, video_for, ctx, clock) -> None:
    """Ask once whether the passages contradict what the question assumes. A correction is kept only
    if at least one of its claims has a verified citation."""
    began = clock()
    message = prompting.build_user_message(question, list(numbered.values()))
    reply = None
    for _attempt in range(MODEL_ATTEMPTS):
        try:
            reply = services.get_chat().chat_json(premise.PREMISE_PROMPT, message, premise.PREMISE_SCHEMA)
            break
        except llm.InvalidModelOutput as exc:
            result.warnings.append(f"The premise check's reply could not be used ({exc}).")
    result.premise_ms = int((clock() - began) * 1000)
    if reply is None:
        return
    result.premise_raw = reply.data
    try:
        status, note, claims, dropped = interpret(reply.data, numbered, video_for)
    except llm.InvalidModelOutput as exc:
        result.warnings.append(f"The premise check's reply could not be used ({exc}).")
        return
    if status != "premise_corrected" or not claims:
        result.dropped = result.dropped + dropped
        return
    verified = verifier.verify(Answer(status, tuple(claims), ""), ctx, note=note)
    result.dropped = result.dropped + dropped + verified.dropped
    if verified.answer.status == "premise_corrected":
        result.answer = verified.answer
        result.uncited_note = verified.uncited_note


def _run_check(result: AskResult, services: AnswerServices, question: str, clock: Callable[[], float]) -> None:
    """The second-model check: drop claims whose quote does not clearly support them or that do not
    answer the question; if none are left the answer becomes "not found"."""
    judge_client = services.get_judge()
    began = clock()
    checked = judge.check_answer(judge_client, question, result.answer.status, result.answer.claims)
    result.check_ms = int((clock() - began) * 1000)
    result.check_raw = checked.raw
    result.check_model = getattr(judge_client, "model", "")
    if checked.warning:
        result.warnings.append(checked.warning)
    result.dropped = result.dropped + checked.dropped
    if checked.kept:
        result.answer = dataclasses.replace(result.answer, claims=tuple(checked.kept))
    elif checked.dropped:
        result.answer = Answer("not_found", (), NOT_FOUND_TEXT)
