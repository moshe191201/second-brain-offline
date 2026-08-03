---
title: Pretraining and Base Models
type: concept
tags: [pretraining, base-model, cpt, self-supervised]
sources:
  - "[[The Finetuning Landscape - A Map of Modern LLM Training]]"
---

# Pretraining and Base Models

Pretraining trains a decoder-only Transformer on **causal language modeling** (predict the next token) over raw text. It is **self-supervised** — the next token *is* the label — which is what makes it scalable to internet-sized corpora. It consumes the vast majority of a model's training compute and is where the model "learns the world": grammar, facts, code patterns, multilingual ability.

The output is a **base model**: excellent at continuing text, unable to reliably follow instructions, refuse requests, or behave safely (Chip Huyen's "Shoggoth" image). Post-training ([[supervised-finetuning]], [[rlhf-ppo-vs-dpo]]) shapes — it does not create — these capabilities.

## Continued Pretraining (CPT)

You rarely pretrain from scratch. **CPT** extends an existing base model on new data. Use it when:

- adding **domain knowledge** (legal, medical text)
- supporting an **underrepresented language**
- your data distribution differs strongly from the original corpus

CPT vs SFT is a difference in *consumption*: CPT is a buffet (loss on every token, aggressive packing for throughput); SFT is a multi-course meal where boundaries matter. See [[loss-masking-and-chat-templates]].

## Related

- [[the-transformer-architectures]]
- [[the-llm-training-pipeline]]
