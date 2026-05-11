# Ollama

## When to pick Ollama
- Offline or air-gapped environments requiring no internet or API calls.
- Cost-free unlimited inference on local hardware without rate limits.
- Privacy-sensitive tasks where data never leaves the device.
- Custom fine-tuned models or uncensored variants for specialized domains.
- Experimentation with many open-weight models without vendor lock-in.

## When NOT to pick Ollama
- Tasks needing live web access; Perplexity for native search capabilities.
- Frontier reasoning beyond 70B params; OpenAI for o3-level agentic performance.
- Scalable production serving; Google for managed high-throughput multimodal.

## Model families

### Llama 3.3
Meta's latest open family optimized for coding, multilingual tasks, and tool use, runnable on consumer GPUs.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| llama3.3:70b | 128K | 2025-12 | no | no | yes | yes | n/a | Best coding/multilingual [web:72] |
| llama3.3:8b | 128K | 2025-12 | no | no | no | yes | n/a | Fast local inference |

### Qwen 3
Alibaba's efficient family excelling in math, coding, and long-context, with strong multilingual support.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| qwen3:72b | 128K | 2025-12 | no | no | yes | yes | n/a | Top math/coding scores |
| qwen3:14b | 128K | 2025-12 | no | no | yes | yes | n/a | Balanced local performance |

### Mistral Large 3
Mistral AI's high-capability family for reasoning and generation, quantized for efficient local runs.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| mistral-large3:123b | 128K | 2025-11 | no | no | yes | yes | n/a | Strong reasoning 123B |
| mistral-nemo:12b | 128K | 2025-07 | no | no | no | yes | n/a | Fast multilingual |

### Phi-4
Microsoft's small high-quality family for on-device tasks, optimized for speed and accuracy.

| Model ID | Context | Cutoff | Web | Citations | Vision | Tools | Cost | Notes |
|----------|---------|--------|-----|-----------|--------|-------|------|-------|
| phi-4-mini:14b | 128K | 2025-10 | no | no | yes | yes | n/a | Best small model quality |

## CLI model spec format

When invoking Ollama models via `dragoman ask`, the correct format is:

    --connection ollama --model localhost:11434:<model-name>

Example: `localhost:11434:qwen2.5:14b`

The `ollama:<model-name>` prefix form is **not valid** and will fail. Always use the localhost address format.

## Decision guidance
- Pick `llama3.3:70b` when coding or multilingual tasks need high accuracy on RTX 4090.
- Pick `qwen3:14b` for math/reasoning on mid-range hardware like RTX 4070.
- Pick `mistral-nemo:12b` for fast local chat in non-English languages.
- Pick `phi-4-mini:14b` for on-device mobile or edge inference.
- Pick 70B models when hardware supports >40GB VRAM for near-frontier performance.