# Plan: Generic Subdomain Classification Template (Stage 6)

**Date:** 2026-08-15
**Status:** Draft for approval
**Parent specs:** `2026-08-02-client-ingest-pipeline-design.md` (backbone), `2026-08-02-stage4-filtering-design.md`, `2026-08-03-stage5-translation-design.md`
**New spec to author:** `2026-08-15-generic-subdomain-classification-design.md` (Stage 6 generic — deferred section 6 of backbone)
**Context source:** 9k English md docs, ~20 subdomains, high lexical overlap across subdomains + high intra-class variance, first-tokens are best signal, implicit mentions (test without naming condition), comparison/relationship docs, open model MiniMax M2.7 via vLLM, Label Studio HITL, categorical confidence `SURE / NEEDS_HUMAN_VALIDATION / I_GUESSED`.

---

## Context

The client pipeline backbone defines every stage except classification as a deep dive. Stage 6 was explicitly deferred: *"taxonomy/questionnaire final form, classification prompts and rubrics, spot-check sampling math."* A user conversation on a concrete 9k-doc, 20-subdomain corpus surfaced the exact pain points a generic template must solve:

- **Embedding-only fails** when documents share structure/boilerplate and vocabulary across subdomains but look nothing alike within a subdomain — cosine collapses.
- **LLM few-shot with reasoning wins** when given 3-8 diverse examples per subdomain, but a 20-class flat prompt is infeasible (30k tokens/call).
- **20-class scale + long md files** requires top-k retrieval (embeddings as filter, LLM as judge) and first-token-aware chunking (the user's corpus is front-loaded).
- **LLMs are uncalibrated on numeric confidence;** categorical buckets tied to observable evidence type (`SURE / NEEDS_HUMAN_VALIDATION / I_GUESSED`) are enforceable via vLLM `guided_json` enums.
- **Human-in-loop must be sample-efficient:** stratified middle-band + disagreement sampling, keyboard-only review of 150-200 docs, prompt/glossary fixes not per-doc fixes.
- **Two recurring document types** break naive single-label: implicit-reference docs (medical test without naming condition) and cross-subdomain comparison/relationship docs (need primary + secondary + relation_type, not a forced single label).

The goal is a **generic, config-driven template** that ships in the framework repo and can be scaffolded for many campaigns/clients with different taxonomies, glossaries, and md shapes — without forking code per scenario. It must respect the framework's hard constraints: `payload/` is source of truth, `core.py` stays pure stdlib, `manifest.json` owns drift, `example_vault/` is an artifact, `vault check` stays fail-closed, ledger is append-only, store is content-addressed.

---

## Goals

- One `Stage 6 — Generic Classification` spec + plan that closes the deferred backbone section.
- A payload-shipped template (`payload/templates/classification/`) + a runnable offline pipeline (`scripts/classify/`) that any vault can scaffold from and per-campaign customize via YAML (no code change).
- Support variable N subdomains (5-50), variable doc length, first-token vs full-doc vs header-aware chunking selectable by config.
- Top-k pipeline: deterministic embedding filter → closed-choice LLM judge (MiniMax M2.7 / any OpenAI-compatible via vLLM) → categorical confidence → Label Studio review → ledger.
- Handle both pain points generically: glossary-backed implicit resolution and primary/secondary/relation_type for cross-subdomain docs.
- Minimal human time: stratified sampling, disagreement sampling, keyboard Label Studio, per-bucket calibration.

## Non-goals

- Translation (Stage 5) or filtering (Stage 4) — consumes their outputs, does not redo them.
- Security/prompt-injection screening (client decision 2026-08-02: trusted corpus, no screening).
- GPU model hosting itself — vLLM/MiniMax is assumed reachable via `QMD_OPENAI_BASE_URL` / `CLASSIFY_LLM_BASE_URL` style env, same seam as `qmd-api`.
- A new vault three-layer — reuses `raw/`, `wiki/`, ledger, store; Stage 6 only writes frontmatter/ledger/review artifacts.

---

## Architecture

### Alignment with existing pipeline

```
Phase 0 calibration → Phase 1 filtering/coarse routing → Stage 5 translation (English text + glossary)
         ↓
   Stage 6 (this plan): taxonomy freeze → classify (embed+LLM) → review queue → ledger + frontmatter
         ↓
   Stage 7 curriculum ingest (order by level/trust, collision rule)
```

Stage 6 consumes English md from the content-addressed store (`store/ab/...`), the per-campaign glossary (`campaigns/<campaign>/glossary.md`), and the frozen taxonomy (`campaigns/<campaign>/taxonomy.yaml`). It writes classification decisions to the ledger and to derived frontmatter on store copies (`domains:`, `doc_type:`, `trust:`, `level:`, `doc_decision`/`decided_by`).

### Config-driven template (the generic lever)

All per-scenario variance lives in YAML, not code:

| Config | Purpose | Example values |
|--------|---------|----------------|
| `taxonomy.yaml` | Frozen closed vocabulary: domains, subdomains (N), per-subdomain 2-3 line definition + include/exclude + 3-8 diverse examples | `subdomains: [diabetes_monitoring: {definition, examples, glossary_keys}]` |
| `glossary.yaml` | Implicit-resolution map: surface form → subdomain (e.g., `HbA1c → diabetes_monitoring`), reused from Stage 5 glossary | `terms: {HbA1c: diabetes_monitoring}` |
| `policy.yaml` | Pipeline policy: chunking mode, top_k, confidence rubric, relation policy | `chunk: {mode: first_window, window: 1500}, retrieval: {top_k: 4}, confidence: {buckets: [SURE, NEEDS_HUMAN_VALIDATION, I_GUESSED], rubric_anchors}, relation: {mode: primary_plus_secondary, allowed: [none, comparison, relationship, progression]}` |
| `questionnaire.md` | Per-campaign intake that *produces* the three YAMLs above | Checklists for domain enumeration, overlap ownership, implicit-term harvesting, comparison-doc policy |

A new scenario is: `cp -r payload/templates/classification campaigns/<campaign>/ && fill questionnaire → freeze taxonomy → run`.

### Pipeline inside `scripts/classify/`

```
md doc ──► chunk (first_window | header_aware | full) ──► embed once (OpenAI-compatible /v1/embeddings)
                                                        │
                                                        └─► top-k retrieval (k from policy, default 4) against per-subdomain centroid/index
                                                                    │
                                           taxonomy+glossary+examples for top-k only ──► vLLM judge (MiniMax M2.7)
                                                                    │
                                                                    ▼
                                              JSON {reasoning_brief, primary, secondary[], relation_type, confidence_bucket}
                                              with reasoning_brief FIRST, no length limit, temp 0, guided_json enum enforcement
                                                                    │
                                                                    ▼
                                              Label Studio export + review queue (stratified middle-band)
                                                                    │
                                                                    ▼
                                              calibration report (per-bucket accuracy) → glossary/taxonomy patch → re-run
                                                                    │
                                                                    ▼
                                              ledger JSONL + frontmatter patches (atomic writes, temp→rename)
```

Key decisions:
- **Chunking:** default `first_window` (frontmatter + title + first ~1500 tokens + header outline) because the user's corpus is front-loaded; `header_aware` for heading-dense docs; `full` (or sliding) as escape hatch. Each chunk writes a content-addressed md with frontmatter `source_doc_id, source_hash, chunk_policy_version`.
- **Embedding as retriever, not decider:** per-subdomain centroid from few-shot examples; top-k recall target 95%+; LLM does disambiguation.
- **Reasoning-first JSON:** `reasoning_brief` first key, no length limit, instructs "think step by step BEFORE choosing" — forces evidence mapping for implicit tests and comparison detection.
- **Categorical confidence via constrained decoding:** vLLM `GuidedDecodingParams(json=schema)` with `confidence_bucket` enum; sampler makes it impossible to emit numeric scores.
- **Relation handling (generic):** policy selects `primary+secondary+relation_type` (recommended) vs `single+extra_comparison_label`; schema enforces allowed values; comparison docs never forced into a single subdomain.
- **Glossary-in-context:** resolved `HbA1c → diabetes_monitoring` injected above examples, not as separate examples — keeps implicit docs solvable without bloating the prompt.

### Payload vs code split (framework constraint)

- **Payload (shipped to vaults, manifest-owned):**
  - `payload/templates/classification/taxonomy.yaml` (example, 5 subdomain toy to pass lint, real campaigns override)
  - `payload/templates/classification/glossary.yaml`
  - `payload/templates/classification/policy.yaml`
  - `payload/templates/classification/questionnaire.md` (the intake that freezes taxonomy)
  - `payload/templates/classification/label_studio/view.xml` (generic view with `{{N}}` subdomain choices, md HyperText, confidence-colored box)
  - `payload/dot-claude/skills/vault-classify/SKILL.md` (thin skill: `classify → review → calibrate`)

- **Code (repo-level scripts, not payload-owned):**
  - `scripts/classify/chunk.py` — frontmatter preservation, three chunk modes, content-addressed writes
  - `scripts/classify/retrieve.py` — embedding + centroid top-k
  - `scripts/classify/judge.py` — vLLM/OpenAI-compat call with guided_json, reasoning-first prompt builder
  - `scripts/classify/export_label_studio.py` — JSON tasks + view.xml rendering
  - `scripts/classify/calibrate.py` — per-bucket accuracy, confusion matrix, glossary/taxonomy patch suggestions
  - `scripts/classify/ledger.py` — append-only JSONL projection helpers (reuse backbone ledger conventions)

- **Core (stdlib-only):**
  - `core.py:cmd_classify` validator — closed-vocabulary check against `taxonomy.yaml`, frontmatter write, fail-closed if `primary ∉ taxonomy`; no LLM call inside core.
  - `manifest.json` add owned paths; `CLAUDE.md` USER ZONE guidance for per-vault taxonomy override if needed.

---

## Critical files to create / modify

**Docs:**
- `docs/superpowers/specs/2026-08-15-generic-subdomain-classification-design.md` — new Stage 6 generic spec (follows Stage 4/5 template: Purpose, Constraints, Module layout, Config contracts, Chunking, Retrieval, Judge prompt + schema, Label Studio contract, Ledger, Testing, Success criteria)
- `docs/superpowers/plans/2026-08-15-generic-subdomain-classification.md` — TDD plan (this file's companion)
- `mkdocs.yml` — register both in `nav`

**Payload (new owned paths):**
- `src/second_brain_vault_framework/payload/templates/classification/taxonomy.yaml`
- `src/second_brain_vault_framework/payload/templates/classification/glossary.yaml`
- `src/second_brain_vault_framework/payload/templates/classification/policy.yaml`
- `src/second_brain_vault_framework/payload/templates/classification/questionnaire.md`
- `src/second_brain_vault_framework/payload/templates/classification/label_studio/view.xml`
- `src/second_brain_vault_framework/payload/dot-claude/skills/vault-classify/SKILL.md`
- `src/second_brain_vault_framework/manifest.json` — add the 6 new owned_paths

**Scripts (new, offline-capable):**
- `scripts/classify/chunk.py`
- `scripts/classify/retrieve.py`
- `scripts/classify/judge.py`
- `scripts/classify/export_label_studio.py`
- `scripts/classify/calibrate.py`
- `scripts/classify/ledger.py`

**Core (stdlib):**
- `src/second_brain_vault_framework/core.py` — add `cmd_classify` + wiring in `cli.py` (argparse only)
- `tests/test_classify_*.py` — taxonomy sync, closed-vocabulary, chunk modes, guided_json schema, Label Studio render, ledger projection

**Example vault (artifact, not edited directly):**
- `vault upgrade example_vault` after payload changes — verifies CI `vault check` still passes and showcase taxonomy appears.

---

## Implementation tasks (TDD per file)

### Task 1 — Spec authoring
- [ ] Draft `2026-08-15-generic-subdomain-classification-design.md` mirroring Stage 4/5 structure; define taxonomy/glossary/policy JSON schemas, chunk modes, retrieval spec, judge prompt (reasoning-first, no length limit, temp 0), confidence enum rubric, relation policy options, Label Studio task schema, ledger event shape, success criteria.
- Verification: `mkdocs build` passes, spec review vs backbone alignment checklist.

### Task 2 — Payload templates (closed-vocabulary scaffolding)
- [ ] Write `taxonomy.yaml` toy (5 subdomains, definitions + include/exclude + 2 examples each, diverse coverage), `glossary.yaml` toy (5 implicit mappings), `policy.yaml` (first_window 1500, top_k 4, three buckets, primary+secondary mode), `questionnaire.md` (domain enumeration, implicit harvesting, comparison policy, example diversity checklist).
- [ ] Tests: `test_classify_taxonomy.py` — taxonomy sync test (taxonomy subdomains == allowed enum in judge schema), glossary key uniqueness, policy enum validity, questionnaire→YAML field coverage.
- Commit: `feat(classification): payload templates + taxonomy sync test`.

### Task 3 — Chunking (first-token priority)
- [ ] `scripts/classify/chunk.py`: frontmatter parse (`core.parse_frontmatter` reuse), `first_window` (frontmatter+title+first N tokens+header outline), `header_aware`, content-addressed write `store/ab/abcdef...md` with frontmatter `source_doc_id, source_hash, chunk_policy_version, window`.
- [ ] Tests: fixture md files (short, long 8k, frontmatter-heavy, header-dense) — assert window token count, header preservation, frontmatter integrity, atomic write (temp→rename).
- Commit: `feat(classify): chunker with first-token priority`.

### Task 4 — Retrieval (embedding top-k filter)
- [ ] `scripts/classify/retrieve.py`: centroid builder from taxonomy examples, `/v1/embeddings` batch client (reuse `qmd-api` env seam `CLASSIFY_EMBED_*` / `QMD_OPENAI_*`), top-k with recall logging.
- [ ] Tests: stub embedding server, toy taxonomy 5 classes, long-tail fixture — assert top-k recall ≥ threshold, k clamping 1-10, empty-embedding fail-closed.
- Commit: `feat(classify): top-k retriever`.

### Task 5 — Judge (vLLM reasoning-first, guided JSON)
- [ ] `scripts/classify/judge.py`: prompt builder (system: role+glossary+top-k definitions+their examples; user: chunk text+headers), JSON schema with `reasoning_brief` first (no length cap), `confidence_bucket` enum, `relation_type` enum, `primary` enum from taxonomy, temp 0, guided decoding; few-shot anchors for each bucket (SURE / NEEDS_HUMAN_VALIDATION / I_GUESSED) including implicit and comparison examples.
- [ ] Tests: schema validation, ordering (reasoning_brief first), enum enforcement (numeric 0.73 rejected), implicit glossary mapping, comparison primary+secondary.
- Commit: `feat(classify): reasoning-first judge with categorical confidence`.

### Task 6 — Label Studio export
- [ ] `scripts/classify/export_label_studio.py` + `payload/templates/classification/label_studio/view.xml`: HyperText md preview, confidence-colored box, Choices for primary (N rendered from taxonomy), secondary multi-choice, relation, TextArea for glossary flag; JSON task export with `text_html, reasoning_brief, candidates, confidence_bucket`.
- [ ] Tests: view renders for N=5 and N=20, single vs multi choice, HTML md rendering, JSON task shape.
- Commit: `feat(classify): Label Studio export`.

### Task 7 — Calibration + ledger
- [ ] `scripts/classify/calibrate.py`: per-bucket accuracy, confusion matrix, glossary-miss report (implicit docs that should have mapped), suggestion patch for taxonomy/glossary.
- [ ] `scripts/classify/ledger.py`: append-only JSONL `doc_id, stage, status, primary, confidence_bucket, method, glossary_version, taxonomy_version, timestamp`; projection script for current state.
- [ ] Tests: calibration math on fixture judgments, ledger append/projection, re-run idempotency.
- Commit: `feat(classify): calibration + ledger`.

### Task 8 — Core validator + CLI + manifest
- [ ] `src/second_brain_vault_framework/core.py:cmd_classify` — closed-vocabulary validator (primary/secondary ∈ taxonomy), frontmatter patch writer, ledger append; strict failure on drift.
- [ ] `src/second_brain_vault_framework/cli.py` — add `classify` subcommand (argparse only, dispatch to core).
- [ ] `src/second_brain_vault_framework/manifest.json` — add 6 payload owned_paths; `src/second_brain_vault_framework/payload/dot-claude/skills/vault-classify/SKILL.md`.
- [ ] Tests: `test_classify_cli.py` — scaffold→classify→check happy path, unknown subdomain rejected, manifest drift backup, `vault upgrade example_vault` still passes `vault check`.
- Commit: `feat(classify): core validator + manifest + skill`.

### Task 9 — Example vault + docs wiring
- [ ] `vault upgrade example_vault`, `mkdocs.yml` nav, `instructions.md` addendum (Stage 6 quick-start: `questionnaire → taxonomy freeze → classify → review`).
- Verification: `python -m unittest discover -s tests` green, `vault check example_vault` exit 0, `qmd update && qmd embed` on example vault still clean, Label Studio import of generated JSON manual smoke.

---

## Verification

```bash
python -m unittest discover -s tests                          # all new + existing tests green
vault check example_vault                                     # fail-closed lint
vault upgrade example_vault && git diff --stat                # payload laid down, backup if drifted
python scripts/classify/chunk.py --mode first_window --window 1500 fixtures/sample.md  # chunk fixture
python scripts/classify/judge.py --dry-run --taxonomy campaigns/demo/taxonomy.yaml  # schema + prompt preview
# Full offline smoke: 100-doc fixture campaign end-to-end (chunk→retrieve→judge→export→calibrate) with stub embed/LLM servers
```

**Success criteria (pilot):** Same campaign run with N=5 toy taxonomy completes end-to-end inside the gap with only stdlib core + stubbed OpenAI-compat endpoints; taxonomy change without code change works by swapping YAML; Label Studio import succeeds and per-bucket calibration report is producible; ledger answers "what decided doc X and why" for every doc; a re-run after taxonomy patch is atomic and reverts via ledger projection alone.

---

## Open inputs (confirm before implementation)

- **First-window size:** default 1500 tokens OK, or should policy default be 1200 for denser front-loaded corpora?
- **Relation policy default:** ship `primary_plus_secondary` as default (recommended above) or simpler `single_plus_comparison_label` for the smallest campaigns?
- **Embedding store:** reuse `.qmd` embeddings or keep classify's centroid index separate?

