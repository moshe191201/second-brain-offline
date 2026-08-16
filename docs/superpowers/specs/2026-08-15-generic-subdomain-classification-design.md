# Stage 6 — Generic Subdomain Classification (Design)

**Date:** 2026-08-15
**Status:** Proposed
**Parent:** `2026-08-02-client-ingest-pipeline-design.md` (backbone approved)
**Scope:** Per-campaign subdomain classification that runs on English md after Stage 5 translation, before Stage 7 curriculum ingest. Closes the deferred backbone item: taxonomy/questionnaire final form, classification prompts and rubrics, spot-check sampling math. Template must be generic across campaigns with different N subdomains, doc shapes, and domain vocabularies without forking code.

## Purpose

Assign every campaign document that survived filtering and translation to its subdomain(s) from a frozen closed vocabulary, handling two recurring hard types — implicit-reference docs (test/procedure mentioned without naming the subdomain) and cross-subdomain comparison/relationship docs — while keeping human time to a stratified sample. Every decision is recorded with its evidence so the classifier can be analyzed, calibrated, and re-run.

## Non-goals

- **No translation.** Consumes Stage 5 English md + glossary; does not re-translate.
- **No corpus-wide filtering.** Stage 4 gates already ran. Stage 6 never rejects for "belongs at all" — only classifies survivors.
- **No security screening** (parent spec, client decision: trusted corpus).
- **No model hosting.** MiniMax M2.7 (or any OpenAI-compatible) is assumed reachable via `CLASSIFY_LLM_BASE_URL` / `QMD_OPENAI_*` env, same seam as `qmd-api`. Scripts call it; they do not run it.
- **No new vault three-layer.** Reuses `raw/`→`raw_md/`→store, `wiki/`, ledger, `.qmd`.

## Decision model

Three categorical buckets, not numeric scores. Buckets are defined by **observable evidence type**, enforced via vLLM `guided_json` enum — a document cannot receive a numeric confidence.

| Bucket | When the judge emits it | Human effect |
|--------|-------------------------|--------------|
| `SURE` | Subdomain name or glossary-mapped surface form appears explicitly and is the primary focus; no second subdomain as comparator | Auto-accept; spot-check audit sample |
| `NEEDS_HUMAN_VALIDATION` | Implicit reference (term requires glossary mapping), or doc compares/relates 2+ subdomains, or top-2 candidates within threshold | Review queue (stratified) |
| `I_GUESSED` | Evidence thin/generic/contradictory; least-bad pick among candidates | Quarantine; never auto-accept; taxonomy/glossary fix signal |

Cross-subdomain docs are never forced into a single label. Policy `primary_plus_secondary` (default) emits:

```json
{
  "reasoning_brief": "2-3 sentences, evidence → subdomain mapping",
  "primary_subdomain": "diabetes_monitoring",
  "secondary_subdomains": ["nephrology"],
  "relation_type": "comparison",
  "confidence_bucket": "NEEDS_HUMAN_VALIDATION"
}
```

`relation_type ∈ {none, comparison, relationship, progression}`. Alternative policy `single_plus_comparison_label` (add 21st label) is supported per-campaign but not default.

Autonomy per task is set by Phase 0 calibration: agreement on a stratified gold sample (~100 docs) between expert and MiniMax sets whether `SURE` auto-accepts and how large the spot-check audit sample is. Re-run calibration when taxonomy, glossary, or model changes.

## Order of operations (per campaign)

1. **Questionnaire → taxonomy freeze.** Expert fills `questionnaire.md`; taxonomy, glossary, and policy YAMLs freeze. Freeze is hashed into ledger; change invalidates downstream decisions.
2. **Chunk.** Per `policy.chunk`: `first_window` (default, frontmatter+title+first ~1500 tokens+header outline) for front-loaded corpora, `header_aware`, or `full`. Never mid-sentence/table/code. Writes content-addressed md `store/ab/abcdef….md` with frontmatter `source_doc_id, source_hash, chunk_policy_version`.
3. **Embed once.** Batch `/v1/embeddings` (reuse `qmd-api` seam). Each doc chunk embedded; per-subdomain centroid built from taxonomy examples.
4. **Top-k retrieval.** `policy.retrieval.top_k` (default 4) cosine candidates against centroids. Logs recall per doc. Candidates are the only subdomains shown to the judge — caps prompt from 20-class flat to 4-class.
5. **Judge.** MiniMax closed-choice on glossary + top-k definitions + their diverse examples + chunk text + headers. `reasoning_brief` **first** (`think step by step BEFORE choosing`, no length limit), then `primary/secondary/relation/confidence_bucket`. Temp 0, `guided_json` schema enforces enums and ordering.
6. **Label Studio export.** JSON tasks + rendered `view.xml` (HyperText md preview, confidence-colored box, reasoning_brief, candidates, Choices for N subdomains). Review queue is stratified middle-band + disagreement sampling (see Human review).
7. **Calibration.** Per-bucket accuracy, confusion matrix, glossary-miss report vs ledger; suggests glossary/taxonomy patches. Patch → version bump → re-run exactly affected docs (ledger query).
8. **Ledger + frontmatter patch.** Append-only JSONL events; derived frontmatter `domains:`, `doc_type:`, `trust:`, `level:`, `doc_decision`/`decided_by` on store copies (atomic temp→rename → ledger). Current state is a projection over the log.

