"""Provider HTTP backends.

Three providers, one shared retry/streaming skeleton:
- ask_openai_compat — OpenAI-compatible /chat/completions
- ask_gemini        — Google Generative Language API
- ask_anthropic     — Anthropic /v1/messages

Each ask_* function builds its provider-specific URL, headers, and body,
then hands off to `_post_with_retry` along with two small extractors that
know how to pull text out of (a) one streaming SSE chunk and (b) the final
JSON payload. The retry loop, error mapping, and SSE plumbing live in one
place.

Bearer tokens are resolved at call time, used in one HTTPS request, and
discarded. They never enter the calling agent's context.
"""

import json
import sys
import time
import urllib.request
import urllib.error
from typing import Callable, Optional

from dragoman import config

DEFAULT_TIMEOUT_SECONDS = 180
_RETRY_STATUS = (408, 429, 500, 502, 503, 504)
_MAX_RETRIES = 3
_BASE_DELAY = 2.0


# ---------------------------------------------------------------------------
# Shared retry + SSE skeleton
# ---------------------------------------------------------------------------

def _post_with_retry(
    url: str,
    body: dict,
    headers: dict,
    *,
    stream: bool,
    extract_stream_text: Callable[[str], Optional[str]],
    extract_final: Callable[[dict], tuple[str, dict]],
    http_error_origin: str,
    connection_origin: str,
) -> tuple[str, dict]:
    """POST JSON, retry transient failures, return (text, usage).

    extract_stream_text: takes the payload after `data: ` is stripped from one
        SSE line and returns the text fragment to emit, or None to skip.
    extract_final: takes the parsed non-stream JSON payload and returns
        (text, usage).
    http_error_origin / connection_origin: labels used in error messages.
    """
    for attempt in range(_MAX_RETRIES + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
                if stream:
                    return _consume_sse(resp, extract_stream_text)
                payload = json.loads(resp.read().decode("utf-8"))
                return extract_final(payload)
        except urllib.error.HTTPError as e:
            if e.code in _RETRY_STATUS and attempt < _MAX_RETRIES:
                time.sleep(_BASE_DELAY * (2 ** attempt))
                continue
            body_preview = ""
            try:
                body_preview = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise RuntimeError(
                f"{http_error_origin} returned HTTP {e.code}: {body_preview or e.reason}"
            ) from None
        except urllib.error.URLError as e:
            if attempt < _MAX_RETRIES:
                time.sleep(_BASE_DELAY * (2 ** attempt))
                continue
            raise RuntimeError(
                f"Connection failed to {connection_origin}: {e.reason}"
            ) from None

    # Loop exits only via return or raise above; this satisfies type-checkers.
    raise RuntimeError("retry loop exited without producing a result")


def _consume_sse(resp, extract_stream_text) -> tuple[str, dict]:
    text_chunks: list[str] = []
    for line in resp:
        line = line.decode("utf-8").strip()
        if not line.startswith("data: "):
            continue
        sse_data = line[6:]
        try:
            text = extract_stream_text(sse_data)
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
        if text:
            print(text, end="", file=sys.stderr, flush=True)
            text_chunks.append(text)
    if text_chunks:
        print(file=sys.stderr, flush=True)
    return "".join(text_chunks), {"tokens_in": 0, "tokens_out": 0}


# ---------------------------------------------------------------------------
# OpenAI-compatible
# ---------------------------------------------------------------------------

def _openai_stream_extract(sse_data: str) -> Optional[str]:
    if sse_data == "[DONE]":
        return None
    chunk = json.loads(sse_data)
    if "choices" in chunk and chunk["choices"]:
        return chunk["choices"][0].get("delta", {}).get("content", "") or None
    return None


def _openai_extract_final(payload: dict) -> tuple[str, dict]:
    if "choices" not in payload or not payload["choices"]:
        raise RuntimeError(f"openai-compat returned unexpected payload: {payload!r}")
    text = payload["choices"][0]["message"]["content"]
    usage_payload = payload.get("usage") or {}
    return text, {
        "tokens_in": int(usage_payload.get("prompt_tokens", 0) or 0),
        "tokens_out": int(usage_payload.get("completion_tokens", 0) or 0),
    }


def ask_openai_compat(
    model: str,
    messages: list[dict],
    host: str = None,
    api_key_ref: str = None,
    stream: bool = False,
) -> tuple[str, dict]:
    if not host:
        raise RuntimeError("Host not configured for this connection. Run `dragoman init`.")

    normalized = config.normalize_host(host)
    if normalized is None:
        raise RuntimeError(
            f"Host {host!r} doesn't look like a URL "
            "(expected something like https://api.openai.com); run `dragoman init` to fix"
        )
    if normalized != host:
        print(
            f"🐉 dragoman: host {host!r} missing scheme; using {normalized!r}",
            file=sys.stderr,
            flush=True,
        )

    from dragoman import secrets
    api_key = secrets.resolve(api_key_ref) if api_key_ref else ""

    # The stored host is the full base URL up to (but not including) /chat/completions.
    # Vendors that use a version path (OpenAI, LiteLLM proxies, Ollama-via-LiteLLM, ...)
    # bake `/v1` into their host. Vendors that don't (Perplexity) leave it out.
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return _post_with_retry(
        url=f"{normalized.rstrip('/')}/chat/completions",
        body={"model": model, "messages": messages, "stream": stream},
        headers=headers,
        stream=stream,
        extract_stream_text=_openai_stream_extract,
        extract_final=_openai_extract_final,
        http_error_origin=normalized,
        connection_origin=normalized,
    )


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

def _gemini_stream_extract(sse_data: str) -> Optional[str]:
    chunk = json.loads(sse_data)
    if "candidates" in chunk and chunk["candidates"]:
        parts = chunk["candidates"][0]["content"].get("parts", [])
        if parts and "text" in parts[0]:
            return parts[0]["text"]
    return None


def _gemini_extract_final(payload: dict) -> tuple[str, dict]:
    if "candidates" not in payload or not payload["candidates"]:
        raise RuntimeError(f"gemini returned unexpected payload: {payload!r}")
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    usage_payload = payload.get("usageMetadata", {})
    return text, {
        "tokens_in": int(usage_payload.get("promptTokenCount", 0)),
        "tokens_out": int(usage_payload.get("candidatesTokenCount", 0)),
    }


def ask_gemini(
    model: str,
    messages: list[dict],
    api_key_ref: str = None,
    stream: bool = False,
) -> tuple[str, dict]:
    from dragoman import secrets
    api_key = secrets.resolve(api_key_ref) if api_key_ref else ""
    if not api_key:
        raise RuntimeError(
            "API key not configured for this Gemini connection. "
            "run `dragoman init`"
        )

    contents = []
    system_instruction = None
    for m in messages:
        if m["role"] == "system":
            system_instruction = {"parts": [{"text": m["content"]}]}
        elif m["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif m["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})

    body: dict = {"contents": contents}
    if system_instruction:
        body["systemInstruction"] = system_instruction

    base = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
    if stream:
        url = f"{base}:streamGenerateContent?alt=sse&key={api_key}"
    else:
        url = f"{base}:generateContent?key={api_key}"

    return _post_with_retry(
        url=url,
        body=body,
        headers={"Content-Type": "application/json"},
        stream=stream,
        extract_stream_text=_gemini_stream_extract,
        extract_final=_gemini_extract_final,
        http_error_origin="gemini",
        connection_origin="Gemini",
    )


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

