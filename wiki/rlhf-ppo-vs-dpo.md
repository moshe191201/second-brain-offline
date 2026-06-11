---
title: RLHF — PPO vs DPO
type: concept
tags: [rlhf, ppo, dpo, alignment, rl]
sources:
  - "[[The RLHF Landscape - Aligning LLMs Beyond SFT]]"
---

# RLHF — PPO vs DPO

SFT hits a ceiling: the model knows *how* to talk, not *what kind of talking humans value*. **RLHF** trains on comparative judgments ("A is better than B") — a signal with no differentiable path to the parameters, which is why policy-gradient RL is needed at all.

**RL → LLM mapping:** policy = the model · state = prompt + tokens so far · action = next token · reward = score of the full response · episode = one generation.

**Three steps:** collect pairwise human preferences → train a **reward model** as a scalable proxy → optimize the policy with RL, constrained by a **KL penalty** against the SFT baseline (without it the model exploits reward-model quirks).

## PPO (on-policy, the proven heavyweight)

REINFORCE + variance reduction via the **advantage function** (GAE) + the **clipped surrogate objective** (trust region: no catastrophic single-batch updates). Cost: **four models in memory** — actor, critic, reward model, reference model. Best alignment ceiling; used for InstructGPT and frontier models.

## DPO (off-policy, the practical default)

Key insight: the RLHF objective has a **closed-form optimal policy**, so the reward can be reparameterized in terms of the policy itself — reducing alignment to a binary cross-entropy loss over preference pairs. Two models in memory, SFT-like speed, one main hyperparameter (β). Trade-offs: off-policy distribution shift, faster overfitting, lower ceiling than PPO on hard benchmarks.

**Decision rule:** DPO for fast/cheap iteration and getting started; PPO when compute and maximum quality justify it. Many teams stage: DPO → PPO.

**Cross-cutting truths:** preference data quality dominates algorithm choice; the KL constraint strength (β / KL coefficient) is one of the most consequential knobs; reward-model quality caps everything.

Also in the toolkit: **IPO** (overfit-robust DPO), **KTO** (good/bad labels, no pairs), **rejection sampling / Best-of-N**, **RLAIF** (AI judges instead of humans).

## Related

- [[grpo-and-variants]] — critic-free RL for reasoning
- [[supervised-finetuning]] · [[the-llm-training-pipeline]]
