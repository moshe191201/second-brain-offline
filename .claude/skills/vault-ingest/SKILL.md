---
name: vault-ingest
description: Ingest a new or changed clipping from raw/ into wiki summaries, concept notes, the registry, the log, and the graph. Use when a file is added to or changed in raw/, or when asked to ingest, index, or refresh the vault.
---

# vault-ingest

Turn an immutable `raw/` clipping into synthesized notes. The CLI does all mechanical work;
you write note bodies only.

## Minimal-model path (default)

1. Run: `python3 scripts/vault.py ingest raw/<file>.md`
   It creates the source-summary stub, the registry row, and the log entry, then prints the
   blanks to fill.
2. Read `raw/<file>.md` in full. Identify each durable concept it teaches.
3. For each concept, run: `python3 scripts/vault.py new-note <kebab-slug> --source raw/<file>.md`
4. Fill ONLY the `<!-- TODO ... -->` blanks in the summary and each concept note. Ground every
   claim in `raw/<file>.md`. Add a placeholder MOC link target where the stub indicates.
5. Run: `python3 scripts/vault.py check`
   - exit 0 → continue to step 6.
   - exit ≠0 → do exactly what the message says, or **STOP and report**. Do NOT free-form
     "fix". Do NOT edit `raw/`.
6. Build the graph: run `/graphify raw/ --update` in Claude Code. Use `raw/`, **not** `.` —
   this vault's graph is raw-only (the `wiki/` notes are derived from `raw/` and would
   duplicate nodes). Check `graphify-out/.graphify_root` if unsure of the established scope.
7. Update search so the new notes are retrievable:
   - **Re-ingest into an already-set-up vault (the usual case):** `qmd update && qmd embed`.
     The collections already exist; do not re-add them.
   - **First-time setup only:** `python3 scripts/vault.py register` (registers the qmd
     collections for `raw/`, `wiki/`, `index/` — never `eval/` — then updates and embeds).

## Capable-model path (opt-in; only if CLAUDE.md STRICTNESS: CAPABLE)

Between steps 4 and 5, re-read `raw/<file>.md` and verify each sentence you wrote traces to
the source. Allowed reactions to a problem: re-run a command, fill a named blank, or STOP.
Never invent content; never edit `raw/`.
