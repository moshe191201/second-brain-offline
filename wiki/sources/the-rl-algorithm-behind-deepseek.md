---
title: "Summary — The RL Algorithm Behind DeepSeek's Reasoning Models"
type: source-summary
tags: [grpo, deepseek, rl, reasoning, dapo, gspo]
sources:
  - "[[The RL Algorithm Behind DeepSeek's Reasoning Models]]"
published: 2026-03-18
---

# Summary — The RL Algorithm Behind DeepSeek's Reasoning Models

**GRPO eliminates the critic by using a group of sampled responses as its own baseline, cutting training cost to roughly 1/18th of PPO — but introduces length bias that DAPO, GSPO, and Dr. GRPO each fix.**

Traditional PPO's critic is a neural network roughly as large as the policy itself. GRPO replaces it by sampling G responses per prompt and computing a reward baseline from the group mean, slashing memory overhead by 40–60% and reducing total training cost to roughly 1/18th of a full PPO run. The article details DeepSeek-R1's training recipe: a cold-start SFT phase on high-quality Chain-of-Thought data seeds step-by-step reasoning (confirming RL cannot invent what SFT never seeded), then GRPO amplifies it with verifiable rewards (math correctness, code execution). However, GRPO's token-level loss averaging creates length bias — rambling wrong answers accumulate fewer per-token penalties than concise wrong answers, perversely training the model to be verbose when uncertain. DAPO fixes this with clip-higher and token-level policy gradient. GSPO replaces per-token loss with a sequence-level KL divergence. Dr. GRPO removes difficulty bias by normalizing rewards per-question. All three preserve GRPO's critic-free economics.

## Key claims
- GRPO cuts cost to ~1/18th of PPO by using group mean reward as baseline → [[grpo-and-variants]]
- 40–60% memory overhead reduction vs PPO → [[grpo-and-variants]]
- Length bias: token-level averaging rewards verbose wrong answers → [[grpo-and-variants]]
- Cold-start SFT still required before GRPO (RL amplifies, not invents) → [[supervised-finetuning]]
- DAPO / GSPO / Dr. GRPO each fix a different GRPO bias → [[grpo-and-variants]]

## Derived concept notes
[[grpo-and-variants]]
