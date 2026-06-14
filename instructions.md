# Building the Obsidian "Second Brain" — Full Instructions & Replication Runbook

> **What this document is.** Part 1 is an exact, step-by-step record of how this vault was
> transformed from a folder of raw web clippings into an indexed, queryable knowledge graph.
> Part 2 is the complete dependency list. Part 3 is a runbook for replicating the entire setup
> in a **closed (air-gapped) environment** with one-way file transfer, starting from vanilla
> Obsidian + raw clippings. It is written to be readable by a human engineer and executable
> verbatim by an AI agent (Claude Code or compatible).

---

## 0. Architecture overview

The vault follows a **three-layer model** (defined by the `obsidian-knowledge-graph` skill),
plus two independent retrieval engines built on top:

```
Moshe Vault/
├── CLAUDE.md       SCHEMA  — the vault contract loaded into every agent session: layer
│                              rules, note templates, the vault-grounding rule, and the
│                              Ingest/Query/Lint workflows. (Karpathy llm-wiki "layer 3".)
├── raw/            LAYER 1 — immutable source clippings (Obsidian Web Clipper output).
│                              NEVER edited, never deleted. The evidence layer.
├── wiki/           LAYER 2 — atomic synthesized concept notes (one idea per note), plus
│                              wiki/sources/ per-source summaries. Provenance in frontmatter.
├── index/          LAYER 3 — navigation: _map-of-content, source-registry, key-takeaways,
│                              and log.md (append-only ingest/analysis journal).
├── scripts/        TOOLING — lint_vault.py: deterministic vault lint (CLAUDE.md Lint workflow).
├── eval/           TESTS   — VAULT_TESTS.md manual checklist. NEVER a qmd collection.
├── graphify-out/   ENGINE A — entity/relationship knowledge graph (graph.json,
│                              graph.html, GRAPH_REPORT.md). Queried via `graphify query`.
└── (qmd index)     ENGINE B — hybrid BM25 + vector search over raw/, wiki/, index/ (NOT eval/).
                               Lives outside the vault in ~/.cache/qmd/. Queried via `qmd`.
```

Why two engines: **qmd** answers "find me the note about X" (lexical + semantic document
retrieval); **graphify** answers "how does X relate to Y" (multi-hop graph traversal across
extracted entities). They are complementary and both fully local.

Vanilla Obsidian needs **no community plugins** to use the result — wikilinks power
Obsidian's built-in graph view and backlinks pane natively.

---

## Part 1 — What was done, step by step

### Step 1. Survey the vault and load the skill

- Loaded the `obsidian-knowledge-graph` skill (`~/.claude/skills/obsidian_knowledge_graph_skill/`),
  which defines the 3-layer model, the ingestion loop, and the safety rules
  (never modify `raw/`, never invent provenance, update notes instead of duplicating).
- Listed `raw/`: 8 markdown clippings — the complete *Finetuning Sessions* series
  (Miguel Otero Pedrido, The Neural Maze, Substack), captured with the Obsidian Web Clipper.
  Each had YAML frontmatter: `source` URL, `author`, `published`/`created` dates, `tags: [clippings]`.
- Read all 8 clippings in full (~24,000 words) before writing anything.

### Step 2. Repair/build the tooling

Two tools needed setup (details and exact errors in §4 Troubleshooting):

1. **qmd** (Claude Code plugin `@tobilu/qmd`) — its `dist/` was missing. Built from source:
   ```bash
   cd ~/.claude/plugins/cache/qmd/qmd/0.1.0
   npm install --cache /tmp/npmcache-qmd && npm run build
   ```
2. **graphify** (PyPI package `graphifyy`) — installed into the active Python:
   ```bash
   python3 -m pip install graphifyy --break-system-packages
   ```

### Step 3. Synthesize the wiki layer (LLM work)

For each clipping, extracted the durable concepts and wrote **atomic notes** in `wiki/` —
13 notes total, each following this template:

