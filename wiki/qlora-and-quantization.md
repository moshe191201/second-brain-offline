---
title: QLoRA and Quantization
type: concept
tags: [qlora, quantization, nf4, vram, gpu]
sources:
  - "[[QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models]]"
---

# QLoRA and Quantization

If [[lora]] reduces *what we train*, **QLoRA** rethinks *how we store what we aren't training*: the frozen base model is quantized to **4-bit**, while 16-bit LoRA adapters handle learning.

## The VRAM arithmetic

Mixed-precision training costs ≈ **16 bytes/parameter**: 2 (weights) + 2 (gradients) + 12 (AdamW: FP32 master copy + momentum + variance). A 70B model → ~1.1 TB before the first token. Every GB of fixed cost is stolen from batch size and [[kv-cache]] (context/concurrency). 4-bit weights cut the static footprint ~75% — and being memory-bound, moving 4× less data also speeds inference.

## QLoRA's three components

1. **NF4 (NormalFloat-4)** — 16 quantization bins spaced to match the Gaussian distribution of NN weights, not linearly. "We don't need more bits; we need the bits in the right place."
2. **Double Quantization** — quantize the quantization constants (+0.37 bits/param saved).
3. **Paged Optimizers** — offload optimizer states to CPU RAM on memory spikes (NVIDIA Unified Memory), preventing OOM crashes.

## Quantization landscape

- **Weights-only formats** (GGUF, GPTQ) store 4-bit but dequantize to 16-bit for compute. **AWQ** protects the ~1% salient weights identified via activations.
- **Microscaling formats**: MXFP4 (power-of-two block scales) and NVIDIA **NVFP4** (E4M3 fractional scales, 16-element blocks) execute natively in 4-bit on Blackwell.
- **Hardware arc**: Turing (FP16 Tensor Cores) → Ampere (BF16/TF32) → Hopper (FP8 Transformer Engine) → Blackwell (native NVFP4) — silicon went from passive container to active compression partner.

## Related

- [[lora]] · [[kv-cache]] · [[llm-inference-at-scale]]
