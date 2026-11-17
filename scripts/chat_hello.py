"""Week 0 step 0.7: minimal local chat page backed by Ollama.

Usage:
    uv run python scripts/chat_hello.py
    then open http://127.0.0.1:8000

Binds to 127.0.0.1 only. Do not expose this to a network: it has no login.
Set OLLAMA_MODEL to use a different model (default: qwen2.5:7b-instruct).
"""

import json
import os
import urllib.error
import urllib.request

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")

app = FastAPI(title="podcast-recall hello")

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Podcast Recall (hello)</title>
<style>
  body { font: 16px system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
  #log div { margin: .5rem 0; white-space: pre-wrap; }
  .you { color: #555; }
  form { display: flex; gap: .5rem; margin-top: 1rem; }
  input { flex: 1; padding: .5rem; }
</style>
<h1>Podcast Recall: hello</h1>
<div id="log"></div>
<form id="f">
  <input id="m" placeholder="Say something" autocomplete="off" autofocus>
  <button>Send</button>
</form>
<script>
const log = document.getElementById("log");
function add(cls, text) {
  const d = document.createElement("div");
  d.className = cls;
  d.textContent = text;  // textContent, never innerHTML
  log.appendChild(d);
}
document.getElementById("f").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("m");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  add("you", "You: " + message);
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await r.json();
    add("bot", r.ok ? data.reply : "Error: " + data.detail);
  } catch (err) {
    add("bot", "Error: " + err);
  }
});
</script>
"""


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    # Sync endpoint: FastAPI runs it in a thread, so a slow model does not block the server.
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": req.message}],
        "stream": False,
    }).encode()
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach Ollama at {OLLAMA_URL} ({exc}). Is the Ollama app running?",
        ) from exc
    return {"reply": data["message"]["content"], "model": MODEL}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
