# xAI

## When to pick xAI
- Truth-seeking queries with minimal hallucinations and real-time search integration via tools.
- Agentic coding and enterprise data extraction with strong tool calling.
- Multimodal tasks combining text and images for visual reasoning or analysis.
- Quantitative math/reasoning workloads where lightweight models outperform larger ones.
- High-context chat or coding sessions up to 1M tokens with low bias.

## When NOT to pick xAI
- Native web access without tools; Perplexity for built-in search without wrappers.
- Ultra-long context beyond 1M; OpenAI o-series for 200k+ with deep research.
- Local offline deployment; Ollama for open-weight models without API dependency.

## Model families

### Grok 4.x
Flagship family for general chat, coding, and agentic tasks with configurable reasoning, native tool use, and image input. Recommended for most use cases.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| grok-4.3 | 1M | 2024-11 | no | no | yes | yes | expensive | Strongest agentic tool calling |
| grok-4 | 256K | 2024-11 | yes | yes | yes | yes | mid | Real-time search integration |

### Grok 3.x
Previous generation for enterprise tasks like programming and summarization, with a lightweight variant for math/reasoning.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| grok-3 | 131K | 2024-11 | no | no | yes | yes | mid | Data extraction and coding |
| grok-3-mini | 131K | 2024-11 | no | no | yes | yes | cheap | Quantitative tasks, low cost |

## Decision guidance
- Pick `grok-4.3` when agentic workflows need 1M context and minimal hallucinations.
- Pick `grok-4` for chat/coding with real-time search and image inputs.
- Pick `grok-3-mini` for high-volume math or reasoning under cost constraints.
- Pick `grok-3` for enterprise summarization or data extraction tasks.
- Pick Grok 4.x family when truthfulness and tool reliability are priorities.