```markdown
---
title: <Human Title>
type: concept
tags: [topic1, topic2]
sources:
  - "[[<exact raw clipping filename, no extension>]]"
---

# <Human Title>

**One-sentence thesis in bold.**

<Standalone explanation. Dense [[wikilinks]] to sibling notes.>

## Related
- [[note-a]] · [[note-b]]
```

Rules applied: one concept per note; every claim traceable to a clipping in `sources:`;
cross-links added in both directions; kebab-case filenames. The 13 notes:
`the-llm-training-pipeline`, `the-transformer-architectures`, `pretraining-and-base-models`,
`supervised-finetuning`, `loss-masking-and-chat-templates`, `lima-hypothesis-data-quality`,
`lora`, `qlora-and-quantization`, `kv-cache`, `rlhf-ppo-vs-dpo`, `grpo-and-variants`,
`multimodal-finetuning-vision-tts`, `llm-inference-at-scale`.

### Step 4. Build the index layer

Three navigation notes in `index/`:

- **`_map-of-content.md`** — master MOC, organized along the training pipeline "spine"
  (pretraining → SFT → alignment → efficiency → production). Entry point for any reader.
- **`source-registry.md`** — table mapping every raw clipping → its derived wiki notes,
  plus the key arXiv papers cited across the series. This is the provenance ledger.
- **`key-takeaways.md`** — 10 distilled cross-cutting insights, each linking back to wiki notes.

### Step 5. Build the knowledge graph (graphify pipeline)

Followed the `/graphify` skill pipeline exactly (commands use the interpreter recorded in
`graphify-out/.graphify_python`):

1. **Detect** — `graphify.detect.detect(Path('.'))` → 8 document files, ~24,046 words,
   no code/video. Result cached to `graphify-out/.graphify_detect.json`.
2. **Semantic extraction** — no `GEMINI_API_KEY` set, so per the skill the **host LLM itself**
   did extraction: dispatched one `general-purpose` subagent with the prompt from
   `~/.claude/skills/graphify/references/extraction-spec.md`, which read the 8 clippings and
   wrote `graphify-out/.graphify_chunk_01.json` (141 nodes, 279 edges, 3 hyperedges, each with
   EXTRACTED/INFERRED provenance and confidence scores). *(In the closed environment this LLM
   is MiniMax 2.7 behind Claude Code — same flow, no API key needed.)*
3. **Merge** — semantic results merged with the (empty) AST extraction into
   `.graphify_semantic.json`, deduplicated.
4. **Build & cluster** — `graphify.build` constructed the graph and ran Louvain community
   detection: **141 nodes, 268 edges, 8 communities**.
5. **Label** — the LLM named each community: Transformer Fundamentals & Pretraining ·
   Supervised Finetuning & Evaluation · LoRA & PEFT · Quantization & GPU Hardware ·
   RLHF & Preference Alignment · GRPO & Reasoning RL · Multimodal: Vision & TTS ·
   Inference Serving & Batching.
6. **Export** — `graphify-out/graph.html` (interactive viz), `graph.json` (GraphRAG-ready),
   `GRAPH_REPORT.md` (god nodes, surprising connections, suggested questions), `cost.json`.

### Step 6. Build the search index (qmd)

```bash
qmd collection add ./raw   --name sources    # + context description
qmd collection add ./wiki  --name concepts   # + context description
qmd collection add ./index --name indices    # + context description
qmd update                                   # index all 24 docs (BM25)
qmd embed                                    # 104 chunks embedded (local GGUF model)
```

Each collection was given a context description so the agent knows what lives where
(`sources` = verbatim clippings, `concepts` = synthesized notes, `indices` = maps).

### Step 7. Verify both retrieval paths

```bash
qmd search "GRPO critic length bias" -n 3
# → qmd://concepts/grpo-and-variants.md at 76% — correct top hit

graphify query "why does GRPO eliminate the critic model"
# → 18-node BFS traversal spanning the RLHF and GRPO communities
#   (Critic, GRPO, PPO, GSPO, DAPO, Dr. GRPO, DeepSeek-R1, KL Penalty, …)
```