## Config contracts (generic lever)

All per-scenario variance lives in YAML under `campaigns/<campaign>/` (scaffolded from `payload/templates/classification/`). No code change per campaign.

### `taxonomy.yaml`

```yaml
version: 1
subdomains:
  diabetes_monitoring:
    definition: "Docs whose primary purpose is tracking diabetes control (HbA1c, glucose trends, monitoring protocols)."
    include: ["monitoring protocols", "HbA1c trending"]
    exclude: ["general endocrinology without monitoring focus"]
    glossary_keys: [HbA1c, glucose]
    examples:
      - {text: "Quarterly HbA1c follow-up...", source: "doc_0341.md", covers: "short protocol"}
      - {text: "Long-form diabetes monitoring essay with no keywords...", source: "doc_0891.md", covers: "lexically thin"}
  # ... N entries (5-50)
```

Constraints: `N` between 5 and 50; each subdomain 1-4 examples, each must cover distinct variance (short/long, lexically thin/rich, edge near neighbor); `definition` ≤ 3 lines; examples are diverse by instruction, not near-duplicates.

### `glossary.yaml`

```yaml
version: 1
terms:
  HbA1c: {maps_to: diabetes_monitoring, notes: "long-term glucose", source: "campaign glossary v1"}
  PSA: {maps_to: prostate_screening}
```

Reused from Stage 5 glossary; one row per surface form → subdomain. Injected as `domain_knowledge` header above examples, not as extra examples.

### `policy.yaml`

```yaml
version: 1
chunk: {mode: first_window, window: 1500}   # first_window | header_aware | full
retrieval: {top_k: 4, embed_model: "embeddinggemma-300M"}  # top_k 1-10 clamped
judge: {model: "minimax-m2.7", temperature: 0.0, few_shot_per_topk: 3}
confidence:
  buckets: [SURE, NEEDS_HUMAN_VALIDATION, I_GUESSED]
  rubric_anchors:
    SURE: "explicit + primary focus, no comparator"
    NEEDS_HUMAN_VALIDATION: "implicit or comparison or close runner-up"
    I_GUESSED: "thin/generic evidence"
relation: {mode: primary_plus_secondary, allowed: [none, comparison, relationship, progression]}
review: {stratified_per_subdomain: 8, disagreement_band: 0.10, spot_check_sure: 20}
```

All thresholds live in one dict; per-campaign overrides allowed; each override documented in the questionnaire.

### `questionnaire.md`

Step-by-step intake that *produces* the three YAMLs: domain/subdomain enumeration, source→domain mapping, overlap ownership, implicit-term harvesting (list 30-50 surface forms), comparison-doc policy choice, example diversity checklist, first-window validation (expert confirms front-loaded signal for this campaign). Freeze checklist at the end gates classification.

## Module layout

```
payload/templates/classification/
  taxonomy.yaml            # toy 5-subdomain example (passes lint)
  glossary.yaml            # toy 5 mappings
  policy.yaml              # first_window 1500, top_k 4, 3 buckets, primary+secondary
  questionnaire.md
  label_studio/view.xml    # generic, renders N Choices from taxonomy

scripts/classify/
  chunk.py                 # three chunk modes, content-addressed writes
  retrieve.py              # centroid builder + /v1/embeddings batch + top-k
  judge.py                 # prompt builder + guided_json schema + vLLM call
  export_label_studio.py   # JSON tasks + view.xml rendering
  calibrate.py             # per-bucket accuracy, confusion matrix, patch suggestions
  ledger.py                # append-only JSONL helpers, projection

payload/dot-claude/skills/vault-classify/SKILL.md
```

`core.py:cmd_classify` stays pure stdlib: closed-vocabulary validator (`primary/secondary ∈ taxonomy`), frontmatter patch, ledger append, fail-closed on violation. No LLM call inside core. `cli.py` adds `classify` dispatch (argparse only). `manifest.json` lists the 6 new owned paths.

## Prompt contract (judge)

System: role + glossary `domain_knowledge` + top-k subdomain definitions (only those k, not all N) + their diverse examples + bucket rubric with anchored SURE/NEEDS_HUMAN_VALIDATION/I_GUESSED examples (implicit + comparison included).

User: chunk text + header outline + frontmatter title.

Output: JSON with keys in order `reasoning_brief, primary_subdomain, secondary_subdomains, relation_type, confidence_bucket`. `reasoning_brief` first enforces think-before-commit; no length cap — thorough reasoning allowed.

Sampling: `temperature: 0.0`, `guided_decoding: {json: schema}` — sampler makes numeric scores impossible; unparseable output treated as `I_GUESSED` + queued.

