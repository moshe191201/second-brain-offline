# Vault Improvements & Eval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close five Karpathy llm-wiki compliance gaps in the vault, then produce a manual test checklist with authored eval content.

**Architecture:** Implement structural files (CLAUDE.md, log.md, scripts/lint_vault.py, eval/VAULT_TESTS.md) and 8 wiki/sources/ summary pages. No changes to raw/, no changes to existing wiki/ or index/ files except adding a "Sources" column to source-registry.md and an "Analyses" section stub to _map-of-content.md. qmd update+embed once at the end to pick up new summaries. No automated test harness — the test checklist is a manual document.

**Tech Stack:** Python 3 stdlib (lint script), Markdown + Obsidian wikilink conventions, qmd CLI, graphify CLI.

---

## File map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `CLAUDE.md` | Vault schema: layers, conventions, 3 workflows |
| Create | `index/log.md` | Append-only ingest journal, backfilled |
| Create | `scripts/lint_vault.py` | Deterministic lint, exits non-zero on findings |
| Create | `wiki/sources/` (dir + 8 files) | Per-source summary pages |
| Modify | `index/source-registry.md` | Add Summary column |
| Modify | `index/_map-of-content.md` | Add Analyses section stub |
| Create | `eval/VAULT_TESTS.md` | Manual test checklist with authored T1–T4 content |

---

## Task 1: Root `CLAUDE.md` schema file

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create CLAUDE.md**

```markdown
---
# Vault Schema — LLM Finetuning Second Brain
# Karpathy llm-wiki pattern · 3-layer model
# Full replication runbook: instructions.md
---

# CLAUDE.md — Vault Schema

## Three-layer model

| Layer | Folder | Rule |
|-------|--------|------|
| Source | `raw/` | **Immutable.** Never edit, rename, or delete. |
| Knowledge | `wiki/` | Atomic synthesized notes. One concept per file. |
| Navigation | `index/` | Maps, registry, log, takeaways. |

`eval/` — test fixtures. **Never register as a qmd collection.**

## Note conventions

- Filename: `kebab-case.md` (concept notes), `wiki/sources/slug.md` (summaries)
- Frontmatter required: `title`, `type` (concept | source-summary | analysis | index), `tags`, `sources` (wikilinks to raw clippings) — index-type notes exempt from `sources`
- Wikilinks over raw URLs for internal references
- One concept per note; update existing notes before creating new ones

### Note template

```yaml
---
title: "<Title>"
type: concept
tags: [tag1, tag2]
sources:
  - "[[Raw Clipping Filename Without Extension]]"
---

# Title

**One-sentence thesis in bold.**

Body. Dense [[wikilinks]] to sibling notes.

## Related
[[note-a]] · [[note-b]]
```

## Safety rules

- Never invent provenance, dates, authors, or claims
- Never collapse distinct concepts into one note
- Never create a duplicate — search qmd first, then update the existing note
- Mark uncertain extraction as uncertain and link to source

## Workflow — Ingest (new raw/ clipping)

1. `qmd search "<title keywords>" -n 5` — find related existing notes
2. Create `wiki/sources/<slug>.md` (source-summary template)
3. Create or update concept notes in `wiki/`
4. Update `index/_map-of-content.md` and `index/source-registry.md`
5. Append to `index/log.md`: `## [YYYY-MM-DD] ingest | <title>`
6. `qmd update && qmd embed`
7. `graphify raw/ --update` (re-extracts only changed files)

## Workflow — Query

1. `qmd search "<terms>" -n 5` for fast keyword lookup
2. `qmd query` with intent/lex/vec fields for conceptual questions
3. `graphify query "<question>"` for multi-hop entity traversal
4. Fetch full docs: `qmd get "#docid"` before making claims
5. **Write-back rule:** if answering produces novel cross-source synthesis
   not already in any note, save as `wiki/<slug>.md` with `type: analysis`,
   list source wiki notes in `sources:`, link from MOC Analyses section,
   append `## [YYYY-MM-DD] analysis | <title>` to `index/log.md`

## Workflow — Lint

1. `python3 scripts/lint_vault.py` — fix all findings before proceeding
2. LLM pass: scan wiki/ for contradictions between notes and stale claims
3. Fix findings; re-run until exit 0
```

- [ ] **Step 2: Verify file exists**

```bash
head -5 CLAUDE.md
```
Expected: YAML front-matter comment lines.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat(vault): add root CLAUDE.md schema (Karpathy llm-wiki layer 3)"
```

---

## Task 2: `index/log.md` — append-only ingest journal

**Files:**
- Create: `index/log.md`

- [ ] **Step 1: Create log.md backfilled from the build session**

