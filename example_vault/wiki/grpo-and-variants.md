---
title: GRPO and Its Variants (GSPO, DAPO, Dr. GRPO)
type: concept
tags: [grpo, deepseek, rl, reasoning, gspo, dapo]
sources:
  - "[[The RL Algorithm Behind DeepSeek's Reasoning Models]]"
---

# GRPO and Its Variants

**GRPO (Group Relative Policy Optimization)**, pioneered by DeepSeek (DeepSeekMath, DeepSeek-R1), removes PPO's biggest cost: the **critic** (value model), which is policy-sized and doubles memory. The critic is also a poor fit for LLMs, where reward arrives only at sequence end.

**Mechanism:** generate a *group* of 4–8 responses per prompt; score each (reward model or rule-based check); advantage = (score − group mean) / group std. **The group is the baseline** — grading on a curve. The KL penalty is applied separately in the loss, not baked into the reward. Result: 40–60% memory savings, ~1/18th the training cost; 1.5B models trainable on 16 GB VRAM. Ideal for **verifiable rewards** (math, code).

## The cracks at scale

- **Granularity mismatch:** sequence-level reward, token-level importance ratios → compounding variance over long chains; especially bad in MoE (volatile expert routing).
- **Length bias:** per-token loss averaging spreads a wrong answer's penalty thin over long responses — the model learns to **ramble when wrong**.
- **Difficulty bias:** dividing by group std explodes gradients when all responses are right or all wrong (std → 0), over-weighting trivial/impossible prompts.

## The fixes

- **DAPO** — token-level gradient loss, overlong reward shaping, asymmetric "Clip-Higher", dynamic sampling (each group must contain ≥1 correct and ≥1 incorrect response).
- **GSPO** — moves importance sampling to the **sequence level** (geometric mean of token ratios), aligning optimization unit with reward unit; natively stabilizes MoE training (no more Routing Replay).
- **Dr. GRPO** — minimalist: drop the length and std normalizations → unbiased estimator, halts wrong-answer length inflation.

## Related

- [[rlhf-ppo-vs-dpo]] — the PPO bottleneck GRPO solves
- [[supervised-finetuning]] — the cold-start SFT that seeds reasoning before RL