Few-shot: one canonical example per bucket embedded in policy, each demonstrating implicit mapping or comparison handling.

## Label Studio contract

View: `<HyperText>` for md preview (rendered HTML), confidence-colored box (`SURE` green, `NEEDS_HUMAN_VALIDATION` yellow, `I_GUESSED` red), reasoning_brief, candidates, `<Choices>` for primary (N from taxonomy, single), secondary (multi), relation (single), `<TextArea>` for glossary flag.

Tasks: one JSON task per doc: `{text_html, filename, llm_primary, llm_secondary, relation_type, confidence_bucket, candidates, reasoning_brief}`. Import is offline file import, no server auth needed for the template.

## Ledger & storage

- **Store:** content-addressed `store/ab/abcdef….md` for chunked copies and frontmatter-patched derivatives; `raw/` and `raw_md/` remain immutable. Atomic writes (temp→rename) → only then ledger update.
- **Events (append-only JSONL):** `taxonomy_frozen`, `glossary_version`, `chunk_written`, `embed_batch`, `retrieval_topk`, `judge_completed` (with model id, glossary/taxonomy versions, top-k, reasoning_brief, confidence_bucket), `review_decision` (`decided_by: human`, with `doc_id, primary, confidence_bucket`), `frontmatter_patched`, `reclassification_scheduled` with cause.
- **Projection:** current state for any doc is ledger projection; glossary/taxonomy version change re-runs exactly affected docs (ledger query: "which docs used glossary v3?").

## Human review (sample-efficient)

- Queue = stratified sample of `NEEDS_HUMAN_VALIDATION` (~8 per subdomain) + docs where top-2 were within `disagreement_band` (default 0.10 semantics: close candidates or `I_GUESSED`) + `I_GUESSED` all. Typical queue 150-200 docs per batch (~30-40 min, keyboard `1` = agree, `2-0` = override, no mouse).
- Batches ordered by campaign priority, then by bucket uncertainty — least-confident first, since they teach the most about rubric weakness.
- Audit sample: ~20 `SURE` docs sampled per batch into queue, marked audit; auto-accept calibration target is >90% correct on audit or `SURE` rubric tightens.
- Disposition per queued doc: accept, override primary/secondary/relation, or flag `glossary`/`taxonomy` patch. Patch → version bump → re-run affected slice.

## Calibration (Phase 0 + per-batch)

Phase 0 gold sample (~100 docs) stratified across subdomains + the two hard types (implicit, comparison). Judge runs on gold; agreement sets `SURE` trust and spot-check size. Per-batch calibration emits: per-bucket accuracy, confusion matrix (pairwise A↔B errors), glossary-miss rate (implicit docs where true term not in glossary), suggestion patch ("add HbA1c→diabetes_monitoring", "tighten definition of B"). `I_GUESSED` correct <40% is a healthy signal — those are genuinely hard docs.

## Testing

- **Taxonomy sync:** taxonomy subdomains == judge schema enum; glossary keys unique; policy enums valid; questionnaire→YAML field coverage. Fails build on drift.
- **Chunk fixtures:** short, long 8k front-loaded, header-dense, frontmatter-heavy — assert window token count, header preservation, frontmatter integrity, atomic write.
- **Retrieval stubs:** stub `/v1/embeddings` server, toy 5-class taxonomy — top-k recall, clamping 1-10, fail-closed on empty embeddings.
- **Judge stubs:** schema ordering (reasoning_brief first), enum enforcement (numeric 0.73 rejected), implicit mapping, comparison primary+secondary.
- **Label Studio:** view renders for N=5 and N=20, JSON task shape, HTML md rendering.
- **Ledger:** append/projection idempotency, re-run after version bump affects exactly correct docs.
- **Gold regression:** standing gold sample vs judge — per-bucket accuracy floor, false-SURE ceiling, fail build on breach.
- **Determinism:** same chunk policy + taxonomy version + glossary version + model id → same ledger projection.

## Success criteria (pilot)

- Same campaign with toy N=5 taxonomy completes chunk→retrieve→judge→export→calibrate end-to-end inside the gap with only stubbed OpenAI-compat endpoints; taxonomy change without code change works by swapping YAML.
- Label Studio import succeeds and per-bucket calibration report is producible.
- Ledger answers "what decided doc X, with which glossary/taxonomy/model, and why (reasoning_brief)" for every doc.
- Re-run after taxonomy/glossary patch re-processes exactly affected docs, atomically.
- `vault check example_vault` still passes; `vault upgrade example_vault` layers new templates with drift backup.

## Open inputs

- First-window default: 1500 (proposed) vs 1200 for denser front-loaded corpora — policy makes it per-campaign adjustable, spec ships 1500.
- Relation default: `primary_plus_secondary` (proposed) vs `single_plus_comparison_label` — spec ships primary_plus_secondary.
- Embedding index: reuse `.qmd` vs separate centroid index — proposed separate per-campaign centroid index for isolation; QMD remains retrieval for vault query.
