# CLAUDE.md — {{VAULT_NAME}} Vault Schema

> Operating skills: `.claude/skills/vault-*` · CLI: `scripts/vault.py` · Lint: `scripts/lint_vault.py`
> STRICTNESS: MINIMAL   <!-- MINIMAL = deterministic-only, self-review off. CAPABLE = enable Layer-3 self-review. -->

## Three-layer model

| Layer | Folder | Rule |
|-------|--------|------|
| Source | `raw/` | **Immutable.** Never edit, rename, or delete. |
| Knowledge | `wiki/` | Atomic synthesized notes. One concept per file. `wiki/sources/` holds per-source summaries. |
| Navigation | `index/` | `_map-of-content.md`, `source-registry.md`, `log.md`, `key-takeaways.md`. |

`eval/` — test fixtures. **Never register as a qmd collection.**

## Answering questions about this vault's domain

When asked any question this vault could plausibly cover, you **MUST** consult the vault
before answering — never answer from prior knowledge alone. Use the **vault-query** skill:
qmd first, graphify for multi-hop, cite the note or its raw source, and if the vault does
not cover it, say so explicitly. Do not fill the gap from training data.

## Working the vault — use the skills, not improvisation

- New/changed clipping in `raw/` → **vault-ingest** skill.
- Question about the domain → **vault-query** skill.
- Health check / before declaring done → **vault-lint** skill (`vault check`).
- New or air-gapped vault setup → **vault-setup** skill.

The mechanical work is done by `scripts/vault.py`. You fill note bodies only.

## Safety rules

- Never invent provenance, dates, authors, or claims.
- Never collapse distinct concepts into one note; never duplicate — search qmd first.
- Never edit `raw/`. If `vault check` fails and you cannot fix it via the skill's
  whitelist, **STOP and report** — do not push a broken vault to "done".