Both engines returned correct, well-scoped results. Build declared complete.

### Step 8. Karpathy llm-wiki compliance pass (schema, journal, summaries, lint, eval)

A follow-up pass closed the gaps between this vault and Andrej Karpathy's llm-wiki
pattern, adding five artifacts:

- **`CLAUDE.md`** (vault root) — the schema/contract loaded into every agent session:
  three-layer rules, note templates, safety rules, a **vault-grounding rule** (for any
  in-domain question, always search + cite the vault; never answer from training data
  alone, and say so explicitly when the vault lacks coverage), and the Ingest / Query /
  Lint workflows. This is the "third layer" the original build lacked.
- **`index/log.md`** — append-only journal (`## [date] <op> | <title>`), backfilled with
  the 8 ingests and the build entry.
- **`wiki/sources/` (8 files)** — one `source-summary` note per raw clipping, linked from
  `index/source-registry.md`.
- **`scripts/lint_vault.py`** — pure-stdlib deterministic lint (broken wikilinks, orphans,
  unreferenced clippings, missing `sources:`, log coverage, MOC reachability, duplicate
  stems); exits non-zero on any finding.
- **`eval/VAULT_TESTS.md`** — manual test checklist (T0 lint · T1 known-answer · T2
  negative controls · T3 cross-source synthesis · T4 engine smoke · T5 incremental ingest).
  `eval/` is deliberately **never** registered as a qmd collection so gold answers cannot
  contaminate retrieval.

---

## Part 2 — Full dependency list

Exact versions as used in this build. Anything marked **(artifact)** must be physically
transferred into the closed environment.

### Runtimes

| Dependency | Version used | Notes |
|---|---|---|
| Node.js | v26.2.0 | Runs qmd. Any ≥20 LTS should work. **(artifact: installer/tarball)** |
| npm | 11.13.0 | Bundled with Node. Used only at install time. |
| Python | 3.12.13 | Runs graphify. ≥3.10 required. **(artifact if not present)** |
| Obsidian | any recent | Vanilla — no community plugins required. **(artifact: installer)** |

### The LLM (closed environment)

| Dependency | Role |
|---|---|
| Claude Code CLI | The agent harness that executes skills, synthesizes wiki notes, and performs graphify semantic extraction via subagents. **(artifact: installer)** |
| MiniMax 2.7 (local) | Wired into Claude Code as the base model (e.g. via `ANTHROPIC_BASE_URL` pointing at the local Anthropic-compatible endpoint). All "LLM work" in Part 1 routes here. No cloud key, no `GEMINI_API_KEY` — the graphify skill falls back to host-LLM subagent extraction automatically when no Gemini key is set, which is exactly what you want. |

### qmd (search engine)

| Item | Detail |
|---|---|
| Package | `@tobilu/qmd` **2.5.3** (npm). Provides the `qmd` binary. **(artifact: npm tarball or prebuilt install tree — see Part 3)** |
| Native deps | Pulls a llama.cpp-based runtime via npm postinstall (prebuilt binaries are **OS/arch-specific** — stage on a machine matching the target). |
| Embedding model | `hf_ggml-org_embeddinggemma-300M-Q8_0.gguf` — **318 MB**, auto-downloaded from HuggingFace to `~/.cache/qmd/models/` on first `qmd embed`. **(artifact: the entire `~/.cache/qmd/models/` directory)** |
| ⚠ Extra models | `qmd query` (reranking/expansion) may fetch *additional* GGUF models on first use. On the staging machine, run `qmd embed` **and** one `qmd query` once, then transfer the whole `models/` dir so nothing is missing offline. |
| Claude Code plugin | `qmd` plugin 0.1.0 (provides the qmd *skill* to the agent). Source at `~/.claude/plugins/cache/qmd/qmd/0.1.0`; must be built (`npm install && npm run build`) or copied prebuilt. **(artifact)** |

### graphify (knowledge graph engine)

