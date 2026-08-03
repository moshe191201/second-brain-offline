---
title: "Summary — The Finetuning Landscape"
type: source-summary
tags: [transformer, pretraining, llm-pipeline]
sources:
  - "[[The Finetuning Landscape - A Map of Modern LLM Training]]"
published: 2026-02-11
---

# Summary — The Finetuning Landscape

**Lesson 1 of 8 establishes the map: all modern LLMs are decoder-only Transformers trained by self-supervised next-token prediction, then shaped by SFT and RL.**

The article traces the history from LSTMs and attention-as-add-on through "Attention Is All You Need," explains the three Transformer families (encoder-only for classification, encoder–decoder for seq2seq, decoder-only for generation), and introduces scaling laws as the empirical foundation for why bigger training runs reliably produce better models. It defines the full LLM pipeline — pretraining builds world knowledge via causal language modeling on trillions of tokens, SFT shapes behavior via instruction data, and alignment (RLHF) further steers outputs toward human preferences. Continued pretraining is presented as a bridge for domain adaptation without rebuilding from scratch. The lesson is intentionally foundational: techniques like LoRA only make sense once you understand what the underlying weight matrix looks like and why it is so large. Attention itself predates the Transformer — it was originally introduced as an add-on to LSTM encoder–decoder architectures to let the model look back at different parts of the input sequence instead of compressing everything into a fixed vector.

## Key claims
- Attention was not invented in the Transformer paper — it preceded it as an LSTM add-on → [[the-transformer-architectures]]
- Decoder-only architecture dominates modern LLMs → [[the-transformer-architectures]]
- Scaling laws make compute, data, and parameters predictably related → [[pretraining-and-base-models]]
- Full pipeline: pretraining → SFT → alignment → [[the-llm-training-pipeline]]

## Derived concept notes
[[the-llm-training-pipeline]] · [[the-transformer-architectures]] · [[pretraining-and-base-models]]
