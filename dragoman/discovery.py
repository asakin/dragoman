import urllib.request
import urllib.error
import json
from dragoman import secrets


def _fetch_models(url: str, headers: dict, list_key: str, id_key: str) -> list[str]:
    """GET <url>, parse JSON, pull [m[id_key] for m in body[list_key]].

    Returns [] on any failure (network, auth, malformed JSON, missing keys).
    Discovery is best-effort — `dragoman init` continues even if a provider
    can't enumerate its models.
    """
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return [m[id_key] for m in data.get(list_key, [])]
    except Exception:
        return []


def discover_openai_compat(host: str, api_key: str = None) -> list[str]:
    """Discover models from OpenAI-compatible endpoint."""
    url = f"{host.rstrip('/')}/models"
    if "api.openai.com" in host and "/v1" not in url:
        url = "https://api.openai.com/v1/models"
    headers = {}
    if api_key:
        resolved = secrets.resolve(api_key)
        if resolved:
            headers["Authorization"] = f"Bearer {resolved}"
    return _fetch_models(url, headers, list_key="data", id_key="id")


def discover_gemini(api_key: str = None) -> list[str]:
    """Discover models from Google Generative Language API."""
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    if api_key:
        resolved = secrets.resolve(api_key)
        if resolved:
            url += f"?key={resolved}"
    return _fetch_models(url, {}, list_key="models", id_key="name")


def discover_anthropic(api_key: str = None) -> list[str]:
    """Discover models from Anthropic."""
    url = "https://api.anthropic.com/v1/models"
    headers = {"anthropic-version": "2023-06-01"}
    if api_key:
        resolved = secrets.resolve(api_key)
        if resolved:
            headers["x-api-key"] = resolved
    return _fetch_models(url, headers, list_key="data", id_key="id")



