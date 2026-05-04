# Contributing to dragoman

Thanks for considering a contribution. Dragoman is small on purpose — a CLI plus a CLAUDE.md fragment — so most patches land fast.

## Before you start

- **Open an issue first for anything non-trivial.** Bug reports and small fixes are fine to send as PRs directly. For new providers, secret-store backends, or anything that touches the persona, please open an issue so we can talk shape before you write code.
- **Keep dragoman tool-less.** Dragoman makes one HTTPS call per `ask` invocation and never executes shell commands. PRs that re-introduce an agent loop, tool-execution surface, or `bash` capability will be politely closed — that work belongs in Claude Code's own harness, not here.
- **Check the persona stays a fragment.** It's deliberately readable in five minutes. PRs that turn it into a config schema or framework will be politely closed with a roadmap pointer.

## Sign your commits — DCO, not CLA

Dragoman uses the [Developer Certificate of Origin](https://developercertificate.org/). It's a one-line attestation that you wrote (or have rights to contribute) the code — no separate paperwork, no CLA to sign.

Every commit needs a `Signed-off-by` trailer. The git CLI does this for you with `-s`:

```bash
git commit -s -m "your commit message"
```

Which adds:

```
Signed-off-by: Your Name <your.email@example.com>
```

The email must match your committer email. If you forgot, amend with `git commit --amend -s` (or rebase the branch with `git rebase --signoff main`).

## Local development

```bash
git clone https://github.com/asakin/dragoman.git
cd dragoman
pip install -e .
dragoman init       # configure providers + inject persona

# Sanity checks
dragoman --help
dragoman ask --model ollama:qwen2.5:14b --prompt "say hello"
dragoman recommend "summarize 200 transcripts privately"
```

There's no formal test harness yet. If your PR makes `secrets.resolve`, `routing.resolve`, `recommend.recommend`, or `config.normalize_host` reasonable to test, please add the tests; that's a clear step forward.

## What we want / don't want

**Welcome:**
- Bug fixes (with a reproducer in the PR description).
- New providers (Gemini-native, Anthropic-Bedrock, etc.) as `routers/<name>.py` with the same `ask(model, messages, ...) -> (text, usage)` shape.
- New secret backends (Linux Secret Service / `secret-tool`, Windows Credential Manager) in `secrets.py`.
- Tightening the persona's trigger logic with concrete examples that mis-fire today.
- Documentation patches, especially around install paths and platform differences.

**Hard sells:**
- Re-introducing an agent loop, tool execution, or shell access in the bridge.
- New abstraction layers in the routers.
- Auto-detection of model intent ("dragoman should know I want X"). Trigger logic is conservative on purpose.

## Code of Conduct

By participating, you agree to abide by the [Contributor Covenant](./CODE_OF_CONDUCT.md). Reports go to the maintainer email listed there.

## License

By submitting a contribution, you agree that it will be licensed under the Apache License 2.0 (the project's license). The DCO sign-off is your attestation that you have the right to do so.
