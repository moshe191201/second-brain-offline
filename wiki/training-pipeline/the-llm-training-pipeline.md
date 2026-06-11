---
title: "The LLM Training Pipeline"
source: "https://theneuralmaze.substack.com/p/the-finetuning-landscape-a-map-of"
author:
  - "[[Miguel Otero Pedrido]]"
tags:
  - "clippings"
  - "training"
---

## Key Takeaways

Modern LLMs follow a well-defined multi-stage training pipeline. Understanding this pipeline is essential before diving into finetuning techniques.

### The Three-Stage Framework

The industry standard (popularized by **InstructGPT in 2022**) consists of:

1. **Pretraining** — on large-scale, raw text data
2. **Supervised Fine-Tuning (SFT)** — on high-quality, task-oriented examples
3. **Alignment via RLHF** — Reinforcement Learning from Human Feedback

This combination proved far more effective than pretraining alone and laid the foundation for systems like ChatGPT.

### Alternative: The Two-Phase View

A broader conceptual view is also common:

- **Pretraining** — builds general-purpose language capabilities
  - Post-training refines and adapts those capabilities
- **Post-training** — SFT + RLHF

Both perspectives describe roughly the same process. The difference is mostly conceptual.

## Stage 1: Pretraining

**Objective:** Self-supervised next-token prediction (causal language modeling)

**What the model learns:**
- Grammar and syntax
- Style and structure
- Facts and common sense
- Code patterns
- Multilingual capabilities (if trained on multilingual data)

> 🌎 *This is why pretraining is often described as the phase where the model "learns the world."*

**Output:** A **base model** (or **foundation model**)

- Extremely good at **continuing text**
- Has absorbed broad language patterns, facts, world knowledge
- **Can't reliably** follow instructions, decide when to refuse, or optimize for helpfulness/safety

### The LLM Training Pipeline Diagram

The pipeline shows the three stages connected:

```
Pretraining → SFT → RLHF
```

### Stage 2: Supervised Fine-Tuning (SFT)

**Purpose:** Teach the model how to follow instructions and behave like a helpful assistant.

**Data:** High-quality, task-oriented examples with clear user prompts and assistant responses.

### Stage 3: RLHF

**Purpose:** Align the model with human preferences.

**How it works:** Instead of showing the model what to say, RLHF teaches it **what humans prefer over others** using comparative judgments.

## Visual Resources

- Watch Daniel Han's **"LLM Training Pipeline"** video (first 20 minutes) for one of the best explanations available.

---

## Next Steps

Now that you understand the full LLM training pipeline, we'll zoom in on each stage in the following lessons:

- **Lesson 2:** Supervised Fine-Tuning
- **Lesson 5:** Reinforcement Learning from Human Feedback (RLHF)

---

## References

- [OpenAI "Aligning language models to follow instructions" (2022)](https://openai.com/index/instruction-following/)
- [Comet Blog "Pretraining: Breaking Down the Modern LLM Training Pipeline" (2025)](https://www.comet.com/site/blog/pretraining/)
- [Chip Huyen "RLHF: Reinforcement learning from human feedback" (2023)](https://huyenchip.com/2023/05/02/rlhf.html)
- [NVIDIA "AI scaling laws: What they are and why they matter" (2023)](https://blogs.nvidia.com/blog/ai-scaling-laws/)
