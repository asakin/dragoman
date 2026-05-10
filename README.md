# dragoman

A small CLI that lets [Claude Code](https://docs.claude.com/en/docs/claude-code) reach non-Anthropic models — Ollama (local), Perplexity (search-augmented), OpenAI, Gemini, anything OpenAI-compatible — through one verb the existing subagent runtime can call.

I have a GPU in my basement running Ollama and a Tailscale link to it from any coffee shop. I have laptop Ollama for when the network drops. I pay for OpenAI, Gemini, and Perplexity because each is the right answer for a different shape of question. Claude Code is the conductor. Dragoman is the verb that lets the conductor talk to the rest of the orchestra.

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

```bash
pip install dragoman-ai
dragoman init
```

Open a fresh Claude Code session. Try: *"What's the best model for [your task]?"* If the dragon shows up, it works.

## Keys live where you already keep them

API keys can be literal strings, environment variables, or references resolved at call time:

```toml
[perplexity]
api_key = "op://Personal/Perplexity/credential"   # 1Password CLI
default_model = "sonar-pro"

[openai_compat]
host = "https://api.openai.com"
api_key = "keychain://openai/apikey"              # macOS Keychain
```

Dragoman fetches by reference, uses the key for one HTTPS call, discards it. The key never enters Claude's context.

## `auto:` routing

If you have a beefy Ollama somewhere and a fallback Ollama somewhere else, `dragoman` will pick:

```toml
[ollama]
host = "http://basement.tailnet.ts.net:11434"
fallback_host = "http://localhost:11434"
default_model = "qwen2.5:14b"
```

Then `--model auto:qwen2.5:14b` does a fast TCP probe; basement first, laptop fallback. The persona never has to know your network state.

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
