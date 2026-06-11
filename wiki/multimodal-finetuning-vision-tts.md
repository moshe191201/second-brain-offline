---
title: Multimodal Finetuning — Vision and TTS
type: concept
tags: [multimodal, vlm, tts, vision, audio]
sources:
  - "[[Beyond Text A Guide to Vision & TTS Finetuning]]"
---

# Multimodal Finetuning — Vision and TTS

**Key insight:** multimodal finetuning is *not a new skill*. The encoders/codecs translate modalities into tokens; your job stays the same — attach [[lora]] adapters to the Transformer backbone, prepare a dataset, run SFT.

## Vision (VLMs)

All modern VLMs (Qwen3-VL, Llama 3.2 Vision, Gemma 3) share three stages:

1. **Vision encoder (ViT)** — image patches → visual tokens. **Frozen** during finetuning (already knows visual features).
2. **Projection layer** — maps visual tokens into the LLM's embedding space (may compress, e.g. 2×2 token merging — visual tokens are expensive context).
3. **LLM decoder** — gets LoRA adapters, exactly like text finetuning. Loss only on text output tokens.

Practical: 300–1000px training resolution; consistent dimensions for batching; mix ~20% general VQA data to prevent forgetting. Use cases: radiology reports, document/OCR extraction to JSON or LaTeX, industrial inspection, crop disease detection.

**Qwen3-VL 8B** highlights: 256K context, DeepStack multi-level ViT feature fusion, Interleaved-MRoPE, text-timestamp alignment for video, 32-language OCR, toggleable thinking mode.

## TTS

Modern LLM-based TTS: **treat audio as just another language.** A **neural audio codec** (SNAC, EnCodec, DAC) tokenizes waveforms into discrete codes from a learned codebook — hierarchical layers at ~12/24/48 Hz capture prosody, phonetics, and texture (7 tokens per frame, ~83 tokens/s). Extend the LLM vocabulary with audio token IDs; train with ordinary next-token prediction. The LLM "doesn't know" it's generating speech.

**Orpheus-TTS 3B** (Canopy Labs): Llama-3B backbone + SNAC 24kHz, emotive tags (`<laugh>`, `<sigh>`), 8 preset voices, ~200ms streaming latency. ~30 min of clean single-speaker audio suffices for voice cloning via finetuning (beats zero-shot cloning on pacing/expression). Practical: token rate caps max duration; repetition_penalty ≥ 1.1 required; **<3B models are the TTS sweet spot** (latency beats size).

## Related

- [[lora]] · [[qlora-and-quantization]] · [[supervised-finetuning]]
