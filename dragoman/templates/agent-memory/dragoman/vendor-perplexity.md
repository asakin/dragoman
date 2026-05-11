# Perplexity

## When to pick Perplexity
- Research queries needing real-time web search with automatic citations.
- Multi-model agentic workflows with fallback chains across vendors.
- Deep analysis requiring exhaustive web crawling and multi-source synthesis.
- Fast grounded answers with verifiable sources for knowledge-intensive tasks.
- Orchestrated tool use including browsing, code execution, and file analysis.

## When NOT to pick Perplexity
- Pure offline generation; Ollama for local hardware without internet dependency.
- Custom fine-tuning; OpenAI for proprietary model customization.
- Native video/audio processing; Google for multimodal media workflows.

## Model families

### Sonar
Perplexity's native family optimized for fast grounded search and research, powered by Llama architectures with web integration.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| perplexity/sonar-deep-research | 128K | 2026-02 | yes | yes | no | yes | mid | Exhaustive web research reports [web:71] |
| perplexity/sonar-large-online | 128K | 2026-02 | yes | yes | no | yes | expensive | Comprehensive analysis with sources |
| perplexity/sonar-medium-online | 128K | 2026-02 | yes | yes | no | yes | mid | Balanced speed and depth |
| perplexity/sonar | 128K | 2026-02 | yes | yes | no | yes | cheap | Fast grounded Q&A [web:71] |

### Preset Orchestrations
Pre-configured multi-model setups for specialized agentic tasks with automatic routing.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| perplexity/preset/pro-search | 128K | n/a | yes | yes | no | yes | mid | Optimized search agents [web:72] |

### Third-party Frontier
Access to hosted frontier models from partners with Perplexity's search/tools layer.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| openai/gpt-5.4 | 200K | 2025-12 | yes | yes | yes | yes | expensive | Advanced reasoning with search [web:72] |
| anthropic/claude-sonnet-4-6 | 1M | 2026-01 | yes | yes | yes | yes | mid | Long-context analysis |
| xai/grok-4.3 | 1M | 2026-01 | yes | yes | yes | yes | mid | Truth-seeking agents [web:71] |

## Decision guidance
- Pick `perplexity/sonar-deep-research` for multi-page web synthesis with citations.
- Pick `perplexity/sonar` for quick factual answers under 1s latency.
- Pick `openai/gpt-5.4` for reasoning-heavy research with vision needs.
- Pick `anthropic/claude-sonnet-4-6` for 1M+ context document analysis.
- Pick `perplexity/preset/pro-search` for automatic model routing in agents.