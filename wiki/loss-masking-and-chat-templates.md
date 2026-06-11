---
title: Loss Masking, Chat Templates, and SFT Mechanics
type: concept
tags: [sft, loss-masking, chat-template, implementation]
sources:
  - "[[The Engineer's Guide to Supervised Finetuning]]"
---

# Loss Masking, Chat Templates, and SFT Mechanics

The implementation details that distinguish SFT from CPT.

## Chat templates

A **chat template** (Jinja2, in `tokenizer_config.json`) flattens `{role, content}` messages into the single string the model sees. Tokens like `<|start_header_id|>user<|end_header_id|>`, `<think>`, `<|tool_call|>` are structural signals, not decoration. **Train/deploy template mismatch** is a classic failure: broken tool calls, the model answering for the user, missed end-of-turn.

## Loss masking

In SFT, loss is computed **only on assistant tokens**: user/system token labels are set to `-100` (PyTorch `CrossEntropyLoss.ignore_index`). "Understand the prompt, but only learn to respond."

- **Shift-right detail:** causal LMs predict the *next* token, so the loss on the last user token predicts the *first* assistant token. Off-by-one masking subtly breaks response initiation.
- **Gradient spikes:** the abrupt `-100` → active-label transition concentrates loss on the first assistant tokens — mitigate with lower LR or warm-up.

## Packing vs structure

CPT packs documents aggressively to saturate GPUs. In SFT naive packing causes **cross-contamination** (attention leaks between conversations). Modern fix: **padding-free SFT** with Flash Attention 2 and varlen (`cu_seqlens`) — multiple conversations per batch with a hard firewall between them. Alternative: grouped batching by length.

## Related

- [[supervised-finetuning]] · [[pretraining-and-base-models]] · [[llm-inference-at-scale]] (chunked prefill is the inference-side cousin of packing)