| Item | Detail |
|---|---|
| Package | `graphifyy` **0.8.37** (PyPI). Provides `graphify` CLI + `graphify` Python module. **(artifact: wheels)** |
| Python deps | `networkx`, `numpy`, `rapidfuzz`, `tree-sitter` + ~28 `tree-sitter-*` grammar wheels (compiled — **OS/arch/Python-version specific**). All resolved automatically by `pip download`. |
| Skill | `~/.claude/skills/graphify/` — `SKILL.md` + `references/` (extraction-spec.md etc.). **(artifact: copy the folder)** |

### Skills (agent instructions)

| Skill | Location | Role |
|---|---|---|
| `obsidian_knowledge_graph_skill` | `~/.claude/skills/obsidian_knowledge_graph_skill/` | The 3-layer model, ingestion loop, safety rules. **(artifact)** |
| `graphify` | `~/.claude/skills/graphify/` | The graph pipeline the agent follows. **(artifact)** |
| `qmd` | inside the qmd plugin (`skills/qmd/`) | Search/retrieval craft. Ships with the plugin. |

### Explicitly NOT needed

- No internet at runtime. No `GEMINI_API_KEY` / `GOOGLE_API_KEY` / any cloud API key.
- No Obsidian community plugins (the Web Clipper is only needed wherever clippings are *captured*).
- No `bun` (qmd builds with plain npm), no `uv` (plain pip works).

---

## Part 3 — Replication runbook for the closed environment

**Scenario:** target network is air-gapped; transfers are one-way (e.g. into a self-managed
Artifactory / local npm / local PyPI that does *not* mirror public registries). You start with
vanilla Obsidian and a folder of raw clippings. Claude Code + local MiniMax 2.7 are assumed
already operational inside.

### Phase A — Stage artifacts on a connected machine

> ⚠ The staging machine **must match the target's OS, CPU architecture, and Python
> minor version** — both qmd (llama.cpp binaries) and graphifyy (tree-sitter grammars)
> ship compiled, platform-specific code.

```bash
# A1. Node.js + Obsidian installers for the target platform → grab from vendor sites.

# A2. qmd — install globally, then capture the entire installed tree (this is the most
#     reliable way to carry npm native postinstall artifacts across an air gap):
npm install -g @tobilu/qmd@2.5.3
tar czf qmd-install-tree.tgz -C "$(npm prefix -g)" .
#     Also keep the plain tarball as a fallback / for the internal registry:
npm pack @tobilu/qmd@2.5.3            # → tobilu-qmd-2.5.3.tgz

# A3. Pre-pull ALL qmd models by exercising every model-backed command once:
mkdir -p /tmp/qmd-smoke && echo "# hello world test note" > /tmp/qmd-smoke/test.md
qmd collection add /tmp/qmd-smoke --name smoke
qmd update && qmd embed
qmd query "hello world test" -n 1     # triggers any reranker/expansion model download
tar czf qmd-models.tgz -C ~/.cache/qmd models

# A4. graphify — download the full wheel set:
python3 -m pip download graphifyy==0.8.37 -d ./graphify-wheels
tar czf graphify-wheels.tgz graphify-wheels

# A5. Skills + plugin folders (from a machine where they exist, e.g. this one):
tar czf skills.tgz -C ~/.claude/skills graphify obsidian_knowledge_graph_skill
tar czf qmd-plugin.tgz -C ~/.claude/plugins/cache/qmd qmd   # includes built dist/
```

**Transfer manifest** (one-way into the closed network):

1. Node.js v26.x installer · Obsidian installer · (Python 3.12 if absent)
2. `qmd-install-tree.tgz` (+ `tobilu-qmd-2.5.3.tgz` fallback → push to internal npm)
3. `qmd-models.tgz` (≥318 MB — contains `hf_ggml-org_embeddinggemma-300M-Q8_0.gguf` + any extras)
4. `graphify-wheels.tgz` (→ optionally push wheels to internal PyPI/Artifactory)
5. `skills.tgz`, `qmd-plugin.tgz`
6. The raw clippings folder

