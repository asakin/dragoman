"""Opinionated recommendations: which model fits which shape of task.

Reads the user's actual config so we never recommend a provider they haven't
configured. Returns a model spec + a one-line rationale, or None if nothing
fits — in which case the caller should default to whatever Anthropic-side
model they were already using.

Pure local logic. No network calls.
"""

import re
from dataclasses import dataclass
from typing import Optional

from dragoman import config


@dataclass
class Recommendation:
    model: str          # e.g. "ollama:qwen2.5:14b" or "perplexity:sonar-pro"
    rationale: str      # one-line "why"


# Rules in priority order. First match whose provider is configured wins.
# Each rule: (regex, config_section, default_model, rationale).
_RULES: list[tuple[str, str, Optional[str], str]] = [
    (
        r"\b(local(?:ly)?|private(?:ly)?|offline|on[- ]?prem|"
        r"stays? on (my|this)|don'?t send|confidential|sensitive|personal)\b",
        "ollama", None,
        "private — keeps data on your machine",
    ),
    (
        r"\b(latest|recent(?:ly)?|news|today'?s|current(?:ly)?|"
        r"cite|citations?|references?|browse|web|search)\b",
        "perplexity", None,
        "search-augmented + citations",
    ),
    (
        # number near a bulk-noun (allow up to 3 words between, like "200 meeting transcripts")
        r"\b(\d{2,}\b(?:\s+\w+){0,3}\s+(files|notes|documents|transcripts|"
        r"records|items|emails)|all of the|all my|bulk|batch|every single)\b",
        "ollama", None,
        "bulk — many small calls fit a local long-context model",
    ),
    (
        r"\b(refactor|debug|complex code|reason about|prove|theorem|hard math|"
        r"frontier|deeply)\b",
        "openai_compat", None,
        "frontier reasoning",
    ),
]


def recommend(task: str) -> Optional[Recommendation]:
    """Pattern-match a task description against the rules table.

    Returns None if no rule fires, or if the matching rule's provider isn't
    configured.
    """
    cfg = config.load_config()
    text = task.lower()

    for pattern, section, model_override, rationale in _RULES:
        if not re.search(pattern, text):
            continue
        provider_cfg = cfg.get(section)
        if not provider_cfg:
            continue  # provider not configured, skip
        model = (
            model_override
            or provider_cfg.get("default_model")
            or _section_default_model(section)
        )
        if not model:
            continue
        spec = f"{_spec_provider(section)}:{model}"
        return Recommendation(model=spec, rationale=rationale)

    return None


def _section_default_model(section: str) -> Optional[str]:
    return {
        "ollama": "qwen2.5:14b",
        "perplexity": "sonar-pro",
        "openai_compat": None,  # too heterogeneous to guess
    }.get(section)


def _spec_provider(section: str) -> str:
    """Translate config section name -> CLI provider name."""
    return {"openai_compat": "openai-compat"}.get(section, section)
