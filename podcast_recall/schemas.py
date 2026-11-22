"""The typed shape of every function's input and output (decision D19, question 19).

These models are the single source of truth. The JSON schemas under `schemas/` are generated from
them (`python -m podcast_recall.schemas`) and a test checks the files match.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from podcast_recall.answering import AskResult
from podcast_recall.golden import format_time
from podcast_recall.models import SearchHit

MAX_QUESTION = 1000


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION)
    show: str | None = Field(default=None, max_length=200)
    since: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    until: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class CitationModel(BaseModel):
    video_id: str
    episode_id: int
    show: str
    title: str
    quote: str
    start_s: float
    time: str
    url: str


class ClaimModel(BaseModel):
    text: str
    citations: list[CitationModel]


class AnswerModel(BaseModel):
    status: Literal["answered", "not_found", "premise_corrected"]
    claims: list[ClaimModel]
    summary: str = ""


class AskResponse(BaseModel):
    request_id: int | None
    answer: AnswerModel
    dropped: int
    dropped_reasons: list[str]
    note_not_quoted: bool
    warnings: list[str]
    latency_ms: int
    model: str


class FeedbackRequest(BaseModel):
    request_id: int
    thumbs: Literal[1, -1]
    note: str = Field(default="", max_length=500)


class FindingRequest(BaseModel):
    request_id: int
    note: str = Field(default="", max_length=1000)


class IdResponse(BaseModel):
    id: int


class SearchHitModel(BaseModel):
    chunk_id: int
    episode_id: int
    show: str
    title: str
    start_s: float
    end_s: float
    time: str
    text: str
    url: str | None
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHitModel]
    warnings: list[str]


class SegmentModel(BaseModel):
    start_s: float
    time: str
    text: str


class TranscriptWindowResponse(BaseModel):
    episode_id: int
    at_s: float
    window_s: float
    segments: list[SegmentModel]


class HealthResponse(BaseModel):
    ok: bool
    model: str
    indexed_episodes: int


MODELS = {
    "ask_request": AskRequest,
    "ask_response": AskResponse,
    "feedback_request": FeedbackRequest,
    "finding_request": FindingRequest,
    "id_response": IdResponse,
    "search_response": SearchResponse,
    "transcript_window_response": TranscriptWindowResponse,
    "health_response": HealthResponse,
}


def ask_response(result: AskResult) -> AskResponse:
    answer = result.answer
    return AskResponse(
        request_id=result.request_id,
        answer=AnswerModel(
            status=answer.status,
            claims=[
                ClaimModel(
                    text=claim.text,
                    citations=[
                        CitationModel(
                            video_id=c.video_id, episode_id=c.episode_id, show=c.show, title=c.title,
                            quote=c.quote, start_s=c.start_s, time=format_time(c.start_s), url=c.url,
                        )
                        for c in claim.citations
                    ],
                )
                for claim in answer.claims
            ],
            summary=answer.summary,
        ),
        dropped=len(result.dropped),
        dropped_reasons=[d.reason for d in result.dropped],
        note_not_quoted=result.uncited_note,
        warnings=result.warnings,
        latency_ms=result.latency_ms,
        model=result.model,
    )


def hit_model(hit: SearchHit) -> SearchHitModel:
    return SearchHitModel(
        chunk_id=hit.chunk_id, episode_id=hit.episode_id, show=hit.show, title=hit.title,
        start_s=hit.start_s, end_s=hit.end_s, time=format_time(hit.start_s), text=hit.text, url=hit.url,
        score=hit.score,
    )


def schema_texts() -> dict[str, str]:
    """File name -> the JSON text of each schema, in a stable format."""
    return {
        f"{name}.json": json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"
        for name, model in MODELS.items()
    }


def write_schemas(directory: str | Path) -> list[str]:
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    texts = schema_texts()
    for name, text in texts.items():
        (folder / name).write_text(text, encoding="utf-8")
    return sorted(texts)


if __name__ == "__main__":
    print("wrote:", ", ".join(write_schemas(Path(__file__).resolve().parents[1] / "schemas")))
