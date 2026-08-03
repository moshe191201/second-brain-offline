---
title: "Chinese frontier models compared: GLM-5, MiniMax M2.5 & M2.7, Kimi K2.5, Qwen 3.5, and MiMo-V2-Pro"
source: "https://www.maniac.ai/blog/chinese-frontier-models-compared-glm5-minimax-kimi-qwen"
author:
  - "[[Maniac]]"
published: 2026-02-28
created: 2026-06-28
description: "A benchmark-driven comparison of leading Chinese foundation models against Claude Opus 4.6, with Vals AI scores, March 2026 updates for MiniMax M2.7 and Xiaomi MiMo-V2-Pro, pricing, and production guidance."
tags:
  - "clippings"
---
\[ Next step \]

## Turn model comparisons into production wins

Benchmarks are a starting point. Maniac helps you evaluate and route models on your real traffic, so you ship the best quality per dollar on the workloads that matter.

**Last updated March 25, 2026.** This post now includes **MiniMax M2.7** with fresh numbers from [Vals AI](https://www.vals.ai/models/minimax_MiniMax-M2.7), and **Xiaomi MiMo-V2-Pro** (released as **Hunter Alpha** on OpenRouter during early testing). MiMo is not on Vals yet; we cite **Artificial Analysis** (via [OpenRouter](https://openrouter.ai/xiaomi/mimo-v2-pro-20260318/benchmarks)) and [Xiaomi](https://mimo.xiaomi.com/mimo-v2-pro) for those rows.

February 2026 was a landmark month for Chinese AI labs. Within weeks of each other, several models shipped that compete with, and in some cases exceed, Western frontier systems on standardized benchmarks, at a fraction of the API cost. For anyone running AI in production, the model landscape just got a lot more interesting.

This article compares **GLM-5** (Zhipu AI), **MiniMax M2.5** and **MiniMax M2.7** (MiniMax), **Kimi K2.5** (Moonshot AI), **Qwen 3.5** (Alibaba), and **MiMo-V2-Pro** (Xiaomi) against **Claude Opus 4.6** across coding, math, reasoning, agentic tasks, and multimodal benchmarks. Where noted, scores come from [Vals AI](https://www.vals.ai/), which runs every model through the same standardized evaluation harness, no cherry-picked lab numbers.

## Quick links

- **March 2026 update**, Jump to MiniMax M2.7 & MiMo-V2-Pro
- **Benchmark tables**, Jump to Head-to-head benchmarks
- **Pricing**, Jump to Pricing comparison
- **Decision guide**, Jump to When to use which model
- **Inference infrastructure**, See [Inference stacks compared](https://www.maniac.ai/blog/inference-stacks-vllm-tgi-tensorrt)

---

## The models at a glance

| Model | Lab | Total params | Active params | Architecture | Context | License | Release |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Opus 4.6 | Anthropic | Undisclosed | Undisclosed | Dense (assumed) | 200K | Proprietary | Feb 5, 2026 |
| GLM-5 | Zhipu AI | **744B** | 40B | MoE | 137K | MIT | Feb 11, 2026 |
| MiniMax M2.5 | MiniMax | 230B | **10B** | MoE (256E / 8A) | 197K | Open weights | Feb 12, 2026 |
| MiniMax M2.7 | MiniMax | Undisclosed | Undisclosed | MoE (proprietary) | ~197K-205K | Proprietary API | Mar 17, 2026 |
| Kimi K2.5 | Moonshot AI | **1T** | 32B | MoE (384E / 8A) | 262K | Modified MIT | Jan 26, 2026 |
| Qwen 3.5 | Alibaba | 397B | 17B | MoE (hybrid attn) | **991K** | Apache 2.0 | Feb 16, 2026 |
| MiMo-V2-Pro | Xiaomi | **1T+** | **42B** | MoE (hybrid attention) | **1M** | Proprietary API | Mar 18, 2026 |

Every Chinese model above uses a **Mixture-of-Experts (MoE)** architecture, activating only a fraction of total parameters per token. Kimi K2.5 packs 1 trillion total parameters but activates just 32B per forward pass. MiniMax M2.5 takes efficiency further: 10B active parameters producing competitive SWE-bench scores. This is the mechanism behind the dramatic cost gap.

---

## A note on methodology

All Vals AI benchmark scores below come from [Vals AI](https://www.vals.ai/), which uses a **standardized evaluation harness** for every model. For SWE-bench, this means all models run through the same [SWE-Agent](https://github.com/SWE-agent/SWE-agent) framework, no custom harnesses or optimized prompts.

This matters. Labs frequently report higher scores using their own optimized setups. For example, Anthropic reports 80.8% on SWE-bench using a custom harness, while Vals AI measures 79.20% using SWE-Agent. The vals.ai numbers are the apples-to-apples comparison.

---

## March 2026 update: MiniMax M2.7 and Xiaomi MiMo-V2-Pro

### MiniMax M2.7 (Vals AI)

[MiniMax M2.7](https://www.minimax.io/models/text/m27) shipped **March 17, 2026**. On [Vals AI](https://www.vals.ai/models/minimax_MiniMax-M2.7) it reaches a **Vals Index of 59.58%** (±2.00), up sharply from M2.5's 53.57%, while keeping the same **$0.16/test** sticker on Vals and a **~620s** average latency (Vals). Context is **197K** tokens per Vals (OpenRouter lists up to **204,800**).

MiniMax also reports **56.22% on SWE-Pro**, **57.0% on Terminal Bench 2**, and **55.6% on VIBE-Pro** on its own evaluation setup ([product page](https://www.minimax.io/models/text/m27)); those are **not** the same as Vals's SWE-bench / Terminal-Bench 2.0 harness below.

Head-to-head on **the same Vals harness** as the rest of this article:

| Benchmark | Claude Opus 4.6 | MiniMax M2.5 | MiniMax M2.7 |
| --- | --- | --- | --- |
| Vals Index | **65.98%** | 53.57% | 59.58% |
| SWE-bench | **79.20%** | 70.40% | 73.80% |
| Terminal-Bench 2.0 | **58.43%** | 41.57% | 47.19% |
| LiveCodeBench v6 | **84.68%** | 79.21% | 79.93% |
| AIME | **95.63%** | 88.75% | 91.04% |
| GPQA | **89.65%** | 82.07% | 86.62% |
| MMLU-Pro | **89.11%** | 80.09% | 80.43% |
| IOI | \- | 6.67% | 4.92% |

M2.7 narrows the SWE-bench gap to Opus by **~5.4 points** versus M2.5, and lifts math (AIME) and knowledge (GPQA, MMLU-Pro) materially. Terminal-Bench 2.0 improves but Opus still leads by **~11 points**.

### MiMo-V2-Pro / Hunter Alpha (not on Vals)

**MiMo-V2-Pro** is [not listed on Vals AI](https://www.vals.ai/) as of this update. For directional comparison we use **Artificial Analysis** metrics republished on [OpenRouter](https://openrouter.ai/xiaomi/mimo-v2-pro-20260318/benchmarks) (March 2026). That suite uses different tasks than Vals (for example **Terminal-Bench Hard** vs Vals's **Terminal-Bench 2.0**), so **do not** treat these cells as directly comparable to the main tables above.

| Metric (Artificial Analysis) | MiMo-V2-Pro |
| --- | --- |
| Intelligence Index | 49.2 |
| Agentic Index | 62.8 |
| Coding Index | 41.4 |
| GPQA Diamond | 87.0% |
| Terminal-Bench Hard | 40.9% |
| SciCode | 42.5% |
| Humanity's Last Exam | 28.3% |
| IFBench | 68.8% |
| τ²-Bench Telecom | 95.0% |
| AA-LCR (long-context reasoning) | 60.7% |
| GDPval-AA | 46.4% |

Xiaomi additionally reports strong **agent** benchmarks on **PinchBench** (**81.0** avg., #3 globally) and **ClawEval** (**61.5**, approaching Opus **66.3**) on [MiMo-V2-Pro](https://mimo.xiaomi.com/mimo-v2-pro). Pricing starts at **$1 / $3 per 1M tokens** (256K context tier) on their API, with higher rates above 256K context.

---

## Head-to-head benchmarks

Bold scores indicate the best result in each row. Dashes indicate the model was not evaluated on that benchmark by Vals AI.

### Coding

| Benchmark | Claude Opus 4.6 | GLM-5 | MiniMax M2.5 | Kimi K2.5 | Qwen 3.5 |
| --- | --- | --- | --- | --- | --- |
| SWE-bench | **79.20%** | 67.80% | 70.40% | 68.60% | 70.40% |
| LiveCodeBench v6 | 84.68% | 81.87% | 79.21% | 83.87% | **85.33%** |
| Terminal-Bench 2.0 | **58.43%** | 49.44% | 41.57% | 40.45% | 41.57% |
| IOI | \- | 22.00% | 6.67% | 17.67% | \- |

*SWE-bench: resolving real GitHub issues. LiveCodeBench: competitive programming. Terminal-Bench: command-line task execution. IOI: International Olympiad in Informatics.*

Claude Opus 4.6 leads SWE-bench decisively at 79.20%, 9+ points ahead of every Chinese model in this table. On the standardized harness, the gap is wider than lab-reported numbers suggest.

LiveCodeBench tells a different story. Qwen 3.5 (85.33%) actually edges out Claude Opus 4.6 (84.68%), with Kimi K2.5 (83.87%) and GLM-5 (81.87%) also competitive. Competitive programming is a clear strength for Chinese models.

Terminal-Bench 2.0, real-world command-line tasks, remains a stronghold for Claude Opus 4.6 (58.43%). The Chinese models cluster between 40-49%, with GLM-5 performing best among them at 49.44%.

IOI (olympiad-level algorithmic problems) shows GLM-5 at 22.00% and MiniMax M2.5 at just 6.67%. Deep algorithmic reasoning remains a challenge for MoE architectures.

### Math & reasoning

| Benchmark | Claude Opus 4.6 | GLM-5 | MiniMax M2.5 | Kimi K2.5 | Qwen 3.5 |
| --- | --- | --- | --- | --- | --- |
| AIME | **95.63%** | 91.67% | 88.75% | **95.63%** | 86.04% |
| GPQA Diamond | **89.65%** | 83.33% | 82.07% | 84.09% | 87.37% |
| MMLU-Pro | **89.11%** | 86.03% | 80.09% | \- | 87.18% |

*AIME: competition math (8 runs averaged). GPQA: PhD-level science. MMLU-Pro: graduate-level knowledge across 14 disciplines.*

Claude Opus 4.6 leads on GPQA (89.65%) and MMLU-Pro (89.11%). On AIME, Kimi K2.5 ties Opus at 95.63%, a remarkable result for an open-weight model at a fraction of the cost.

Qwen 3.5 is the strongest Chinese contender on knowledge benchmarks, scoring 87.37% on GPQA and 87.18% on MMLU-Pro, within 2 points of Opus on both. GLM-5 (91.67% AIME) and MiniMax M2.5 (88.75% AIME) are solid but not at the same tier.

### Multimodal

| Benchmark | Claude Opus 4.6 | GLM-5 | MiniMax M2.5 | Kimi K2.5 | Qwen 3.5 |
| --- | --- | --- | --- | --- | --- |
| MMMU | 83.87% | \- | \- | **84.34%** | 22.77%\* |

*MMMU: university-level multimodal reasoning.*

\* *Qwen 3.5's 22.77% MMMU score (last place, 58/58) likely reflects an evaluation issue rather than actual capability, Alibaba reports substantially higher scores using their own harness.*

Kimi K2.5 edges out Claude Opus 4.6 on MMMU (84.34% vs 83.87%), one of the few benchmarks where a Chinese model takes the lead. GLM-5 and MiniMax M2.5 were not evaluated on MMMU by Vals AI.

### Vals Index (overall composite)

The Vals Index is a composite score across multiple enterprise-relevant benchmarks including finance, legal, medical, tax, and coding tasks.

| Model | Vals Index | Cost/Test | Latency |
| --- | --- | --- | --- |
| Claude Opus 4.6 | **65.98%** | $1.00 | 337s |
| GLM-5 | 60.69% | \- | \- |
| MiniMax M2.7 | 59.58% | **$0.16** | 620s |
| Kimi K2.5 | 59.74% | $0.13 | 378s |
| Qwen 3.5 | 57.06% | $0.31 | 575s |
| MiniMax M2.5 | 53.57% | **$0.16** | **264s** |

Claude Opus 4.6 leads the composite at 65.98%. Among Chinese models, GLM-5 (60.69%) and Kimi K2.5 (59.74%) are closest to the frontier; **MiniMax M2.7** (59.58%) now sits in the same band on Vals while staying at **$0.16/test**. MiniMax M2.5 remains the **fastest** in this group (264s) but trails on overall index.

### Enterprise benchmarks (selected)

Vals AI also tests domain-specific enterprise tasks. Here are notable results:

| Benchmark | Claude Opus 4.6 | GLM-5 | MiniMax M2.5 | Kimi K2.5 | Qwen 3.5 |
| --- | --- | --- | --- | --- | --- |
| CorpFin | 67.02% | 62.90% | 59.60% | **68.26%** | 65.31% |
| TaxEval v2 | **75.96%** | 70.03% | 68.15% | 74.20% | \- |
| Finance Agent | **60.05%** | 53.18% | 38.58% | 50.62% | 54.47% |
| MedQA | **95.41%** | 94.27% | 92.53% | 94.37% | 95.21% |
| LegalBench | **85.30%** | 84.06% | 79.96% | \- | 85.10% |

*CorpFin: corporate finance reasoning. TaxEval: tax law. Finance Agent: multi-step financial workflows. MedQA: medical questions. LegalBench: legal reasoning.*

Kimi K2.5 takes #1 on CorpFin (68.26%), beating Claude Opus 4.6. Qwen 3.5 nearly matches Opus on LegalBench (85.10% vs 85.30%) and MedQA (95.21% vs 95.41%). Claude leads most other enterprise benchmarks, but the margins are often slim.

**MiniMax M2.7 (Vals, March 2026):** CorpFin **61.19%**, TaxEval v2 **66.56%**, Finance Agent **48.40%**, LegalBench **83.98%** (see [Vals model page](https://www.vals.ai/models/minimax_MiniMax-M2.7)).

---

## Pricing comparison

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cost vs Opus (input) |
| --- | --- | --- | --- |
| Claude Opus 4.6 | $5.00 | $25.00 | **1x** |
| GLM-5 | $1.00 | $3.20 | 5x cheaper |
| Qwen 3.5 | $0.60 | $3.60 | 8.3x cheaper |
| Kimi K2.5 | $0.60 | $2.00 | 8.3x cheaper |
| MiniMax M2.5 | **$0.30** | **$1.10** | **16.7x cheaper** |
| MiniMax M2.7 | $0.30 | $1.20 | 16.7x cheaper |
| MiMo-V2-Pro (≤256K ctx) | $1.00 | $3.00 | 5x cheaper |

MiniMax M2.5 is **16.7x cheaper** than Claude Opus 4.6 on input tokens and **22.7x cheaper** on output tokens. **M2.7** matches M2.5 on input ($0.30) with slightly higher output ($1.20) per [OpenRouter / Artificial Analysis](https://openrouter.ai/minimax/minimax-m2.7). **MiMo-V2-Pro** is priced closer to mid-tier Western APIs; see [Xiaomi](https://mimo.xiaomi.com/mimo-v2-pro) for 256K-1M context tiers ($2 / $6 per 1M).

### What this means at scale

| Scenario: 1M calls/day (1K tok/call) | Claude Opus 4.6 | GLM-5 | Kimi K2.5 | MiniMax M2.5 |
| --- | --- | --- | --- | --- |
| Daily cost | $5,000 | $1,000 | $600 | **$300** |
| Monthly cost | $150,000 | $30,000 | $18,000 | **$9,000** |
| Annual cost | $1.83M | $365K | $219K | **$110K** |
| Annual savings vs Opus | \- | $1.46M | $1.61M | **$1.72M** |

---

## Architecture deep dives

### GLM-5, Zhipu AI

GLM-5 is trained **entirely on Huawei Ascend 910B chips**, achieving complete independence from NVIDIA hardware. At 744B total / 40B active, it has the highest active parameter count of the Chinese models. It uses DeepSeek Sparse Attention for long-context handling and was trained on 28.5 trillion tokens. Fully MIT-licensed.

On Vals AI, GLM-5 scores highest among Chinese models on SWE-bench (67.80%) and Terminal-Bench (49.44%), suggesting strength in real-world software engineering tasks. Its AIME score (91.67%) is solid but trails Kimi K2.5 by 4 points.

**Strengths:** Highest Vals Index among Chinese models (60.69%), strong SWE-bench, fully open-source, NVIDIA-independent. **Weaknesses:** Low IOI (22.00%), weaker GPQA (83.33%), most expensive Chinese option.

### MiniMax M2.5

The efficiency outlier. MiniMax M2.5 activates just **10 billion parameters** yet achieves 70.40% on SWE-bench, competitive with Qwen 3.5 and only 9 points behind Claude Opus 4.6, while activating a fraction of the parameters.

The model uses 256 experts with 8 active per token across 230B total parameters. At $0.16 per test on Vals AI with 264s average latency, it is the cheapest and fastest model in the entire comparison.

**Strengths:** Lowest cost ($0.16/test), fastest latency (264s), strong SWE-bench for its parameter budget. **Weaknesses:** Lowest Vals Index (53.57%), weak IOI (6.67%), trails on enterprise benchmarks.

### MiniMax M2.7

Successor to M2.5, tuned for **agentic** workflows and long-horizon tasks. On Vals, M2.7 lands at **59.58%** Vals Index with the same **$0.16/test** cost label, but **higher latency** (~620s vs 264s for M2.5). SWE-bench rises to **73.80%**, still behind Opus’s **79.20%** on the same harness.

**Strengths:** Large jump vs M2.5 on Vals Index and SWE-bench, strong AIME (91.04%) and GPQA (86.62%) on Vals, competitive API pricing vs Western frontier. **Weaknesses:** Slower on Vals than M2.5, IOI still low (4.92%), proprietary weights.

### Kimi K2.5, Moonshot AI

The largest model at **1 trillion total parameters** (32B active, 384 experts with 8 active per token). Kimi K2.5 is natively multimodal, jointly pre-trained on approximately 15 trillion mixed text and vision tokens.

Its **Agent Swarm** feature orchestrates up to 100 parallel sub-agents, trained via Parallel-Agent Reinforcement Learning (PARL). On Vals AI, it ties Claude Opus 4.6 on AIME (95.63%) and takes #1 on CorpFin (68.26%). Strong MMMU (84.34%) confirms its multimodal capability.

**Strengths:** Best math among Chinese models (AIME: 95.63%), #1 CorpFin, strong MMMU, Agent Swarm parallelism. **Weaknesses:** SWE-bench (68.60%) trails GLM-5, Terminal-Bench (40.45%) is lowest in group.

### Qwen 3.5, Alibaba

The **context window champion** at 991K tokens, nearly 5x Claude Opus 4.6's 200K. At 397B total / 17B active, it uses a hybrid attention mechanism for efficient long-context handling.

On Vals AI, Qwen 3.5 beats Claude Opus 4.6 on LiveCodeBench (85.33% vs 84.68%) and leads among Chinese models on GPQA (87.37%) and MMLU-Pro (87.18%). It ties MiniMax M2.5 on SWE-bench at 70.40%.

**Strengths:** Massive context (991K), strongest GPQA and MMLU-Pro among Chinese models, leads LiveCodeBench. **Weaknesses:** Weakest AIME (86.04%), MMMU evaluation issues, higher latency (575s).

### MiMo-V2-Pro, Xiaomi

Flagship **1T+ total / 42B active** MoE with **1M-token** context, aimed at **agent** stacks (OpenClaw and similar). Publicly traced to the **Hunter Alpha** OpenRouter drop. Benchmarks outside Vals (Artificial Analysis + Xiaomi’s PinchBench / ClawEval story) suggest **strong agentic and long-context positioning**, with API pricing that undercuts Opus but sits above MiniMax.

**Strengths:** 1M context, leading Agentic Index on Artificial Analysis, competitive GPQA Diamond (87.0%), Xiaomi-reported PinchBench / ClawEval tier-1 placement. **Weaknesses:** No Vals row yet for apples-to-apples comparison to the rest of this post, higher list price than MiniMax, proprietary.

---

## When to use which model

**SWE-bench (real-world coding) → Claude Opus 4.6.** At 79.20%, it leads the original five-model table by 9+ points. **MiniMax M2.7** narrows that gap to **~5.4 points** vs M2.5 at the same Vals harness.

**Competitive programming → Qwen 3.5.** At 85.33% on LiveCodeBench, it edges out even Claude Opus 4.6 (84.68%). Kimi K2.5 (83.87%) is also strong here.

**Math → Kimi K2.5.** Ties Claude Opus 4.6 on AIME at 95.63%, at a fraction of the price. **M2.7** is next among MiniMax generations on Vals (91.04% AIME).

**Enterprise tasks → Claude Opus 4.6 or Kimi K2.5.** Opus leads most enterprise benchmarks. Kimi K2.5 takes #1 on CorpFin and is competitive on TaxEval.

**Massive context → Qwen 3.5 or MiMo-V2-Pro.** Qwen 3.5 at 991K tokens is unmatched in this Vals cohort. **MiMo-V2-Pro** advertises **1M** tokens for agent workloads when you need Xiaomi’s stack and integrations.

**Cost optimization → MiniMax M2.5 or M2.7.** Both show **$0.16/test** on Vals; M2.5 is faster, M2.7 scores higher. At published API rates, both remain **order of magnitude** cheaper than Opus for high-volume agents.

**Agent frameworks (OpenClaw-class) → MiMo-V2-Pro (evaluate yourself).** Early Hunter Alpha volume and Xiaomi’s PinchBench / ClawEval numbers make it a sensible candidate to **A/B test** beside Opus; wait for Vals for strict comparison to the tables above.

**General-purpose frontier → Claude Opus 4.6.** Highest Vals Index (65.98%), leads SWE-bench, Terminal-Bench, most enterprise benchmarks.

---

## The bigger picture

The February 2026 wave showed Chinese labs closing the gap; **March 2026** added **MiniMax M2.7** and **MiMo-V2-Pro**, pushing SWE-bench and agent positioning further. On standardized Vals evaluation, Claude Opus 4.6 still leads most benchmarks in the original comparison. The gap is narrowest on math (Kimi K2.5 ties Opus on AIME) and competitive programming (Qwen 3.5 edges Opus on LiveCodeBench). It is widest on software engineering (Opus leads SWE-bench by 9+ points vs the Feb table; **M2.7** shrinks that margin) and terminal tasks.

For teams running high-throughput background agents, the question is: which task are you optimizing for? If it is a well-defined, repetitive task where Chinese models score within a few points of frontier, and it often is, the 5-17x cost savings are real.

That is exactly what Maniac optimizes. We evaluate these models on your production data, fine-tune task-specialized variants, and route to the best quality-per-dollar model, so you get the right answer at a fraction of the cost.

---

*Vals AI scores for GLM-5, MiniMax M2.5, Kimi K2.5, Qwen 3.5, Claude Opus 4.6, and MiniMax M2.7 from [Vals AI](https://www.vals.ai/) as of **March 25, 2026** (M2.7 from its [model page](https://www.vals.ai/models/minimax_MiniMax-M2.7)). MiMo-V2-Pro: Artificial Analysis via [OpenRouter benchmarks](https://openrouter.ai/xiaomi/mimo-v2-pro-20260318/benchmarks); PinchBench / ClawEval figures from [Xiaomi](https://mimo.xiaomi.com/mimo-v2-pro). Pricing from provider pages and OpenRouter as of March 2026.*

\[ Next step \]

## Turn model comparisons into production wins

Benchmarks are a starting point. Maniac helps you evaluate and route models on your real traffic, so you ship the best quality per dollar on the workloads that matter.