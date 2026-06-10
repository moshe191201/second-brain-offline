---
title: "The Finetuning Landscape - A Map of Modern LLM Training"
source: "https://theneuralmaze.substack.com/p/the-finetuning-landscape-a-map-of"
author:
  - "[[Miguel Otero Pedrido]]"
published: 2026-02-11
created: 2026-06-09
description: "Finetuning Sessions · Lesson 1 / 8"
tags:
  - "clippings"
---
![](https://substackcdn.com/image/fetch/$s_!_Yph!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff1909018-fbb6-4a19-8eb3-7cce5c333837_1920x1080.png)

Welcome to **Lesson 1** of the **Finetuning Sessions**!

> 🙋 *Here's a small plot twist: for this first lesson, we're not talking about finetuning!*

Before jumping into techniques like **SFT** or **LoRA**, it's important to understand what happens *before* finetuning ever starts. That's exactly what this lesson is about.

We'll break down what **pretraining** really means, introduce the **Transformer** architecture that modern LLMs are built on, and explain the key differences between **encoder-only**, **encoder–decoder**, and **decoder-only** models.

Along the way, you'll build a clear mental map of the **training pipeline of modern language models**, from pretraining to alignment.

> **✅** ***This context will pay off later.***

Many advanced techniques—e.g. LoRA—only truly make sense once you understand how Transformers work under the hood.

So, think of this lesson as setting the foundation. Once that's in place, everything that follows will click into place much faster.

---

## Transformer 101

![Transformers One (2024) - IMDb](https://substackcdn.com/image/fetch/$s_!dxuS!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F900aa4be-69b0-40a7-a71e-93ccad6c3f02_2108x1186.jpeg)

You know this is the first Transformer that came to mind!

At this point, you've probably heard the word *Transformer* so many times that it feels almost synonymous with "modern AI."

And in practice, that's not far from the truth: today, **nearly every state-of-the-art language model** is built on top of the Transformer architecture.

> 🙋 *But here's a small surprise to kick things off: **attention was not invented in the Transformer paper**!*

![A LSTM neural network.](https://substackcdn.com/image/fetch/$s_!z-yc!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62c76a05-b01a-483c-9645-2b49c007a1fd_2233x839.png)

Before the Transformer era, LSTMs ruled the world of sequences (image from Understanding LSTM Networks )

Long before Transformers took over natural language processing, deep learning was already going through its first major boom. Architectures like **convolutional neural networks (CNNs)** dominated vision, while **recurrent neural networks (RNNs)** —especially **LSTMs** —were the workhorse of sequence modeling tasks such as **machine translation**, **speech recognition**, and **text generation**.

These models worked, but they came with clear limitations, especially when dealing with **long sequences** and **long-range dependencies**.

> ✅ *This is where **attention mechanisms** first entered the picture.*

---

### The Attention Mechanism

Originally introduced as an improvement to encoder–decoder recurrent models for sequence-to-sequence tasks (like machine translation), attention was designed to solve a simple but fundamental problem: **instead of compressing an entire input sequence into a single fixed-length vector** (**state**), **why not allow the model to** ***look back*** **at different parts of the input as needed?**

![](https://substackcdn.com/image/fetch/$s_!jqNl!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbeb4b694-e899-4244-9572-76c99c4cc6c7_1200x209.png)

The encoder-decoder architecture

At its simplest, **attention is a weighted lookup mechanism**.

You start with:

- A set of **keys**: k1, k2, …, kn.
- A corresponding **set of values**: v1, v2, …, vn.
- A **query** that expresses what you're looking for.

The attention mechanism compared the query against all keys, assigns a **weight** to each one, and then produces a **weighted sum of the values**. This operation is often called **attention pooling.**

![](https://substackcdn.com/image/fetch/$s_!ITLW!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2f86980f-0b97-4cb4-8630-7e5471bb0ef7_910x579.png)

The Attention Mechanism

In other words:

> 🙋 *Attention decides which pieces of information matter most, and combines them accordingly.*

Early encoder–decoder models had to squeeze an entire input sentence into one vector before decoding. Attention removed this constraint by allowing the decoder to dynamically access *all* encoder states at every step. Longer sentences, richer context, better translations.

And this is where things get interesting … because at first, attention, was "just" an add-on! These mechanisms were trying to improve the encoder-decoder architecture in very specific applications.

**But the implications, dear builders, ran much deeper …**

Once you realise that this architecture can:

- Query a set of representations
- Select relevant information dynamically
- Do so in a differentiableand parallelizableway

**You no longer need recurrence at all!**

> 🙋 *This insight would end up reshaping neural network architectures across every domain.*

---

### Preparing the Ground for Transformers

So, as we already know by now, attention was not invented for Transformers, but one thing it's true. It radically expanded what attention mechanisms could do.

Several key evolutions turn basic attention pooling into the architecture that domains every domain nowadays.

---

#### Self-Attention

![](https://substackcdn.com/image/fetch/$s_!aVXN!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff970d7f6-c93f-4558-8f49-780f02c572ee_701x459.png)

Self-attention

So far, attention has helped models **look back at an input sequence** when generating outputs, as in encoder–decoder models for machine translation.

> ✅ *Self-attention takes this idea one step further.*

Instead of having one sequence attend to another, **each token in a sequence attends to all the other tokens in the same sequence**! Simple and genius at the same time.

Imagine you feed a sequence of tokens into a model:

```markup
The cat sat on the mat
```

In self-attention:

- Every token is turned into a **query (Q)**, a **key (K)**, and a **value (V)**
- For each token, its **query** is compared with the **keys of all tokens** (including itself)
- These comparisons determine how much attention the token pays to every other token
- The token's new representation is built as a **weighted sum of all values**

So when the model updates the representation of **"sat"**, it can:

- Strongly attend to **"cat"** (who is sitting)
- Attend to **"mat"** (where the action happens)
- Largely ignore function words like **"the"**

Clear, right? Let's move on to another key technique: **positional encodings.**

---

#### Positional Encoding

![](https://substackcdn.com/image/fetch/$s_!h6cx!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F45442da8-06d8-4145-8580-aba4dd51e313_1015x489.png)

Sine and cosine functions as positional encodings (image from Dive into Deep Learning )

Attention itself has no notion of order. To make sequences meaningful, **positional information is injected into token representations**, allowing the model to distinguish "first", "next", and "last" without relying on recurrence.

In the original Transformer, positional encodings are built using **sine and cosine functions at different frequencies**.

Each dimension of the positional encoding corresponds to a sinusoid:

- Low-frequency sinusoids capture coarse position information
- High-frequency sinusoids capture fine-grained differences

Together, they form a rich representation of position.

> 🙋 **A quick reassurance before moving on:** don't worry if the exact intuition behind sinusoidal positional encodings doesn't fully click right now. We're mentioning them because they were an important design choice in the original Transformer architecture, and it’s useful to know *why* they exist.

---

#### Multi-Head Attention

![](https://substackcdn.com/image/fetch/$s_!hLX4!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc1b08e65-b3e8-469b-a313-f50668673f63_961x516.png)

Scaled Dot-Product Attention and Multi-Head Attention (image from Attention Is All You Need )

So far, we've talked about attention as a general idea: **queries (Q)** interact with **keys** **(K)** to decide how **values** **(V)** should be combined.

**Scaled dot-product attention** is the specific, concrete way the Transformer implements this idea.

At a high level, it works like this:

1. Each token produces a **query**, **key**, and **value**
2. Queries are compared with keys using a **dot product**
3. The resulting scores are normalized with a **softmax**
4. These normalized scores are used to compute a weighted sum of the values

This is the mathematical formula, in case you are interested:

$Attention \left(\right. Q , K , V \left.\right) = softmax \left(\right. \frac{Q K^{\top}}{\sqrt{d_{k}}} \left.\right) V$

With a single attention head, the model is forced to average all relationships into one view.

**Multi-head attention removes this constraint.**

Different heads can specialize in different patterns, such as:

- Short-range vs long-range dependencies
- Syntactic relationships
- Semantic similarity

This allows the model to **jointly attend to information from different representation subspaces**, all at once.

$MultiHead \left(\right. Q , K , V \left.\right) = Concat \left(\right. head_{1} , \ldots , head_{h} \left.\right) W^{O}$

---

### Bringing It All Together: The Transformer

If you combine all of these techniques, you arrive at **the most important neural network architecture of our time**.

This is the backbone behind models like **BERT**, **ChatGPT**, and **Qwen**. Different flavors, different objectives … but the same core idea.

At this point, it's hard not to recognize *one of the most famous diagrams in modern deep learning*, which I'll take the liberty of sharing here.

**Ladies and gentlemen… meet the Transformer.**

![](https://substackcdn.com/image/fetch/$s_!dBoF!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3330bd3c-aac0-466d-9993-e4dd785213a3_960x678.png)

The Transformer Architecture (image from Attention Is All You Need )

So before we dive into LoRA or GRPO, **remember this**:

> 🙋 *Understanding the structure we're working with is **essential**. That's exactly why we're taking the time to walk through these concepts!*

This mental model will make every future lesson **clearer**, **more intuitive**, and **far more effective**!

---

## The 3 Transformer architectures

![](https://substackcdn.com/image/fetch/$s_!mRlz!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa13c886e-05c9-4da4-aeec-3e4c6deeb046_1200x630.png)

The 3 Transformer Architectures

When people hear *Large Language Models*, many immediately think of systems like ChatGPT or Claude. That's understandable—but also a bit misleading.

> ⚠️ *LLMs are not a single thing!*

They come in **three different Transformer architectures**, each designed for different kinds of problems. Modern LLMs mostly rely on one of them—but the other two are just as important historically and practically.

Let's take a quick tour.

---

## Encoder-Only Transformers

Encoder-only Transformers take an input sequence and turn it into **rich representations**, one per token.

All tokens attend to each other freely (bidirectional self-attention), which makes these models especially good at:

- Understanding text
- Classification
- Retrieval
- Semantic similarity

> There's no text generation here—only **encoding**.

This family includes models like **BERT**, which popularized large-scale pretraining via **masked language modeling**. Encoder-only models shine when the goal is *“understand this input”* rather than *“generate the next token.”*

---

## Encoder–Decoder Transformers

Encoder–decoder Transformers were the **original Transformer design**, created for sequence-to-sequence tasks like machine translation.

Here, the architecture is split into two parts:

- The **encoder** reads and represents the input sequence
- The **decoder** generates an output sequence, token by token

The decoder uses:

- **Cross-attention** to look at the encoder outputs
- **Causal self-attention** to avoid peeking at future tokens

This setup is ideal when:

- Input and output are both sequences
- Output length can vary freely

Models like **T5** and **BART** belong to this family. They’re extremely flexible and powerful, especially for tasks like summarization, translation, and text-to-text learning.

---

## Decoder-Only Transformers

Now we get to the architecture that powers **modern LLMs**.

Decoder-only Transformers remove the encoder entirely and rely on a single mechanism:

> ***Causal self-attention** over a growing sequence of tokens*

Each token can only attend to tokens that came before it. The model is trained with a simple objective: **predict the next token**.

This design turns out to be shockingly powerful.

Almost every modern LLM follows this pattern. With enough data, parameters, and compute, decoder-only Transformers:

- Learn language, reasoning, and structure
- Perform tasks via prompting (in-context learning)
- Scale remarkably well

> 🙋 *This is the architecture we'll focus on for the rest of the course, because it's the foundation behind today's most capable LLMs*

---

## The Scaling Laws

![](https://substackcdn.com/image/fetch/$s_!WAiF!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7358e37b-623f-4e1a-acf5-552147b42b2f_926x406.png)

Language modeling performance improves smoothly as we increase the model size, dataset size, and amount of compute used for training (image from Scaling Laws for Neural Language Models )

One last ingredient explains *why* Transformers became dominant: **scaling**.

Empirical studies have shown that Transformer performance improves smoothly as we increase:

- Model size (parameters)
- Training data (tokens)
- Training compute

These improvements follow **power-law scaling relationships**, meaning that bigger models trained on more data tend to get predictably better—especially for language modeling.

Decoder-only architectures are particularly well-suited to this regime:

- Simple objective
- Massive unlabeled data
- Efficient parallel training

This is why the biggest breakthroughs in recent years didn't come from radically new architectures— **but from scaling Transformers to unprecedented sizes.**

---

## The LLM Training Pipeline

![](https://substackcdn.com/image/fetch/$s_!CetZ!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F48baf6dd-9664-4ccc-9ebf-4fca2bb400fe_1200x394.png)

The LLM Training Pipeline

So far, we've talked about architectures. Now it's time to talk about **how modern LLMs are actually trained**.

When we refer to *LLMs* in this course, we'll be talking specifically about **decoder-only language models** —the family behind systems like ChatGPT, Claude, and Qwen. And while these models may look magical from the outside, their training follows a fairly well-defined pipeline.

> 🙋 *That pipeline was clearly formalized in **[2022 by OpenAI's InstructGPT](https://openai.com/index/instruction-following/)**.*

Before InstructGPT, most language models were trained primarily as next-token predictors. They were good at completing text—but not necessarily good at **following instructions**, reasoning step by step, or aligning with human preferences.

InstructGPT marked a turning point. While it wasn't the first or the largest model of its time, it introduced and popularized a **multi-stage training pipeline** that has since become the standard for modern LLMs.

![Diagram showing three-step methodology to train InstructGPT models.](https://substackcdn.com/image/fetch/$s_!bjNt!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9a51db03-a5db-48e8-b4bf-52d2fc8ff433_2560x1440.webp)

SFT and RLHF steps (image from Aligning language models to follow instructions )

Concretely, it established a **three-stage framework**:

1. **Pretraining** on large-scale, raw text data
2. **Supervised Fine-Tuning (SFT)** on high-quality, task-oriented examples
3. **Alignment via Reinforcement Learning from Human Feedback (RLHF)**

This combination— *pretraining + SFT + RLHF* —proved far more effective than pretraining alone and laid the foundation for systems like ChatGPT and many successors.

As training methods evolved, people began describing this process in slightly different ways.

- The **three-stage view** (pretraining → SFT → RLHF) is still widely used because of its historical and practical clarity.
- A broader **two-phase view** is also common:
	- **Pretraining**, which builds general-purpose language capabilities
		- **Post-training**, which refines, adapts, and aligns those capabilities

Both perspectives describe roughly the same process. The difference is mostly conceptual.

If you want a great high-level walkthrough of this pipeline, we highly recommend the video below. **It offers one of the best explanations available and complements this lesson beautifully!**

> 👉 *Watch the first 20 minutes, where Daniel Han covers the LLM Training Pipeline!*

![](https://www.youtube.com/watch?v=OkEGJ5G3foU)

---

## Pretraining 101

Now that we've mapped out the full LLM training pipeline, it's time to zoom in on the first—and most foundational—stage: **pretraining**.

Before models learn to follow instructions, answer questions, or behave nicely in a chat interface, they go through a **much more fundamental phase**. Pretraining is where a language model learns the basics of language itself—syntax, semantics, patterns, facts, and a surprising amount of what we often call *world knowledge*.

> 💸 *It's also where the vast majority of a model's training compute and data are spent!*

**So what does pretraining actually look like?**

---

### What Happens During Pretraining

![](https://substackcdn.com/image/fetch/$s_!gb6a!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa2a095ff-c348-4a7a-a09f-5228019d8246_3106x1888.png)

A good example of a pretrained (base) model. The model we deploy in Lab 0 falls into this category: it has been trained to complete text, not to answer questions or follow instructions. These are typically referred to as base models.

At its core, pretraining is simple.

A decoder-only Transformer is trained to **predict the next token in a sequence**, given all previous tokens. This is known as **causal language modeling (CLM)**.

There are:

- No instructions
- No human feedback
- No task-specific labels

Just raw text, one token at a time. Because pretraining uses **the largest and most diverse dataset the model will ever see**, this is the phase where it acquires:

- Grammar and syntax
- Style and structure
- Facts and common sense
- Code patterns
- Multilingual capabilities (if trained on multilingual data)

> 🌎 *This is why pretraining is often described as the phase where the model **"learns the world."***

---

### Self-Supervised Learning

![](https://substackcdn.com/image/fetch/$s_!gm6Z!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffc83ad34-7a9f-4e92-8165-2c85880a0a64_1015x742.png)

This is an example of a pretraining dataset that contains mathematical text. We will use this dataset in this week's lab.

Pretraining does **not** rely on labeled data.

Instead, it uses **self-supervised learning**. The supervision signal is already present in the data itself: **the** ***next token*** **is the label.**

This is what makes pretraining scalable. The internet provides an enormous supply of raw text, and as long as you can tokenize it, you can train on it.

That's why most pretraining corpora consist largely of **web pages**, **books**, **articles** or **repositories**!

---

### The output of pretraining: A Base Model

The result of pretraining is what we usually call a **base model** (or **foundation model**).

At this stage, the model is extremely good at **continuing text**. It has absorbed a broad distribution of language patterns, facts about the world, and even coding styles.

What it **can’t do** —at least not reliably—is follow instructions, decide when to refuse a request, or optimize for helpfulness or safety. None of that has been taught yet. The model has learned *what language looks like*, not *how it should behave*.

In other words, it’s powerful—but not yet usable as a product. This is where a famous analogy comes in.

![3 phases of ChatGPT development](https://substackcdn.com/image/fetch/$s_!vT6I!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F50ad2b12-d3dc-4a64-83b7-1a2fa40eaefd_793x671.jpeg)

The best visualization of the LLM training pipeline you'll ever see! (image from RLHF: Reinforcement Learning from Human Feedback )

Chip Huyen's Shoggoth meme captures this stage perfectly. During pretraining, the model is essentially a **raw pattern-learning engine** —absorbing everything it sees, without judgment or alignment. The structure is there. The power is there. But the behavior is… unpredictable.

> This is where everything that comes *after* pretraining enters the picture.

Techniques like **Supervised Fine-Tuning (SFT)**, **LoRA**, and **QLoRA** are not about teaching the model language from scratch. Instead, they **shape and steer** the capabilities already learned during pretraining.

They teach the model how to respond to instructions, how to structure answers, and how to behave in ways that are consistent with human expectations—without rewriting everything it already knows.

In other words, pretraining builds the raw intelligence. Fine-tuning and alignment are what turn that raw intelligence into something usable.

> 🙋 **And that's exactly where we're headed in the next lessons.**

---

## Next Steps

Now that you understand the theory behind pretraining, a very reasonable question might be:

> *When would I ever need to use this?*

It’s not like most of us are sitting on a million-dollar budget to pretrain a model from scratch… right? 😄

The good news is that **pretraining doesn't always mean starting from zero**. In practice, there *are* very real scenarios where pretraining—or a variant of it—makes a lot of sense. For example:

- When you want to add **new domain knowledge**, like legal or medical text
- When you want to support an **underrepresented language**
- When your data distribution is very different from what the original model saw

In these cases, **continued pretraining** can be a powerful tool. Instead of rebuilding a model from scratch, you extend an existing base model by exposing it to new data, allowing it to absorb new patterns and knowledge while retaining what it already knows.

![](https://substackcdn.com/image/fetch/$s_!w_li!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fffd01b51-408c-47fb-aa53-626d2cd29721_600x267.svg)

Continued Pretraining using Unsloth (image from Continued Pretraining with Unsloth )

This is exactly what we'll cover in this Friday's lab, walking you through how to implement it step by step using our tech stack.

**See you there!**

---

## References

- [Olah, C. (2015, August 27).](https://colah.github.io/posts/2015-08-Understanding-LSTMs/) *[Understanding LSTM Networks](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)*[. Colah’s Blog.](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)
- [Zhang, A., Lipton, Z. C., Li, M., & Smola, A. J. (2023).](https://d2l.ai/) *[Dive into Deep Learning](https://d2l.ai/)*[.](https://d2l.ai/)
- [Morgan, A. (2025, August 1).](https://www.comet.com/site/blog/pretraining/) *[Pretraining: Breaking Down the Modern LLM Training Pipeline](https://www.comet.com/site/blog/pretraining/)*[. Comet Blog.](https://www.comet.com/site/blog/pretraining/)
- [Kaplan, J., McCandlish, S., Henighan, T., Brown, T. B., Chess, B., Child, R., Gray, S., Radford, A., Wu, J., & Amodei, D. (2020).](https://arxiv.org/abs/2001.08361) *[Scaling laws for neural language models](https://arxiv.org/abs/2001.08361)*[. arXiv.](https://arxiv.org/abs/2001.08361)
- [Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017).](https://arxiv.org/pdf/1706.03762) *[Attention is all you need](https://arxiv.org/pdf/1706.03762)*[. arXiv.](https://arxiv.org/pdf/1706.03762)
- [Huyen, C. (2023, May 2).](https://huyenchip.com/2023/05/02/rlhf.html) *[RLHF: Reinforcement learning from human feedback](https://huyenchip.com/2023/05/02/rlhf.html)*[. Chip Huyen Blog.](https://huyenchip.com/2023/05/02/rlhf.html)
- [NVIDIA. (2023).](https://blogs.nvidia.com/blog/ai-scaling-laws/) *[AI scaling laws: What they are and why they matter](https://blogs.nvidia.com/blog/ai-scaling-laws/)*[. NVIDIA Blog.](https://blogs.nvidia.com/blog/ai-scaling-laws/)
- [OpenAI. (2022, January 27).](https://openai.com/index/instruction-following/) *[Aligning language models to follow instructions](https://openai.com/index/instruction-following/)*[. OpenAI.](https://openai.com/index/instruction-following/)