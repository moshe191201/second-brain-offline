---
name: vault-classify
description: Classify md docs into subdomains — closed-choice LLM judge with glossary, top-k retrieval, and Label Studio HITL.
---

# vault-classify

Generic subdomain classification (Stage 6) for any campaign. Deterministic scripts do the work; the LLM only makes closed-choice picks against your frozen taxonomy.

## When to use

- After `vault ingest` / translation for a campaign, before curriculum ingest.
- When `campaigns/<campaign>/taxonomy.yaml` is frozen (questionnaire complete).
- To re-classify after a glossary/taxonomy patch.

## Workflow

1. **Scaffold (once per campaign):**
   ```bash
   cp -r payload/templates/classification campaigns/<campaign>/
   # fill campaigns/<campaign>/questionnaire.md → freeze taxonomy.yaml + glossary.yaml + policy.yaml
   ```

2. **Chunk (first-token priority, default 1500):**
   ```bash
   python scripts/classify/chunk.py --campaign campaigns/<campaign> --store store/
   ```

3. **Retrieve (top-k filter):**
   ```bash
   python scripts/classify/retrieve.py --campaign campaigns/<campaign> --store store/
   ```

4. **Judge (reasoning-first, guided JSON):**
   ```bash
   python scripts/classify/judge.py --campaign campaigns/<campaign> --store store/
   # emits {reasoning_brief, primary, secondary[], relation_type, confidence_bucket}
   # with SURE / NEEDS_HUMAN_VALIDATION / I_GUESSED enforced via vLLM guided_json
   ```

5. **Export for human review:**
   ```bash
   python scripts/classify/export_label_studio.py --campaign campaigns/<campaign>
   # import tasks JSON into Label Studio with payload/templates/classification/label_studio/view.xml
   # review 150-200 docs (stratified NEEDS_HUMAN_VALIDATION + I_GUESSED + SURE audit)
   ```

6. **Calibrate & patch:**
   ```bash
   python scripts/classify/calibrate.py --campaign campaigns/<campaign>
   # per-bucket accuracy, confusion matrix, glossary-miss report
   # patch glossary/taxonomy → bump version → re-run judge on affected docs only (ledger query)
   ```

7. **Ledger + frontmatter (stdlib):**
   ```bash
   python scripts/classify/validate.py <vault_root> --campaign campaigns/<campaign> --store store/
   # closed-vocabulary validator: rejects primary ∉ taxonomy, patches frontmatter ledger atomically
   vault check
   ```

## Env

- Embeddings: `QMD_OPENAI_BASE_URL` / `CLASSIFY_EMBED_BASE_URL` + `QMD_OPENAI_API_KEY`
- Judge LLM: `CLASSIFY_LLM_BASE_URL` (or `QMD_OPENAI_BASE_URL`) — MiniMax M2.7 via vLLM OpenAI-compat

## Constraints

- `core.py:cmd_classify` stays pure stdlib — no LLM call inside core. Scripts call the model.
- `taxonomy.yaml` is closed vocabulary. `primary ∉ taxonomy` fails closed with no patch written.
- Every decision is ledgered with `taxonomy_version, glossary_version, policy_version, model_id, top_k, reasoning_brief`.

## Failure modes to watch

- Numeric confidence like `0.73` — must never appear; `confidence_bucket` enum is sampler-enforced.
- Implicit docs that should map via glossary but don't — calibrate reports glossary-miss rate; patch glossary.
- 20-class prompt bloat — judge shows only top-k candidates (default 4), not all N.
