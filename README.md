# 🐉 Dragoman

[![PyPI](https://img.shields.io/pypi/v/dragoman-ai)](https://pypi.org/project/dragoman-ai/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![Status](https://img.shields.io/badge/status-alpha-orange)]()

**Give Claude Code access to every other AI model you pay for.**

You use Claude Code. You also pay for Perplexity, OpenAI, Gemini, or run Ollama locally. Right now Claude can't reach any of them. Dragoman fixes that — it plugs into Claude Code's sub-agent system and lets it route questions to the right model, automatically.

## What does that look like?

You're in Claude Code and ask: *"What happened in the news today about the OpenAI acquisition?"*

Instead of *"I don't have web access,"* Claude recognizes this is a search question, hands it to Dragoman, and Dragoman routes it to Perplexity — which was built for exactly that. The answer comes back into your Claude session with sources.

**More things you can do:**

- 🔍 **Search the web** — "Find me sources on X," "what's the latest on Y" → routes to Perplexity
- 🧠 **Ask another model** — "What would GPT-5 say?" or "Try Gemini on this" → routes to that provider
- 🏠 **Stay local** — "Run this through Llama on my machine" → routes to Ollama, nothing leaves your network
- 🔀 **Fan out** — Send the same question to four models and have Claude synthesize the best answer
- 🎯 **Upgrade selectively** — Coding in Sonnet, but need Opus + GPT-5 for a deep research question? Just ask

## Install

```bash
# Homebrew (macOS)
brew install asakin/tap/dragoman

# uv (fastest)
uv tool install dragoman-ai

# pipx
pipx install dragoman-ai
```

Then run the setup wizard:

```bash
dragoman init
```

It walks you through connecting your providers — API keys, Ollama hosts, whatever you use — and installs the sub-agent persona into Claude Code. Open a fresh Claude Code session and try: *"What's the latest news on [topic]?"*

## Your keys never leave your machine

Dragoman resolves API keys at call time from wherever you already keep them, uses each key for one request, and throws it away. The key never enters Claude's context window.

```toml
# ~/.config/dragoman/config.toml

[providers.perplexity]
type = "openai_compat"
host = "https://api.perplexity.ai"
api_key = "op://Personal/Perplexity/credential"   # 1Password CLI

[providers.openai]
type = "openai_compat"
host = "https://api.openai.com/v1"
api_key = "keychain://openai/apikey"               # macOS Keychain

[providers.ollama]
type = "openai_compat"
host = "http://localhost:11434/v1"                  # no key needed
```

Supported secret backends: **1Password CLI** (`op://`), **macOS Keychain** (`keychain://`), and **environment variables** (`env:`).

## This isn't a hack — it's how sub-agents are supposed to work

Anthropic built a genuinely good sub-agent architecture into Claude Code. Sub-agents get their own context, their own persona, and their own mission — completely separated from the parent. Dragoman is just one example of what that architecture makes possible with very little code.

You don't need a plugin system that doesn't exist yet. You don't need to reverse-engineer anything. And when Anthropic improves their sub-agent runtime — better fan-out, richer permissions, longer context — Dragoman gets better for free.

## What it writes

| What | Where | Created by | Removed by |
| --- | --- | --- | --- |
| Provider config | `~/.config/dragoman/config.toml` | `dragoman init` | `dragoman uninstall --purge-config` |
| Sub-agent files | `~/.claude/agents/dragoman/` | `dragoman init` | `dragoman uninstall` |
| Persona import | `~/.claude/CLAUDE.md` | `dragoman init` | `dragoman uninstall` |

Clean removal: `dragoman uninstall` reverses everything. Add `--purge-config` to also delete your provider config.

## Platform support

| | Status |
| --- | --- |
| **macOS** | ✅ Fully supported |
| **Linux** | ✅ Works — `keychain://` is macOS-only, but `op://` and `env:` work everywhere |
| **Windows** | ❓ Untested — PRs welcome |

## Telemetry

None. Dragoman makes no outbound calls of its own — only to the provider endpoints you configured.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Small PRs welcome; commits need DCO sign-off (`git commit -s`). [Contributor Covenant](./CODE_OF_CONDUCT.md) applies.

## License

Apache 2.0 — see [LICENSE](./LICENSE).

---

*Dragoman was the translator-fixer at Ottoman, Levantine, and European courts. The English word and the Hebrew* meturgeman *share an Akkadian root and have nothing to do with reptiles. The 🐉 emoji is a typo I refuse to fix. There is also no evidence that dragons were actually reptiles.*