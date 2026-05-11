"""Model-spec parsing and dynamic routing.

A model spec is `connection:name`. For example: `groq_1:llama-3`.
The connection defines the internal router type (`openai_compat` or `gemini`) 
and contains the specific host and api keys needed to reach the provider.
"""

from dataclasses import dataclass
from typing import Optional

from dragoman import config


@dataclass
class ResolvedModel:
    connection: str
    model: str
    type: str                           # "openai_compat" or "gemini"
    host: Optional[str] = None
    api_key_ref: Optional[str] = None


def parse(model_spec: str, known_connections: list[str] | None = None) -> tuple[str, str]:
    """Parse 'connection:name' into (connection, name).

    When ``known_connections`` is supplied the parser tries each connection name
    (longest first) as a prefix so that connection names that themselves contain
    colons (e.g. ``localhost:11434``) are resolved correctly.
    """
    if ":" not in model_spec:
        raise ValueError(
            f"model spec must be 'connection:name' (e.g. groq_1:llama3); got {model_spec!r}"
        )

    if known_connections:
        # Try longest connection name first to avoid prefix collisions.
        for conn in sorted(known_connections, key=len, reverse=True):
            prefix = conn + ":"
            if model_spec.startswith(prefix):
                return conn, model_spec[len(prefix):]

    connection, name = model_spec.split(":", 1)
    return connection, name


def resolve(model_spec: str) -> ResolvedModel:
    """Resolve a model spec by looking up its connection in the config."""
    cfg = config.load_config()
    providers = cfg.get("providers", {})

    connection, name = parse(model_spec, known_connections=list(providers.keys()))

    if connection not in providers:
        raise RuntimeError(
            f"Connection {connection!r} not found in config. Run `dragoman init`."
        )
        
    block = providers[connection]
    
    return ResolvedModel(
        connection=connection,
        model=name,
        type=block.get("type", "openai_compat"),
        host=block.get("host"),
        api_key_ref=block.get("api_key")
    )
