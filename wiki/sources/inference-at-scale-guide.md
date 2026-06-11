---
title: "Summary — A Practical Guide to LLM Inference at Scale"
type: source-summary
tags: [inference, serving, vllm, batching, kv-cache, pagedattention]
sources:
  - "[[A Practical Guide to LLM Inference at Scale]]"
published: 2026-04-01
---

# Summary — A Practical Guide to LLM Inference at Scale

**Inference is a resource-management problem: compute-bound prefill and memory-bound decode fight over the same GPU, and the whole serving stack is a chain of patches negotiating that tension.**

Prefill processes the full prompt in one parallel pass and is compute-bound; its metric is TTFT (time to first token). Decode generates one token at a time using the KV cache and is memory-bandwidth-bound; its metric is TPOT (time per output token). Static batching wastes GPU time by making all sequences wait for the longest one. Continuous batching (iteration-level scheduling) fixes utilization but causes prefill-decode interference — long prompts stall everyone's TPOT. Chunked prefill splits prompts into token-budgeted chunks to smooth TPOT at the cost of TTFT and re-reading HBM. Prefill-decode disaggregation puts each phase on separate GPUs scaled independently, but ships multi-GB KV caches across the network, demanding ~90 Gbps. vLLM addresses memory waste with PagedAttention (OS-style KV cache paging): limits fragmentation to under 4% vs up to 80% with naive contiguous allocation, achieving up to ~24× throughput improvement. kvcached adds a virtual-memory abstraction over the KV cache, enabling elastic multi-LLM GPU sharing, true serverless cold starts, and a 2×–28× reduction in TTFT on bursty workloads.

## Key claims
- Prefill = compute-bound (TTFT); decode = memory-bandwidth-bound (TPOT) → [[llm-inference-at-scale]]
- PagedAttention: <4% fragmentation vs up to 80% naive; up to ~24× throughput → [[llm-inference-at-scale]]
- Disaggregation requires ~90 Gbps for KV cache network transfer → [[llm-inference-at-scale]]
- kvcached: 2×–28× TTFT reduction via virtual memory over KV cache → [[llm-inference-at-scale]]
- Shrinking static weights (quantization) frees VRAM for the KV cache → [[kv-cache]]

## Derived concept notes
[[llm-inference-at-scale]] · [[kv-cache]]
