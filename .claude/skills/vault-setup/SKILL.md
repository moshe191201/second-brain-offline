---
name: vault-setup
description: Create a new vault or bootstrap one in an air-gapped environment, then register the search and graph engines. Use when setting up, scaffolding, or replicating a vault.
---

# vault-setup

## Minimal-model path (default)

Pick the matching section below and follow its numbered steps in order. Do not improvise the
directory structure — the CLI creates it exactly right. If `vault check` fails after setup,
use the **vault-lint** skill to diagnose.

## Create a new vault

1. From a directory that already contains `scripts/vault.py` (clone this repo, or copy
   `vault.py` from an existing vault first — a brand-new empty folder has no CLI to run),
   run: `python3 scripts/vault.py scaffold <vault-name>`. It creates
   `raw/ wiki/ index/ eval/ scripts/ .claude/skills/`, renders `CLAUDE.md`, copies the CLI +
   lint + templates, and writes the four skills.
2. Put source clippings in `<vault-name>/raw/` (these become immutable).
3. `cd <vault-name>` and ingest each clipping with the **vault-ingest** skill.

## Air-gapped bootstrap

The vault repo carries `vault.py`, the skills, and `CLAUDE.md`. The ENGINES (qmd, graphify,
the embedding model, the graphify skill, the qmd plugin) transfer separately — follow
`instructions.md` Phase A (stage) and Phase B (install). Then:

1. Confirm Claude Code routes to the local model and no `GEMINI_API_KEY` is set.
2. `python3 scripts/vault.py register` to add qmd collections and embed.
3. `python3 scripts/vault.py check` — must exit 0.
