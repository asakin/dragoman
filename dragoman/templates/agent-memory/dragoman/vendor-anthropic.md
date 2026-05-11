# Anthropic

## When to pick Anthropic
- Long-context analysis exceeding 500k tokens for contract review or research synthesis.
- Agentic coding with high reliability in tool calling and low hallucination.
- Safety-aligned responses for enterprise compliance or public-facing chat.
- Multilingual creative writing or nuanced communication tasks.
- Batch processing of 300k+ output tokens for data generation.

## When NOT to pick Anthropic
- Real-time web search; Perplexity for native browsing and citations.
- Video multimodal; Google Gemini for native audio/video handling.
- Local uncensored runs; Ollama for open-weight flexibility.

## Model families

### Claude Opus 4.x
Flagship intelligence family for frontier agentic tasks, extended outputs up to 300k in batch mode, and complex reasoning.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| claude-opus-4-7-20260201 | 1M | 2026-02 | no | no | yes | yes | expensive | Highest capability coding/reasoning [page:48] |
| claude-opus-4-6 | 1M | 2025-11 | no | no | yes | yes | expensive | Batch 300k outputs |

### Claude Sonnet 4.x
Production workhorse for interactive agents, with extended thinking for dynamic reasoning.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| claude-sonnet-4-6 | 1M | 2026-01 | no | no | yes | yes | mid | Best latency/capability balance [page:48] |
| claude-sonnet-4-5 | 1M | 2025-08 | no | no | yes | yes | mid | Adaptive extended thinking |

### Claude Haiku 4.x
Latency-optimized family for high-throughput tasks like classification or quick QA.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| claude-haiku-4-5 | 200K | 2025-10 | no | no | yes | yes | cheap | Lowest latency in lineup [page:48] |

## Decision guidance
- Pick `claude-opus-4-7-20260201` for frontier agentic coding over 100k outputs.
- Pick `claude-sonnet-4-6` for interactive long-context agents under 5s latency.
- Pick `claude-haiku-4-5` for high-RPM classification or multilingual QA.
- Pick `claude-opus-4-6` for batch data generation exceeding 200k tokens.
- Pick Sonnet family when safety alignment is required for compliance tasks.