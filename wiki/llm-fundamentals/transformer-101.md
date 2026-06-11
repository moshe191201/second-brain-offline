---
title: "Transformer 101"
source: "https://theneuralmaze.substack.com/p/the-finetuning-landscape-a-map-of"
author:
  - "[[Miguel Otero Pedrido]]"
tags:
  - "clippings"
  - "transformers"
  - "architecture"
---

## Key Takeaways

- **Attention was invented before Transformers** — first introduced as an improvement to encoder–decoder recurrent models for sequence-to-sequence tasks
- **Transformers are now the standard** — nearly every state-of-the-art language model is built on the Transformer architecture
- **RNNs had limitations** — recurrent neural networks (LSTMs) struggled with long sequences and long-range dependencies

## The Attention Mechanism

- **Weighted lookup mechanism** — attention decides which pieces of information matter most
- **Components**
  - **Keys** — k1, k2, …, kn
  - **Values** — v1, v2, …, vn
  - **Query** — expresses what you're looking for
- **Attention pooling** — compares query against all keys, assigns weights, produces weighted sum of values

> 🙋 *Attention decides which pieces of information matter most, and combines them accordingly.*

## Self-Attention

> ✅ *Self-attention takes this idea one step further.*

Instead of having one sequence attend to another, **each token in a sequence attends to all the other tokens in the same sequence**!

### How Self-Attention Works

1. Every token is turned into a **query (Q)**, **key (K)**, and **value (V)**
2. For each token, its **query** is compared with the **keys of all tokens** (including itself)
3. These comparisons determine how much attention the token pays to every other token
4. The token's new representation is built as a **weighted sum of all values**

### Example

For the sentence "The cat sat on the mat":

- When updating **"sat"**, the model can:
  - Strongly attend to **"cat"** (who is sitting)
  - Attend to **"mat"** (where the action happens)
  - Largely ignore function words like **"the"**

## Positional Encoding

Attention itself has no notion of order. To make sequences meaningful, **positional information is injected into token representations**.

### Implementation

In the original Transformer, positional encodings are built using **sine and cosine functions at different frequencies**:

- **Low-frequency sinusoids** capture coarse position information
- **High-frequency sinusoids** capture fine-grained differences

### Why It Matters

> 🙋 Don't worry if the exact intuition behind sinusoidal positional encodings doesn't fully click. We're mentioning them because they were an important design choice in the original Transformer architecture.

## Multi-Head Attention

### Scaled Dot-Product Attention

The concrete way the Transformer implements attention:

1. Each token produces a **query**, **key**, and **value**
2. Queries are compared with keys using a **dot product**
3. The resulting scores are normalized with a **softmax**
4. These normalized scores are used to compute a weighted sum of the values

**Formula:**

```
Attention(Q, K, V) = softmax(QKᵗ / √dₖ) V
```

### Why Multi-Head?

With a single attention head, the model is forced to average all relationships into one view.

**Multi-head attention removes this constraint.** Different heads can specialize in:

- Short-range vs long-range dependencies
- Syntactic relationships
- Semantic similarity

This allows the model to **jointly attend to information from different representation subspaces**, all at once.

## Key Insight

> 🙋 *But the implications, dear builders, ran much deeper.*

Once you realize that this architecture can:

- Query a set of representations
- Select relevant information dynamically
- Do so in a differentiable and parallelizable way

**You no longer need recurrence at all!**

---

## References

- [Vaswani et al. (2017) "Attention is all you need"](https://arxiv.org/pdf/1706.03762)
- [Colah's Blog "Understanding LSTM Networks"](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)
- [Dive into Deep Learning](https://d2l.ai/)
