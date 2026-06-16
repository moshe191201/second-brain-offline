# Second Brain Offline

A local, AI-operable **knowledge vault** — an Obsidian-style "second brain" that turns raw
source clippings into atomic, cross-linked notes you can search and traverse, with the whole
workflow driven by Claude Code skills and a deterministic CLI.

Inspired by Andrej Karpathy's *llm-wiki* idea: immutable sources, synthesized knowledge, and
a schema the LLM follows — built to run fully offline (including air-gapped) on minimal local
models.

## Three-layer model

| Layer | Folder | Rule |
|-------|--------|------|
| Source | `raw/` | **Immutable** clippings — the evidence layer. Never edited or deleted. |
| Knowledge | `wiki/` | Atomic concept notes (one idea each) + `wiki/sources/` per-source summaries. |
| Navigation | `index/` | Map of content, source registry, log, key takeaways. |

`eval/` holds test fixtures and is **never** indexed for search.

## Two local engines

- **[qmd](https://www.npmjs.com/package/@tobilu/qmd)** — hybrid BM25 + vector search. *"Find me the note about X."*
- **graphify** — entity/relationship knowledge graph. *"How does X relate to Y?"*

Both run fully locally. See [`instructions.md`](instructions.md) for the full build and
air-gapped replication runbook.

## How you work with it

The vault carries its own operating manual. When you run Claude Code in this folder it loads
[`CLAUDE.md`](CLAUDE.md) (the schema + the rule to always ground answers in the vault) and four
skills, each backed by the deterministic CLI `scripts/vault.py`:

| Skill | Use it to | CLI it wraps |
|-------|-----------|--------------|
| **vault-setup** | create or air-gap-bootstrap a vault | `vault scaffold`, `vault register` |
| **vault-ingest** | turn a new `raw/` clipping into notes | `vault ingest`, `vault new-note` |
| **vault-query** | answer a question, grounded + cited | (qmd / graphify) |
| **vault-lint** | health-check before calling work done | `vault check` |

The CLI does the mechanical work (scaffolding, stubs, registry/log, validation); you only
fill in note bodies. `vault check` is **fail-closed** — it exits non-zero on broken links,
orphans, or unfilled stubs, so a half-done vault never looks finished.

## Quick start

```bash
# Health-check the vault (deterministic; exits non-zero on any finding)
python3 scripts/vault.py check          # Windows: py scripts\vault.py check

# See per-clipping ingest state
python3 scripts/vault.py status

# Ingest a new clipping (then fill the note bodies it stubs out)
python3 scripts/vault.py ingest raw/<your-clipping>.md

# Run the test suite for the CLI itself
python3 -m unittest discover -s tests
```

To search once the index is built: `qmd search "<terms>"` /
`graphify query "<question>"` (see [`CLAUDE.md`](CLAUDE.md) for the full query workflow).

## Layout

```
CLAUDE.md            schema + grounding rule + workflows (loaded every session)
instructions.md      full build record + air-gapped replication runbook
raw/  wiki/  index/  the three layers
eval/                manual test checklist (never indexed)
scripts/             vault.py (CLI) · lint_vault.py · templates/
.claude/skills/      vault-setup · vault-ingest · vault-query · vault-lint
tests/               stdlib unittest suite for the CLI
```

## Creating a new vault

```bash
python3 scripts/vault.py scaffold "My New Vault"
```

This stamps out the full layout (including the CLI, skills, and templates) so the new vault is
self-contained and can itself scaffold others. Drop clippings into its `raw/` and ingest.
