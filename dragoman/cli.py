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
    from dragoman.routers import providers

    try:
        resolved = routing.resolve(args.model)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    messages: list[dict] = []
    if getattr(args, "messages", None):
        import json
        with open(args.messages, "r", encoding="utf-8") as f:
            messages = json.load(f)
    else:
        if not args.prompt:
            print("error: --prompt is required unless --messages is provided", file=sys.stderr)
            return 2
        if args.system:
            messages.append({"role": "system", "content": args.system})
        messages.append({"role": "user", "content": args.prompt})

    try:
        if resolved.type == "openai_compat":
            text, usage = providers.ask_openai_compat(
                model=resolved.model,
                messages=messages,
                host=resolved.host,
                api_key_ref=resolved.api_key_ref,
                stream=args.stream
            )
        elif resolved.type == "gemini":
            text, usage = providers.ask_gemini(
                model=resolved.model,
                messages=messages,
                api_key_ref=resolved.api_key_ref,
                stream=args.stream
            )
        else:
            print(f"error: unknown connection type {resolved.type!r}", file=sys.stderr)
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
    providers = cfg.get("providers", {})
    if not providers:
        print("(no providers configured — run `dragoman init`)", file=sys.stderr)
        return 0

    for conn_name, settings in providers.items():
        host = settings.get("host")
        endpoint = f" ({host})" if host else ""
        print(f"{conn_name}{endpoint}:")
        
        approved = settings.get("approved_models", [])
        if not approved:
            print("  (no models approved)")
        else:
            for m in approved:
                print(f"  - {conn_name}:{m}")

    return 0


# ---------- persona inject / remove ----------

PERSONA_START_MARKER = "<!-- dragoman persona — managed by `dragoman init`, do not edit directly -->"
PERSONA_END_MARKER = "<!-- /dragoman persona -->"


def _persona_template_path() -> Path:
    return Path(__file__).parent / "templates" / "persona.claude.md"


def _persona_block(approved_table: str = "") -> str:
    persona = _persona_template_path().read_text()
    version_line = f"<!-- dragoman version: {__version__} -->"
    
    if approved_table:
        persona += f"\n\n## Approved Models\n\n{approved_table}\n"
        
    return f"{PERSONA_START_MARKER}\n{version_line}\n\n{persona.rstrip()}\n\n{PERSONA_END_MARKER}\n"


def _inject_persona(target_path: Path, approved_table: str = "") -> str:
    """Inject (or update) the dragoman persona in target_path. Idempotent.

    Returns one of: "created", "appended", "updated", "unchanged".
    """
    block = _persona_block(approved_table)
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


def _auto_name_from_host(host: str) -> str:
    from urllib.parse import urlparse
    try:
        parsed = urlparse(host if "://" in host else f"http://{host}")
        domain = parsed.hostname or ""
        domain = domain.lower()
        for prefix in ("api.", "www."):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        base = domain.split('.')[0] if '.' in domain else domain
        return base or "custom"
    except Exception:
        return "custom"

def _get_unique_name(base: str, existing_names: set) -> str:
    name = base
    count = 1
    while name in existing_names:
        count += 1
        name = f"{base}_{count}"
    return name

def _prompt_connection_name(default_name: str) -> str:
    name = input(f"  Name this connection [{default_name}]: ").strip()
    return name or default_name

