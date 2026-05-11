# Google

## When to pick Google
- Multimodal tasks involving video, audio, and 1M+ token context for document analysis.
- High-volume low-latency inference for chatbots or classification at scale.
- Image/video generation and editing workflows with conversational refinement.
- Real-time voice agents with bidirectional audio streaming.
- Embedding and RAG setups needing multimodal semantic search.

## When NOT to pick Google
- Deep agentic tool chaining; OpenAI for superior function calling reliability.
- Native web search without tools; Perplexity for built-in citations and browsing.
- Uncensored local models; Ollama for open-weight deployment flexibility.

## Model families

### Gemini 3.x
Advanced family for complex reasoning, agentic workflows, and multimodal problem-solving with up to 1M context window.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| gemini-3.1-pro | 1M | 2026-01 | no | no | yes | yes | expensive | Complex agentic coding [page:71] |
| gemini-3-flash | 1M | 2026-05 | no | no | yes | yes | mid | Strong multimodal reasoning |
| gemini-3.1-flash-lite | 1M | 2026-05 | no | no | yes | yes | cheap | Low latency high-volume |

### Gemini 2.5
Workhorse family for balanced price-performance in reasoning, coding, and generation tasks.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| gemini-2.5-pro | 1M | 2025-09 | no | no | yes | yes | mid | Adaptive thinking 1M context [page:71] |
| gemini-2.5-flash | 1M | 2025-09 | no | no | yes | yes | cheap | Controllable thinking budget |
| gemini-2.5-flash-lite | 1M | 2025-09 | no | no | yes | yes | cheap | Cost-optimized throughput |

## Decision guidance
- Pick `gemini-3.1-pro` when 1M context needed for agentic multimodal analysis.
- Pick `gemini-3.1-flash-lite` for high-volume low-latency classification tasks.
- Pick `gemini-2.5-pro` for complex reasoning with adaptive compute levels.
- Pick `gemini-2.5-flash` for fast coding or chat with 1M context.
- Pick Flash-Lite family when input rate exceeds 1K RPM under cost limits.