# Second Brain Vault Framework

Build a local, AI-operable **knowledge vault** — an Obsidian-style "second brain" that turns
raw source clippings into atomic, cross-linked notes you can search and traverse, with the
whole workflow driven by Claude Code skills and a deterministic CLI.

Inspired by Andrej Karpathy's *llm-wiki* idea: immutable sources, synthesized knowledge, and
a schema the LLM follows — built to run fully offline (including air-gapped) on minimal local
models.

## Framework vs. vault

This repo is the **framework**. A **vault** is a normal folder you own, anywhere on disk.

```bash
pip install second-brain-vault-framework
vault scaffold "My Vault"     # lay down the framework into a new vault
cd "My Vault"                 # drop clippings into raw/ and ingest
```

Later, when a new framework version ships:

```bash
pip install --upgrade second-brain-vault-framework
vault upgrade .               # re-lays framework files; never touches your content
```

Framework files are replaced wholesale on upgrade; your `raw/`, `wiki/`, and `index/` are
never read or written. The one editable region inside a framework file is the USER ZONE block
in `CLAUDE.md`, which is preserved verbatim across upgrades.

## Three-layer model

| Layer | Folder | Rule |
|-------|--------|------|
| Source | `raw/` | **Immutable** clippings — the evidence layer. Never edited or deleted. |
| Knowledge | `wiki/` | Atomic concept notes (one idea each) + `wiki/sources/` per-source summaries. |
| Navigation | `index/` | Map of content, source registry, log, key takeaways. |

`tests/` holds the eval checklist and is **never** indexed for search — gold answers must not
contaminate retrieval.

## Two local engines

- **[qmd](https://www.npmjs.com/package/@tobilu/qmd)** — hybrid BM25 + vector search. *"Find me the note about X."*
- **graphify** — entity/relationship knowledge graph. *"How does X relate to Y?"*

Both run fully locally. `example_vault/instructions.md` is the full build and air-gapped
replication runbook; `qmd-api/` covers staging the OpenAI-backend qmd fork for a no-GPU gap.

## How you work with it

A vault carries its own operating manual. Running Claude Code in a vault loads its
`CLAUDE.md` (the schema + the rule to always ground answers in the vault) and four skills,
each backed by the deterministic CLI:

| Skill | Use it to | CLI it wraps |
|-------|-----------|--------------|
| **vault-setup** | create or air-gap-bootstrap a vault | `vault scaffold`, `vault register` |
| **vault-ingest** | turn a new `raw/` clipping into notes | `vault ingest`, `vault new-note` |
| **vault-query** | answer a question, grounded + cited | (qmd / graphify) |
| **vault-lint** | health-check before calling work done | `vault check` |

The CLI does the mechanical work (scaffolding, stubs, registry/log, validation); you only
fill in note bodies. `vault check` is **fail-closed** — it exits non-zero on broken links,
orphans, unfilled stubs, or framework drift, so a half-done vault never looks finished.

## Repo layout

```
docs/                              mkdocs site — user guide + design specs and plans
example_vault/                     a real vault built by the current payload (CI-verified)
qmd-api/                           staging + install scripts for the qmd OpenAI-backend fork
src/second_brain_vault_framework/  the pip package (core · cli · manifest · payload)
tests/                             stdlib unittest suite for the package
```

`example_vault/` is living documentation: CI fails if it drifts from the payload, so what
you see there is exactly what `vault scaffold` produces today.

## Development

```bash
pip install -e .
python -m unittest discover -s tests
vault check example_vault
```

Edit framework files in `src/second_brain_vault_framework/payload/` — never directly in
`example_vault/` — then run `vault upgrade example_vault` and commit the result.