def _anthropic_stream_extract(sse_data: str) -> Optional[str]:
    chunk = json.loads(sse_data)
    if chunk.get("type") == "content_block_delta":
        return chunk["delta"].get("text", "") or None
    return None


def _anthropic_extract_final(payload: dict) -> tuple[str, dict]:
    if "content" not in payload or not payload["content"]:
        raise RuntimeError(f"anthropic returned unexpected payload: {payload!r}")
    text = "".join(c["text"] for c in payload["content"] if c["type"] == "text")
    usage_payload = payload.get("usage", {})
    return text, {
        "tokens_in": int(usage_payload.get("input_tokens", 0)),
        "tokens_out": int(usage_payload.get("output_tokens", 0)),
    }


def ask_anthropic(
    model: str,
    messages: list[dict],
    api_key_ref: str = None,
    stream: bool = False,
) -> tuple[str, dict]:
    from dragoman import secrets
    api_key = secrets.resolve(api_key_ref) if api_key_ref else ""
    if not api_key:
        raise RuntimeError(
            "API key not configured for this Anthropic connection. "
            "run `dragoman init`"
        )

    system_text = ""
    anthropic_messages = []
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        else:
            anthropic_messages.append({"role": m["role"], "content": m["content"]})

    body: dict = {
        "model": model,
        "max_tokens": 8192,
        "messages": anthropic_messages,
        "stream": stream,
    }
    if system_text:
        body["system"] = system_text.strip()

    return _post_with_retry(
        url="https://api.anthropic.com/v1/messages",
        body=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        stream=stream,
        extract_stream_text=_anthropic_stream_extract,
        extract_final=_anthropic_extract_final,
        http_error_origin="anthropic",
        connection_origin="Anthropic",
    )
