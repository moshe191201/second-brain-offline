---
title: "A Practical Guide to LLM Inference at Scale"
source: "https://theneuralmaze.substack.com/p/a-practical-guide-to-llm-inference"
author:
  - "[[Miguel Otero Pedrido]]"
published: 2026-04-01
created: 2026-06-10
description: "Finetuning Sessions · Lesson 8 / 8"
tags:
  - "clippings"
---
![](https://substackcdn.com/image/fetch/$s_!pNbD!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbfbae89d-dd90-4c0c-ac25-fabd9518a21e_700x380.png)

So far in this series, we've stayed firmly in **model-land** — architectures, training loops, finetuning tricks. All important stuff. But at some point, you need to actually *serve* the thing. And that's where it gets humbling.

> 🙋 Because here's what nobody tells you: a single LLM request involves **two computationally opposite phases** fighting over the same GPU.

One is massively parallel and compute-hungry. The other is sequential and starved for memory bandwidth. Making them coexist efficiently is basically the entire game of LLM inference — and it's led to a beautiful chain of engineering ideas, each one patching the flaw the previous one introduced.

That's what this post is about.

We'll start from the basics of how a single request flows through a model, and build all the way up to production-scale techniques like **chunked prefill**, **prefill-decode** **disaggregation**, **PagedAttention**, and **elastic GPU sharing**.

Let's get into it! 👇

---

## Introduction to LLM Inference

![](https://substackcdn.com/image/fetch/$s_!wcBq!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3f3c6ed2-9a87-4830-be64-ec0c398170eb_700x700.png)

Image from Understanding the Two Key Stages of LLM Inference: Prefill and Decode

At the heart of it, all large language models (LLMs) are simply **sophisticated next-token predictors**.

When a user submits a query to an AI service, the model first processes the entire prompt and then iteratively generates the response one token at a time. This generation process creates a highly variable input-to-output workload: user prompts can range from a handful of words to thousands of tokens, and the length of the generated response is unpredictable until the model decides to emit an end-of-sequence token.

> 🙋 Because of this dynamic and variable nature, serving LLMs at scale requires **high-performance infrastructure** that differs significantly from traditional deep learning inference paradigms.

To handle these variable workloads effectively, modern inference engines divide the generation process into two fundamentally distinct computational stages: the **prefill phase** and the **decoding phase**.

This dual-phase architecture dictates how hardware resources are allocated and forms the basis for all modern inference optimizations. Understanding the distinct computational characteristics of each phase is crucial for identifying bottlenecks, maximizing GPU utilization, and achieving high throughput in production environments.

> The **prefill phase** is responsible for processing the user's initial prompt in its entirety to generate the very first token.

During this stage, the model computes the **hidden representations** for all input tokens concurrently in a single forward pass. Because it processes a large sequence of tokens simultaneously, this phase heavily utilizes the GPU's parallel processing capabilities through massive matrix multiplications, making it highly **compute-bound**.

> The primary performance metric for this phase is the **Time to First Token (TTFT)**, which is critical for maintaining responsiveness in real-time applications like chatbots.

As the prefill phase computes these token representations, it saves intermediate attention states—specifically the key and value vectors—in GPU memory to avoid redundant calculations in future steps. **This stored data is known as the** **KV cache**.

By preserving the keys and values of the initial prompt and every subsequently generated token, the model drastically reduces the computational cost of generating new tokens from quadratic to linear time. However, this optimization shifts the system’s bottleneck, as it requires maintaining and continuously accessing an ever-growing memory footprint for every active request.

![](https://substackcdn.com/image/fetch/$s_!qI7s!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb08ccb77-8173-4f36-9d6a-82fa8641a8b9_1500x420.png)

Link: https://huggingface.co/blog/tngtech/llm-performance-prefill-decode-concurrent-requests

> Following the prefill, the **decoding phase** takes over to sequentially generate the remainder of the response step-by-step.

In each decoding iteration, the model only processes the single newest token, relying on the saved KV cache to provide the necessary historical context. Because the compute cores only handle one token per sequence but must still load the massive model parameters and the entire KV cache from high-bandwidth memory (HBM) to the SRAM, the decoding phase is severely **memory-bandwidth bound**.

> Consequently, the performance of this phase is measured by the **Time Per Output Token (TPOT)**, and inference engines must rely on sophisticated batching strategies to prevent the GPU from being underutilized.

---

## Decoding (I): The baseline of static batching

Modern GPUs are designed for highly parallel computational workloads, capable of executing trillions or even quadrillions of floating-point operations per second.

However, large language models (LLMs) often struggle to fully saturate these powerful chips because a significant portion of the GPU's memory bandwidth is bottlenecked by the constant need to load massive model parameters from memory.

> To mitigate this inefficiency, **inference serving systems** employ **batching**, which allows the engine to load the model parameters once and use them to process multiple input sequences concurrently.

The simplest and most traditional approach to this technique is known as **static batching**.

In static batching, the inference server waits until a fixed number of user requests arrive, grouping them together to process as a single, unified batch.

Because traditional tensor operations require rectangular shapes, the system must add padding tokens to shorter prompts so that all sequences match the length of the longest prompt in the batch. Once the batch is assembled, the model executes its forward passes, generating new tokens for every sequence in lockstep. This process continues iteratively until the entire batch has completed its generation phase.

![](https://substackcdn.com/image/fetch/$s_!lcY4!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F86e55c07-2ba0-4597-823d-91007059f7e8_1500x780.png)

Link: https://huggingface.co/blog/tngtech/llm-performance-prefill-decode-concurrent-requests

> While static batching is relatively straightforward to implement, it possesses a critical flaw when applied to LLMs: **the entire batch is strictly tied to the longest-running request**.

In real-world applications, output sequences vary drastically; one prompt might require a short, single-sentence response, while another demands a lengthy, step-by-step explanation.

Even if a shorter request emits its end-of-sequence token after just a few iterations, it must remain in the batch. The system **cannot remove** the finished request to free up memory, nor can it insert a new prompt, **until the absolute longest sequence in that specific batch finishes generating its final token.**

> This rigid limitation directly leads to **severe GPU underutilization and increased latency**.

For every iteration where a completed sequence sits idle waiting for the longest sequence to finish, valuable compute resources are wasted.

Furthermore, new incoming requests are forced to wait in a queue until the currently active batch completely clears, which adds unnecessary delays for users. Ultimately, while static batching provides a baseline improvement over processing single requests sequentially, its inability to handle variable-length outputs makes it highly inefficient for production-scale LLM inference.

---

## Decoding (II): Continuous batching

![](https://substackcdn.com/image/fetch/$s_!c03K!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F86fc92aa-b7c8-4927-b292-40ca5b5ce3d2_1800x690.png)

Link: https://huggingface.co/blog/tngtech/llm-performance-prefill-decode-concurrent-requests

To overcome the severe limitations of static batching, inference systems initially turned to **dynamic batching**, which collects incoming requests within a set time window before processing them.

However, while this balances throughput and latency better than static approaches, it still forces shorter requests to wait for the longest sequence in the batch to finish. The definitive solution to this inefficiency is **continuous batching**, also widely known as **iteration-level scheduling**.

> This approach fundamentally rethinks request scheduling by **ensuring** **that the GPU does not wait for all sequences in a batch to complete before starting new ones.**

At its core, continuous batching operates by **evaluating the batch composition dynamically at each decoding iteration**.

As soon as a sequence within the batch finishes generating its response—typically indicated by emitting an end-of-sequence token—the system immediately removes it from the batch.

Instead of waiting for the rest of the batch to clear, **a new request from the waiting queue is instantly inserted into the freed compute slot**. This assembly-line mechanism keeps the compute resources constantly busy, completely eliminating the idle time that plagues traditional batching methods.

Implementing this continuous flow requires a departure from traditional tensor operations that rely on rectangular shapes and extensive padding.

To avoid the massive computational waste of padding when constantly swapping prompts, modern serving engines employ **ragged batching**, where prompts of uneven lengths are simply concatenated together into a single sequence.

The system then uses precise **attention masks** to seamlessly control token interactions, ensuring that tokens from one prompt never interact with tokens from another. This clever use of masking eliminates padding waste and allows the engine to mix sequences of drastically different lengths efficiently.

Managing this continuous influx of new requests requires the system to handle the prefill phase alongside ongoing decoding tasks. Because the initial prefill phase is highly compute-intensive and differs significantly from the memory-bound decoding phase, continuous batching frameworks must utilize specific scheduling policies to balance the two.

> By intelligently mixing and scheduling prefill computations with ongoing decoding steps, continuous batching ensures that the GPU remains fully utilized at all times.

Ultimately, this iteration-level scheduling is the crucial optimization that allows production services to handle thousands of concurrent users with variable-length queries while drastically multiplying overall inference throughput.

---

## Decoding (III): Chunked Prefill

![](https://substackcdn.com/image/fetch/$s_!Mcfj!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3e5988d5-a83d-4d64-82b6-7793d729c358_1800x690.png)

Link: https://huggingface.co/blog/tngtech/llm-performance-prefill-decode-concurrent-requests

While continuous batching keeps the GPU highly occupied by constantly swapping in new requests, it introduces a severe new problem known as **prefill-decode interference**.

When a new user submits a long prompt, the system must execute a highly compute-intensive prefill phase. If this massive prefill job is inserted into the same batch as ongoing decoding tasks, the decoding requests are forced to wait for the long prefill computation to finish before they can generate their next token.

> This massive compute stall significantly increases the **Time Per Output Token (TPOT)**, or inter-token latency, creating a jarring and slow experience for users who are already in the middle of receiving their generated text.

To overcome these crippling compute stalls, modern inference engines implement a technique called **chunked prefill**.

![Image](https://substackcdn.com/image/fetch/$s_!-TAE!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F81f07190-0a04-4d7b-ab76-6498baaa6199_1598x1096.jpeg)

Instead of forcing the GPU to process a massive prompt in a single, monolithic forward pass, **the system divides the long input sequence into smaller, strictly sized segments or "chunks"**.

By enforcing a strict token budget per batch, the engine prevents any single long prefill request from monopolizing the GPU's compute cycles and indefinitely delaying the progress of other requests.

> Mechanically, chunked prefill relies on the **iterative flexibility of the KV cache**.

During the first forward pass, the engine processes the **first chunk** of the prompt and stores its KV states.

For the **second chunk**, it simply prepends these previously stored KV states to the new computation, updating the attention mask accordingly so no contextual information is lost.

This segmenting allows the system's scheduler to cleverly **piggyback** or mix smaller prefill chunks with the single-token decoding steps of other ongoing requests.

The scheduler can fill the batch with decoding tokens and then pack any remaining computational space with a prefill chunk, ensuring the GPU is perfectly utilized without ever starving the decoding sequences.

Despite its effectiveness at smoothing out inter-token latency, chunked prefill introduces its own unavoidable tradeoffs. Because the initial prompt is processed over multiple iterations and forced to share compute time with decoding tasks, the **Time to First Token (TTFT)** for that specific new request inherently increases.

Furthermore, **chunked prefill** causes significantly more memory access overhead for the prefill job. To compute each subsequent chunk, the KV cache of all the previously processed chunks must be repeatedly loaded from the GPU's High-Bandwidth Memory (HBM) into its SRAM, an overhead that scales quadratically with context length.

> Yet, even with these costs, chunked prefill remains an essential mechanism for balancing high throughput with stable decoding latencies in dynamic LLM workloads.

---

## Decoding (IV): Prefill-Decode Disaggregation

![scaling](https://substackcdn.com/image/fetch/$s_!1YCt!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F16dd2197-1da6-4650-bc7b-68b4e81bdf51_2124x1592.png)

Link: https://haoailab.com/blogs/distserve-retro/

As inference systems scale to handle thousands of concurrent users, a fundamental architectural flaw in traditional continuous batching becomes apparent: **the forced colocation of prefill and decoding phases on the same hardware**.

> Because prefill is heavily compute-bound and decoding is heavily memory-bandwidth bound, placing them on the same GPUs **intrinsically couples their resource allocation and parallelism strategies.**

In these colocated setups, systems are forced to batch these distinct computation types together to maximize overall throughput.

However, this leads to strong **prefill-decoding interference**, where **latency-sensitive decoding steps** are significantly **delayed** by **lengthy prefill computations**, forcing service providers to over-provision expensive compute resources to **meet both Time to First Token (TTFT)** and **Time Per Output Token (TPOT)** service-level objectives.

To break this compromise, modern high-performance inference architectures have introduced **prefill-decode disaggregation**, a paradigm shift that assigns the prefill and decoding computation to entirely separate GPUs.

In a disaggregated system, a dedicated "prefill instance" handles only the processing of the user's prompt to generate the very first token. Once this compute-intensive prefill phase is complete, the prefill instance transmits the generated intermediate states— **specifically the KV cache** —along with the first token to a separate "decoding instance".

This complete isolation fundamentally **eliminates prefill-decoding interference**, ensuring that bursty, long-context prompts never stall the continuous, step-by-step generation of ongoing responses.

Beyond eliminating interference, disaggregation allows each phase to scale independently using **tailored resource allocation and model parallelism strategies** optimized for their specific latency requirements.

For example, to meet stringent TTFT service-level objectives, prefill instances can utilize high degrees of intra-operator parallelism to accelerate the compute-heavy prompt processing. Conversely, because the decoding phase requires far less computation per token but struggles with GPU underutilization, the architecture can allocate multiple prefill instances to feed a single decoding instance. This funneling effect allows the decoding instance to accumulate a much larger batch size on dedicated hardware, **maximizing throughput without sacrificing TPOT**.

> While disaggregation solves compute contention, it introduces a significant new challenge: the **communication overhead of transferring massive KV caches across the network**.

The intermediate states generated during the prefill phase can be exceptionally large; for instance, serving a single **512-token** **request on a 66-billion parameter model generates over a gigabyte of KV cache data**.

When serving hundreds of requests per second, transferring this data from prefill GPUs to decoding GPUs demands immense network bandwidth—often requiring 90 Gbps or more just to render the transmission overhead invisible to the user. If not managed correctly, this data transfer can quickly replace compute stalls as the primary bottleneck in the inference pipeline.

![afd](https://substackcdn.com/image/fetch/$s_!1tC5!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4c015b61-b71f-45b5-a4c2-b8fb90d82e28_2618x1494.png)

Link: https://haoailab.com/blogs/distserve-retro/

To mitigate these massive data transfer costs, disaggregated serving frameworks must employ sophisticated, **topology-aware placement algorithms**.

In clusters equipped with cutting-edge InfiniBand networks, prefill and decoding instances can be flexibly placed across different nodes without severe penalties.

However, in environments with limited cross-node bandwidth, the system must strategically colocate the corresponding prefill and decoding instances within the same physical node.

By doing so, the architecture can route the heavy KV cache transfers through ultra-fast intra-node connections, such as NVIDIA's NVLink, which boasts peak bandwidths of up to 600 GB/s.

> This hardware-aware orchestration ensures that the system maintains high goodput and strict latency guarantees, making disaggregation a vital strategy for cost-effective, large-scale LLM serving.

---

## Frameworks in Action

To truly understand how these theoretical optimizations translate into real-world performance, we must look at **production-grade inference engines like** **vLLM**.

> **vLLM** successfully **orchestrates continuous batching** (iteration-level scheduling) while **solving** one of the **most critical bottlenecks in LLM serving**: memory fragmentation.

Traditional inference frameworks allocate a contiguous chunk of GPU memory ahead-of-time for a request's maximum possible context length. Because generation lengths are unpredictable, this rigid allocation leads to massive memory waste—often up to 80% memory fragmentation.

> vLLM solves this through its core innovation, **PagedAttention**, which takes inspiration from operating **system virtual memory and paging**.

![Introduction to vLLM and PagedAttention | Runpod Blog](https://substackcdn.com/image/fetch/$s_!SDdq!,w_1456,c_limit,f_webp,q_auto:good,fl_lossy/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F598abbab-88eb-441b-a037-3dea5b00f01b_1200x591.gif)

Link: https://www.runpod.io/blog/introduction-to-vllm-and-pagedattention

Instead of demanding contiguous memory, **PagedAttention divides the KV cache into fixed-size blocks (or "pages") that can be stored non-contiguously in the GPU's memory**.

The engine's Block Manager maintains a mapping between logical virtual blocks and physical memory blocks, allocating them on the fly only when they are actually needed during generation. This dynamic, just-in-time memory management practically eliminates waste, limiting memory fragmentation to under 4% (only occurring in the last partially filled block).

By drastically reducing memory waste, vLLM frees up vast amounts of VRAM. This recovered memory can be used to hold significantly more sequences at once, allowing the engine to drastically increase its batch size. When combined with a preemptive scheduler and continuous batching, **this architecture yields massive performance gains, achieving up to 23x or 24x higher throughput compared to naive static batching systems** like Hugging Face Transformers, while simultaneously reducing p50 latency.

---

## Elastic Resource Allocation

As inference infrastructure scales, maximizing hardware utilization across variable, multi-tenant workloads becomes essential.

While hardware features like MIG partition the GPU physically, modern software projects like **[kvcached](https://github.com/ovg-project/kvcached)** achieve elastic GPU sharing by bringing OS-style virtual memory abstraction directly to the LLM's KV cache.

Traditional serving engines must statically reserve physical GPU memory at startup, which is **highly inefficient for dynamic workloads**.

> The `kvcached` daemon solves this by **decoupling logical GPU virtual addressing from physical memory allocation**.

When multiple LLMs share a GPU, `kvcached` reserves only the virtual address space initially; it then dynamically maps and allocates physical GPU memory strictly on-demand as cache blocks are actively used during inference.

![Make GPU Sharing Flexible and Easy](https://substackcdn.com/image/fetch/$s_!lkDr!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F244e7e7c-013b-4386-8eb7-0b4d2e75f8e2_3080x1388.jpeg)

Link: https://github.com/ovg-project/kvcached?tab=readme-ov-file

This elastic architecture provides several transformative benefits for production deployments:

- **Multi-LLM Serving:** Multiple different models can concurrently share the same physical GPU memory pool elastically, replacing rigid memory partitioning and significantly reducing serving costs.
- **Serverless and Compound AI:** Models can allocate memory only when actively serving requests and release it immediately when idle or finished. This enables true serverless LLM scaling with rapid cold-starts and allows complex multi-model pipelines (e.g., retrieval, reasoning, summarization) to share resources fluidly.
- **Workload Colocation:** Because memory can be reclaimed instantly without modifying the underlying engine code, LLM inference can efficiently coexist on the same hardware alongside other memory-intensive GPU jobs like model training, fine-tuning, or vision workloads.

By implementing this fast-path/slow-path page allocation system, `kvcached` has been shown to deliver a **2x to 28x reduction in Time to First Token (TTFT)** compared to static allocation systems when handling bursty, concurrent workloads.

---

## Next Steps

If there's one thing to take away from all of this, it's that LLM inference is essentially a **resource management problem disguised as a generation task**.

Every optimization we covered — continuous batching, chunked prefill, disaggregation, PagedAttention — exists because prefill and decode want opposite things from the hardware, and the entire history of inference engineering has been about negotiating that tension more cleverly.

The good news? **You don't need to build any of this from scratch**. Frameworks like **vLLM** and **kvcached** package these ideas into production-ready systems.

But understanding *why* they work the way they do makes you a much better operator — you'll know which knobs to turn, what tradeoffs you're accepting, and when something is actually bottlenecked vs. just misconfigured.

On Friday, we'll get hands-on with this. See you in the lab! 🔬

![](https://substackcdn.com/image/fetch/$s_!64d4!,w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8a5b08d8-cb8d-4094-9ce8-605b87b3e2cd_1200x630.png)