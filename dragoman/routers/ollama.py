"""Ollama router. Single-shot chat completion via /api/chat.

No streaming, no agent loop, no tool use. The foreign model gets a question
and answers with text. That's the whole contract.
"""

import json
import sys
import urllib.request
from typing import Optional

from dragoman import config

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 180


def ask(
    model: str,
    messages: list[dict],
    host: Optional[str] = None,
) -> tuple[str, dict]:
    """Single-shot chat against Ollama's /api/chat.

    Returns (response_text, usage) where usage = {"tokens_in": int, "tokens_out": int}.
    `host` overrides the configured/env host (used by routing.auto).
    """
    resolved_host = (host or _resolve_host()).rstrip("/")
    payload = _post(
        f"{resolved_host}/api/chat",
        {"model": model, "messages": messages, "stream": False},
    )
    if "message" not in payload or "content" not in payload["message"]:
        raise RuntimeError(f"ollama returned unexpected payload: {payload!r}")
    text = payload["message"]["content"]
    usage = {
        "tokens_in": int(payload.get("prompt_eval_count", 0) or 0),
        "tokens_out": int(payload.get("eval_count", 0) or 0),
    }
    return text, usage


def _resolve_host() -> str:
    raw = config.get_value("ollama", "host", "OLLAMA_HOST") or DEFAULT_HOST
    normalized = config.normalize_host(raw)
    if normalized is None:
        print(
            f"🐉 dragoman: warning · ollama host {raw!r} doesn't look like a URL; "
            f"falling back to {DEFAULT_HOST}",
            file=sys.stderr,
            flush=True,
        )
        return DEFAULT_HOST
    return normalized


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"ollama error: {payload['error']}")

    if not isinstance(payload, dict):
        raise RuntimeError(f"ollama returned non-dict payload: {payload!r}")

    return payload
