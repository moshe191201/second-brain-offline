---
title: The LIMA Hypothesis — Data Quality over Quantity
type: concept
tags: [data-curation, lima, sft, dataset]
sources:
  - "[[The Engineer's Guide to Supervised Finetuning]]"
---

# The LIMA Hypothesis — Data Quality over Quantity

**LIMA (Less Is More for Alignment)** showed ~1,000 carefully curated examples can outperform tens of thousands of noisy ones for SFT.

Consequences:

- If CPT is about **scale**, SFT is about **precision**. The engineer's job shifts from watching loss curves to **designing the data mixture** — composition, not collection.
- A strong SFT mix balances math reasoning, high-quality code, conversational tone, and safety samples. The model absorbs *patterns of behavior*: sloppy reasoning or inconsistent formatting in the data becomes the model's norm.
- Labs increasingly use **synthetic pipelines**: strong teacher models generate examples, then aggressive filtering. The goal is **density** — maximum useful structure per example.

The same principle echoes in RLHF: "Get the data right first, then worry about the algorithm" ([[rlhf-ppo-vs-dpo]]).

## Related

- [[supervised-finetuning]] · [[lima-hypothesis-data-quality]] source: LIMA paper (arXiv 2305.11206)
