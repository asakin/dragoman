# Dragoman's memory map

This file is your map. The first ~25KB of it is auto-injected into your system prompt at the start of every session. Keep it short — it's the router, not the archive.

## Files in this directory

- `configured-models.md` — the real, current list of models you can actually call. The install script writes this; you read it but never edit it. If it looks wrong, say so to the parent; don't try to fix it yourself.
- `vendor-*.md` — one file per supported vendor (e.g., `vendor-openai.md`, `vendor-perplexity.md`, `vendor-ollama.md`, `vendor-gemini.md`,`vendor-xai.md`). Each contains a narrative plus a table about that vendor's model families, strengths, and use cases. After reading `configured-models.md`, load **only** the vendor files matching what's configured. Ignore the rest to keep context clean.
- Anything else in this directory is something you (or a past you in another session) wrote. Read deliberately when relevant — don't load everything every session.

## Writing rules

Store each learning as its own file named `<type>_<slug>.md` with frontmatter:

---
name: Short human-readable title
description: One-line summary
type: feedback | preference | model-quirk | research | routing
---

Then the content.

Add every new file to the Files list above. The map should always reflect reality.

When you learn something worth remembering, write it to the file where it thematically belongs:

- **Vendor-specific knowledge** — a model's quirk, a new family, a benchmark observation, the answer to a research question about a specific provider → append to the relevant `vendor-*.md`. Preserve the file's existing structure (narrative + table); extend, don't replace.
- **User preferences** — "the user always wants citations for legal questions," "the user prefers shorter answers" → `preferences.md`. Create it if it doesn't exist.
- **Cross-vendor comparisons or routing heuristics** — "for Rust code review, GPT-5 outperformed sonar-pro in three trials" → `routing-notes.md`. Create it if it doesn't exist.

When you create a new file, **update the Files list above** in this MEMORY.md to mention it. The map should always reflect reality.

## What not to do

- Don't edit `configured-models.md`. That's the install's source of truth.
- Don't push knowledge into this MEMORY.md itself. This is the router. Keep it short.
- Don't fabricate models. If a model isn't in `configured-models.md`, you can't call it, even if you know it exists from a vendor file.