### Phase B — Install inside the closed environment

```bash
# B1. Install Node.js and Obsidian from the transferred installers.

# B2. qmd — unpack the install tree into the npm global prefix:
tar xzf qmd-install-tree.tgz -C "$(npm prefix -g)"
qmd --version                          # expect: qmd 2.5.3
#    (Alternative if using internal registry: npm install -g @tobilu/qmd --registry <internal>)

# B3. qmd models — restore the cache BEFORE first run so nothing tries to download:
mkdir -p ~/.cache/qmd
tar xzf qmd-models.tgz -C ~/.cache/qmd

# B4. graphify — offline wheel install:
tar xzf graphify-wheels.tgz
python3 -m pip install --no-index --find-links ./graphify-wheels graphifyy
#    (add --break-system-packages if pip refuses on a managed environment)
python3 -c "import graphify; print('graphify OK')"

# B5. Skills and plugin:
mkdir -p ~/.claude/skills ~/.claude/plugins/cache/qmd
tar xzf skills.tgz -C ~/.claude/skills
tar xzf qmd-plugin.tgz -C ~/.claude/plugins/cache/qmd
ls ~/.claude/plugins/cache/qmd/qmd/0.1.0/dist/cli/qmd.js   # must exist (prebuilt)

# B6. Confirm Claude Code routes to local MiniMax 2.7 and that NO Gemini key is set
#     (unset GEMINI_API_KEY GOOGLE_API_KEY) — this makes graphify use host-LLM extraction.
```

### Phase C — Create the vault and run the pipeline

```bash
# C1. Vault skeleton — open Obsidian, create a vault, then:
mkdir -p "<Vault>"/{raw,wiki,index,scripts,eval}
cp <clippings>/*.md "<Vault>/raw/"     # raw/ is now FROZEN — never edit these files
cp <source-vault>/CLAUDE.md "<Vault>/"             # schema + grounding rule (loaded every session)
cp <source-vault>/scripts/lint_vault.py "<Vault>/scripts/"
# Optionally seed eval/VAULT_TESTS.md from the source vault, then rewrite its gold
# facts (T1–T3) for the NEW corpus — the structure carries over, the answers do not.
```

**C2. Agent-driven path (recommended).** Start Claude Code in the vault root and prompt:

> *"The vault contains only raw clippings in `raw/`. Follow the obsidian-knowledge-graph
> skill: ingest the clippings, synthesize atomic wiki notes and index maps, build the
> graphify knowledge graph, and register + embed qmd collections so the vault is queryable."*

The agent will execute Steps 1–7 of Part 1 (the skills encode the whole procedure).
MiniMax 2.7 performs the synthesis and the graphify semantic extraction via subagents.

**C3. Manual path (equivalent, for humans or scripting).**

```bash
# Search index:
cd "<Vault>"
qmd collection add ./raw   --name sources
qmd collection add ./wiki  --name concepts
qmd collection add ./index --name indices
# NEVER: qmd collection add ./eval — gold answers must not enter retrieval.
qmd update && qmd embed

# Knowledge graph (the /graphify skill drives these via Claude Code; LLM required
# for extraction + labeling, so the manual path still uses the agent for those parts):
#   detect → extract (subagent) → build/cluster → label → export
# Outputs land in graphify-out/: graph.json, graph.html, GRAPH_REPORT.md

# Wiki + index notes: write them per the templates in Part 1, Steps 3–4.
# Without an LLM these are human-authored — the templates and safety rules still apply.
```

### Phase D — Verify

```bash
python3 scripts/lint_vault.py                  # deterministic structure check — must exit 0
qmd collection list                            # confirm eval/ is NOT among the collections
qmd status                                     # collections present, chunks embedded
qmd search "<term you know is in a clipping>" -n 3        # BM25 path
qmd query $'intent: find the concept note about <X>\nlex: <exact terms>\nvec: <paraphrase>'  # hybrid path
graphify query "<conceptual question spanning two articles>"  # graph traversal path
open graphify-out/graph.html                   # visual sanity check (8-ish communities)
```

