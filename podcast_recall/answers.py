"""The shape of an answer: the contract between the answering code (U6) and the evaluation.

    { "status": "answered" | "not_found" | "premise_corrected",
      "claims": [ { "text": "...",
                    "citations": [ { "video_id", "episode_id", "show", "title",
                                     "quote", "start_s", "url" } ] } ],
      "summary": "optional" }

Answers are read from JSON. A quote is at most 2 sentences and 60 words. Anything structurally wrong raises `AnswerFormatError`, and the
harness counts that answer as failed with the reason `format`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from podcast_recall.errors import ConfigError, PodcastRecallError

STATUSES = ("answered", "not_found", "premise_corrected")
MAX_QUOTE_SENTENCES = 2
MAX_QUOTE_WORDS = 60  # sentence counting means nothing on transcripts without punctuation
LINK_LEAD_S = 10  # links open this many seconds before the quote


class AnswerFormatError(PodcastRecallError):
    """An answer does not have the required shape."""


@dataclass(frozen=True)
class Citation:
    video_id: str
    episode_id: int
    show: str
    title: str
    quote: str
    start_s: float
    url: str


@dataclass(frozen=True)
class Claim:
    text: str
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class Answer:
    status: str
    claims: tuple[Claim, ...] = field(default_factory=tuple)
    summary: str = ""


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def _text(data: dict, key: str, where: str, *, required: bool = True) -> str:
    value = data.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise AnswerFormatError(f"{where}: '{key}' must be text.")
    if required and not value.strip():
        raise AnswerFormatError(f"{where}: '{key}' is required.")
    return value


def parse_citation(data: object, where: str) -> Citation:
    if not isinstance(data, dict):
        raise AnswerFormatError(f"{where}: a citation must be an object.")
    episode_id = data.get("episode_id")
    start_s = data.get("start_s")
    if isinstance(episode_id, bool) or not isinstance(episode_id, int):
        raise AnswerFormatError(f"{where}: 'episode_id' must be a whole number.")
    if isinstance(start_s, bool) or not isinstance(start_s, (int, float)) or start_s < 0:
        raise AnswerFormatError(f"{where}: 'start_s' must be a number of seconds, zero or more.")
    quote = _text(data, "quote", where)
    if sentence_count(quote) > MAX_QUOTE_SENTENCES:
        raise AnswerFormatError(f"{where}: a quote may be at most {MAX_QUOTE_SENTENCES} sentences.")
    if len(quote.split()) > MAX_QUOTE_WORDS:
        raise AnswerFormatError(f"{where}: a quote may be at most {MAX_QUOTE_WORDS} words.")
    return Citation(
        video_id=_text(data, "video_id", where),
        episode_id=episode_id,
        show=_text(data, "show", where, required=False),
        title=_text(data, "title", where, required=False),
        quote=quote.strip(),
        start_s=float(start_s),
        url=_text(data, "url", where, required=False),
    )


def parse_answer(data: object) -> Answer:
    if not isinstance(data, dict):
        raise AnswerFormatError("An answer must be an object.")
    status = data.get("status")
    if status not in STATUSES:
        raise AnswerFormatError(f"'status' must be one of {', '.join(STATUSES)}.")
    raw_claims = data.get("claims", [])
    if not isinstance(raw_claims, list):
        raise AnswerFormatError("'claims' must be a list.")
    claims = []
    for number, raw in enumerate(raw_claims, 1):
        where = f"claim {number}"
        if not isinstance(raw, dict):
            raise AnswerFormatError(f"{where}: a claim must be an object.")
        raw_citations = raw.get("citations", [])
        if not isinstance(raw_citations, list):
            raise AnswerFormatError(f"{where}: 'citations' must be a list.")
        citations = tuple(
            parse_citation(c, f"{where}, citation {n}") for n, c in enumerate(raw_citations, 1)
        )
        claims.append(Claim(_text(raw, "text", where), citations))
    summary = data.get("summary", "")
    if summary is not None and not isinstance(summary, str):
        raise AnswerFormatError("'summary' must be text.")
    return Answer(status, tuple(claims), summary or "")


def citation_to_dict(c: Citation) -> dict:
    return {
        "video_id": c.video_id, "episode_id": c.episode_id, "show": c.show, "title": c.title,
        "quote": c.quote, "start_s": c.start_s, "url": c.url,
    }


def answer_to_dict(a: Answer) -> dict:
    return {
        "status": a.status,
        "claims": [
            {"text": claim.text, "citations": [citation_to_dict(c) for c in claim.citations]}
            for claim in a.claims
        ],
        "summary": a.summary,
    }


def load_answers(path: str | Path) -> dict[str, object]:
    """Read answers from a JSON Lines file: one object per line with an `id` (the golden item's id)
    and the answer's own fields. Returns id -> the raw object (parsed later, so a bad answer fails
    one item, not the whole file)."""
    found: dict[str, object] = {}
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                raise ConfigError(f"{path} line {number} is not valid JSON.") from None
            if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not data["id"]:
                raise ConfigError(f"{path} line {number} needs an 'id'.")
            if data["id"] in found:
                raise ConfigError(f"{path} line {number}: the id '{data['id']}' appears twice.")
            found[data["id"]] = data
    return found


def link_for(video_id: str, start_s: float) -> str:
    """The YouTube link for a quote: opens a few seconds early so the words are not missed."""
    return f"https://youtu.be/{video_id}?t={max(0, int(start_s) - LINK_LEAD_S)}"
