"""Command-line interface for dragoman.

Verbs:
    ask         — forward a prompt to a foreign model; print response.
    models      — list configured models.
    init        — interactive setup (provider keys + agent file installation).
    uninstall   — remove the agent file from .claude/agents/ (and optionally config).
    (no args)   — print status.

Dragoman holds keys (or references to them) and forwards prompts to non-Anthropic
models. Everything else happens in the calling Claude Code subagent through the
harness's normal tools.
"""

import argparse
import sys
from pathlib import Path

from dragoman import __version__


# ---------- ask ----------

def cmd_ask(args: argparse.Namespace) -> int:
    """Forward a prompt to a foreign model. Print response to stdout."""
    from dragoman import routing
    from dragoman.routers import providers

    try:
        resolved = routing.resolve(args.model)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    import json
    messages: list[dict] = []
    if getattr(args, "messages", None):
        with open(args.messages, "r", encoding="utf-8") as f:
            messages = json.load(f)
    else:
        if not args.prompt:
            print("error: --prompt is required unless --messages is provided", file=sys.stderr)
            return 2
        if args.system:
            messages.append({"role": "system", "content": args.system})
        messages.append({"role": "user", "content": args.prompt})

    dispatch = {
        "gemini": providers.ask_gemini,
        "anthropic": providers.ask_anthropic,
        "openai_compat": providers.ask_openai_compat,
    }
    fn = dispatch.get(resolved.type)
    if fn is None:
        print(f"error: unknown connection type {resolved.type!r}", file=sys.stderr)
        return 2

    kwargs = dict(
        model=resolved.model,
        messages=messages,
        api_key_ref=resolved.api_key_ref,
        stream=args.stream,
    )
    if resolved.type == "openai_compat":
        kwargs["host"] = resolved.host

    try:
        text, usage = fn(**kwargs)
    except Exception as e:
        print(f"error: request failed: {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(
            f"🐉 dragoman: {resolved.connection}:{resolved.model} · "
            f"{usage.get('tokens_in', 0)} in / {usage.get('tokens_out', 0)} out",
            file=sys.stderr,
            flush=True,
        )
    print(text)
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


# ---------- uninstall ----------

def cmd_uninstall(args: argparse.Namespace) -> int:
    """Reverse what `dragoman init` wrote to your system."""
    from dragoman import config as cfg_mod, agent

    print("dragoman uninstall — removing what `dragoman init` wrote.")
    print()

    claude_dirs = [
        Path.home() / ".claude",
        Path.cwd() / ".claude",
    ]

    print("Agent files:")
    for claude_dir in claude_dirs:
        results = agent.uninstall(claude_dir)
        for rel_path, status in results.items():
            target = claude_dir / rel_path
            if status == "removed":
                print(f"  ✓  removed {target}")
            elif status == "absent":
                print(f"  -  {target} not found (skipped)")
            else:
                print(f"  -  {claude_dir} doesn't exist (skipped)")

        md_path, md_status = agent.remove_claude_md_block(claude_dir)
        if md_status == "removed":
            print(f"  ✓  removed Dragoman block from {md_path}")
        elif md_status == "absent":
            print(f"  -  no Dragoman block in {md_path} (skipped)")
        else:
            print(f"  -  {md_path} doesn't exist (skipped)")
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
    providers = cfg.get("providers", {})
    if not providers:
        print("⚠  No providers configured.")
        print("   Run: dragoman init")
    else:
        print("🐉 Configured providers:")
        for conn_name, settings in providers.items():
            details = []
            if settings.get("host"):
                details.append(settings["host"])
            key_ref = settings.get("api_key", "")
            if key_ref:
                details.append(f"key via {key_ref}")
            n_models = len(settings.get("approved_models", []))
            if n_models:
                details.append(f"{n_models} models")
            print(f"   - {conn_name}: {' · '.join(details) if details else '(configured)'}")
    print()

    print("Verbs:")
    print('   dragoman ask --model <connection>:<model> --prompt "..."')
    print("   dragoman models")
    print("   dragoman init     # provider keys + agent setup")
    return 0


# ---------- entry point ----------

def main() -> int:
    try:
        parser = argparse.ArgumentParser(
            prog="dragoman",
            description="A small CLI that lets Claude Code reach non-Anthropic models.",
        )
        parser.add_argument("--version", action="version", version=f"dragoman {__version__}")

        sub = parser.add_subparsers(dest="command", title="commands")

        p_ask = sub.add_parser("ask", help="Forward a prompt to a foreign model. Print response.")
        p_ask.add_argument("--model", required=True, help="Model spec: connection:name (e.g. openai:gpt-4o).")
        p_ask.add_argument("--prompt", help="The prompt. Required unless --messages is provided.")
        p_ask.add_argument("--messages", help="Path to a JSON file containing a conversation history array.")
        p_ask.add_argument("--system", help="Optional system prompt.")
        p_ask.add_argument("--stream", action="store_true", help="Stream response to stderr in real time.")
        p_ask.add_argument("--quiet", action="store_true", help="Suppress the 🐉 cost line on stderr.")

        sub.add_parser("models", help="List configured models, one per line.")
        sub.add_parser("init", help="Interactive setup; writes provider config + agent file.")

        p_uninst = sub.add_parser("uninstall", help="Remove the agent file (and optionally the config file).")
        p_uninst.add_argument("--purge-config", action="store_true", help="Also delete the config file.")

        args = parser.parse_args()

        if args.command == "ask":
            return cmd_ask(args)
        if args.command == "models":
            return cmd_models(args)
        if args.command == "init":
            from dragoman.init_wizard import cmd_init
            return cmd_init()
        if args.command == "uninstall":
            return cmd_uninstall(args)
        return cmd_status()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
