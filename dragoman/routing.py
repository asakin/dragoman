"""Model-spec parsing and `auto:` routing.

A model spec is `provider:name`. Provider is one of:
    ollama, perplexity, openai-compat, auto

`auto:<name>` resolves to the best available Ollama host based on a fast TCP
probe. The basement (config[ollama][host]) is tried first; the laptop
(config[ollama][fallback_host]) is the fallback. This is the only place
dragoman makes its own routing decision — the persona doesn't need to know
your network state, and Claude doesn't either.
"""

import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from dragoman import config


@dataclass
class ResolvedModel:
    provider: str                       # "ollama" | "perplexity" | "openai-compat"
    model: str                          # e.g. "qwen2.5:14b"
    host_override: Optional[str] = None # set when auto: picks a specific host


def parse(model_spec: str) -> tuple[str, str]:
    """Parse 'provider:name' into (provider, name)."""
    if ":" not in model_spec:
        raise ValueError(
            f"model spec must be 'provider:name' (e.g. ollama:qwen2.5:14b); got {model_spec!r}"
        )
    provider, name = model_spec.split(":", 1)
    return provider, name


def resolve(model_spec: str) -> ResolvedModel:
    """Resolve a model spec to a concrete (provider, model, host_override).

    For auto:<name>, probes basement Ollama, falls back to laptop Ollama.
    """
    provider, name = parse(model_spec)
    if provider != "auto":
        return ResolvedModel(provider=provider, model=name)

    primary = _normalize(config.get_value("ollama", "host", "OLLAMA_HOST"))
    fallback = _normalize(config.get_value("ollama", "fallback_host"))

    if primary and _reachable(primary):
        return ResolvedModel(provider="ollama", model=name, host_override=primary)
    if fallback and _reachable(fallback):
        return ResolvedModel(provider="ollama", model=name, host_override=fallback)
    if primary or fallback:
        raise RuntimeError(
            f"auto:{name}: neither primary host ({primary!r}) "
            f"nor fallback ({fallback!r}) responded to a TCP probe"
        )
    raise RuntimeError(
        "auto:<model> needs [ollama] host (and optionally fallback_host) "
        "in ~/.config/dragoman/config.toml; run `dragoman init`"
    )


def _normalize(host: Optional[str]) -> Optional[str]:
    """Normalize host strings (e.g. add scheme) before storing as host_override."""
    if not host:
        return None
    return config.normalize_host(host)


def _reachable(url: str, timeout: float = 2.0) -> bool:
    """Fast TCP probe — no HTTP round-trip, sub-second."""
    candidate = url if "://" in url else f"http://{url}"
    parsed = urlparse(candidate)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False
