---
title: The Three Transformer Architectures
type: concept
tags: [transformer, architecture, attention]
sources:
  - "[[The Finetuning Landscape - A Map of Modern LLM Training]]"
---

# The Three Transformer Architectures

Attention predates the Transformer — it began as a weighted lookup (query vs keys → weighted sum of values) added to encoder–decoder RNNs. The Transformer's insight: with **self-attention**, **positional encodings**, and **multi-head attention**, recurrence is unnecessary.

## The three families

| Family | Attention | Strength | Examples |
|---|---|---|---|
| **Encoder-only** | Bidirectional | Understanding, classification, retrieval | BERT |
| **Encoder–decoder** | Cross + causal | Seq-to-seq (translation, summarization) | T5, BART |
| **Decoder-only** | Causal only | Generation; powers modern LLMs | GPT, Claude, Qwen |

Decoder-only dominates because of **scaling laws**: performance improves predictably (power-law) with parameters, data, and compute — and the simple next-token objective scales over unlimited unlabeled text.

Key attention components: scaled dot-product attention `softmax(QKᵀ/√d_k)V`; multi-head attention lets different heads specialize (short- vs long-range, syntax vs semantics).

## Why it matters downstream

- [[lora]] targets the projection matrices (`q_proj`, `k_proj`, `v_proj`, `o_proj`, MLP projections) inside each Transformer block.
- The [[kv-cache]] exists because causal attention must "look back" at all prior tokens.

## Related

- [[pretraining-and-base-models]]
- [[the-llm-training-pipeline]]
