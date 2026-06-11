---
title: "Data Curation: The LIMA Hypothesis"
source: "https://theneuralmaze.substack.com/p/the-engineers-guide-to-supervised-finetuning"
author:
  - "[[Miguel Otero Pedrido]]"
tags:
  - "clippings"
  - "data-curation"
  - "sft"
---

## Key Takeaways

### The LIMA Hypothesis

[Less Is More for Alignment](https://arxiv.org/pdf/2305.11206) showed something counterintuitive:

> If CPT was about scale, SFT is about **precision**.

Research demonstrated that a model fine-tuned on **around 1,000 carefully curated, high-quality examples** could outperform models trained on **tens of thousands of noisy examples**.

> And that shift has changed the role of the AI engineer.

The job is no longer just watching loss curves drop. It's about **designing the right data mixture** — less like data collection, more like **composition**.

### What Makes a Strong SFT Dataset

A strong SFT dataset is **balanced**:

- Some mathematical reasoning to sharpen logic
- High-quality code to reinforce structure
- Conversational examples to shape tone and persona
- Safety-aligned samples to anchor behavior

**The mix matters.** Why? Because SFT is sensitive. The model doesn't just absorb facts during fine-tuning — it **absorbs patterns of behavior**.

> If the dataset contains sloppy reasoning, inconsistent formatting, or vague answers, those patterns become normalized. The model treats them as the standard.

### Synthetic Data Pipelines

That's why many labs have moved away from large, scraped instruction datasets and toward **synthetic pipelines**:

1. Generate **high-quality examples** using **strong teacher models**
2. Filter **aggressively**
3. Focus on **density** — packing each example with as much useful structure and clarity as possible

---

## References

- [LIMA paper](https://arxiv.org/pdf/2305.11206)
