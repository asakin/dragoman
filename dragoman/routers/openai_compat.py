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
) -> tuple[str, dict]:
    """POST to <host><endpoint> with an OpenAI-format chat body.

    Returns (response_text, usage) where usage = {"tokens_in": int, "tokens_out": int}.
    """
    url = f"{host.rstrip('/')}{endpoint}"
    body = {"model": model, "messages": messages, "stream": False}

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


def ask_perplexity(model: str, messages: list[dict]) -> tuple[str, dict]:
    api_key = config.get_secret("perplexity", "api_key", "PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PERPLEXITY_API_KEY not set and perplexity.api_key not in config; "
            "run `dragoman init` or set the env var"
        )
    return _ask(
        host="https://api.perplexity.ai",
        model=model,
        messages=messages,
        api_key=api_key,
        endpoint="/chat/completions",
    )


def ask_openai_compat(model: str, messages: list[dict]) -> tuple[str, dict]:
    raw_host = config.get_value("openai_compat", "host", "OPENAI_COMPAT_HOST")
    if not raw_host:
        raise RuntimeError(
            "OPENAI_COMPAT_HOST not set and openai_compat.host not in config; "
            "run `dragoman init` or set the env var"
        )
    normalized = config.normalize_host(raw_host)
    if normalized is None:
        raise RuntimeError(
            f"openai_compat host {raw_host!r} doesn't look like a URL "
            "(expected something like https://api.openai.com); run `dragoman init` to fix"
        )
    if normalized != raw_host:
        print(
            f"🐉 dragoman: openai_compat host {raw_host!r} missing scheme; using {normalized!r}",
            file=sys.stderr,
            flush=True,
        )
    api_key = config.get_secret("openai_compat", "api_key", "OPENAI_COMPAT_API_KEY") or ""
    return _ask(
        host=normalized,
        model=model,
        messages=messages,
        api_key=api_key,
        endpoint="/v1/chat/completions",
    )


def ask_gemini(model: str, messages: list[dict]) -> tuple[str, dict]:
    api_key = config.get_secret("gemini", "api_key", "GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set and gemini.api_key not in config; "
            "run `dragoman init` or set the env var"
        )
    return _ask(
        host="https://generativelanguage.googleapis.com",
        model=model,
        messages=messages,
        api_key=api_key,
        endpoint="/v1beta/openai/chat/completions",
    )
