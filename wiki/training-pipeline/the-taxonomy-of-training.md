---
title: "The Taxonomy of Training"
source: "https://theneuralmaze.substack.com/p/the-engineers-guide-to-supervised-finetuning"
author:
  - "[[Miguel Otero Pedrido]]"
tags:
  - "clippings"
  - "training"
---

## Key Takeaways

Common misinterpretations of the training pipeline:

### Myth 1: "Instruct Models" and "Reasoning Models" are different species

**Reality:** They're not. It's the same SFT process with different data.

- If you SFT on short answers → model produces short answers
- If you SFT on reasoning traces → model produces reasoning traces

> The difference comes from the data, not from some new underlying algorithm.

### Myth 2: Reinforcement Learning is what makes models "think"

**Reality:** SFT teaches the model **what reasoning looks like** by exposing it to examples of structured reasoning.

> 🙋 *SFT is what gives the model the structure of reasoning. RL comes later to reinforce good behavior and discourage bad shortcuts.*

### The Layered View

Think of the training process as layers:

1. **Continued Pretraining (CPT)** — builds broad knowledge (the encyclopedia)
2. **Supervised Fine-Tuning (SFT)** — shapes behavior (the persona and rules)
3. **Reinforcement Learning (RL)** — refines alignment (encourages accuracy, coherence, preference matching)

**Each stage builds on the previous one.** Together, they move the system from raw statistical patterns toward structured, aligned behavior.

---

## References

- [DeepSeek-R1 paper](https://arxiv.org/pdf/2501.12948)
