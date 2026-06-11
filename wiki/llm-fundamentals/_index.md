# LLM Fundamentals

> The foundation of understanding Large Language Models: transformers, architecture, and scaling.

## Key Takeaways

- **Attention mechanism** — invented before Transformers, allows models to query relevant information dynamically
- **Self-attention** — each token in a sequence attends to all other tokens in the same sequence
- **Positional encoding** — injects order information into transformer models (sine/cosine functions at different frequencies)
- **Multi-head attention** — allows the model to attend to different representation subspaces simultaneously
- **Three Transformer architectures**
  - **Encoder-only** — for understanding tasks (BERT)
  - **Encoder–decoder** — for sequence-to-sequence tasks (T5, BART)
  - **Decoder-only** — for next-token prediction (modern LLMs)
- **Scaling laws** — performance improves smoothly with model size, dataset size, and compute
- **Transformer architecture** — encoder, decoder, and output projection layers

## Articles

- [[transformer-101]]
- [[three-transformer-architectures]]
- [[the-transformer]]
- [[transformer-layers]]
- [[scaling-laws]]
- [[the-llm-training-pipeline]]
