# Vault Improvements & Evaluation Plan — Design

**Date:** 2026-06-11
**Status:** Approved (Approach A: improve first, then test)
**Context:** This vault implements Karpathy's llm-wiki pattern (raw/ → wiki/ → index/,
with qmd search and a graphify knowledge graph). An assessment against the
[llm-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
found five gaps. This design closes all five and defines a manual test plan that
verifies the whole system works.

## Goals

1. Full structural compliance with Karpathy's llm-wiki spec (schema layer, log,
   write-back loop, per-source summaries, lint).
2. A repeatable, manual test checklist that answers: *can a cold agent answer
   questions from this vault accurately, with provenance, without fabricating?*

## Non-goals

- No automated test harness (manual checklist only — user decision).
- No re-architecture of existing layers; raw/, wiki/, index/ conventions stand.
- The knowledge graph remains built from `raw/` only. The wiki is an LLM-authored
  derivative of the same sources; re-extracting it would duplicate nodes.
- No baseline/before-after eval runs; deterministic lint runs before and after
  implementation, the manual checklist runs once against the finished state.

---

## Part A — Improvements

### A1. `CLAUDE.md` (vault root) — the schema layer

The missing third layer of Karpathy's architecture. A compact document (~100 lines,
hard cap 150 — it loads into every agent session's context) containing:

- **Layers & safety rules:** raw/ immutable; wiki/ atomic + linked + provenanced;
  index/ navigation. Never invent provenance; update notes instead of duplicating.
- **Note conventions:** kebab-case filenames; frontmatter template
  (`title`, `type: concept|source-summary|analysis|index`, `tags`, `sources:` as
  wikilinks); wikilinks over URLs; one concept per note.
- **Workflow — Ingest:** read new clipping in `raw/` → qmd-search for existing
  related notes → write `wiki/sources/<slug>.md` summary → create/update concept
  notes → update `index/_map-of-content.md` + `index/source-registry.md` → append
  to `index/log.md` → `qmd update && qmd embed` → `graphify <vault>/raw --update`.
- **Workflow — Query:** qmd first (search → query → get), graphify for multi-hop;
  write-back rule (A3).
- **Workflow — Lint:** run `scripts/lint_vault.py`; LLM-level pass for
  contradictions between notes and stale claims; fix findings.
- Pointer to `instructions.md` for full replication runbook; note that `eval/`
  is never registered as a qmd collection.

### A2. `index/log.md` — append-only ingest journal

Karpathy's grep-able format, one H2 per event:

```
## [YYYY-MM-DD] <operation> | <title>
<one or two lines of detail>
```

Operations: `ingest`, `build`, `lint`, `analysis`. Backfill: eight `ingest`
entries (one per clipping) plus one `build` entry, all dated 2026-06-11 — the
actual build date per git history; no invented dates. The Ingest workflow (A1)
appends here on every future ingest.

### A3. Query→write-back convention

A rule in CLAUDE.md, not a mechanism: when answering a question produces novel
cross-source synthesis (an insight not already in any single note), save it as a
flat `wiki/` note with `type: analysis` frontmatter whose `sources:` lists the
wiki notes it drew from, link it from an "Analyses" section in
`index/_map-of-content.md`, and append an `analysis` entry to `log.md`.
Routine lookups are NOT written back — only novel synthesis.

### A4. Per-source summary pages

Eight notes in `wiki/sources/`, one per raw clipping, filename = kebab-case slug
of the article title. Template:

```markdown
---
title: "Summary — <Article Title>"
type: source-summary
sources:
  - "[[<exact raw clipping filename>]]"
published: <date from clipping frontmatter>
---

# Summary — <Article Title>

<~200 words: what this article argues, in its own arc.>

## Key claims
- <claim> → [[derived-concept-note]]
- ...

## Derived concept notes
[[note-a]] · [[note-b]]
```

`index/source-registry.md` gains a "Summary" column linking each page. qmd's
`concepts` collection (`./wiki`) indexes subdirectories recursively, so summaries
become searchable with no collection changes.

### A5. `scripts/lint_vault.py` — standing deterministic lint

Pure-stdlib Python, prints a findings report, exits non-zero on any finding.
Checks:

1. Broken wikilinks (target resolves to no file in raw/, wiki/, wiki/sources/, index/).
2. Orphan wiki notes (no inbound link from any wiki/index note).
3. Raw clippings never referenced by any wiki/index note.
4. Wiki notes missing `sources:` frontmatter (index-type notes exempt).
5. Every raw clipping has an `ingest` entry in `index/log.md`.
6. Every wiki note reachable from `index/_map-of-content.md` (transitive link closure).
7. Duplicate note stems across folders (wikilink ambiguity).

