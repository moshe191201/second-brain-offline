---
title: Supervised Finetuning (SFT)
type: concept
tags: [sft, finetuning, behavior, instruction-tuning]
sources:
  - "[[The Engineer's Guide to Supervised Finetuning]]"
---

# Supervised Finetuning (SFT)

**SFT is not about adding knowledge — it's about changing behavior.** It teaches a base model structure: roles, boundaries, turn-taking. Special tokens mark where the user ends and the assistant begins; once internalized, the model stops being a text-completion engine and becomes a *participant*.

Key claims:

- **"Instruct models" and "reasoning models" are not different species.** SFT is a training step, not a model type — the difference comes from the data (short answers vs long reasoning traces).
- **RL does not invent reasoning.** SFT seeds the structure of reasoning (A → B → C, with `<think>` traces); RL later reinforces it. DeepSeek-R1's "cold start" SFT phase on chain-of-thought data is the canonical example. See [[grpo-and-variants]].
- **Agentic SFT** teaches tool use via `Thought → Action → Action Input → Observation → Final Response` traces. Format discipline (exact JSON schemas) matters as much as content.

## Evaluation

Low loss can be a *warning sign* (memorized phrasing — "a polished parrot"). The industry instead uses LLM-as-a-judge, instruction-following benchmarks (**IFEval**), and agentic benchmarks (**GAIA**, **SWE-bench**, **WebShop/Mind2Web**). SFT evaluation measures **alignment, not accuracy**.

## Mechanics

See [[loss-masking-and-chat-templates]] for loss masking (`-100`), chat templates, packing, and the shift-right boundary. See [[lima-hypothesis-data-quality]] for data curation.

## Related

- [[the-llm-training-pipeline]] · [[rlhf-ppo-vs-dpo]] · [[lora]]
