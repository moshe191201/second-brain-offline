---
title: LLM Inference at Scale
type: concept
tags: [inference, serving, vllm, batching]
sources:
  - "[[A Practical Guide to LLM Inference at Scale]]"
---

# LLM Inference at Scale

**LLM inference is a resource-management problem disguised as a generation task.** Every request has two computationally opposite phases fighting over one GPU:

- **Prefill** — process the whole prompt in one parallel pass. **Compute-bound.** Metric: **TTFT** (time to first token). Produces the initial [[kv-cache]].
- **Decode** — generate one token at a time using the cache. **Memory-bandwidth bound.** Metric: **TPOT** (time per output token).

The history of serving is a chain of patches, each fixing the previous one's flaw:

1. **Static batching** — batch fixed groups; everyone waits for the longest sequence. Severe GPU idle.
2. **Continuous batching** (iteration-level scheduling) — swap finished sequences out per step; ragged batching + attention masks instead of padding. New problem: **prefill-decode interference** (long prompts stall everyone's TPOT).
3. **Chunked prefill** — split prompts into token-budgeted chunks, piggyback on decode batches. Smooths TPOT at the cost of TTFT and quadratic HBM re-reads.
4. **Prefill-decode disaggregation** — separate GPUs per phase, scaled independently. New bottleneck: shipping multi-GB KV caches across the network (needs ~90 Gbps or NVLink-aware placement).

## Frameworks

- **vLLM** — continuous batching + **PagedAttention** (OS-style paging of the KV cache; <4% fragmentation vs up to 80%; up to ~24× throughput vs naive serving).
- **kvcached** — virtual-memory abstraction for the cache: reserve address space, map physical memory on demand → elastic multi-LLM GPU sharing, serverless cold starts, 2–28× TTFT gains on bursty workloads.

## Related

- [[kv-cache]] · [[qlora-and-quantization]] (4-bit weights reclaim cache space) · [[the-llm-training-pipeline]]