Author wikilinks (e.g. `[[Miguel Otero Pedrido]]`) are allowed as a configurable
known-exceptions list in the script, not hardcoded skips.

---

## Part B — Test plan: `eval/VAULT_TESTS.md`

A manual checklist in a root-level `eval/` folder. **`eval/` is never registered
as a qmd collection** — if gold answers were indexed, a cold agent could pass
retrieval tests by finding the answer key. Each group has explicit pass criteria;
a results tally table at the bottom records dated runs.

### T0 — Lint
Run `python3 scripts/lint_vault.py`. **Pass:** zero findings.

### T1 — Known-answer eval (core test)
Ten questions authored during implementation, each verified against the raw
clipping text (not against wiki notes), spread so all 8 articles are covered at
least once. Table format: question · gold fact · gold note. Example row:
"What token rate does the SNAC codec produce?" · ~83 audio tokens/s (7 per frame)
· `multimodal-finetuning-vision-tts`.
**Procedure:** open a fresh Claude Code session in the vault root (no prior
conversation), ask the question verbatim, nothing else.
**Pass per question:** correct fact AND the correct note (or its raw source)
cited. **Group pass: ≥ 8/10.**

### T2 — Negative controls
Three questions about topics verifiably absent from the corpus (e.g., Mamba/SSMs,
speculative decoding, constitutional AI — confirmed absent during authoring).
**Pass:** agent explicitly answers "not covered in this vault" (or equivalent).
Any fabricated answer fails the whole group. **Group pass: 3/3.**

### T3 — Cross-source synthesis
Two questions requiring connecting ≥2 articles (e.g., QLoRA's paged optimizers
vs vLLM's PagedAttention; how 4-bit weights buy KV-cache headroom).
**Pass per question:** the connection is drawn correctly and both contributing
notes/sources are cited. **Group pass: 2/2.**

### T4 — Engine smoke tests (no agent)
Direct commands with expected top hits, isolating retrieval from agent reasoning:
- `qmd search "<known term>"` → expected note is top-3.
- `qmd query` (structured intent/lex/vec) → expected note is top-3.
- `graphify query "<multi-hop question>"` → traversal includes the expected nodes.
Concrete commands and expected hits are written during implementation.
**Group pass:** all commands return expected results.

### T5 — Incremental ingest (the compounding test, generic procedure)
Run whenever a real new clipping arrives (no designated fixture article):
1. Drop the clipping into `raw/` (never editing existing files).
2. Execute the Ingest workflow from CLAUDE.md.
3. Verify: no near-duplicate concept notes created (existing notes updated
   instead); MOC, registry, and log updated; `qmd search` finds the new content;
   `graphify --update` re-extracted only the new file; T0 passes.
**Pass:** all five checks hold.

### Scoring
A run of T0–T4 passes overall when every group meets its threshold. Record each
run as a dated row in the tally table (date, T0–T5 results, notes). T5 is
recorded per-ingest, not per-run.

---

## Execution order

1. `CLAUDE.md` (A1)
2. `index/log.md` backfill (A2; A3 lands inside A1's text)
3. `wiki/sources/` summary pages ×8 (A4)
4. `scripts/lint_vault.py` (A5) — then run it; fix any findings
5. `qmd update && qmd embed` (indexes the new summaries)
6. `eval/VAULT_TESTS.md` with authored T1/T2/T3/T4 content
7. User runs the checklist manually; results recorded in the tally table

## Error handling & edge cases

- Lint finding during step 4: fix the vault content, re-run until clean —
  findings are defects, not warnings.
- T1 authoring must quote gold facts from `raw/` text; if a candidate question's
  answer can't be located verbatim in a clipping, discard the question.
- T2 topics must be checked against the corpus (qmd search returns no relevant
  hit) before being used as negative controls.
- If `qmd embed` fails offline (model cache), see instructions.md §4.

## Success criteria

- All five improvements in place; lint exits 0.
- Karpathy-spec compliance: schema ✓ log ✓ write-back ✓ summaries ✓ lint ✓.
- User's manual run meets T0–T4 thresholds (T1 ≥8/10, T2 3/3, T3 2/2, T4 all).
- T5 procedure documented and ready for the next real clipping.
