"""Turn text into vectors with Ollama's embedding model, on this Mac only.

The only network address this module talks to is Ollama on a loopback address (decision D17,
question 22). Documents and queries get the prefixes that `nomic-embed-text` expects.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence

from podcast_recall import paths
from podcast_recall.errors import ApiError, ConfigError

BATCH_SIZE = 16
TIMEOUT_S = 60
ATTEMPTS = 3
RETRY_WAIT_S = (1.0, 3.0)
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

Post = Callable[[str, dict, float], dict]


class EmbeddingUnavailable(ConfigError):
    """Ollama is not running, or the model has not been pulled. Stops the whole run."""


def check_loopback(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or host not in LOOPBACK_HOSTS:
        raise ConfigError(
            "PODCAST_RECALL_OLLAMA_URL must point to this computer (127.0.0.1 or localhost)."
        )
    return url.rstrip("/")


def _http_post(url: str, payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class OllamaEmbedder:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        *,
        post: Post = _http_post,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = check_loopback(base_url or paths.ollama_url())
        self.model = model or paths.embed_model()
        self._post = post
        self._sleep = sleep

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        payload = {"model": self.model, "input": inputs}
        last: Exception | None = None
        for attempt in range(ATTEMPTS):
            try:
                reply = self._post(f"{self.base_url}/api/embed", payload, TIMEOUT_S)
                vectors = reply.get("embeddings")
                if not isinstance(vectors, list) or len(vectors) != len(inputs):
                    raise ApiError("Ollama gave an unexpected answer to the embedding request")
                return vectors
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise EmbeddingUnavailable(
                        f"The embedding model '{self.model}' is not installed. "
                        f"Run: ollama pull {self.model}"
                    ) from None
                last = exc
            except urllib.error.URLError as exc:
                raise EmbeddingUnavailable(
                    "Could not reach Ollama at "
                    f"{self.base_url}. Start it (open the Ollama app or run `ollama serve`) and try again."
                ) from exc
            except (TimeoutError, ConnectionError, ValueError, ApiError) as exc:
                last = exc
            if attempt < ATTEMPTS - 1:
                self._sleep(RETRY_WAIT_S[min(attempt, len(RETRY_WAIT_S) - 1)])
        raise ApiError(f"Ollama could not embed the text after {ATTEMPTS} tries ({type(last).__name__})")

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        items = [DOCUMENT_PREFIX + t for t in texts]
        for start in range(0, len(items), BATCH_SIZE):
            vectors.extend(self._embed(items[start:start + BATCH_SIZE]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([QUERY_PREFIX + text])[0]
