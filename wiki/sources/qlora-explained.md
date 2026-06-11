---
title: "Summary — QLoRA Explained"
type: source-summary
tags: [qlora, nf4, quantization, vram, gpu]
sources:
  - "[[QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models]]"
published: 2026-03-04
---

# Summary — QLoRA Explained

**QLoRA makes large-model finetuning possible on a single consumer GPU by combining NF4 quantization, double quantization, and paged optimizers.**

Standard INT8/INT4 quantization is lossy because weight distributions are approximately Gaussian but uniform grid quantization wastes bins at the extremes. NF4 (NormalFloat 4) solves this by computing quantile-based boundaries to ensure equal expected occupancy per bin — making it information-theoretically optimal for normally distributed weights. Double quantization quantizes the per-block scaling constants themselves, saving approximately 0.5 bits per parameter. Paged optimizers use CPU RAM as an overflow buffer for optimizer states during gradient accumulation spikes, preventing OOM crashes. Together these allow a frozen 4-bit base model plus 16-bit LoRA adapters to match full 16-bit finetuning quality while freeing roughly 75% of weight VRAM — that freed VRAM is available for activations, longer context, and larger batches. The article also surveys the GPU hardware landscape (A100, H100, consumer 3090/4090) and reviews other quantization formats: GPTQ and AWQ for inference, GGUF for CPU/edge, NF4 for training.

## Key claims
- NF4 places quantile boundaries to match Gaussian weight distributions → [[qlora-and-quantization]]
- Double quantization saves ~0.5 bits/param by quantizing the scaling constants → [[qlora-and-quantization]]
- Paged optimizers use CPU RAM overflow to prevent OOM → [[qlora-and-quantization]]
- 4-bit base + 16-bit adapters ≈ full 16-bit quality; ~75% VRAM freed → [[qlora-and-quantization]]
- Freed weight VRAM expands available KV cache budget → [[kv-cache]]

## Derived concept notes
[[qlora-and-quantization]] · [[kv-cache]]
