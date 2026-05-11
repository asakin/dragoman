"""OpenAI-compatible router. Single-shot /chat/completions.

Two flavors:
- ask_perplexity(model, messages)        — host pinned to api.perplexity.ai;
                                            api key from PERPLEXITY_API_KEY
                                            (env, op://, keychain://, or literal in config).
- ask_openai_compat(model, messages)     — host from OPENAI_COMPAT_HOST env or config;
                                            api key (optional) from OPENAI_COMPAT_API_KEY.

Bearer tokens are resolved at call time, used in one HTTPS request, and
discarded. They never enter the calling agent's context.
"""

import json
import sys
import time
import urllib.request
import urllib.error

from dragoman import config

DEFAULT_TIMEOUT_SECONDS = 180


def _ask(
    host: str,
    model: str,
    messages: list[dict],
    api_key: str = "",
    endpoint: str = "/chat/completions",
    stream: bool = False,
) -> tuple[str, dict]:
    """POST to <host><endpoint> with an OpenAI-format chat body.

    Returns (response_text, usage) where usage = {"tokens_in": int, "tokens_out": int}.
    """
    url = f"{host.rstrip('/')}{endpoint}"
    body = {"model": model, "messages": messages, "stream": stream}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
                if stream:
                    text_chunks = []
                    for line in resp:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                if "choices" in chunk and chunk["choices"]:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        print(content, end="", file=sys.stderr, flush=True)
                                        text_chunks.append(content)
                            except json.JSONDecodeError:
                                pass
                    if text_chunks:
                        print(file=sys.stderr, flush=True)
                    text = "".join(text_chunks)
                    return text, {"tokens_in": 0, "tokens_out": 0}
                else:
                    payload = json.loads(resp.read().decode("utf-8"))
            break  # Success
        except urllib.error.HTTPError as e:
            if e.code in (408, 429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
                continue
            
            # Don't echo the bearer back even if the server does.
            body_preview = ""
            try:
                body_preview = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise RuntimeError(
                f"{host} returned HTTP {e.code}: {body_preview or e.reason}"
            ) from None
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise RuntimeError(f"Connection failed to {host}: {e.reason}") from None

    if "choices" not in payload or not payload["choices"]:
        raise RuntimeError(f"openai-compat returned unexpected payload: {payload!r}")

    text = payload["choices"][0]["message"]["content"]
    usage_payload = payload.get("usage") or {}
    usage = {
        "tokens_in": int(usage_payload.get("prompt_tokens", 0) or 0),
        "tokens_out": int(usage_payload.get("completion_tokens", 0) or 0),
    }
    return text, usage


def ask_openai_compat(
    model: str, 
    messages: list[dict], 
    host: str = None,
    api_key_ref: str = None,
    stream: bool = False
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
    
    return _ask(
        host=normalized,
        model=model,
        messages=messages,
        api_key=api_key,
        endpoint="/v1/chat/completions",
        stream=stream,
    )


def ask_gemini(
    model: str, 
    messages: list[dict], 
    api_key_ref: str = None,
    stream: bool = False
) -> tuple[str, dict]:
    from dragoman import secrets
    api_key = secrets.resolve(api_key_ref) if api_key_ref else ""
    if not api_key:
        raise RuntimeError(
            "API key not configured for this Gemini connection. "
            "run `dragoman init`"
        )

    # Convert OpenAI messages to Gemini structure
    contents = []
    system_instruction = None

    for m in messages:
        if m["role"] == "system":
            system_instruction = {"parts": [{"text": m["content"]}]}
        elif m["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif m["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})

    body = {"contents": contents}
    if system_instruction:
        body["systemInstruction"] = system_instruction

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}" if stream else f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
                if stream:
                    text_chunks = []
                    for line in resp:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            try:
                                chunk = json.loads(line[6:])
                                if "candidates" in chunk and chunk["candidates"]:
                                    parts = chunk["candidates"][0]["content"].get("parts", [])
                                    if parts and "text" in parts[0]:
                                        content = parts[0]["text"]
                                        print(content, end="", file=sys.stderr, flush=True)
                                        text_chunks.append(content)
                            except json.JSONDecodeError:
                                pass
                    if text_chunks:
                        print(file=sys.stderr, flush=True)
                    text = "".join(text_chunks)
                    return text, {"tokens_in": 0, "tokens_out": 0}
                else:
                    payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (408, 429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
                continue
            body_preview = ""
            try:
                body_preview = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise RuntimeError(
                f"gemini returned HTTP {e.code}: {body_preview or e.reason}"
            ) from None
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise RuntimeError(f"Connection failed to Gemini: {e.reason}") from None

    if "candidates" not in payload or not payload["candidates"]:
        raise RuntimeError(f"gemini returned unexpected payload: {payload!r}")

    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    usage_payload = payload.get("usageMetadata", {})
    usage = {
        "tokens_in": int(usage_payload.get("promptTokenCount", 0)),
        "tokens_out": int(usage_payload.get("candidatesTokenCount", 0)),
    }
    return text, usage
