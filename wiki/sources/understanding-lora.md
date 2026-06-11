---
title: "Summary — Understanding LoRA from First Principles"
type: source-summary
tags: [lora, peft, vram, adapters]
sources:
  - "[[Understanding LoRA from First Principles]]"
published: 2026-02-25
---

# Summary — Understanding LoRA from First Principles

**LoRA's central claim: finetuning updates are intrinsically low-rank, so freezing the base weights and training a small BA factorization is sufficient.**

Full finetuning has two problems: VRAM constraints (all gradients and optimizer states for every parameter) and catastrophic forgetting (unguarded weight updates destroy prior knowledge). LoRA freezes W and introduces two thin matrices B (d×r) and A (r×d) with r ≪ d; the update W' = W + (α/r)BA is applied at inference with no extra latency (B and A can be merged back into W). The hyperparameter α controls update strength relative to rank; a common heuristic is α = 2r. The intrinsic dimensionality hypothesis from prior work is the theoretical foundation — finetuning directions live in a low-dimensional subspace of the full weight space. Practical guidance covers rank selection (8–32 usually suffices), target module selection (attention projections yield more improvement per parameter than MLP layers for most tasks), and when to consider higher ranks (long-context tasks, code, multilingual). The article notes that QLoRA extends this approach by quantizing the frozen base to 4-bit, freeing most VRAM for activations and the LoRA adapters.

## Key claims
- Finetuning updates are low-rank — B and A with r≪d suffice → [[lora]]
- W' = W + (α/r)BA; α controls update strength → [[lora]]
- Freezing W prevents catastrophic forgetting → [[lora]]
- B and A can be merged at inference: zero latency overhead → [[lora]]
- QLoRA extends LoRA to 4-bit frozen base → [[qlora-and-quantization]]

## Derived concept notes
[[lora]]
