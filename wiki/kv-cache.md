---
title: KV Cache
type: concept
tags: [kv-cache, inference, memory, attention]
sources:
  - "[[QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models]]"
  - "[[A Practical Guide to LLM Inference at Scale]]"
---

# KV Cache

The **KV cache** stores the key/value tensors of all previous tokens so attention doesn't recompute them each step — turning per-token generation cost from quadratic to linear. It is the LLM's "short-term working memory" and the central resource constraint in serving.

- Size scales with sequence length × batch size × layers × hidden dim. A 70B model can consume ~2.5 GB per 4k-context request — concurrency hits a hard VRAM ceiling.
- Decoding is **memory-bandwidth bound**: the GPU spends most time moving weights + cache from HBM to SRAM, not computing.
- **GQA** (fewer KV heads) and 4-bit base weights ([[qlora-and-quantization]]) shrink the static footprint, shifting the bottleneck "from the model to the context".

Managing the cache spawned an OS-inspired lineage: **PagedAttention** (vLLM — non-contiguous fixed-size pages, <4% fragmentation) and **kvcached** (virtual-address-space reservation, on-demand physical mapping, elastic multi-LLM GPU sharing). In disaggregated serving, transferring the cache between prefill and decode GPUs becomes the new bottleneck (a 512-token request on a 66B model > 1 GB).

## Related

- [[llm-inference-at-scale]] — the full serving stack
- [[the-transformer-architectures]] — why causal attention needs it
