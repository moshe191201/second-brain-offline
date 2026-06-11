# Graph Report - .  (2026-06-11)

## Corpus Check
- Corpus is ~24,046 words - fits in a single context window. You may not need a graph.

## Summary
- 141 nodes · 268 edges · 8 communities
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 6 edges (avg confidence: 0.73)
- Token cost: 100,000 input · 13,584 output

## Community Hubs (Navigation)
- [[_COMMUNITY_RLHF & Preference Alignment|RLHF & Preference Alignment]]
- [[_COMMUNITY_Quantization & GPU Hardware|Quantization & GPU Hardware]]
- [[_COMMUNITY_Transformer Fundamentals & Pretraining|Transformer Fundamentals & Pretraining]]
- [[_COMMUNITY_Supervised Finetuning & Evaluation|Supervised Finetuning & Evaluation]]
- [[_COMMUNITY_Inference Serving & Batching|Inference Serving & Batching]]
- [[_COMMUNITY_Multimodal Vision & TTS|Multimodal: Vision & TTS]]
- [[_COMMUNITY_GRPO & Reasoning RL|GRPO & Reasoning RL]]
- [[_COMMUNITY_LoRA & Parameter-Efficient Finetuning|LoRA & Parameter-Efficient Finetuning]]

## God Nodes (most connected - your core abstractions)
1. `The Finetuning Landscape - A Map of Modern LLM Training` - 23 edges
2. `QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models` - 23 edges
3. `The RLHF Landscape - Aligning LLMs Beyond SFT` - 21 edges
4. `The Engineer's Guide to Supervised Finetuning` - 20 edges
5. `Beyond Text: A Guide to Vision & TTS Finetuning` - 19 edges
6. `Understanding LoRA from First Principles` - 17 edges
7. `The RL Algorithm Behind DeepSeek's Reasoning Models` - 16 edges
8. `A Practical Guide to LLM Inference at Scale` - 15 edges
9. `LoRA (Low-Rank Adaptation)` - 14 edges
10. `GRPO (Group Relative Policy Optimization)` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Chunked Prefill` --semantically_similar_to--> `Sequence Packing`  [INFERRED] [semantically similar]
  raw/A Practical Guide to LLM Inference at Scale.md → raw/The Engineer's Guide to Supervised Finetuning.md
- `PagedAttention` --semantically_similar_to--> `Paged Optimizers`  [INFERRED] [semantically similar]
  raw/A Practical Guide to LLM Inference at Scale.md → raw/QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models.md
- `RLAIF (RL from AI Feedback)` --semantically_similar_to--> `LLM-as-a-Judge Evaluation`  [INFERRED] [semantically similar]
  raw/The RLHF Landscape - Aligning LLMs Beyond SFT.md → raw/The Engineer's Guide to Supervised Finetuning.md
- `The Engineer's Guide to Supervised Finetuning` --references--> `The Finetuning Landscape - A Map of Modern LLM Training`  [EXTRACTED]
  raw/The Engineer's Guide to Supervised Finetuning.md → raw/The Finetuning Landscape - A Map of Modern LLM Training.md
- `Understanding LoRA from First Principles` --references--> `The Finetuning Landscape - A Map of Modern LLM Training`  [EXTRACTED]
  raw/Understanding LoRA from First Principles.md → raw/The Finetuning Landscape - A Map of Modern LLM Training.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Three-Stage LLM Training Pipeline** — raw_the_finetuning_landscape_a_map_of_modern_llm_training_pretraining, raw_the_engineer_s_guide_to_supervised_finetuning_sft, raw_the_rlhf_landscape_aligning_llms_beyond_sft_rlhf, raw_the_finetuning_landscape_a_map_of_modern_llm_training_llm_training_pipeline [EXTRACTED 1.00]
- **QLoRA Component Stack** — raw_qlora_explained_how_4_bit_quantization_unlocks_frontier_models_qlora, raw_qlora_explained_how_4_bit_quantization_unlocks_frontier_models_nf4, raw_qlora_explained_how_4_bit_quantization_unlocks_frontier_models_double_quantization, raw_qlora_explained_how_4_bit_quantization_unlocks_frontier_models_paged_optimizer, raw_understanding_lora_from_first_principles_lora [EXTRACTED 1.00]
- **GRPO Variant Family** — raw_the_rl_algorithm_behind_deepseek_s_reasoning_models_grpo, raw_the_rl_algorithm_behind_deepseek_s_reasoning_models_dapo, raw_the_rl_algorithm_behind_deepseek_s_reasoning_models_gspo, raw_the_rl_algorithm_behind_deepseek_s_reasoning_models_dr_grpo [EXTRACTED 1.00]

