# Vault Test Checklist

Manual test procedure for the LLM Finetuning Second Brain.

> ⚠ `eval/` is **never** a qmd collection. These gold answers must not contaminate retrieval.
> If you ever run `qmd collection add`, do NOT include this folder.

**How to run T1–T3:** Open a *fresh* Claude Code session in the vault root (no prior conversation context in that session). Ask the question verbatim, nothing else. Record the answer.

**How to run T0, T4:** Execute the shell commands directly; no agent session needed.

---

## Results tally

Add a row after each complete run (T0–T4). T5 is recorded per-ingest.

| Date | T0 | T1 (n/10) | T2 (n/3) | T3 (n/2) | T4 | Notes |
|------|----|-----------|----------|----------|----|-------|
| — | — | — | — | — | — | (first run pending) |

---

## T0 — Lint (deterministic, ~1 second)

```bash
python3 scripts/lint_vault.py
```

**Pass:** exits 0, prints `VAULT LINT: OK`.

---

## T1 — Known-answer eval (core test)

**Pass per question:** correct gold fact **AND** the gold note (or its raw source) cited.
**Group pass: ≥ 8/10.**

> ⚠ Note for first few runs: if a T2 negative-control failure occurs (hallucinated answer),
> flag it prominently in the tally — it may also affect T1 scoring.

| # | Ask verbatim | Gold fact | Gold note |
|---|-------------|-----------|-----------|
| 1 | "What does PyTorch's CrossEntropyLoss do with a label value of -100?" | It is the `ignore_index` — that position is excluded from the loss computation entirely | `loss-masking-and-chat-templates` |
| 2 | "According to the LIMA paper as discussed in this vault, approximately how many training examples are needed to produce a well-aligned model?" | Around a thousand carefully curated, high-quality examples | `lima-hypothesis-data-quality` |
| 3 | "In LoRA, what does the hyperparameter α control, and what is the update formula?" | α controls the strength of the adapter update relative to rank; formula: W' = W + (α/r)BA | `lora` |
| 4 | "What property makes NF4 well-suited for quantizing LLM weights compared to standard INT4?" | NF4 computes quantile-based bin boundaries to match the approximately Gaussian distribution of LLM weights, giving equal expected occupancy per bin — making it information-theoretically optimal for that distribution | `qlora-and-quantization` |
| 5 | "How many models must be held in GPU memory simultaneously for a full PPO-based RLHF training run?" | Four: actor (policy), reference policy, critic (value model), and reward model | `rlhf-ppo-vs-dpo` |
| 6 | "By approximately what fraction does GRPO reduce training cost compared to traditional PPO, and what architectural change achieves this?" | Roughly 1/18th the cost (also: 40–60% memory overhead reduction); achieved by eliminating the critic and using the group mean reward as the baseline instead | `grpo-and-variants` |
| 7 | "What audio token rate does the SNAC codec produce, and how many tokens does it generate per frame?" | ~83 tokens per second total; 7 tokens per frame, across three hierarchical quantization layers at 12/24/48 Hz | `multimodal-finetuning-vision-tts` |
| 8 | "What repetition_penalty value is required when generating speech with Orpheus-TTS, and what happens without it?" | `repetition_penalty ≥ 1.1` is required; without it the model repeats the same syllable or produces monotonic droning | `multimodal-finetuning-vision-tts` |
| 9 | "What is PagedAttention's maximum KV cache memory fragmentation, and what throughput improvement does vLLM claim over naive serving?" | Under 4% fragmentation (vs up to 80% with naive contiguous allocation); up to ~24× throughput improvement | `llm-inference-at-scale` |
| 10 | "What network bandwidth is required to make prefill-decode disaggregation practical, and what project provides a virtual-memory abstraction over the KV cache?" | ~90 Gbps for KV cache network transfer; `kvcached` provides the virtual-memory abstraction, delivering 2×–28× TTFT reduction on bursty workloads | `llm-inference-at-scale` |

---

## T2 — Negative controls