For a richer behavioral check, run the `eval/VAULT_TESTS.md` checklist (T0–T4): T1
known-answer recall, T2 negative controls (the vault-grounding rule must make the agent
say "not covered" instead of fabricating), T3 cross-source synthesis.

Acceptance criteria (what "done" looked like in this build):
- every raw clipping byte-identical to its original;
- every wiki note has `sources:` frontmatter pointing at ≥1 raw clipping;
- `index/_map-of-content.md` reaches every wiki note;
- `python3 scripts/lint_vault.py` exits 0; `eval/` is absent from `qmd collection list`;
- both query engines return the correct note/subgraph for a known-answer question.

### Ongoing maintenance (new clippings later)

1. Drop new clippings into `raw/` (never edit existing ones).
2. `qmd update && qmd embed` (incremental).
3. Re-run the agent ingestion prompt — the skill's loop searches qmd **first** to update
   existing wiki notes instead of duplicating, then `/graphify <vault> --update` re-extracts
   only new/changed files (extraction cache makes this cheap).
4. Add the new source to `index/source-registry.md` and add a `wiki/sources/<slug>.md` summary.
5. Append a `## [date] ingest | <title>` line to `index/log.md`.
6. `python3 scripts/lint_vault.py` and fix any findings until it exits 0.

(Steps 4–6 are the `CLAUDE.md` **Ingest** workflow — the single source of truth for the loop.)

---

## 4. Troubleshooting (errors actually hit in this build, with fixes)

| Symptom | Cause | Fix |
|---|---|---|
| `qmd.js` missing — `Error: Cannot find .../dist/cli/qmd.js` | Plugin shipped unbuilt; first build attempt used `bun` which wasn't installed (exit 0 but no output — check for the file, not the exit code) | Build with npm: `npm install && npm run build` in the plugin dir |
| `npm install` → `EEXIST`/`EACCES` on `~/.npm/_cacache` | Corrupted/foreign-owned npm cache | Use an alternate cache: `npm install --cache /tmp/npmcache-qmd` |
| `python3 -m pip install graphifyy` → "externally managed environment" | PEP 668 protected Python | Add `--break-system-packages`, or use a venv |
| `graphify query` warns "skill is from 0.8.36, package is 0.8.37" | Skill/package version skew | Cosmetic — queries work; sync versions when convenient |
| `qmd embed`/`qmd query` tries to download a model offline | `~/.cache/qmd/models/` incomplete | Restore the full models dir from staging (Phase A3) |
| graphify subagent chunk file missing after extraction | Subagent dispatched as read-only `Explore` type | Always dispatch with `subagent_type="general-purpose"` |

---

## 5. Query cheat sheet (day-to-day use)

```bash
# "Where is the note about …" — exact words known:
qmd search "loss masking -100 chat template" -n 5

# Conceptual / fuzzy recall:
qmd query $'intent: find the concept note explaining why 4-bit NF4 matches bf16 quality\nlex: NF4 QLoRA double quantization\nvec: information-theoretically optimal 4-bit datatype for normally distributed weights'

# Read a hit:
qmd get "#<docid>"            # or: qmd get qmd://concepts/lora.md

# "How does X relate to Y" — multi-hop:
graphify query "how does the KV cache connect quantization to serving throughput"
graphify path "LoRA" "PagedAttention"
graphify explain "GRPO"
```

*Generated 2026-06-11 from the build session that produced this vault; revised 2026-06-14
to document the llm-wiki compliance pass (CLAUDE.md schema + grounding rule, log.md,
wiki/sources/ summaries, scripts/lint_vault.py, eval/VAULT_TESTS.md). Versions:
qmd 2.5.3 · graphifyy 0.8.37 · Node v26.2.0 · Python 3.12.13 · embeddinggemma-300M-Q8_0.*