## Communities (8 total, 0 thin omitted)

### Community 0 - "RLHF & Preference Alignment"
Cohesion: 0.17
Nodes (21): InstructGPT, LLM Training Pipeline, The RLHF Landscape - Aligning LLMs Beyond SFT, Advantage Function, Clipped Surrogate Objective, DPO (Direct Preference Optimization), Direct Preference Optimization (Rafailov et al., 2023), Generalized Advantage Estimation (GAE) (+13 more)

### Community 1 - "Quantization & GPU Hardware"
Cohesion: 0.18
Nodes (20): QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models, AdamW Optimizer, AWQ (Activation-aware Weight Quantization), BF16 (Brain Float 16), NVIDIA Blackwell Architecture, Double Quantization, FP8, GGUF (+12 more)

### Community 2 - "Transformer Fundamentals & Pretraining"
Cohesion: 0.18
Nodes (19): The Finetuning Landscape - A Map of Modern LLM Training, Attention Is All You Need (Vaswani et al., 2017), Attention Mechanism, Base Model, BERT, Causal Language Modeling, Continued Pretraining (CPT), Encoder-Decoder Transformers (+11 more)

### Community 3 - "Supervised Finetuning & Evaluation"
Cohesion: 0.15
Nodes (18): The Engineer's Guide to Supervised Finetuning, Agentic SFT, Chain-of-Thought (CoT), Chat Template, Flash Attention 2, GAIA Benchmark, IFEval Benchmark, LIMA Hypothesis (+10 more)

### Community 4 - "Inference Serving & Batching"
Cohesion: 0.24
Nodes (17): A Practical Guide to LLM Inference at Scale, Chunked Prefill, Continuous Batching, Decoding Phase, kvcached, PagedAttention, Prefill-Decode Disaggregation, Prefill Phase (+9 more)

### Community 5 - "Multimodal: Vision & TTS"
Cohesion: 0.23
Nodes (17): Beyond Text: A Guide to Vision & TTS Finetuning, Llama 3B Backbone, Neural Audio Codec, Orpheus-TTS, Projection Layer, Qwen3-VL, Qwen3-VL Technical Report (arXiv 2511.21631), SNAC Codec (+9 more)

### Community 6 - "GRPO & Reasoning RL"
Cohesion: 0.27
Nodes (15): DeepSeek-R1, The RL Algorithm Behind DeepSeek's Reasoning Models, Critic (Value Model), DAPO (Dynamic Advantage Policy Optimization), DeepSeekMath, GRPO Difficulty Bias, Dr. GRPO (GRPO Done Right), Group-Relative Advantage (+7 more)

### Community 7 - "LoRA & Parameter-Efficient Finetuning"
Cohesion: 0.27
Nodes (14): Understanding LoRA from First Principles, Autoencoder, Catastrophic Forgetting, Full Finetuning, Hugging Face peft Library, Intrinsic Rank Hypothesis, LoRA (Low-Rank Adaptation), LoRA Alpha (+6 more)

## Knowledge Gaps
- **8 isolated node(s):** `LSTM`, `IFEval Benchmark`, `GAIA Benchmark`, `SWE-bench`, `INT8 Quantization` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `The Finetuning Landscape - A Map of Modern LLM Training` connect `Transformer Fundamentals & Pretraining` to `RLHF & Preference Alignment`, `Supervised Finetuning & Evaluation`, `Multimodal: Vision & TTS`, `LoRA & Parameter-Efficient Finetuning`?**
  _High betweenness centrality (0.335) - this node is a cross-community bridge._
- **Why does `Beyond Text: A Guide to Vision & TTS Finetuning` connect `Multimodal: Vision & TTS` to `Quantization & GPU Hardware`, `Supervised Finetuning & Evaluation`, `LoRA & Parameter-Efficient Finetuning`?**
  _High betweenness centrality (0.299) - this node is a cross-community bridge._
- **Why does `The Engineer's Guide to Supervised Finetuning` connect `Supervised Finetuning & Evaluation` to `Transformer Fundamentals & Pretraining`, `GRPO & Reasoning RL`?**
  _High betweenness centrality (0.282) - this node is a cross-community bridge._
- **What connects `Encoder-Decoder Transformers`, `LSTM`, `Shift-Right Setup` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._