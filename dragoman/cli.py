"""Command-line interface for dragoman.

Verbs:
    ask         — one HTTPS call to a foreign model; print response.
    recommend   — print a model spec for a task description.
    models      — list configured models.
    init        — interactive setup (provider keys + persona injection).
    uninstall   — remove the persona block from CLAUDE.md (and optionally config).
    (no args)   — print status.

No agent loop. No tool execution. No bash. Dragoman holds keys (or references
to them) and makes one HTTPS call per `ask` invocation. Everything else
happens in the calling Claude Code subagent through the harness's normal tools.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from dragoman import __version__


# ---------- ask ----------

def cmd_ask(args: argparse.Namespace) -> int:
    """One HTTPS call to a foreign model. Print response to stdout."""
    from dragoman import routing
    from dragoman.routers import ollama, openai_compat

    try:
        resolved = routing.resolve(args.model)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    messages: list[dict] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.prompt})

    try:
        if resolved.provider == "ollama":
            text, usage = ollama.ask(resolved.model, messages, host=resolved.host_override)
        elif resolved.provider == "perplexity":
            text, usage = openai_compat.ask_perplexity(resolved.model, messages)
        elif resolved.provider == "gemini":
            text, usage = openai_compat.ask_gemini(resolved.model, messages)
        elif resolved.provider == "openai-compat":
            text, usage = openai_compat.ask_openai_compat(resolved.model, messages)
        else:
            print(
                f"error: unknown provider {resolved.provider!r}; "
                "supported: ollama, perplexity, gemini, openai-compat, auto",
                file=sys.stderr,
            )
            return 2
    except Exception as e:
        print(f"error: {resolved.provider} request failed: {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        host_note = f" via {resolved.host_override}" if resolved.host_override else ""
        print(
            f"🐉 dragoman: {resolved.provider}:{resolved.model}{host_note} · "
            f"{usage.get('tokens_in', 0)} in / {usage.get('tokens_out', 0)} out",
            file=sys.stderr,
            flush=True,
        )
    print(text)
    return 0


# ---------- recommend ----------

def cmd_recommend(args: argparse.Namespace) -> int:
    """Print a model recommendation for a task description.

    stdout: the model spec (easy to pipe into `dragoman ask --model "$(...)"`).
    stderr: 🐉 line with the rationale.
    Exit 0 on match, 0 on no-match (with a hint), non-zero only on error.
    """
    from dragoman import recommend as rec_mod

    try:
        rec = rec_mod.recommend(args.task)
    except Exception as e:
        print(f"error: recommend failed: {e}", file=sys.stderr)
        return 1

    if rec is None:
        print(
            "🐉 dragoman: no specific recommendation — Sonnet is probably fine",
            file=sys.stderr,
        )
        return 0
    print(f"🐉 dragoman: {rec.model} — {rec.rationale}", file=sys.stderr)
    print(rec.model)
    return 0


# ---------- models ----------

def cmd_models(args: argparse.Namespace) -> int:
    """List configured models, one per line, on stdout."""
    from dragoman import config as cfg_mod

    cfg = cfg_mod.load_config()
    if not cfg:
        print("(no providers configured — run `dragoman init`)", file=sys.stderr)
        return 0

    lines: list[str] = []
    for section, settings in cfg.items():
        provider = "openai-compat" if section == "openai_compat" else section
        default_model = settings.get("default_model")
        if default_model:
            lines.append(f"{provider}:{default_model}")
        else:
            # OpenAI-compat doesn't have a single sane default — note the host.
            host = settings.get("host", "(host unset)")
            lines.append(f"{provider}:<model>  # endpoint: {host}")

    for line in lines:
        print(line)
    return 0


# ---------- persona inject / remove ----------

PERSONA_START_MARKER = "<!-- dragoman persona — managed by `dragoman init`, do not edit directly -->"
PERSONA_END_MARKER = "<!-- /dragoman persona -->"


def _persona_template_path() -> Path:
    return Path(__file__).parent / "templates" / "persona.claude.md"


def _persona_block() -> str:
    persona = _persona_template_path().read_text()
    version_line = f"<!-- dragoman version: {__version__} -->"
    return f"{PERSONA_START_MARKER}\n{version_line}\n\n{persona.rstrip()}\n\n{PERSONA_END_MARKER}\n"


def _inject_persona(target_path: Path) -> str:
    """Inject (or update) the dragoman persona in target_path. Idempotent.

    Returns one of: "created", "appended", "updated", "unchanged".
    """
    block = _persona_block()
    target_path = Path(target_path)

    if not target_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(block)
        return "created"

    existing = target_path.read_text()

    if PERSONA_START_MARKER in existing and PERSONA_END_MARKER in existing:
        start = existing.index(PERSONA_START_MARKER)
        end = existing.index(PERSONA_END_MARKER) + len(PERSONA_END_MARKER)
        old_block = existing[start:end]
        if old_block.strip() == block.strip():
            return "unchanged"
        new_content = existing[:start].rstrip() + "\n\n" + block + existing[end:].lstrip("\n")
        target_path.write_text(new_content)
        return "updated"

    target_path.write_text(existing.rstrip() + "\n\n" + block)
    return "appended"


def _remove_persona(target_path: Path) -> str:
    """Remove the dragoman persona block from target_path. Idempotent.

    Returns one of: "removed", "absent", "missing-file".
    """
    target_path = Path(target_path)
    if not target_path.exists():
        return "missing-file"

    existing = target_path.read_text()
    if PERSONA_START_MARKER not in existing or PERSONA_END_MARKER not in existing:
        return "absent"

    start = existing.index(PERSONA_START_MARKER)
    end = existing.index(PERSONA_END_MARKER) + len(PERSONA_END_MARKER)
    before = existing[:start].rstrip()
    after = existing[end:].lstrip("\n")

    if before and after:
        new_content = f"{before}\n\n{after}"
    elif before:
        new_content = before + "\n"
    else:
        new_content = after

    target_path.write_text(new_content)
    return "removed"


# ---------- uninstall ----------

def cmd_uninstall(args: argparse.Namespace) -> int:
    """Reverse what `dragoman init` wrote to your system.

    Removes the marker-bracketed persona block from the global and project
    CLAUDE.md (whichever exist). With --purge-config, also deletes
    ~/.config/dragoman/config.toml. Run `pip uninstall dragoman` separately.
    """
    from dragoman import config as cfg_mod

    print("dragoman uninstall — removing what `dragoman init` wrote.")
    print()

    targets = [
        Path.home() / ".claude" / "CLAUDE.md",
        Path.cwd() / "CLAUDE.md",
    ]

    print("Persona block:")
    for target in targets:
        result = _remove_persona(target)
        if result == "removed":
            print(f"  ✓  removed from {target}")
        elif result == "absent":
            print(f"  -  no persona block in {target} (skipped)")
        else:
            print(f"  -  {target} doesn't exist (skipped)")
    print()

    print("Provider config:")
    cfg_path = Path(cfg_mod.CONFIG_FILE)
    if not cfg_path.exists():
        print(f"  -  {cfg_path} doesn't exist (skipped)")
    elif args.purge_config:
        cfg_path.unlink()
        print(f"  ✓  deleted {cfg_path}")
    else:
        print(f"  -  {cfg_path} kept (pass --purge-config to delete)")
    print()

    print("To remove the dragoman package itself:")
    print("  pip uninstall dragoman")
    return 0


# ---------- status ----------

def cmd_status() -> int:
    """Print dragoman status — what `dragoman` bare invocation shows."""
    from dragoman import config as cfg_mod

    print(f"dragoman {__version__} — multi-model verb for Claude Code")
    print()

    cfg = cfg_mod.load_config()
    if not cfg:
        print("⚠  No providers configured.")
        print("   Run: dragoman init")
    else:
        print("🐉 Configured providers:")
        for provider, settings in cfg.items():
            label = "openai-compat" if provider == "openai_compat" else provider
            details = []
            if settings.get("host"):
                details.append(settings["host"])
            if settings.get("fallback_host"):
                details.append(f"fallback {settings['fallback_host']}")
            if settings.get("default_model"):
                details.append(f"default {settings['default_model']}")
            if settings.get("api_key") and provider != "ollama":
                ref = settings["api_key"]
                if ref.startswith(("op://", "keychain://", "env:")):
                    details.append(f"key via {ref}")
                else:
                    details.append("key set (literal)")
            print(f"   - {label}: {' · '.join(details) if details else '(configured)'}")
    print()

    print("Verbs:")
    print('   dragoman ask --model perplexity:sonar-pro --prompt "..."')
    print('   dragoman recommend "summarize 200 transcripts privately"')
    print("   dragoman models")
    print("   dragoman init     # provider keys + CLAUDE.md persona")
    return 0


# ---------- init ----------

def _prompt_host(label: str, default: str = "") -> Optional[str]:
    from dragoman import config as cfg_mod

    while True:
        suffix = f"[{default}]" if default else "(empty to skip)"
        raw = input(f"  {label} {suffix}: ").strip()
        if not raw and default:
            raw = default
        if not raw or raw.lower() == "skip":
            return None
        normalized = cfg_mod.normalize_host(raw)
        if normalized is None:
            print(f"    {raw!r} doesn't look like a URL — try again or 'skip'.")
            continue
        if normalized != raw:
            print(f"    (normalized to {normalized})")
        return normalized


def _prompt_secret(label: str, existing: str = "") -> Optional[str]:
    """Prompt for a secret reference. Accepts:
       - literal key (anything not starting with op://, keychain://, env:)
       - op://vault/item/field
       - keychain://service/account
       - env:VAR_NAME
       - blank → keep existing (or skip if no existing)
       - 'skip' → drop the provider entirely
    """
    if existing:
        existing_label = (
            existing if existing.startswith(("op://", "keychain://", "env:"))
            else "(literal stored)"
        )
        prompt_text = (
            f"  {label}\n"
            f"    current: {existing_label}\n"
            f"    new value (blank = keep, 'skip' = drop, op:// / keychain:// / env: refs welcome): "
        )
    else:
        prompt_text = (
            f"  {label}\n"
            f"    paste a literal key, or a reference (op://..., keychain://..., env:...), or 'skip': "
        )
    raw = input(prompt_text).strip()
    if raw.lower() == "skip":
        return "__SKIP__"
    if not raw:
        return existing or None
    return raw


def cmd_init(args: argparse.Namespace) -> int:
    """Interactive setup: provider config + CLAUDE.md persona injection."""
    from dragoman import config as cfg_mod

    print(f"dragoman init — interactive setup")
    print(f"(config will be written to {cfg_mod.CONFIG_FILE})")
    print(
        "API keys can be literal strings or references:\n"
        "  - op://Personal/Perplexity/credential   (1Password CLI)\n"
        "  - keychain://perplexity/apikey          (macOS Keychain)\n"
        "  - env:PERPLEXITY_API_KEY                (environment variable)\n"
    )

    cfg = cfg_mod.load_config()

    # Ollama: optional basement + laptop fallback
    print("Ollama (local LLM server):")
    existing = cfg.get("ollama", {})
    primary = _prompt_host(
        "primary host",
        existing.get("host") or "http://localhost:11434",
    )
    if primary is None:
        cfg.pop("ollama", None)
    else:
        fallback = _prompt_host(
            "fallback host (e.g. http://localhost:11434 if primary is your basement)",
            existing.get("fallback_host", ""),
        )
        default_model = existing.get("default_model") or "qwen2.5:14b"
        model = input(f"  default model [{default_model}]: ").strip() or default_model
        cfg["ollama"] = {"host": primary, "default_model": model}
        if fallback:
            cfg["ollama"]["fallback_host"] = fallback
    print()

    # Perplexity
    print("Perplexity:")
    existing = cfg.get("perplexity", {})
    api_key = _prompt_secret("api key", existing.get("api_key", ""))
    if api_key == "__SKIP__":
        cfg.pop("perplexity", None)
    else:
        default_model = existing.get("default_model") or "sonar-pro"
        model = input(f"  default model [{default_model}]: ").strip() or default_model
        cfg["perplexity"] = {"default_model": model}
        if api_key:
            cfg["perplexity"]["api_key"] = api_key
    print()

    # Gemini
    print("Gemini (Google):")
    existing = cfg.get("gemini", {})
    api_key = _prompt_secret("api key", existing.get("api_key", ""))
    if api_key == "__SKIP__":
        cfg.pop("gemini", None)
    else:
        default_model = existing.get("default_model") or "gemini-2.5-flash"
        model = input(f"  default model [{default_model}]: ").strip() or default_model
        cfg["gemini"] = {"default_model": model}
        if api_key:
            cfg["gemini"]["api_key"] = api_key
    print()

    # OpenAI-compat
    print("OpenAI-compatible endpoint (OpenAI proper, LiteLLM, vLLM, Gemini-via-proxy, …):")
    existing = cfg.get("openai_compat", {})
    host = _prompt_host("endpoint URL", existing.get("host", ""))
    if host is None:
        cfg.pop("openai_compat", None)
    else:
        api_key = _prompt_secret("api key (blank if endpoint doesn't need one)", existing.get("api_key", ""))
        if api_key == "__SKIP__":
            api_key = None
        cfg["openai_compat"] = {"host": host}
        if api_key:
            cfg["openai_compat"]["api_key"] = api_key
        if existing.get("default_model"):
            cfg["openai_compat"]["default_model"] = existing["default_model"]
    print()

    cfg_mod.save_config(cfg)
    print(f"Config saved to {cfg_mod.CONFIG_FILE}")
    print("Env vars override config values per-invocation; references are resolved at call time.")
    print()

    # Persona
    print("Persona setup")
    print("Dragoman speaks inline in Claude Code via a CLAUDE.md persona fragment.")
    print("Where should it live?")
    print("  1. Global (~/.claude/CLAUDE.md) — applies to all Claude Code sessions")
    print("  2. Project (<cwd>/CLAUDE.md) — only this project")
    print("  3. Skip — paste it manually later")
    persona_choice = input("Choice [1/2/3, default 1]: ").strip() or "1"

    if persona_choice == "1":
        target = Path.home() / ".claude" / "CLAUDE.md"
        result = _inject_persona(target)
        print(f"  → {result} {target}")
    elif persona_choice == "2":
        target = Path.cwd() / "CLAUDE.md"
        result = _inject_persona(target)
        print(f"  → {result} {target}")
    else:
        print(f"  Persona template lives at {_persona_template_path()}")
    return 0


# ---------- entry point ----------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dragoman",
        description="A small CLI that lets Claude Code reach non-Anthropic models.",
    )
    parser.add_argument("--version", action="version", version=f"dragoman {__version__}")

    sub = parser.add_subparsers(dest="command", title="commands")

    p_ask = sub.add_parser(
        "ask",
        help="One HTTPS call to a foreign model. Print response.",
        description=(
            "Send a single message to a foreign model and print its reply. "
            "No agent loop, no tool execution. Providers: ollama, perplexity, gemini, "
            "openai-compat, auto (auto: probes basement Ollama, falls back to laptop)."
        ),
    )
    p_ask.add_argument(
        "--model", required=True,
        help="Model spec, 'provider:name' (e.g. ollama:qwen2.5:14b, auto:qwen2.5:14b).",
    )
    p_ask.add_argument("--prompt", required=True, help="The user's task.")
    p_ask.add_argument("--system", help="Optional system prompt.")
    p_ask.add_argument(
        "--quiet", action="store_true",
        help="Suppress the 🐉 cost line on stderr.",
    )

    p_rec = sub.add_parser(
        "recommend",
        help="Print a model spec for a task description (no network call).",
        description=(
            "Pattern-match a task description against an opinionated rules table "
            "and print a model spec for the best fit drawn from your configured "
            "providers. stdout = bare spec; stderr = 🐉 rationale line."
        ),
    )
    p_rec.add_argument("task", help="The task description.")

    sub.add_parser(
        "models",
        help="List configured models, one per line.",
        description="Print the configured models from ~/.config/dragoman/config.toml.",
    )

    sub.add_parser(
        "init",
        help="Interactive setup; writes ~/.config/dragoman/config.toml.",
        description=(
            "Walk through provider configuration and CLAUDE.md persona injection. "
            "API keys can be literal strings, 1Password (op://) references, "
            "macOS Keychain (keychain://) references, or env: references."
        ),
    )

    p_uninst = sub.add_parser(
        "uninstall",
        help="Remove the persona block (and optionally the config file).",
    )
    p_uninst.add_argument(
        "--purge-config", action="store_true",
        help="Also delete ~/.config/dragoman/config.toml.",
    )

    args = parser.parse_args()

    if args.command == "ask":
        return cmd_ask(args)
    if args.command == "recommend":
        return cmd_recommend(args)
    if args.command == "models":
        return cmd_models(args)
    if args.command == "init":
        return cmd_init(args)
    if args.command == "uninstall":
        return cmd_uninstall(args)
    return cmd_status()


if __name__ == "__main__":
    sys.exit(main())
