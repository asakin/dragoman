"""Interactive setup wizard for dragoman.

Walks through provider configuration and Claude Code agent file installation.
Uses questionary for all interactive prompts.
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

import questionary

from dragoman import __version__, config as cfg_mod, discovery, agent
from datetime import date

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_KEY_PREFIXES = ("op://", "keychain://", "env:")


def _validate_key_ref(value: str) -> bool | str:
    """Questionary validator: only accept secure references, not literal keys."""
    if not value:
        return True  # blank = skip
    if any(value.startswith(p) for p in _VALID_KEY_PREFIXES):
        return True
    return (
        "Dragoman does not store literal API keys. Use one of:\n"
        "  op://vault/item/field\n"
        "  keychain://service/account\n"
        "  env:VAR_NAME"
    )

def _auto_name(host: str) -> str:
    try:
        parsed = urlparse(host if "://" in host else f"http://{host}")
        domain = (parsed.hostname or "").lower()
        for prefix in ("api.", "www."):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        return domain.split(".")[0] if "." in domain else domain or "custom"
    except Exception:
        return "custom"


def _unique_name(base: str, existing: set) -> str:
    name, n = base, 1
    while name in existing:
        n += 1
        name = f"{base}_{n}"
    return name


def _normalize_host(host: str) -> str | None:
    return cfg_mod.normalize_host(host)


# ---------------------------------------------------------------------------
# Provider setup flows
# ---------------------------------------------------------------------------

_PROVIDERS = [
    {"name": "Anthropic",                    "type": "anthropic",     "host": "https://api.anthropic.com",  "needs_host": False, "needs_key": True},
    {"name": "OpenAI",                       "type": "openai_compat", "host": "https://api.openai.com/v1", "needs_host": False, "needs_key": True},
    {"name": "OpenAI-compatible (Groq, Together, LM Studio, ...)", "type": "openai_compat", "host": None,  "needs_host": True,  "needs_key": True},
    {"name": "Google Gemini",                "type": "gemini",        "host": None,                         "needs_host": False, "needs_key": True},
    {"name": "Perplexity",                   "type": "openai_compat", "host": "https://api.perplexity.ai",  "needs_host": False, "needs_key": True},
    {"name": "Ollama local [localhost:11434]","type": "openai_compat", "host": "http://localhost:11434/v1",  "needs_host": False, "needs_key": False},
]


def _setup_provider(prov: dict, existing_names: set) -> tuple[str, dict, list[dict]] | None:
    """Run the setup flow for one provider. Returns (conn_name, block, approved_models) or None."""
    print(f"\n--- {prov['name']} ---")

    # Host
    host = prov["host"]
    if prov["needs_host"]:
        raw = questionary.text("Endpoint URL:").ask()
        if not raw:
            return None
        host = _normalize_host(raw)
        if host is None:
            print(f"  {raw!r} doesn't look like a URL. Skipping.")
            return None

    # API key
    api_key = None
    if prov["needs_key"]:
        api_key = questionary.text(
            "API key reference (op://, keychain://, or env:):",
            validate=_validate_key_ref,
        ).ask()
        if api_key is None:  # user cancelled
            return None
        api_key = api_key.strip() or None

    # Connection name
    if "Ollama" in prov["name"]:
        base = "ollama"
    else:
        base = _auto_name(host) if host else prov["name"].split()[0].lower()
    default = _unique_name(base, existing_names)
    conn_name = questionary.text(
        f"Connection handle (used as handle:model_id) [{default}]:"
    ).ask()
    conn_name = (conn_name or "").strip() or default

    # Build config block
    block: dict = {"type": prov["type"]}
    if host:
        block["host"] = host
    if api_key:
        block["api_key"] = api_key

    # Discover models
    print(f"  Discovering live models for {conn_name}...")
    if prov["type"] == "gemini":
        raw_models = discovery.discover_gemini(api_key)
    elif prov["type"] == "anthropic":
        raw_models = discovery.discover_anthropic(api_key)
    else:
        raw_models = discovery.discover_openai_compat(host, api_key)

    approved = _select_models(conn_name, raw_models)
    if approved:
        for m in approved:
            m["connection"] = conn_name
        block["approved_models"] = [m["model_id"] for m in approved]

    return conn_name, block, approved


def _select_models(conn_name: str, raw_models: list[str]) -> list[dict]:
    """Approve all discovered models automatically without prompting."""
    cat_approved, cat_rejected, unknowns = discovery.map_discovered_models(conn_name, raw_models)

    if not cat_approved and not cat_rejected and not unknowns:
        print(f"  No models discovered from {conn_name}.")
        return []

    selected = []
    selected.extend(cat_approved)
    selected.extend(cat_rejected)
    for uid in unknowns:
        selected.append({
            "model_id": uid,
            "provider": conn_name,
            "strengths": "Unknown model",
            "suitable_for": "general",
            "context": "?",
            "propose": "yes",
        })

    print(f"  Discovered {len(selected)} models.")
    return selected


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def cmd_init() -> int:
    """Interactive setup: provider config + Claude Code agent installation."""
    print(f"🐉 dragoman init\n")
    print("Dragoman helps Claude Code and background agents use models from other providers.")
    print("This setup will create a local config for the providers you want to connect.")
    print(f"Config: {cfg_mod.CONFIG_FILE}\n")
    print("API keys are never stored directly. Use one of:")
    print("  keychain://service/account     macOS Keychain")
    print("  op://vault/item/field          1Password CLI")
    print("  env:VAR_NAME                   environment variable\n")

    cfg = cfg_mod.load_config()
    providers = cfg.setdefault("providers", {})
    all_approved: list[dict] = []

    while True:
        provider_names = [p["name"] for p in _PROVIDERS] + ["Done — finish setup"]
        choice = questionary.select(
            "Connect a provider:",
            choices=provider_names,
        ).ask()

        if choice is None or choice.startswith("Done"):
            break

        prov = next(p for p in _PROVIDERS if p["name"] == choice)
        result = _setup_provider(prov, set(providers.keys()))
        if result:
            conn_name, block, approved = result
            providers[conn_name] = block
            all_approved.extend(approved)
            print(f"  ✓ {conn_name} configured.\n")

    # Save config
    cfg_mod.save_config(cfg)
    print(f"\nConfig saved to {cfg_mod.CONFIG_FILE}")

    # Agent file installation
    print("\n--- Claude Code Agent ---")
    print("Dragoman installs a Claude Code sub-agent file so Claude knows how to use it.")
    target_choice = questionary.select(
        "Which .claude directory should the Dragoman agent be installed in?",
        choices=[
            "Global (~/.claude) — all Claude Code sessions",
            "Project (./.claude) — this project only",
            "Skip — I'll handle it manually",
        ],
        default="Global (~/.claude) — all Claude Code sessions",
    ).ask()

    if target_choice and "Global" in target_choice:
        claude_dir = Path.home() / ".claude"
        results = agent.install(claude_dir)
        _generate_configured_models(claude_dir, providers)
        results["agent-memory/dragoman/configured-models.md"] = "generated"
        for rel_path, status in results.items():
            print(f"  → {status} {claude_dir / rel_path}")
    elif target_choice and "Project" in target_choice:
        claude_dir = Path.cwd() / ".claude"
        results = agent.install(claude_dir)
        _generate_configured_models(claude_dir, providers)
        results["agent-memory/dragoman/configured-models.md"] = "generated"
        for rel_path, status in results.items():
            print(f"  → {status} {claude_dir / rel_path}")
    else:
        print(f"  Agent templates: {agent.templates_dir()}")

    print("\nSetup complete! Dragoman is ready.")
    return 0


def _generate_configured_models(claude_dir: Path, providers: dict) -> None:
    """Generate the configured-models.md file based on all known providers."""
    content = [
        "# Configured models",
        "",
        "This file is generated by the Dragoman install script from the API connections you've authorized in your keychain. Dragoman reads this to know what he can actually call. It does not get edited by Dragoman — if you add or remove a configured connection, re-run the install script.",
        "",
        f"Last updated: {date.today().isoformat()}",
        "",
        "## Connections"
    ]

    for conn, block in providers.items():
        # Heuristic for local vs remote
        loc_type = "local" if "localhost" in conn or conn == "ollama" else "remote"
        content.append("")
        content.append(f"### {conn} ({loc_type})")
        
        models = block.get("approved_models", [])
        if not models:
            content.append("- *(no models configured)*")
            continue
            
        for model in sorted(set(models)):
            content.append(f"- `{model}`")

    target = claude_dir / "agent-memory" / "dragoman" / "configured-models.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(content) + "\n")