def cmd_init(args: argparse.Namespace) -> int:
    """Interactive setup: provider config + CLAUDE.md persona injection."""
    from dragoman import config as cfg_mod

    print("🐉 dragoman init\n")
    print("Dragoman helps Claude Code and background agents use models from other providers.")
    print("It also helps you and Claude choose the right model for each job.\n")
    print("This setup will create a local config for the providers you want to connect.")
    print("You can add multiple providers now, or press Enter to finish at any time.\n")
    print(f"Config will be saved to: {cfg_mod.CONFIG_FILE}\n")
    print("How Dragoman can access API keys:")
    print("  - Environment variable name, for example OPENAI_API_KEY")
    print("  - macOS Keychain reference, for example keychain://openai/apikey")
    print("  - 1Password reference, for example op://Private/OpenAI API Key/credential")
    print("  - Plain key saved in config, not recommended\n")
    
    cfg = cfg_mod.load_config()
    providers = cfg.setdefault("providers", {})
    all_approved = []
    
    first_time = True

    while True:
        if first_time:
            print("What would you like to connect first?\n")
            first_time = False
        else:
            print("What would you like to connect next?\n")
            
        print("  [1] OpenAI")
        print("  [2] Other OpenAI-compatible provider or gateway")
        print("      Examples: Groq, Together, LM Studio, LiteLLM")
        print("  [3] Google Gemini")
        print("  [4] Perplexity")
        print("  [5] Ollama local server [http://localhost:11434]\n")
        
        choice = input("Options: [1-5] Connect provider, [Enter] Exit\n> ").strip()
        if not choice:
            break
            
        if choice == "1":
            print("\n--- OpenAI ---")
            api_key = _prompt_secret("API key", "")
            if api_key == "__SKIP__":
                continue
                
            default_name = _get_unique_name("openai", set(providers.keys()))
            conn_name = _prompt_connection_name(default_name)
            
            block = {"type": "openai_compat", "host": "https://api.openai.com/v1"}
            if api_key:
                block["api_key"] = api_key
                
            print(f"  Discovering live models for {conn_name}...")
            from dragoman import discovery
            discovered = discovery.discover_openai_compat(block["host"], api_key)
            approved = _prompt_checkbox_menu(conn_name, discovered)
            if approved:
                for m in approved:
                    m["connection"] = conn_name
                all_approved.extend(approved)
                block["approved_models"] = [m["model_id"] for m in approved]
            
            providers[conn_name] = block
            print()
            
        elif choice == "2":
            print("\n--- Other OpenAI-compatible provider ---")
            host = _prompt_host("Endpoint URL", "")
            if not host:
                continue
                
            api_key = _prompt_secret("API key (blank if none)", "")
            if api_key == "__SKIP__":
                api_key = None
            
            base_name = _auto_name_from_host(host)
            default_name = _get_unique_name(base_name, set(providers.keys()))
            conn_name = _prompt_connection_name(default_name)
            
            block = {"type": "openai_compat", "host": host}
            if api_key:
                block["api_key"] = api_key
                
            print(f"  Discovering live models for {conn_name}...")
            from dragoman import discovery
            discovered = discovery.discover_openai_compat(host, api_key)
            approved = _prompt_checkbox_menu(conn_name, discovered)
            if approved:
                for m in approved:
                    m["connection"] = conn_name
                all_approved.extend(approved)
                block["approved_models"] = [m["model_id"] for m in approved]
                
            providers[conn_name] = block
            print()
            
        elif choice == "3":
            print("\n--- Google Gemini ---")
            api_key = _prompt_secret("API key", "")
            if api_key == "__SKIP__":
                continue
                
            default_name = _get_unique_name("gemini", set(providers.keys()))
            conn_name = _prompt_connection_name(default_name)
            
            block = {"type": "gemini"}
            if api_key:
                block["api_key"] = api_key
            
            print(f"  Discovering models for {conn_name}...")
            from dragoman import discovery
            discovered = discovery.discover_gemini(api_key)
            approved = _prompt_checkbox_menu(conn_name, discovered)
            if approved:
                for m in approved:
                    m["connection"] = conn_name
                all_approved.extend(approved)
                block["approved_models"] = [m["model_id"] for m in approved]
                
            providers[conn_name] = block
            print()
            
        elif choice == "4":
            print("\n--- Perplexity ---")
            api_key = _prompt_secret("API key", "")
            if api_key == "__SKIP__":
                continue
                
            default_name = _get_unique_name("perplexity", set(providers.keys()))
            conn_name = _prompt_connection_name(default_name)
            
            block = {"type": "openai_compat", "host": "https://api.perplexity.ai"}
            if api_key:
                block["api_key"] = api_key
                
            print(f"  Discovering live models for {conn_name}...")
            from dragoman import discovery
            discovered = discovery.discover_openai_compat(block["host"], api_key)
            approved = _prompt_checkbox_menu(conn_name, discovered)
            if approved:
                for m in approved:
                    m["connection"] = conn_name
                all_approved.extend(approved)
                block["approved_models"] = [m["model_id"] for m in approved]
                
            providers[conn_name] = block
            print()
            
        elif choice == "5":
            print("\n--- Ollama ---")
            host = _prompt_host("Primary host", "http://localhost:11434")
            if not host:
                continue
                
            # Ollama speaks openai protocol on /v1
            if not host.endswith("/v1"):
                host = host.rstrip("/") + "/v1"
                
            base_name = _auto_name_from_host(host)
            default_name = _get_unique_name(base_name, set(providers.keys()))
            conn_name = _prompt_connection_name(default_name)
            
            block = {"type": "openai_compat", "host": host}
                
            print(f"  Discovering models for {conn_name}...")
            from dragoman import discovery
            discovered = discovery.discover_openai_compat(host)
            approved = _prompt_checkbox_menu(conn_name, discovered)
            if approved:
                for m in approved:
                    m["connection"] = conn_name
                all_approved.extend(approved)
                block["approved_models"] = [m["model_id"] for m in approved]
                
            providers[conn_name] = block
            print()
            
        else:
            print("  [!] Invalid choice. Enter a number 1-5, or press Enter to finish.")
            print()

    # Save and inject phase
    cfg_mod.save_config(cfg)
    print(f"\nConfig saved to {cfg_mod.CONFIG_FILE}")
    print("Env vars override config values per-invocation; references are resolved at call time.\n")
    
    approved_table = ""
    # Collect approved from config to support multiple sequential runs where all_approved resets but config remembers
    
    # We rebuild the final_approved list from the config and catalogue, so if they configure multiple providers it aggregates properly.
    if all_approved:
        approved_table = "| Connection | Model | Strengths | Suitable For |\n|---|---|---|---|\n"
        seen = set()
        for m in all_approved:
            key = f"{m['connection']}:{m['model_id']}"
            if key not in seen:
                seen.add(key)
                approved_table += f"| `{m['connection']}` | `{m['model_id']}` | {m['strengths']} | {m['suitable_for']} |\n"

    print("--- Claude Setup ---")
    print("Dragoman speaks directly to Claude Code to advise on model selection and usage.")
    print("Where should these instructions live?")
    print("  1. Global (~/.claude/CLAUDE.md) — applies to all Claude Code sessions")
    print("  2. Project (<cwd>/CLAUDE.md) — only this project")
    print("  3. Skip — I'll paste it manually later")
    persona_choice = input("Choice [1/2/3, default 1]: ").strip() or "1"

    if persona_choice == "1":
        target = Path.home() / ".claude" / "CLAUDE.md"
        result = _inject_persona(target, approved_table)
        print(f"  → {result} {target}")
    elif persona_choice == "2":
        target = Path.cwd() / "CLAUDE.md"
        result = _inject_persona(target, approved_table)
        print(f"  → {result} {target}")
    else:
        print(f"  Persona template lives at {_persona_template_path()}")
        
    print("\nSetup complete! Dragoman is ready.")
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
    p_ask.add_argument(
        "--prompt",
        help="The user's task. Required unless --messages is provided.",
    )
    p_ask.add_argument(
        "--messages",
        help="Path to a JSON file containing a conversation history array.",
    )
    p_ask.add_argument("--system", help="Optional system prompt.")
    p_ask.add_argument(
        "--stream", action="store_true",
        help="Stream the response to stderr in real time.",
    )
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

