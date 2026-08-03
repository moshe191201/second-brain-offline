---
title: LoRA — Low-Rank Adaptation
type: concept
tags: [lora, peft, finetuning, low-rank]
sources:
  - "[[Understanding LoRA from First Principles]]"
---

# LoRA — Low-Rank Adaptation

**LoRA** (Microsoft, 2021) is the default parameter-efficient finetuning (PEFT) method. Core hypothesis (**intrinsic rank hypothesis**): the weight *update* ΔW from finetuning lives in a low-dimensional subspace — analogous to how autoencoders compress high-dimensional data into a small latent space.

Instead of full finetuning `W' = W + ΔW`, LoRA factorizes: `W' = W + (α/r)·BA`, with `W` **frozen** and only the small matrices `A`, `B` trainable.

## Why full finetuning hurts

1. **VRAM** — gradients + Adam states + weights ≈ 16 bytes/param ([[qlora-and-quantization]]).
2. **Catastrophic forgetting** — unconstrained updates overwrite general capability when adapting to a narrow domain.

## Stability tricks

- **B initialized to zero** → BA = 0 at start; model begins exactly as the base model.
- **α/r scaling** decouples rank choice from update magnitude.

## Hyperparameters

- **Rank `r`** — capacity of the update. 8–32 works for most instruction tuning; higher = more capacity, more memory, more overfitting risk.
- **Alpha** — update strength; common choices α = r or 2r.
- **Learning rate** — still critical; controls optimization dynamics.
- **Target modules** — which projections get adapters: `q/k/v/o_proj` (attention) and `gate/up/down_proj` (MLP). Targeting all major linear layers approaches full-finetuning quality.

## Related

- [[qlora-and-quantization]] — 4-bit frozen base + LoRA adapters
- [[the-transformer-architectures]] — where the target matrices live
- [[multimodal-finetuning-vision-tts]] — same adapters on VLM/TTS backbones
