# Finetuning

> Learn how to adapt Large Language Models for specific tasks without starting from scratch.

## Key Takeaways

- **LoRA (Low-Rank Adaptation)** — replaces full model updates with low-rank matrices; reduces trainable parameters by 80-90%
- **QLoRA (Quantized LoRA)** — combines LoRA with 4-bit quantization to enable training frontier models on consumer hardware
- **Multimodal finetuning** — finetuning vision-language models and text-to-speech systems using the same LoRA technique
- **RLHF vs LoRA/QLoRA** — RLHF optimizes alignment, LoRA/QLoRA preserve capability while teaching new behaviors
- **SFT vs alignment** — supervised fine-tuning shapes behavior; reinforcement learning aligns with human preferences

## Articles

- [[understanding-lora-from-first-principles]]
- [[qlora-explained]]
- [[beyond-text-vision-and-tts-finetuning]]
- [[the-rl-algorithm-behind-deepseeks-reasoning-models]]

## Related

- See also: [[training-pipeline]] for the full training pipeline
- See also: [[llm-fundamentals]] for transformer architecture background