def _prompt_checkbox_menu(provider_name: str, discovered: list[str]) -> list[dict]:
    from dragoman import discovery
    cat_approved, cat_rejected, unknown_families = discovery.map_discovered_models(provider_name, discovered)
    
    items = []
    # Auto-select recommended families since the list is now curated and small
    for m in cat_approved:
        items.append({"id": m["model_id"], "status": "Recommended", "selected": True, "dict": m})
    for m in cat_rejected:
        items.append({"id": m["model_id"], "status": "Not Recommended", "selected": False, "dict": m})
    for m in unknown_families:
        dummy = {
            "model_id": m,
            "provider": provider_name,
            "strengths": "Unknown model (manually approved)",
            "suitable_for": "general",
            "context": "?",
            "propose": "yes"
        }
        items.append({"id": m, "status": "Unknown", "selected": False, "dict": dummy})
        
    if not items:
        print(f"  [!] No models discovered from {provider_name} endpoint.")
        return []

    show_all = False
    filter_text = ""
    
    while True:
        visible_items = []
        for i, item in enumerate(items, 1):
            item["display_idx"] = i
            if filter_text and filter_text not in item["id"].lower():
                continue
            visible_items.append(item)
            
        print(f"\n--- {provider_name} Models ({len(items)} discovered) ---")
        if filter_text:
            print(f"  (Filtering by: {filter_text!r})")
            
        limit = len(visible_items) if show_all else min(10, len(visible_items))
        
        for item in visible_items[:limit]:
            checkbox = "[x]" if item["selected"] else "[ ]"
            print(f"  [{item['display_idx']:2}] {checkbox} {item['id']:<40} ({item['status']})")
            
        if len(visible_items) > limit:
            print(f"  ... and {len(visible_items) - limit} more hidden.")
            
        print("\nOptions: [S] Show all  [F <text>] Filter  [A] Select recommended  [1-X] Toggle  [Enter] Confirm")
        choice = input("> ").strip().lower()
        
        if not choice:
            break
        elif choice == 's':
            show_all = not show_all
        elif choice.startswith('f '):
            filter_text = choice[2:].strip()
            show_all = True
        elif choice == 'f':
            filter_text = ""
        elif choice == 'a':
            for item in items:
                item["selected"] = (item["status"] == "Recommended")
        else:
            for p in choice.split():
                if p.isdigit():
                    idx = int(p) - 1
                    if 0 <= idx < len(items):
                        items[idx]["selected"] = not items[idx]["selected"]

    return [item["dict"] for item in items if item["selected"]]