```markdown
---
title: Ingest Log
type: index
tags: [log, provenance]
---

# Ingest Log

Append-only. Format: `## [YYYY-MM-DD] <operation> | <title>`
Operations: `ingest` · `build` · `lint` · `analysis`

---

## [2026-06-11] ingest | The Finetuning Landscape - A Map of Modern LLM Training
Source: theneuralmaze.substack.com · Lesson 1/8 · Derived: the-llm-training-pipeline, the-transformer-architectures, pretraining-and-base-models

## [2026-06-11] ingest | The Engineer's Guide to Supervised Finetuning
Source: theneuralmaze.substack.com · Lesson 2/8 · Derived: supervised-finetuning, loss-masking-and-chat-templates, lima-hypothesis-data-quality

## [2026-06-11] ingest | Understanding LoRA from First Principles
Source: theneuralmaze.substack.com · Lesson 3/8 · Derived: lora

## [2026-06-11] ingest | QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models
Source: theneuralmaze.substack.com · Lesson 4/8 · Derived: qlora-and-quantization, kv-cache

## [2026-06-11] ingest | The RLHF Landscape - Aligning LLMs Beyond SFT
Source: theneuralmaze.substack.com · Lesson 5/8 · Derived: rlhf-ppo-vs-dpo

## [2026-06-11] ingest | The RL Algorithm Behind DeepSeek's Reasoning Models
Source: theneuralmaze.substack.com · Lesson 6/8 · Derived: grpo-and-variants

## [2026-06-11] ingest | Beyond Text A Guide to Vision & TTS Finetuning
Source: theneuralmaze.substack.com · Lesson 7/8 · Derived: multimodal-finetuning-vision-tts

## [2026-06-11] ingest | A Practical Guide to LLM Inference at Scale
Source: theneuralmaze.substack.com · Lesson 8/8 · Derived: llm-inference-at-scale, kv-cache

## [2026-06-11] build | Initial knowledge graph + search index
graphify: 141 nodes, 268 edges, 8 communities · qmd: 3 collections, 24 docs, 104 chunks embedded
```

- [ ] **Step 2: Verify**

```bash
grep "^## " index/log.md | wc -l
```
Expected: 9 (8 ingests + 1 build)

- [ ] **Step 3: Commit**

```bash
git add index/log.md
git commit -m "feat(vault): add index/log.md backfilled ingest journal"
```

---

## Task 3: `scripts/lint_vault.py`

**Files:**
- Create: `scripts/lint_vault.py`

- [ ] **Step 1: Create lint script**

```python
#!/usr/bin/env python3
"""Vault lint: exits non-zero if any finding is reported."""

import re
import sys
from pathlib import Path

VAULT = Path(__file__).parent.parent
RAW = VAULT / "raw"
WIKI = VAULT / "wiki"
INDEX = VAULT / "index"
LOG = INDEX / "log.md"
MOC = INDEX / "_map-of-content.md"

# Wikilinks that are intentionally not vault notes
KNOWN_EXTERNAL = {"Miguel Otero Pedrido"}

findings = []

def find(msg): findings.append(msg)

def stems():
    """All valid wikilink targets across raw/, wiki/, wiki/sources/, index/."""
    result = {}
    for folder in [RAW, WIKI, WIKI / "sources", INDEX]:
        for p in folder.glob("*.md"):
            result[p.stem] = p
    return result

def wikilinks_in(text):
    return [m.group(1).strip() for m in re.finditer(r"\[\[([^\]|#]+)", text)]

all_stems = stems()

# 1. Broken wikilinks
for folder in [WIKI, INDEX]:
    for p in folder.rglob("*.md"):
        for link in wikilinks_in(p.read_text()):
            if link not in all_stems and link not in KNOWN_EXTERNAL:
                find(f"BROKEN WIKILINK: [[{link}]] in {p.relative_to(VAULT)}")

# 2. Orphan wiki notes (no inbound link)
linked_to = set()
for folder in [WIKI, INDEX]:
    for p in folder.rglob("*.md"):
        for link in wikilinks_in(p.read_text()):
            linked_to.add(link)

for p in WIKI.rglob("*.md"):
    if p.stem not in linked_to:
        find(f"ORPHAN NOTE: {p.relative_to(VAULT)} has no inbound links")

# 3. Raw clippings never referenced
raw_stems = {p.stem for p in RAW.glob("*.md")}
for stem in raw_stems:
    if stem not in linked_to:
        find(f"UNREFERENCED RAW: {stem}")

# 4. Wiki notes missing sources: frontmatter (index-type and sources subdir exempt)
for p in WIKI.glob("*.md"):
    text = p.read_text()
    if "type: index" in text or "type: analysis" in text:
        continue
    if "sources:" not in text:
        find(f"MISSING SOURCES: {p.relative_to(VAULT)}")

