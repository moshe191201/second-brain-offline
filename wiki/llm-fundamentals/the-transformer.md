---
title: "The Transformer Architecture"
source: "https://theneuralmaze.substack.com/p/the-finetuning-landscape-a-map-of"
author:
  - "[[Miguel Otero Pedrido]]"
tags:
  - "clippings"
  - "transformers"
---

## Key Takeaways

Understanding the structure of the Transformer architecture is essential before diving into finetuning techniques. The Transformer is the backbone of modern LLMs.

## The Three Transformer Architectures

There are **three different Transformer architectures**, each designed for different kinds of problems:

### 1. Encoder-Only Transformers

**Purpose:** Understanding text, classification, retrieval, semantic similarity.

**How they work:**
- Take an input sequence and turn it into rich representations, one per token
- All tokens attend to each other freely (bidirectional self-attention)
- **No text generation** — only encoding

**Examples:**
- **BERT** — popularized large-scale pretraining via masked language modeling

### 2. Encoder–Decoder Transformers

**Purpose:** Sequence-to-sequence tasks like machine translation, summarization.

**How they work:**
- **Encoder** reads and represents the input sequence
- **Decoder** generates an output sequence, token by token
- Uses **cross-attention** to look at encoder outputs
- Uses **causal self-attention** to avoid peeking at future tokens

**Examples:**
- **T5**
- **BART**

### 3. Decoder-Only Transformers

**Purpose:** Next-token prediction — this is the architecture behind modern LLMs.

**How they work:**
- Remove the encoder entirely
- Rely on a single mechanism: **causal self-attention over a growing sequence of tokens**
- Each token can only attend to tokens that came before it
- Simple objective: **predict the next token**

**Why they're powerful:**
- Learn language, reasoning, and structure
- Perform tasks via prompting (in-context learning)
- Scale remarkably well

> 🙋 *This is the architecture we'll focus on for the rest of the course, because it's the foundation behind today's most capable LLMs.*

---

## References

- [Vaswani et al. (2017) "Attention is all you need"](https://arxiv.org/pdf/1706.03762)
