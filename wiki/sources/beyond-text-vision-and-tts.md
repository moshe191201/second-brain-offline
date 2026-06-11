---
title: "Summary — Beyond Text: Vision & TTS Finetuning"
type: source-summary
tags: [multimodal, vlm, tts, snac, qwen3-vl, orpheus]
sources:
  - "[[Beyond Text A Guide to Vision & TTS Finetuning]]"
published: 2026-03-25
---

# Summary — Beyond Text: Vision & TTS Finetuning

**Multimodal finetuning is not a new skill: encoders and codecs translate modalities into tokens, then you attach LoRA adapters and run standard SFT.**

For VLMs, a frozen ViT encodes image patches into visual tokens; a projection layer maps them into the LLM's embedding space (with optional compression, e.g. 2×2 token merging, since visual tokens are expensive context); the LLM decoder receives LoRA adapters and is trained with loss only on text output tokens. Qwen3-VL 8B is the featured model: 256K native context window, DeepStack multi-level ViT feature fusion, Interleaved-MRoPE for spatial-temporal positional encoding, text-timestamp alignment for video, 32-language OCR, and a toggleable thinking mode. For TTS, neural audio codecs (SNAC, EnCodec, DAC) tokenize waveforms into discrete codes — hierarchical layers at 12/24/48 Hz, 7 tokens per frame, approximately 83 tokens per second total, with a codebook of 4,096 entries per layer. The LLM vocabulary is extended with audio token IDs and trained with ordinary next-token prediction; it does not "know" it is generating speech. Orpheus-TTS 3B (Llama backbone + SNAC 24kHz) achieves ~200ms streaming latency, needs ~30 minutes of clean audio for voice cloning, and requires `repetition_penalty ≥ 1.1` to prevent syllable repetition.

## Key claims
- Vision encoder frozen during VLM finetuning; LoRA on LLM decoder only → [[multimodal-finetuning-vision-tts]]
- SNAC: 7 tokens per frame, ~83 tokens/second total → [[multimodal-finetuning-vision-tts]]
- Qwen3-VL: 256K native context, DeepStack ViT fusion → [[multimodal-finetuning-vision-tts]]
- `repetition_penalty ≥ 1.1` required for TTS or model drones → [[multimodal-finetuning-vision-tts]]
- ~30 minutes of clean single-speaker audio sufficient for voice cloning → [[multimodal-finetuning-vision-tts]]

## Derived concept notes
[[multimodal-finetuning-vision-tts]]