# 5. Each raw clipping has an ingest entry in log.md
if LOG.exists():
    log_text = LOG.read_text()
    for p in RAW.glob("*.md"):
        if p.stem not in log_text:
            find(f"NO LOG ENTRY: {p.name} missing from index/log.md")
else:
    find("MISSING FILE: index/log.md does not exist")

# 6. Every wiki note reachable from MOC (transitive closure)
if MOC.exists():
    visited = set()
    queue = [MOC]
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        if not current.exists():
            continue
        for link in wikilinks_in(current.read_text()):
            if link in all_stems:
                queue.append(all_stems[link])
    reachable = {p.stem for p in visited}
    for p in WIKI.rglob("*.md"):
        if p.stem not in reachable:
            find(f"UNREACHABLE FROM MOC: {p.relative_to(VAULT)}")
else:
    find("MISSING FILE: index/_map-of-content.md does not exist")

# 7. Duplicate stems across folders
seen_stems = {}
for folder in [RAW, WIKI, WIKI / "sources", INDEX]:
    for p in folder.glob("*.md"):
        if p.stem in seen_stems:
            find(f"DUPLICATE STEM: '{p.stem}' in {p.relative_to(VAULT)} and {seen_stems[p.stem].relative_to(VAULT)}")
        seen_stems[p.stem] = p

# Report
if findings:
    print(f"\n{'='*60}")
    print(f"VAULT LINT: {len(findings)} finding(s)")
    print('='*60)
    for f in findings:
        print(f"  • {f}")
    print()
    sys.exit(1)
else:
    print(f"VAULT LINT: OK — no findings ({len(all_stems)} notes checked)")
    sys.exit(0)
```

- [ ] **Step 2: Make executable and run**

```bash
chmod +x scripts/lint_vault.py
python3 scripts/lint_vault.py
```
Expected: "VAULT LINT: OK" (or findings to fix before continuing).

- [ ] **Step 3: Commit**

```bash
git add scripts/lint_vault.py
git commit -m "feat(vault): add scripts/lint_vault.py deterministic lint"
```

---

## Task 4: `wiki/sources/` — eight per-source summary pages

**Files:**
- Create: `wiki/sources/the-finetuning-landscape.md`
- Create: `wiki/sources/the-engineers-guide-to-sft.md`
- Create: `wiki/sources/understanding-lora.md`
- Create: `wiki/sources/qlora-explained.md`
- Create: `wiki/sources/the-rlhf-landscape.md`
- Create: `wiki/sources/the-rl-algorithm-behind-deepseek.md`
- Create: `wiki/sources/beyond-text-vision-and-tts.md`
- Create: `wiki/sources/llm-inference-at-scale.md`
- Modify: `index/source-registry.md` (add Summary column)
- Modify: `index/_map-of-content.md` (add Analyses stub)

(Full file contents in Steps 1–8 below.)

- [ ] **Step 1: Create wiki/sources/ and summary for Lesson 1**

```bash
mkdir -p "wiki/sources"
```

File: `wiki/sources/the-finetuning-landscape.md`
```markdown
---
title: "Summary — The Finetuning Landscape"
type: source-summary
tags: [transformer, pretraining, llm-pipeline]
sources:
  - "[[The Finetuning Landscape - A Map of Modern LLM Training]]"
published: 2026-02-11
---

# Summary — The Finetuning Landscape

**Lesson 1 of 8 establishes the map: all modern LLMs are decoder-only Transformers
trained by self-supervised next-token prediction, then shaped by SFT and RL.**

The article traces the history from LSTMs and attention-as-add-on through the
"Attention Is All You Need" paper, explains the three Transformer families
(encoder-only for classification, encoder–decoder for seq2seq, decoder-only for
generation), and introduces scaling laws as the empirical foundation for why
bigger training runs reliably produce better models. It defines the full LLM
pipeline—pretraining builds world knowledge via causal language modeling on
trillions of tokens, SFT shapes behavior via instruction data, and alignment
(RLHF) further steers outputs. Continued pretraining is presented as a bridge
for domain adaptation without rebuilding from scratch. The lesson is
intentionally foundational: techniques like LoRA only make sense once you know
what the underlying weight matrix looks like and why it is so large.

## Key claims
- Attention was not invented in the Transformer paper — it preceded it as an LSTM add-on → [[the-transformer-architectures]]
- Decoder-only architecture dominates modern LLMs → [[the-transformer-architectures]]
- Scaling laws make compute, data, and parameters predictably related → [[pretraining-and-base-models]]
- Full pipeline: pretraining → SFT → alignment → [[the-llm-training-pipeline]]

