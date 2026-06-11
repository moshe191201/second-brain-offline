---
title: "SFT vs CPT"
source: "https://theneuralmaze.substack.com/p/the-engineers-guide-to-supervised-finetuning"
author:
  - "[[Miguel Otero Pedrido]]"
tags:
  - "clippings"
  - "training"
  - "sft"
---

## Key Takeaways

The distinction between **Continued Pretraining (CPT)** and **Supervised Fine-Tuning (SFT)** is fundamentally a difference in **how data is consumed**, not just the data itself.

### CPT: The Buffet

- **Goal:** Maximize knowledge absorption per FLOP
- **Data:** Massive, blended corpora (books, articles, forums, code)
- **Loss calculation:** On **every token** in the sequence
- **Strategy:** Pack multiple documents into context window to keep GPUs saturated

> 🙋 CPT is about **scale**. The model eats everything in sight.

### SFT: The Multi-Course Meal

- **Goal:** Change how the model **behaves** (teach structure and intention)
- **Data:** Carefully curated, high-quality examples with clear user-assistant turns
- **Loss calculation:** **Only on assistant tokens** (user tokens masked with -100)
- **Strategy:** Padding-free using Flash Attention 2 and variable lengths

> 🙋 SFT is about **precision**. The order, cleanliness, and boundaries are the entire point.

## The Loss Masking Trick

During SFT, we compute loss only on the Assistant's tokens by setting User token labels to **-100** (the `ignore_index` in PyTorch's `CrossEntropyLoss`).

> *Process the User's prompt to understand the context, but do not try to learn how to predict it. Only learn how to respond.*

## The Packing Paradox

| Phase   | Packing Strategy      | Reason                                           |
| :------ | :-------------------- | :----------------------------------------------- |
| CPT     | Aggressive packing     | Keep GPUs saturated with data                    |
| SFT     | **Avoid packing**      | Prevent cross-contamination between conversations |

If conversations are packed too tightly in SFT, the model's attention can leak, confusing the context of one dialogue with another.

### Solution: Variable Length Sequences

Modern trainers use **"Padding-Free SFT"** with:

- **Flash Attention 2**
- **Variable Length (Varlen)** sequences
- A `cu_seqlens` tensor that tells the GPU how many tokens to process for each sequence

This allows batching conversations of different lengths while maintaining a hard firewall between them.

## What SFT Actually Does

> 🙋 *We're not filling the model with new facts. We're teaching it how to respond in a structured way.*

SFT:

1. Teaches **structure** — roles, boundaries, turn-taking
2. Teaches **intention** — what is input vs. response
3. Shapes **behavior** — helpfulness, safety, tone

**It doesn't add knowledge.** It changes the model's behavior by changing its next-token prediction probabilities.

---

## References

- The LLM Training Pipeline (previous lesson in this series)
