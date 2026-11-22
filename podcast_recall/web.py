"""The local web chat: a small FastAPI app that only listens on this computer (decision D19).

There is no login, so the app protects itself from other web pages open in the same browser:
- the Host header must be this computer's own address and port (blocks DNS rebinding),
- a request that carries an Origin header must come from this same address (blocks other sites),
- every /api call must carry the per-run token, which only the served page knows.
All transcript text is shown as text by the page, never as HTML, and links are built only from
validated video IDs. Nothing here is meant to be reachable from a network.
"""

from __future__ import annotations

import hmac
import logging
import secrets
import threading
from importlib import resources

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from podcast_recall import core, embeddings, llm, paths, retrieval, schemas
from podcast_recall.answering import AnswerServices
from podcast_recall.errors import ApiError, ConfigError, NotSignedIn, PodcastRecallError
from podcast_recall.golden import format_time

log = logging.getLogger(__name__)

TOKEN_HEADER = "x-recall-token"
MAX_WINDOW_S = 120.0  # the transcript endpoint serves a short window, never a whole transcript
MAX_SEARCH_LIMIT = 20
_TOKEN_MARK = "__RECALL_TOKEN__"


def _json_error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"detail": message}, status_code=status)


class LocalOnly:
    """Refuse any request that does not come from this computer's own page (a pure ASGI layer, so it
    runs before routing and covers every path)."""

    def __init__(self, app, port: int, token: str) -> None:
        self.app = app
        self.hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        self.token = token

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        problem = None
        if headers.get("host", "") not in self.hosts:
            problem = "This address is not allowed."
        elif "origin" in headers and headers["origin"] not in self.origins:
            problem = "Requests from other sites are not allowed."
        elif scope["path"].startswith("/api/") and not hmac.compare_digest(
            headers.get(TOKEN_HEADER, ""), self.token
        ):
            problem = "A valid token is required. Reload the page."
        if problem:
            await _json_error(403, problem)(scope, receive, send)
            return
        await self.app(scope, receive, send)


def page_html(token: str) -> str:
    html = (resources.files("podcast_recall") / "static" / "index.html").read_text(encoding="utf-8")
    return html.replace(_TOKEN_MARK, token)


def create_app(
    user_id: str = core.OWNER,
    port: int = 8000,
    services: AnswerServices | None = None,
    token: str | None = None,
    video_ids=None,
) -> LocalOnly:
    token = token or secrets.token_urlsafe(24)
    services = services or AnswerServices()
    model_lock = threading.Lock()  # one model call at a time
    app = FastAPI(title="Podcast Recall", docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(NotSignedIn)
    async def _not_signed_in(request: Request, exc: NotSignedIn):
        return _json_error(401, str(exc))

    @app.exception_handler(llm.ModelUnavailable)
    async def _model_unavailable(request: Request, exc: llm.ModelUnavailable):
        return _json_error(503, str(exc))

    @app.exception_handler(embeddings.EmbeddingUnavailable)
    async def _embedding_unavailable(request: Request, exc: embeddings.EmbeddingUnavailable):
        return _json_error(503, str(exc))

    @app.exception_handler(ConfigError)
    async def _config_error(request: Request, exc: ConfigError):
        return _json_error(400, str(exc))

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return _json_error(502, str(exc))

    @app.exception_handler(PodcastRecallError)
    async def _other_known(request: Request, exc: PodcastRecallError):
        return _json_error(400, str(exc))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.error("unexpected error in the web app: %s", type(exc).__name__)  # the type only, no text
        return _json_error(500, "Something went wrong. Check the terminal where `serve` is running.")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return page_html(token)

    @app.get("/api/health", response_model=schemas.HealthResponse)
    def health():
        conn = core.open_db()
        try:
            indexed = conn.execute("SELECT COUNT(*) FROM index_state").fetchone()[0]
        finally:
            conn.close()
        return schemas.HealthResponse(ok=True, model=paths.answer_model(), indexed_episodes=indexed)

    @app.post("/api/ask", response_model=schemas.AskResponse)
    def ask(body: schemas.AskRequest):
        with model_lock:
            result = core.ask(
                body.question, user_id, show=body.show, since=body.since, until=body.until,
                video_ids=video_ids, services=services,
            )
        return schemas.ask_response(result)

    @app.get("/api/search", response_model=schemas.SearchResponse)
    def search(
        q: str = Query(min_length=1, max_length=schemas.MAX_QUESTION),
        show: str | None = Query(default=None, max_length=200),
        since: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        until: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        limit: int = Query(default=8, ge=1, le=MAX_SEARCH_LIMIT),
    ):
        result = core.search_episodes(
            q, user_id, show=show, since=since, until=until, limit=limit, video_ids=video_ids,
            services=services.index,
        )
        return schemas.SearchResponse(
            hits=[schemas.hit_model(h) for h in result.hits], warnings=result.warnings
        )

    @app.get("/api/transcript/{episode_id}", response_model=schemas.TranscriptWindowResponse)
    def transcript_window(
        episode_id: int,
        at: float = Query(ge=0),
        window: float = Query(default=30.0, gt=0, le=MAX_WINDOW_S),
    ):
        conn = core.open_db()
        try:
            if episode_id not in set(retrieval.library_episode_ids(conn, user_id, video_ids)):
                return _json_error(404, "That episode is not in your library.")
        finally:
            conn.close()
        shown = core.show_transcript(episode_id, at, window)
        return schemas.TranscriptWindowResponse(
            episode_id=episode_id, at_s=at, window_s=window,
            segments=[
                schemas.SegmentModel(start_s=start, time=format_time(start), text=text)
                for start, _end, text in shown.text_before_and_after
            ],
        )

    @app.post("/api/feedback", response_model=schemas.IdResponse)
    def feedback(body: schemas.FeedbackRequest):
        return schemas.IdResponse(id=core.record_feedback(body.request_id, body.thumbs, body.note, user_id))

    @app.post("/api/findings", response_model=schemas.IdResponse)
    def findings(body: schemas.FindingRequest):
        return schemas.IdResponse(id=core.save_finding(body.request_id, body.note, user_id))

    return LocalOnly(app, port, token)

