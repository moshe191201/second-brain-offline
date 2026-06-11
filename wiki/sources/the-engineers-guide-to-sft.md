---
title: "Summary — The Engineer's Guide to Supervised Finetuning"
type: source-summary
tags: [sft, loss-masking, chat-templates, lima]
sources:
  - "[[The Engineer's Guide to Supervised Finetuning]]"
published: 2026-02-18
---

# Summary — The Engineer's Guide to Supervised Finetuning

**SFT teaches behavioral patterns — roles, turn-taking, structure — not new factual knowledge; the two key mechanics are loss masking and chat templates.**

The article argues SFT changes behavior, not world knowledge: the model already knows facts from pretraining; SFT teaches it how to respond. Loss masking sets all non-assistant tokens to `-100` (PyTorch's `CrossEntropyLoss` ignore_index) so the model only learns to predict its own outputs. Chat templates (Jinja2 strings, e.g. Qwen3's) format multi-turn conversations into a single token sequence; train/deploy template mismatch is flagged as a top real-world failure mode. The LIMA hypothesis is introduced: around a thousand carefully curated, high-quality examples can outperform models trained on tens of thousands of noisy ones — data mixture design is the engineer's core job. DeepSeek-R1's cold-start SFT on high-quality chain-of-thought data shows that RL cannot invent reasoning that SFT never seeded. The article covers sequence packing for compute efficiency, agentic SFT for tool-use and multi-step reasoning, and evaluation via qualitative review, LLM-as-judge, and benchmark suites.

## Key claims
- Loss masking: `-100` is `CrossEntropyLoss` ignore_index, applied to user tokens → [[loss-masking-and-chat-templates]]
- Chat template train/deploy mismatch is a top production failure mode → [[loss-masking-and-chat-templates]]
- LIMA: ~1k curated examples beats tens of thousands of noisy ones → [[lima-hypothesis-data-quality]]
- Cold-start SFT seeds reasoning that RL then refines → [[supervised-finetuning]]

## Derived concept notes
[[supervised-finetuning]] · [[loss-masking-and-chat-templates]] · [[lima-hypothesis-data-quality]]
