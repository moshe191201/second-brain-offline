---
title: Key Takeaways — Finetuning Sessions
type: index
tags: [takeaways, summary]
updated: 2026-06-11
---

# 💡 Key Takeaways

The distilled, cross-cutting insights from the corpus. Each links to the full note.

1. **Training is layered, and layers don't substitute for each other.** Pretraining builds knowledge, SFT shapes behavior, RL refines alignment. RL cannot invent reasoning SFT never seeded (DeepSeek-R1's cold-start). → [[the-llm-training-pipeline]], [[supervised-finetuning]]
2. **SFT changes behavior, not knowledge.** It teaches roles, turn-taking, and structure via chat templates and loss masking (`-100` on non-assistant tokens). Template train/deploy mismatch is a top real-world failure mode. → [[loss-masking-and-chat-templates]]
3. **Data quality beats quantity (LIMA).** ~1k curated examples can beat tens of thousands of noisy ones; the engineer's job is mixture design. Same rule in RLHF: data first, algorithm second. → [[lima-hypothesis-data-quality]]
4. **Finetuning updates are low-rank.** LoRA freezes W and trains a small BA factorization (ranks 8–32 usually suffice); this avoids both the 16-bytes/param VRAM tax and catastrophic forgetting. → [[lora]]
5. **Bits in the right place beat more bits.** QLoRA's NF4 matches the Gaussian shape of weight distributions, making a 4-bit frozen base ≈ 16-bit quality and freeing ~75% of weight VRAM for batch/context. → [[qlora-and-quantization]]
6. **Alignment optimizes preferences, not correctness.** RLHF exists because "A is better than B" isn't differentiable; the KL penalty against the SFT baseline is the most underrated knob. PPO = quality ceiling (4 models in memory); DPO = practicality (2 models, closed-form). → [[rlhf-ppo-vs-dpo]]
7. **GRPO made reasoning RL affordable by deleting the critic** — the group of sampled responses is its own baseline (~1/18th cost). But its token-level math teaches models to *ramble when wrong* (length bias) — fixed by DAPO, GSPO, Dr. GRPO. → [[grpo-and-variants]]
8. **Multimodal finetuning is the same job.** Vision encoders and audio codecs translate the world into tokens; you still just attach LoRA adapters and run SFT. Audio is "just another language" via codec tokens. → [[multimodal-finetuning-vision-tts]]
9. **Inference is a resource-management problem.** Compute-bound prefill vs memory-bound decode fight over one GPU; the whole serving stack (continuous batching → chunked prefill → disaggregation → PagedAttention) negotiates that tension. → [[llm-inference-at-scale]]
10. **The KV cache is the hidden protagonist** connecting quantization, context length, concurrency, and serving cost. Shrink the static weights and you buy dynamic memory. → [[kv-cache]]
