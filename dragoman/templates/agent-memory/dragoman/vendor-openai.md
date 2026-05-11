# OPENAI

## When to pick OPENAI
- Agentic workflows requiring tool calling and computer use, like multi-step coding or automation.
- High-precision reasoning tasks such as math proofs, scientific analysis, or long-chain logic.
- Multimodal inputs combining text, vision, and audio for tasks like video description or image reasoning.
- High-volume production tasks where cost-efficiency and speed balance with capability.
- Custom fine-tuning or open-weight models for on-premise deployment.

## When NOT to pick OPENAI
- Real-time web search without tools; use Perplexity for native internet access and citations.
- Ultra-low latency audio/video generation at scale; Gemini offers better multimodal efficiency.
- Fully open-source local inference; Ollama supports uncensored local models without API costs.

## Model families

### GPT-5.x
Flagship family for advanced coding, agentic tasks, and reasoning across industries, with configurable compute for precision. Includes pro variants for enhanced responses and codex-optimized for long-horizon programming.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| GPT-5.2 | 200K | 2025-12 | no | no | yes | yes | expensive | Best for agentic tasks [web:47] |
| GPT-5.2 pro | 200K | 2025-12 | no | no | yes | yes | expensive | Smarter, more precise responses |
| GPT-5.2-Codex | 128K | 2025-12 | no | no | no | yes | mid | Optimized for agentic coding |
| GPT-5.1 | 200K | 2025-09 | no | no | yes | yes | mid | Configurable reasoning effort |
| GPT-5 mini | 128K | 2025-09 | no | no | yes | yes | cheap | Cost-efficient for defined tasks |
| GPT-5 nano | 128K | 2025-09 | no | no | yes | yes | cheap | Fastest, most cost-efficient |

### GPT-4.1
Non-reasoning family for general smart tasks, balancing speed and intelligence without heavy compute.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| GPT-4.1 | 128K | 2025-06 | no | no | yes | yes | mid | Smartest non-reasoning model |
| GPT-4.1 mini | 128K | 2025-06 | no | no | yes | yes | cheap | Smaller, faster version |
| GPT-4.1 nano | 128K | 2025-06 | no | no | yes | yes | cheap | Most cost-efficient version |

### o-series
Deep research and reasoning models for complex analysis, with deep-research variants for extended investigation.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| o3-deep-research | 200K | 2025-04 | no | yes | yes | yes | expensive | Most powerful deep research |
| o4-mini-deep-research | 128K | 2025-04 | no | yes | yes | yes | mid | Faster, affordable research |
| o3 | 200K | 2025-04 | no | no | yes | yes | expensive | Complex reasoning tasks |
| o4-mini | 128K | 2025-04 | no | no | yes | yes | cheap | Fast reasoning alternative |

### Open-weight
Permissive Apache 2.0 models for local deployment, focusing on power vs. latency tradeoffs.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| gpt-oss-120b | 128K | 2025-12 | no | no | no | no | n/a | Fits H100 GPU, most powerful |
| gpt-oss-20b | 128K | 2025-12 | no | no | no | no | n/a | Low latency medium model |

## Decision guidance
- Pick `GPT-5.2` when building production agents with long tool chains and high precision needed.
- Pick `GPT-5 mini` for high-volume chat or summarization where cost under $0.01/1K tokens matters.
- Pick `o3-deep-research` for investigative tasks requiring citations and multi-step web-like analysis.
- Pick `GPT-4.1 mini` for quick vision tasks like image captioning without reasoning overhead.
- Pick `gpt-oss-120b` when deploying locally on H100 hardware for privacy-sensitive inference.
- Pick `GPT-5.2-Codex` for autonomous coding sessions exceeding 10K tokens of context.