---
name: vault-lint
description: Run the deterministic vault health check and interpret the findings. Use before declaring vault work complete, or whenever asked to lint, validate, or verify the vault.
---

# vault-lint

## Minimal-model path (default)

1. Run: `python3 scripts/vault.py check` (Windows: `py scripts\vault.py check`).
2. exit 0 → the vault is structurally sound. Done.
3. exit ≠0 → the output names each finding. Allowed fixes (whitelist only):
   - "unfilled stub / TODO marker in <file>" → fill that note's `<!-- TODO -->` body from its
     `sources:` clipping.
   - "missing registry row / log entry for <raw>" → re-run `vault ingest raw/<that-file>.md`.
   - "<note> not reachable from MOC" → add a wikilink to it under the right
     `index/_map-of-content.md` section.
   - anything else, or still failing after one pass → **STOP and report**. Do NOT edit `raw/`.
4. Re-run `vault check` until exit 0 or you hit the STOP condition.
