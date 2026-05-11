# dragoman

A small CLI that lets [Claude Code](https://docs.claude.com/en/docs/claude-code) reach non-Anthropic models — Ollama (local), Perplexity (search-augmented), OpenAI, Gemini, anything OpenAI-compatible — through one verb the existing subagent runtime can call.

I have a GPU running Ollama. I pay for OpenAI, Gemini, and Perplexity because each is the right answer for a different shape of question. Claude Code is the conductor. Dragoman is the verb that lets the conductor talk to the rest of the orchestra.

**v0.5.0 alpha. Apache 2.0.**

## What it does

Three commands. No agent loop. No tool execution. No shell. Just one HTTPS call per `ask`.

```bash
dragoman ask --model perplexity:sonar-pro --prompt "..."   # one HTTPS call, prints text
dragoman recommend "summarize 200 transcripts privately"   # rules table + your config
dragoman models                                            # what's configured, one per line
```

The persona injected by `dragoman init` teaches Claude Code when to spawn a real `Task()` subagent that uses `dragoman ask` for the cognitive step. All filesystem and shell work happens through Claude Code's normal tools — the harness's audit, fan-out, and permissions stay intact. Dragoman holds keys; the harness holds the runtime.

## Install

You can install Dragoman securely using any modern Python tool manager:

```bash
# Using pipx (Standard)
pipx install dragoman-ai

# Using uv (Fastest)
uv tool install dragoman-ai
```

*(Homebrew support is currently being built!)*

Then, initialize your config and provider keys:
```bash
dragoman init
```

Open a fresh Claude Code session. Try: *"What's the best model for [your task]?"* If the dragon shows up, it works.

## Keys live where you already keep them

API keys can be literal strings, environment variables, or references resolved at call time:

```toml
[providers.perplexity_1]
type = "openai_compat"
host = "https://api.perplexity.ai"
api_key = "op://Personal/Perplexity/credential"   # 1Password CLI

[providers.groq_1]
type = "openai_compat"
host = "https://api.groq.com/v1"
api_key = "keychain://groq/apikey"              # macOS Keychain
```

Dragoman fetches by reference, uses the key for one HTTPS call, discards it. The key never enters Claude's context.

## Infinite Dynamic Providers

Dragoman replaces hardcoded singleton endpoints with a dynamic provider registry. You can connect as many distinct accounts, gateways, or local instances as you want simultaneously. 

For example, if you have a local laptop Ollama and a heavy basement workstation on Tailscale:

```toml
[providers.laptop_1]
type = "openai_compat"
host = "http://localhost:11434/v1"

[providers.basement_1]
type = "openai_compat"
host = "http://basement.tailnet.ts.net:11434/v1"
```

Then you simply tell Claude exactly which pipe to use: `--model basement_1:qwen2.5:72b`. No magic network probing; just explicit, unopinionated routing.

## What it writes to your system

| Artifact | Path | Created by | Removed by |
| --- | --- | --- | --- |
| Provider config | `~/.config/dragoman/config.toml` | `dragoman init` | `dragoman uninstall --purge-config` |
| Persona block | `~/.claude/CLAUDE.md` (or project) | `dragoman init` | `dragoman uninstall` |
| Python package | active env | `pip install dragoman-ai` | `pip uninstall dragoman-ai` |

The persona block is bracketed by `<!-- dragoman persona ... -->` markers; removal is exact and idempotent.

## Telemetry

None. Dragoman makes no outbound calls of its own — only to provider endpoints you configured.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Small PRs welcome; commits need DCO sign-off (`git commit -s`); [Contributor Covenant](./CODE_OF_CONDUCT.md) applies.

## License

Apache 2.0. See [`LICENSE`](./LICENSE).

---

*Dragoman was the translator-fixer at Ottoman, Levantine, and European courts. The English word and the Hebrew* meturgeman *share an Akkadian root and have nothing to do with reptiles. The 🐉 emoji is a typo I refuse to fix.*
