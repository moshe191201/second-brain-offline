---
title: The LLM Training Pipeline
type: concept
tags: [llm, training, pipeline, map]
sources:
  - "[[The Finetuning Landscape - A Map of Modern LLM Training]]"
  - "[[The RLHF Landscape - Aligning LLMs Beyond SFT]]"
---

# The LLM Training Pipeline

Modern LLM training follows a **three-stage pipeline**, formalized by OpenAI's InstructGPT (2022):

1. **Pretraining** — self-supervised next-token prediction on massive raw text. Builds language, world knowledge, and raw capability. See [[pretraining-and-base-models]].
2. **Supervised Fine-Tuning (SFT)** — curated demonstrations teach structure, turn-taking, and instruction-following. See [[supervised-finetuning]].
3. **Alignment (RLHF)** — preference-based optimization (PPO, DPO, GRPO) teaches what humans actually *prefer*. See [[rlhf-ppo-vs-dpo]] and [[grpo-and-variants]].

A broader two-phase framing is also common: **pretraining** (build capability) vs **post-training** (shape and align it).

## Layered mental model

- **CPT builds knowledge** — the encyclopedia.
- **SFT shapes behavior** — the persona and conversational rules.
- **RL refines alignment** — accuracy, coherence, preference matching.

Each stage builds on the previous. RL cannot invent behaviors (e.g., reasoning) that SFT never seeded — DeepSeek-R1 needed a "cold start" SFT phase on chain-of-thought data before RL could refine it.

## Efficiency layer

Orthogonal to the stages, parameter-efficient methods make them affordable: [[lora]] (train low-rank adapters), [[qlora-and-quantization]] (4-bit frozen base + 16-bit adapters). Serving the result is its own discipline: [[llm-inference-at-scale]].

## Related

- [[the-transformer-architectures]] — the substrate all stages train
- [[multimodal-finetuning-vision-tts]] — same pipeline, non-text modalities
