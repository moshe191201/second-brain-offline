---
title: "Understanding LoRA from First Principles"
source: "https://theneuralmaze.substack.com/p/understanding-lora-from-first-principles"
author:
  - "[[Miguel Otero Pedrido]]"
published: 2026-02-25
created: 2026-06-10
description: "Finetuning Sessions · Lesson 3 / 8"
tags:
  - "clippings"
---
![](https://substackcdn.com/image/fetch/$s_!YesL!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F993b4776-26e8-4cd9-9c21-09b537b28a43_1920x1080.png)

Welcome to **Lesson 3** of the **[Finetuning Sessions](https://theneuralmaze.substack.com/t/finetuning-sessions)**!

**[Low-Rank Adaptation (LoRA)](https://arxiv.org/pdf/2106.09685)** has quietly transformed from a clever research trick into the default strategy for steering large-scale models in production.

What began as a parameter-efficient finetuning (**PEFT**) method is now an industry standard. Yet while libraries like Hugging Face's **[peft](https://github.com/huggingface/peft)** or **[Unsloth](https://unsloth.ai/)** have democratized its use, they've also abstracted away the deeper mechanics.

> 🙋 The **"how"** is packaged into a few lines of code, but the **"why"** is left implicit. And that **"why"** is where **real understanding** lives!

To truly grasp LoRA, we have to step past the convenience of the API and return to **first principles**. Large models are not magic—they are compositions of weight matrices, and those matrices encode behavior.

If you understand how those weights shape representation and transformation, you begin to see **why we can alter a model's behavior without retraining billions of parameters.**

> ✅ In this article, we'll strip **LoRA** down to its **foundations**.

We'll start at the architectural level—what weight matrices actually *do* —and then descend into the linear algebra that makes low-rank updates not just efficient, but surprisingly expressive.

**Ready? Let's go!** 👇

---

## LoRA Foundations

Do you remember when, in **[Lesson 1](https://theneuralmaze.substack.com/p/the-finetuning-landscape-a-map-of)**, we dissected the **three Transformer architectures**?

![](https://substackcdn.com/image/fetch/$s_!mRlz!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa13c886e-05c9-4da4-aeec-3e4c6deeb046_1200x630.png)

If not, here's a quick mental refresh — think of it as clearing the cache before we continue … 🤣

- **Encoder-only models** use **bidirectional attention** to produce **contextualized** **representations** of an **input**. They are designed for understanding tasks, where the goal is to extract meaning rather than generate new sequences.
- **Decoder-only models** are **autoregressive**. Each token attends only to previous tokens, enabling next-token prediction and large-scale text generation. The LLMs we finetune in this course belong to this category!
- **Encoder–decoder models** combine both components: an **encoder** first builds a representation of the input, and a **decoder** then generates a new sequence conditioned on that representation. They are commonly used for structured transformation tasks such as translation. This was also the original Transformer formulation introduced in *[Attention Is All You Need](https://arxiv.org/pdf/1706.03762)*.

> **🙋 That's the structural landscape most modern models live in.**

Now, even though almost every large-scale system today is some variant of the Transformer, understanding LoRA benefits from stepping slightly outside that family.

To see why low-rank adaptation works, we need to revisit a **simpler architectural idea** — one centered on compression and latent structure: **the autoencoder**.

---

## Connecting Autoencoders and LoRA

![](https://substackcdn.com/image/fetch/$s_!5V3v!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4ddc8aec-7018-4b30-86c3-3363877211b9_955x418.png)

Autoencoder architecture (source: What is an autoencoder? )

Although the architectures discussed above are Transformer-based, the **concept of the autoencoder is particularly useful for understanding the logic behind LoRA.**

An **autoencoder** is composed of two parts: an **encoder** that compresses the input into a **lower-dimensional representation** (the **latent space**), and a **decoder** that reconstructs the original input from that compressed representation.

This structure is commonly used for tasks such as feature extraction, denoising, and dimensionality reduction.

> 🤔 At this point, you might be wondering: **how is this related to LoRA or large language models?**

**👉 The connection lies in dimensionality!**

Just as an autoencoder demonstrates that **high-dimensional input data can often be compressed into a much lower-dimensional latent space** without losing its essential structure, LoRA is built on a similar assumption.

> 🙋 Instead of compressing data, **LoRA** assumes that the ***updates*** **applied to a model's weights during finetuning can be represented in a lower-dimensional subspace!**

![](https://substackcdn.com/image/fetch/$s_!gRwA!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd6701158-bfe3-4bd6-90e8-65c46543a59e_563x274.png)

Representing model updates in a lower-dimensional subspace! (Image from LoRA: Low-Rank Adaptation of Large Language Models )

---

## Returning to Transformers

Regardless of the specific architecture — encoder-only, decoder-only, or encoder–decoder — **a model's knowledge is encoded in large weight matrices.**

In **full finetuning** (as in **[Lab 2](https://theneuralmaze.substack.com/p/supervised-finetuning-for-reasoning)**), we adapt a pre-trained LLM to a new task by updating its weights. If we denote the original weight matrix as `W`, then finetuning learns a modification `ΔW`. The updated weights can therefore be written as:

$W^{'} = W + \Delta W$

**Now, check the figure below.**

This is exactly what is happening. We start with an input `X`, which is multiplied by the pre-trained weight matrix `W`.

During full finetuning, `W` is updated directly. In other words, the model learns a dense correction `ΔW`, and all parameters of `W` are allowed to change.

![](https://substackcdn.com/image/fetch/$s_!q0jb!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F94c6bab9-0dcb-46d6-adb5-285495d30b86_1200x1094.png)

This approach is simple and effective … but creates two major issues.

#### ➤ Issue 1 - VRAM Constraints

For very large models (e.g., 70B parameters), updating all weights requires storing:

- **Gradients**
- **Optimizer states** (e.g., Adam moments)
- **The updated parameters themselves**

> 🙋 This makes **full finetuning prohibitively expensive** without access to large GPU clusters.

#### ➤ Issue 2 - Catastrophic Forgetting

Full finetuning gives the model **complete freedom** in parameter space. But this freedom comes at a cost!

When adapting to a narrow task (e.g., medical coding), gradients can overwrite useful general-purpose knowledge. **The model may improve on the new domain but degrade in reasoning, fluency, or broader capabilities.**

Because full finetuning has effectively unlimited degrees of freedom, nothing constrains the update to remain "close" to the original solution.

---

## The LoRA Hypothesis

![](https://substackcdn.com/image/fetch/$s_!BzHz!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd61f8a1-cdf6-4237-b7c2-91236bc69f4f_1200x1068.png)

**LoRA**, introduced by Microsoft researchers in 2021, proposes a **structural solution**.

The core intuition:

> 🙋 The weight update `ΔW` does **not require full rank**. The adaptation lies in a **low-dimensional subspace.**

This is sometimes referred to as the **intrinsic rank hypothesis**. So, instead of learning a full dense `ΔW`, LoRA factorizes it into two smaller matrices, `A` and `B`.

$\Delta W = B A$

The updated weight matrix becomes:

$W^{'} = W + B A$

Here is the key difference from full finetuning:

- The original pre-trained matrix `W` is **frozen**.
- Only `A` and `B` are trainable.

In the figure above, instead of modifying `W` directly, the input `X` flows through the frozen weights, and an additional low-rank correction `BA` is added to the transformation.

> ✅ The model's behavior changes, but the original parameters remain untouched.

---

## Why LoRA is stable?

Two technical decisions make LoRA practical and stable.

### ➤ Decision 1 - Zero initialization of B

Matrix `B` is initialized to zero. This ensures:

$B A = 0$

at the start of training.

As a result, the model initially behaves **exactly like the pre-trained base model**. There is no sudden perturbation or instability at the beginning of finetuning.

The update grows gradually as training progresses.

### ➤ Decision 2 - The scaling factor α

In practice, the update is applied as:

$W^{'} = W + \frac{\alpha}{r} B A$

The hyperparameter `α` controls the **strength of the update.**

Scaling by `α/r`:

- Allows us to change the rank `r`
- Without drastically retuning the learning rate
- Improves numerical stability

It effectively decouples rank selection from update magnitude.

---

## LoRA Hyperparameters

![](https://substackcdn.com/image/fetch/$s_!tGDR!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F588f1f7d-bdda-4960-b356-35d40c07a11e_1261x418.png)

An example of how LoRA is implemented in practice using Unsloth.

Up to this point, we've focused on *what* **LoRA** does: it constrains weight updates to a low-rank subspace. But in practice, that constraint is controlled by a set of **hyperparameters** that determine how expressive, stable, and efficient the adaptation will be.

> 🙋 Even though LoRA dramatically reduces the number of trainable parameters, it does not eliminate the need for tuning.

In fact, because we are deliberately limiting the adaptation to a smaller space, **choosing the right configuration becomes even more important**. The hyperparameters define the size of that space, the strength of the update, and the way optimization unfolds over time.

In the following sections, we will examine the most important LoRA hyperparameters at a high level!

---

#### ➤ LoRA Rank (r)

> The rank `r` is the most important LoRA-specific hyperparameter.

It determines the dimensionality of the subspace in which the weight update lives. Since LoRA decomposes the update as `ΔW=BA`, the rank defines how expressive that update can be.

A **small rank** (e.g., 4 or 8) **constrains adaptation heavily**. This acts as a strong regularizer and is often sufficient for relatively simple tasks.

A **larger rank** (e.g., 32, 64, or higher) **increases capacity**, allowing the adapter to model more complex task shifts. **However, increasing rank also increases memory usage and the risk of overfitting!**

> 🙋 In practice, **ranks** **between** **8** **and** **32** work well for most instruction-tuning tasks. The key trade-off is **capacity** versus **efficiency**. Rank defines how many independent "directions" the model is allowed to move in weight space.

---

#### ➤ LoRA Alpha (lora\_alpha)

LoRA does not apply the raw product `BA` directly. Instead, the update is typically scaled:

$W^{'} = W + \frac{\alpha}{r} B A$

The parameter α controls the strength of the update relative to the base model. If the **rank** defines the dimensionality of adaptation, **alpha** defines its magnitude.

> 🙋 A common and stable choice is `α=r`. Some practitioners use `2r` to allow slightly more aggressive updates.

**If alpha is too small**, the adapter may struggle to influence the model. **If too large**, training can become unstable.

---

#### ➤ Learning Rate

Even though we are only updating a small subset of parameters, the **learning rate** remains **critical**.

**Too high** a learning rate can cause **divergence** or **noisy training**. **Too low** may **slow convergence** or prevent the adapter from learning meaningful corrections.

> Unlike rank, which controls capacity, **the learning rate controls optimization dynamics.**

---

#### ➤ Target Modules

Up to now, we have described LoRA using a generic matrix `W`. However, in a Transformer, there is no single weight matrix.

> 🙋 **There are many projection matrices, each serving a distinct role.**

The `target_modules` parameter determines which linear layers receive LoRA adapters. Common targets include:

- **q\_proj**
- **k\_proj**
- **v\_proj**
- **o\_proj**
- **gate\_proj**
- **up\_proj**
- **down\_proj**

> Targeting **fewer modules** reduces memory slightly, but **may limit performance**. Targeting **all major linear layers** usually produces results closer to **full finetuning**.

To understand why, we need to look inside a Transformer block!

![The Attention Mechanism and the Transformer Model](https://substackcdn.com/image/fetch/$s_!t6RA!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc9664dbc-2068-4a0c-ab85-42d2b4aa1a99_1999x1151.png)

The Attention Mechanism and the Transformer Model

Inside every self-attention layer, each token vector is projected into three different spaces (remember the queries (Q), keys (K) and values (V)?)

$Q = x W_{q} , K = x W_{k} , V = x W_{v}$

These projections serve distinct purposes:

- **Query (W\_q)** determines what each token is "looking for".
- **Key (W\_k)** determines how each token represents what it contains.
- **Value (W\_v)** determines what information is passed forward once attention is computed.

After attention weights are applied, **the outputs from multiple heads are combined through another projection:**

$O u t p u t = A t t e n t i o n \left(\right. Q , K , V \left.\right) W_{o}$

That final matrix, **W\_o**, controls how information from different heads is mixed back into the residual stream.

In addition to attention, each Transformer layer contains an **MLP block** with large projection matrices (`gate_proj`, `up_proj`, `down_proj`) that transform representations nonlinearly.

> **Each of these matrices can be enormous.**

In a 7B model with hidden size 4096, a single projection matrix may contain over 16 million parameters.

Multiply that across **dozens of layers**, and it becomes clear why full finetuning is computationally expensive!

So, when we define as target module **q\_proj**, for example, what we are actually doing is:

$Q = x W_{q} + x A B$

And the same applied for the rest of them!

> 🧪 In the lab, we'll experiment with **different hyperparameter values** and observe how they affect performance in practice.

---

## Next Steps

![](https://substackcdn.com/image/fetch/$s_!vlEt!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F77bdd99a-a3af-4ed4-aabe-e070999e0c04_1200x630.png)

That's everything for today's article!

We've covered the foundations of LoRA, its mathematical intuition, how it integrates into Transformer architectures, and the key hyperparameters that control its behavior.

You should now have both the **conceptual understanding** and the **structural intuition** behind low-rank adaptation!

This Friday, we'll move from theory to practice in a hands-on LoRA lab.

See you there! 👋