**Pass per question:** agent explicitly states the topic is not covered in this vault (or equivalent clear negative).
**Any fabricated/hallucinated answer fails the entire group.**
**Group pass: 3/3.**

> ⚠ A T2 failure is a system-trust issue. Flag it prominently in the tally even if T1 passes.
> Note: RLAIF via LLM-as-Judge IS in the corpus. Constitutional AI specifically is not —
> Q3 is worded to distinguish these.

| # | Ask verbatim | Verified absent |
|---|-------------|-----------------|
| 1 | "What does this vault say about Mamba or state-space models as an alternative to Transformers?" | Mamba / SSMs: confirmed absent from all 8 clippings |
| 2 | "What does this vault say about speculative decoding for faster inference?" | Speculative decoding: confirmed absent from all 8 clippings |
| 3 | "What does this vault say about Constitutional AI — the specific technique of using a list of principles to train a model to critique its own outputs?" | Constitutional AI (Anthropic's RLAIF-with-constitution technique): confirmed absent. RLAIF via LLM-as-Judge is present but is a different technique. |

---

## T3 — Cross-source synthesis

**Pass per question:** the connection is drawn correctly and both contributing notes/sources are cited.
**Group pass: 2/2.**

| # | Ask verbatim | Expected synthesis | Expected sources |
|---|-------------|-------------------|-----------------|
| 1 | "The vault covers both QLoRA and vLLM. Is there a conceptual connection between QLoRA's paged optimizers and vLLM's PagedAttention?" | Both apply OS-style memory paging to a GPU memory pressure problem — paged optimizers offload optimizer state pages to CPU RAM during gradient accumulation spikes (training), while PagedAttention pages KV cache blocks to eliminate fragmentation (inference). Same paging idea applied to two different bottlenecks in the LLM lifecycle. | `qlora-and-quantization` + `llm-inference-at-scale` (or `kv-cache`) |
| 2 | "How does 4-bit quantization of model weights (QLoRA/NF4) affect the KV cache budget available during inference?" | Shrinking static model weights from 16-bit to 4-bit frees roughly 75% of weight VRAM. At inference time, that freed VRAM becomes available for the dynamic KV cache — enabling larger batch sizes, longer contexts, or more concurrent requests on the same GPU. | `qlora-and-quantization` + `kv-cache` |

---

## T4 — Engine smoke tests (no agent session)

Run these commands directly in the vault root. All should complete in seconds.

```bash
# BM25 keyword search — expected: grpo-and-variants in top 3
qmd search "length bias GRPO critic group baseline" -n 3

# Hybrid semantic query — expected: qlora-and-quantization or qlora-explained in top 3
qmd query "intent: find the note about 4-bit quantization for LLM training
lex: NF4 double quantization paged optimizer QLoRA
vec: information-theoretically optimal 4-bit datatype for normally distributed weights" -n 3

# Graph traversal — expected: traversal includes NF4, KV Cache, PagedAttention nodes
graphify query "how does quantization connect to inference memory management"
```

**Pass:** each command returns the expected note/nodes in top results within a few seconds.
If `qmd query` fails due to a local model issue, fall back to `qmd search` with stronger lexical terms and note it in the tally.

---

## T5 — Incremental ingest (generic procedure, run per new clipping)

Run whenever a real new article is clipped into `raw/`. There is no designated fixture article — use the next real clipping you add.

1. Drop the new `.md` clipping into `raw/` — do not edit any existing file.
2. Execute the full **Ingest** workflow from `CLAUDE.md`.
3. Verify each checkpoint:
   - [ ] No near-duplicate concept notes created (existing notes updated instead of new ones spawned)
   - [ ] `index/_map-of-content.md` links to any new wiki note
   - [ ] `index/source-registry.md` has a new row for the clipping
   - [ ] `index/log.md` has a new `## [date] ingest | <title>` entry
   - [ ] `qmd search "<unique term from new clipping>" -n 3` returns the new content
   - [ ] T0 (lint) still passes after the ingest
4. Record result in the tally table with the clipping title in the Notes column.

**Pass:** all six checkpoints hold.