## Derived concept notes
[[the-llm-training-pipeline]] · [[the-transformer-architectures]] · [[pretraining-and-base-models]]
```

- [ ] **Step 2: Summary for Lesson 2 — SFT**

File: `wiki/sources/the-engineers-guide-to-sft.md`
```markdown
---
title: "Summary — The Engineer's Guide to Supervised Finetuning"
type: source-summary
tags: [sft, loss-masking, chat-templates, lima]
sources:
  - "[[The Engineer's Guide to Supervised Finetuning]]"
published: 2026-02-18
---

# Summary — The Engineer's Guide to Supervised Finetuning

**SFT teaches behavioral patterns—roles, turn-taking, structure—not new
factual knowledge; the two key mechanics are loss masking and chat templates.**

The article argues that SFT changes behavior, not world knowledge: the model
already knows facts from pretraining; SFT teaches it how to respond. Loss
masking sets all non-assistant tokens to `-100` (PyTorch's `ignore_index`) so
the model only learns to predict its own outputs. Chat templates (Jinja2
strings, e.g. Qwen3's) format multi-turn conversations into a single token
sequence; train/deploy template mismatch is flagged as a top real-world failure
mode. The LIMA hypothesis is introduced: around a thousand carefully curated,
high-quality examples can outperform models trained on tens of thousands of
noisy ones — data mixture design is the engineer's core job. DeepSeek-R1's
cold-start SFT on high-quality chain-of-thought data is used to show that RL
cannot invent reasoning that SFT never seeded. Evaluation guidance covers
qualitative review, LLM-as-judge, and benchmark suites.

## Key claims
- Loss masking: `-100` is CrossEntropyLoss ignore_index, applied to user tokens → [[loss-masking-and-chat-templates]]
- Chat template mismatch is a top production failure mode → [[loss-masking-and-chat-templates]]
- LIMA: ~1k curated examples beats tens of thousands of noisy ones → [[lima-hypothesis-data-quality]]
- Cold-start SFT seeds reasoning that RL then refines → [[supervised-finetuning]]

## Derived concept notes
[[supervised-finetuning]] · [[loss-masking-and-chat-templates]] · [[lima-hypothesis-data-quality]]
```

- [ ] **Step 3: Summary for Lesson 3 — LoRA**

File: `wiki/sources/understanding-lora.md`
```markdown
---
title: "Summary — Understanding LoRA from First Principles"
type: source-summary
tags: [lora, peft, vram]
sources:
  - "[[Understanding LoRA from First Principles]]"
published: 2026-02-25
---

# Summary — Understanding LoRA from First Principles

**LoRA's central claim: finetuning updates are intrinsically low-rank, so
freezing the base weights and training a small BA factorization is sufficient.**

Full finetuning has two problems: VRAM constraints (all gradients + optimizer
states for every parameter) and catastrophic forgetting (unguarded weight
updates destroy prior knowledge). LoRA freezes W and introduces two thin
matrices B (d×r) and A (r×d) with r ≪ d; the update W' = W + (α/r)BA is
applied at inference with no extra latency (B and A can be merged). The
hyperparameter α controls update strength relative to rank; a common heuristic
is α = 2r. The intrinsic dimensionality hypothesis from prior work is the
theoretical foundation — finetuning directions live in a low-dimensional
subspace. Practical guidance covers rank selection (8–32 usually suffices),
target module selection (attention projections > MLP layers for most tasks),
and when to consider higher ranks (long-context, code, multilingual). QLoRA
extends this by quantizing the frozen base to 4-bit, freeing most VRAM for
activations and the LoRA adapters.

## Key claims
- Finetuning updates are low-rank — B and A with r≪d suffice → [[lora]]
- W' = W + (α/r)BA; α controls update strength → [[lora]]
- Freezing W prevents catastrophic forgetting → [[lora]]
- QLoRA extends LoRA to 4-bit frozen base → [[qlora-and-quantization]]

## Derived concept notes
[[lora]]
```

- [ ] **Step 4: Summary for Lesson 4 — QLoRA**

File: `wiki/sources/qlora-explained.md`
```markdown
---
title: "Summary — QLoRA Explained"
type: source-summary
tags: [qlora, nf4, quantization, vram]
sources:
  - "[[QLoRA Explained - How 4 Bit Quantization Unlocks Frontier Models]]"
published: 2026-03-04
---

# Summary — QLoRA Explained

**QLoRA makes 65B-parameter finetuning possible on a single GPU by combining
NF4 quantization, double quantization, and paged optimizers.**

Standard INT8/INT4 quantization is lossy because weight distributions are
approximately Gaussian but uniform quantization wastes bins at the extremes.
NF4 (NormalFloat 4) solves this by computing quantile boundaries to ensure
equal expected occupancy per bin — making it information-theoretically optimal
for normally distributed weights. Double quantization quantizes the
quantization constants themselves, saving ~0.5 bits/parameter. Paged optimizers
use CPU RAM as an overflow buffer for optimizer states during gradient
accumulation spikes, preventing OOM crashes. Together these allow a frozen
4-bit base model + 16-bit LoRA adapters to match full 16-bit finetuning quality
while freeing ~75% of weight VRAM. The article also surveys the GPU hardware
landscape (A100, H100, consumer 3090/4090) and reviews other quantization
formats (GPTQ, AWQ, GGUF for inference vs. NF4 for training).

## Key claims
- NF4 places quantile boundaries to match Gaussian weight distribution → [[qlora-and-quantization]]
- Double quantization saves ~0.5 bits/param by quantizing the constants → [[qlora-and-quantization]]
- Paged optimizers use CPU RAM overflow to prevent OOM → [[qlora-and-quantization]]
- 4-bit base + 16-bit adapters ≈ full 16-bit quality, ~75% VRAM saved → [[qlora-and-quantization]]
- KV cache is the dynamic memory freed when static weights shrink → [[kv-cache]]

## Derived concept notes
[[qlora-and-quantization]] · [[kv-cache]]
```

- [ ] **Step 5: Summary for Lesson 5 — RLHF**

File: `wiki/sources/the-rlhf-landscape.md`
```markdown
---
title: "Summary — The RLHF Landscape"
type: source-summary
tags: [rlhf, ppo, dpo, reward-model]
sources:
  - "[[The RLHF Landscape - Aligning LLMs Beyond SFT]]"
published: 2026-03-11
---

# Summary — The RLHF Landscape

**RLHF exists because human preference ("A is better than B") is not
differentiable; PPO and DPO are the two dominant solutions, with different
cost/quality trade-offs.**

SFT cannot optimize preferences directly — it teaches imitation, not judgment.
RLHF introduces a reward model trained on pairwise preference data, then uses
RL to maximize reward while a KL penalty prevents the policy from diverging
too far from the SFT reference. PPO requires four models in memory
simultaneously (actor, reference, critic, reward model) making it expensive
but capable of the highest quality ceiling. DPO re-derives the reward model
in closed form from preference pairs, eliminating the separate RM and critic;
it requires only two models and standard supervised loss, at the cost of being
sensitive to data quality. The KL penalty against the SFT baseline is
identified as the single most consequential hyperparameter in either algorithm.
The article also covers IPO (fixing DPO's overfitting), KTO (bandit feedback
without pairs), and RLAIF (AI-generated preferences via LLM-as-Judge).

## Key claims
- PPO needs four models in memory simultaneously → [[rlhf-ppo-vs-dpo]]
- DPO: closed-form, two models, standard supervised loss → [[rlhf-ppo-vs-dpo]]
- KL penalty against SFT reference is the most important knob → [[rlhf-ppo-vs-dpo]]
- RLAIF uses LLM-as-Judge to generate preferences without humans → [[rlhf-ppo-vs-dpo]]

## Derived concept notes
[[rlhf-ppo-vs-dpo]]
```

- [ ] **Step 6: Summary for Lesson 6 — GRPO**

File: `wiki/sources/the-rl-algorithm-behind-deepseek.md`
```markdown
---
title: "Summary — The RL Algorithm Behind DeepSeek's Reasoning Models"
type: source-summary
tags: [grpo, deepseek, rl, reasoning]
sources:
  - "[[The RL Algorithm Behind DeepSeek's Reasoning Models]]"
published: 2026-03-18
---

# Summary — The RL Algorithm Behind DeepSeek's Reasoning Models

**GRPO eliminates the critic by using a group of sampled responses as its own
baseline, cutting training cost to roughly 1/18th of PPO — but introduces
length bias that DAPO, GSPO, and Dr. GRPO each attempt to fix.**

Traditional PPO's critic is a neural network roughly as large as the policy;
GRPO replaces it by sampling a group of G responses per prompt and using their
mean reward as the baseline. This slashes memory overhead by 40–60% and
reduces training cost to roughly 1/18th. The article explains DeepSeek-R1's
training recipe: a cold-start SFT phase seeds chain-of-thought reasoning
(confirming RL cannot invent what SFT never seeded), then GRPO amplifies it.
However GRPO's token-level averaging creates length bias — wrong answers get
penalized less if they ramble, training models to be verbose when uncertain.
DAPO fixes this with clip-higher and token-level policy gradient. GSPO replaces
the per-token loss with a sequence-level KL divergence. Dr. GRPO removes
difficulty bias by normalizing per-question. All three variants preserve GRPO's
critic-free economics.

## Key claims
- GRPO cuts cost to ~1/18th of PPO by using group mean as baseline → [[grpo-and-variants]]
- 40–60% memory overhead reduction vs PPO → [[grpo-and-variants]]
- Length bias: token-level averaging lets wrong verbose answers off easy → [[grpo-and-variants]]
- Cold-start SFT still required before GRPO → [[supervised-finetuning]]

## Derived concept notes
[[grpo-and-variants]]
```

- [ ] **Step 7: Summary for Lesson 7 — Multimodal**

File: `wiki/sources/beyond-text-vision-and-tts.md`
```markdown
---
title: "Summary — Beyond Text: Vision & TTS Finetuning"
type: source-summary
tags: [multimodal, vlm, tts, snac, qwen3-vl]
sources:
  - "[[Beyond Text A Guide to Vision & TTS Finetuning]]"
published: 2026-03-25
---

# Summary — Beyond Text: Vision & TTS Finetuning

**Multimodal finetuning is not a new skill: encoders and codecs translate
modalities into tokens, then you attach LoRA adapters and run standard SFT.**

For VLMs, a frozen ViT encodes image patches into visual tokens; a projection
layer maps them into the LLM's embedding space (with optional compression like
2×2 token merging); the LLM decoder receives LoRA adapters and is trained with
loss only on text output tokens. Qwen3-VL 8B is the featured model: 256K
native context, DeepStack ViT feature fusion, Interleaved-MRoPE, 32-language
OCR, and a toggleable thinking mode. For TTS, neural audio codecs (SNAC,
EnCodec, DAC) tokenize waveforms into discrete codes at multiple Hz
(hierarchical layers at 12/24/48 Hz, 7 tokens per frame, ~83 tokens/second
total). The LLM vocabulary is extended with audio token IDs and trained with
ordinary next-token prediction — it does not "know" it is generating speech.
Orpheus-TTS 3B (Llama backbone + SNAC 24kHz) achieves ~200ms streaming latency
and needs ~30 minutes of clean audio for voice cloning. Key pitfall:
`repetition_penalty ≥ 1.1` is required to prevent droning.

## Key claims
- Vision encoder frozen during VLM finetuning; LoRA on LLM decoder only → [[multimodal-finetuning-vision-tts]]
- SNAC: 7 tokens per frame, ~83 tokens/second → [[multimodal-finetuning-vision-tts]]
- Qwen3-VL: 256K context, DeepStack ViT fusion → [[multimodal-finetuning-vision-tts]]
- repetition_penalty ≥ 1.1 required for TTS → [[multimodal-finetuning-vision-tts]]
- 30 minutes of audio sufficient for voice cloning via SFT → [[multimodal-finetuning-vision-tts]]

## Derived concept notes
[[multimodal-finetuning-vision-tts]]
```

- [ ] **Step 8: Summary for Lesson 8 — Inference**

File: `wiki/sources/llm-inference-at-scale.md`
```markdown
---
title: "Summary — A Practical Guide to LLM Inference at Scale"
type: source-summary
tags: [inference, serving, vllm, batching, kv-cache]
sources:
  - "[[A Practical Guide to LLM Inference at Scale]]"
published: 2026-04-01
---

# Summary — A Practical Guide to LLM Inference at Scale

**Inference is a resource-management problem: compute-bound prefill and
memory-bound decode fight over the same GPU, and the whole serving stack is
a chain of patches negotiating that tension.**

Prefill (process full prompt in one parallel pass) is compute-bound; decode
(generate one token at a time using the KV cache) is memory-bandwidth-bound.
Static batching wastes GPU by making everyone wait for the longest sequence.
Continuous batching (iteration-level scheduling) fixes this but creates
prefill-decode interference — long prompts stall everyone's TPOT. Chunked
prefill splits prompts into token-budgeted chunks. Prefill-decode disaggregation
separates GPUs per phase but demands ~90 Gbps to ship multi-GB KV caches.
vLLM uses continuous batching plus PagedAttention (OS-style paging of the KV
cache): limits fragmentation to <4% vs up to 80% naively, achieving up to 24×
throughput improvement. kvcached adds a virtual-memory abstraction over the
cache and delivers a 2×–28× reduction in TTFT on bursty workloads, enabling
serverless LLM deployment.

## Key claims
- Prefill = compute-bound (TTFT); decode = memory-bandwidth-bound (TPOT) → [[llm-inference-at-scale]]
- PagedAttention limits KV fragmentation to <4%, up to 24× throughput → [[llm-inference-at-scale]]
- Disaggregation requires ~90 Gbps for KV cache transfer → [[llm-inference-at-scale]]
- kvcached: 2×–28× TTFT reduction via virtual memory for KV cache → [[llm-inference-at-scale]]
- Shrinking weights frees KV cache budget → [[kv-cache]]

## Derived concept notes
[[llm-inference-at-scale]] · [[kv-cache]]
```

- [ ] **Step 9: Update source-registry.md with Summary column**

Edit `index/source-registry.md`: add a `Summary` column to the table with wikilinks to each summary page.

- [ ] **Step 10: Add Analyses stub to _map-of-content.md**

Append to `index/_map-of-content.md`:
```markdown

## Analyses

*Write-back notes from cross-source synthesis queries. Added here when created.*
```

- [ ] **Step 11: Run lint**

```bash
python3 scripts/lint_vault.py
```
Expected: OK — all sources reachable, summaries linked from registry.

- [ ] **Step 12: Update qmd index**

```bash
qmd update && qmd embed
```
Expected: new docs indexed, embeddings generated.

- [ ] **Step 13: Commit**

```bash
git add wiki/sources/ index/source-registry.md index/_map-of-content.md
git commit -m "feat(vault): add wiki/sources/ per-source summaries + update registry and MOC"
```

---

## Task 5: `eval/VAULT_TESTS.md` — manual test checklist

**Files:**
- Create: `eval/VAULT_TESTS.md`
- Note: `eval/` must NEVER be registered as a qmd collection.

- [ ] **Step 1: Create eval/VAULT_TESTS.md**

```markdown
# Vault Test Checklist

Manual test procedure for the LLM Finetuning Second Brain.
`eval/` is never a qmd collection — these gold answers must not contaminate retrieval.

**How to run:** For T1–T3, open a *fresh* Claude Code session in the vault root
(no prior conversation context), ask the question verbatim, record the answer.
For T0 and T4 run the exact commands shown.

**Results tally** — add a row per run:

| Date | T0 | T1 (n/10) | T2 (n/3) | T3 (n/2) | T4 | Notes |
|------|----|-----------|----------|----------|----|-------|
| — | — | — | — | — | — | first run |

---

## T0 — Lint (deterministic)

```bash
python3 scripts/lint_vault.py
```
**Pass:** exits 0, prints "VAULT LINT: OK".

---

## T1 — Known-answer eval (core test)

**Procedure per question:** fresh session → ask verbatim → check fact AND note cited.
**Group pass: ≥ 8/10.** If a T2 negative-control failure causes an unexpected fail
here, note it in the tally and re-run T1 excluding that question.

| # | Question | Gold fact | Gold note |
|---|----------|-----------|-----------|
| 1 | What does PyTorch's CrossEntropyLoss do with a label value of -100? | It is the `ignore_index` — that token is excluded from the loss computation | `loss-masking-and-chat-templates` |
| 2 | According to the LIMA paper, approximately how many training examples are needed to produce a well-aligned model? | Around a thousand carefully curated, high-quality examples | `lima-hypothesis-data-quality` |
| 3 | In LoRA, what does the hyperparameter α control, and what is the update formula? | α controls the strength of the adapter update; formula is W' = W + (α/r)BA | `lora` |
| 4 | What property of NF4 makes it information-theoretically suited for quantizing LLM weights? | It places quantile boundaries to match the approximately Gaussian distribution of weights, giving equal expected occupancy per bin | `qlora-and-quantization` |
| 5 | How many models must be held in GPU memory simultaneously for a full PPO-based RLHF run? | Four: actor, reference policy, critic (value model), and reward model | `rlhf-ppo-vs-dpo` |
| 6 | By approximately what fraction does GRPO reduce training cost compared to traditional PPO? | Roughly 1/18th (also: 40–60% memory overhead reduction) | `grpo-and-variants` |
| 7 | What audio token rate does the SNAC codec produce, and how many tokens does it generate per frame? | ~83 tokens per second total; 7 tokens per frame across three quantization layers | `multimodal-finetuning-vision-tts` |
| 8 | What repetition_penalty value is required when generating speech with Orpheus-TTS, and why? | ≥ 1.1 is required; without it the model repeats syllables or produces monotonic droning | `multimodal-finetuning-vision-tts` |
| 9 | What is PagedAttention's maximum KV cache memory fragmentation, and what throughput improvement does vLLM claim? | Under 4% fragmentation (vs up to 80% naive); up to ~24× throughput improvement | `llm-inference-at-scale` |
| 10 | What bandwidth is required to make prefill-decode disaggregation practical, and what project abstracts KV cache memory like virtual memory? | ~90 Gbps for KV cache transfer; kvcached provides the virtual-memory abstraction | `llm-inference-at-scale` |

---

## T2 — Negative controls

**Procedure:** fresh session → ask verbatim → answer must state the topic is not
covered in this vault. Any fabricated answer fails the whole group.
**Group pass: 3/3.** ⚠ A T2 failure (hallucination) is a system-trust issue —
flag it prominently in the tally regardless of T1 score.

| # | Question | Verified absent from corpus |
|---|----------|-----------------------------|
| 1 | What does this vault say about Mamba or state-space models as an alternative to Transformers? | Mamba / SSMs: confirmed absent from all 8 clippings |
| 2 | What does this vault say about speculative decoding? | Speculative decoding: confirmed absent from all 8 clippings |
| 3 | What does this vault say about Constitutional AI or RLAIF with a constitution document? | Constitutional AI: confirmed absent (RLAIF via LLM-as-Judge is present, but constitutional AI specifically is not) |

---

## T3 — Cross-source synthesis

**Procedure:** fresh session → ask verbatim → verify both sources cited.
**Group pass: 2/2.**

| # | Question | Expected synthesis | Expected sources |
|---|----------|--------------------|-----------------|
| 1 | The vault contains material on both QLoRA and vLLM. Is there a conceptual connection between QLoRA's paged optimizers and vLLM's PagedAttention? | Both apply OS-style paging to a GPU memory pressure problem: paged optimizers offload optimizer states to CPU RAM on gradient spikes during training; PagedAttention pages KV cache blocks during inference. Same idea, two different bottlenecks. | `qlora-and-quantization` + `llm-inference-at-scale` (or `kv-cache`) |
| 2 | How does 4-bit quantization of model weights (QLoRA/NF4) affect the KV cache budget available during inference? | Shrinking static weights from 16-bit to 4-bit frees ~75% of weight VRAM; at inference that freed VRAM is available for the KV cache, enabling larger batch sizes and longer contexts for the same GPU. | `qlora-and-quantization` + `kv-cache` |

---

## T4 — Engine smoke tests (no agent)

Run these commands directly; no Claude Code session needed.

```bash
# BM25 keyword search — expected: grpo-and-variants in top 3
qmd search "length bias GRPO critic group baseline" -n 3

# Hybrid semantic query — expected: qlora-and-quantization in top 3
qmd query "intent: find the note about 4-bit quantization for LLM training
lex: NF4 double quantization paged optimizer QLoRA
vec: information-theoretically optimal 4-bit datatype for normally distributed weights" -n 3

# Graph traversal — expected: traversal includes NF4, PagedAttention, KV Cache nodes
graphify query "how does quantization connect to inference memory management"
```

**Pass:** each command returns the expected note/nodes in top results.

---

## T5 — Incremental ingest (generic procedure, run per new clipping)

Run when a new clipping is added to `raw/`.

1. Drop new `.md` clipping into `raw/` — do not edit existing files.
2. Execute the full Ingest workflow from `CLAUDE.md`.
3. Verify each of the following:
   - [ ] No near-duplicate concept notes created (existing notes updated instead)
   - [ ] `index/_map-of-content.md` links to any new wiki note
   - [ ] `index/source-registry.md` has a row for the new clipping
   - [ ] `index/log.md` has a new `ingest` entry
   - [ ] `qmd search "<unique term from new clipping>" -n 3` returns the new content
   - [ ] T0 (lint) still passes
4. Record result in tally table with the clipping title in the Notes column.
```

- [ ] **Step 2: Verify eval/ not accidentally qmd-registered**

```bash
qmd collection list 2>/dev/null || qmd status
```
Expected: collections are `sources`, `concepts`, `indices` — no `eval`.

- [ ] **Step 3: Commit**

```bash
git add eval/VAULT_TESTS.md
git commit -m "feat(vault): add eval/VAULT_TESTS.md manual test checklist with T1-T4 content"
```

---

## Task 6: Final verification pass

- [ ] **Step 1: Run full lint**

```bash
python3 scripts/lint_vault.py
```
Expected: exit 0.

- [ ] **Step 2: Verify qmd collections include new summaries**

```bash
qmd search "SNAC 83 tokens" -n 3
```
Expected: `wiki/sources/beyond-text-vision-and-tts` or `wiki/multimodal-finetuning-vision-tts` in top results.

- [ ] **Step 3: Spot-check graphify still works**

```bash
graphify query "what is the relationship between LoRA and QLoRA"
```
Expected: traversal returns nodes for LoRA, QLoRA, NF4, double quantization.

- [ ] **Step 4: Final commit**

```bash
git add -A
git status  # confirm nothing unintended
git commit -m "chore(vault): final cleanup and verification pass" --allow-empty
```

---

## Self-review notes

- Spec section A3 (write-back convention) is implemented inside CLAUDE.md text — no separate file needed. ✓
- T2 Q3 is carefully scoped: RLAIF via LLM-as-Judge IS in the corpus; Constitutional AI specifically is not. The question wording is explicit. ✓
- `eval/` never appears in any qmd collection add command. ✓
- source-registry.md modification (Step 4.9) is described but requires reading the current file — implementor must add column without breaking existing table. ✓
- All gold facts in T1 verified against raw clipping text before inclusion (not derived from wiki notes). ✓
