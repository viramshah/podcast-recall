"""Talk to the local answering model through Ollama's chat endpoint, on this Mac only.

The reply is forced into a JSON schema (Ollama's `format`), so the model cannot answer in free
text. The only address this module talks to is Ollama on a loopback address (decision D19).
"""

from __future__ import annotations

import json
import time
import urllib.error
from collections.abc import Callable
from dataclasses import dataclass

from podcast_recall import embeddings, paths
from podcast_recall.errors import ApiError, ConfigError

NUM_CTX = 8192  # Ollama's default window is smaller; eight passages need about 3,500 tokens
MAX_NEW_TOKENS = 700
SEED = 7
ATTEMPTS = 2  # one retry for a temporary failure
RETRY_WAIT_S = 2.0

Post = Callable[[str, dict, float], dict]


class ModelUnavailable(ConfigError):
    """Ollama is not running, or the answering model is not installed."""


class InvalidModelOutput(ApiError):
    """The model returned text that is not valid JSON."""


@dataclass
class ChatReply:
    data: dict
    prompt_tokens: int | None
    completion_tokens: int | None
    seconds: float


class OllamaChat:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        *,
        timeout_s: float | None = None,
        post: Post = embeddings._http_post,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_url = embeddings.check_loopback(base_url or paths.ollama_url())
        self.model = model or paths.answer_model()
        self.timeout_s = timeout_s if timeout_s is not None else paths.answer_timeout_s()
        self._post = post
        self._sleep = sleep
        self._clock = clock

    def chat_json(self, system: str, user: str, schema: dict) -> ChatReply:
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": 0,
                "seed": SEED,
                "num_ctx": NUM_CTX,
                "num_predict": MAX_NEW_TOKENS,
            },
        }
        started = self._clock()
        last: Exception | None = None
        for attempt in range(ATTEMPTS):
            try:
                reply = self._post(f"{self.base_url}/api/chat", payload, self.timeout_s)
                content = (reply.get("message") or {}).get("content")
                if not isinstance(content, str):
                    raise ApiError("Ollama gave an unexpected answer to the chat request")
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise ModelUnavailable(
                        f"The answering model '{self.model}' is not installed. "
                        f"Run: ollama pull {self.model}"
                    ) from None
                last = exc
            except urllib.error.URLError as exc:
                raise ModelUnavailable(
                    f"Could not reach Ollama at {self.base_url}. Start it (open the Ollama app or "
                    "run `ollama serve`) and try again."
                ) from exc
            except (TimeoutError, ConnectionError, ValueError, ApiError) as exc:
                last = exc
            if attempt < ATTEMPTS - 1:
                self._sleep(RETRY_WAIT_S)
        else:
            raise ApiError(
                f"The answering model did not reply in time ({type(last).__name__}). "
                "Try again, or set a longer PODCAST_RECALL_ANSWER_TIMEOUT_S."
            )
        try:
            data = json.loads(content)
        except ValueError:
            raise InvalidModelOutput("the model's reply was not valid JSON") from None
        if not isinstance(data, dict):
            raise InvalidModelOutput("the model's reply was not a JSON object")
        return ChatReply(
            data, reply.get("prompt_eval_count"), reply.get("eval_count"), self._clock() - started
        )
