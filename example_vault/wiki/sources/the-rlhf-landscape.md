---
title: "Summary — The RLHF Landscape"
type: source-summary
tags: [rlhf, ppo, dpo, reward-model, alignment]
sources:
  - "[[The RLHF Landscape - Aligning LLMs Beyond SFT]]"
published: 2026-03-11
---

# Summary — The RLHF Landscape

**RLHF exists because human preference ("A is better than B") is not differentiable; PPO and DPO are the two dominant solutions, with different cost/quality trade-offs.**

SFT cannot optimize preferences directly — it teaches imitation, not judgment. RLHF introduces a reward model trained on pairwise preference data (human annotators rank model outputs), then uses RL to maximize the learned reward while a KL divergence penalty against the SFT reference policy prevents the model from exploiting the reward model with degenerate outputs. PPO requires four models in memory simultaneously — actor, reference policy, critic (value model), and reward model — making it expensive but capable of the highest quality ceiling. DPO re-derives the reward model in closed form from preference pairs, eliminating the separate reward model and critic; it uses only two models and standard supervised cross-entropy loss, at the cost of sensitivity to data quality and less flexibility in the reward signal. The KL penalty against the SFT baseline is identified as the single most consequential hyperparameter. The article also covers IPO (fixing DPO's overfitting tendency), KTO (binary bandit feedback without preference pairs), and RLAIF (AI-generated preferences via LLM-as-Judge).

## Key claims
- PPO requires four models in memory simultaneously → [[rlhf-ppo-vs-dpo]]
- DPO: closed-form, two models, standard cross-entropy loss → [[rlhf-ppo-vs-dpo]]
- KL penalty against SFT reference is the most important knob in either algorithm → [[rlhf-ppo-vs-dpo]]
- RLAIF uses LLM-as-Judge to generate preferences without human annotators → [[rlhf-ppo-vs-dpo]]

## Derived concept notes
[[rlhf-ppo-vs-dpo]]
