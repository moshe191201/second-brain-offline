---
name: vault-lint
description: Run the deterministic vault health check and interpret the findings. Use before declaring vault work complete, or whenever asked to lint, validate, or verify the vault.
---

# vault-lint

## Minimal-model path (default)

1. Run: `python3 scripts/vault.py check` (Windows: `py scripts\vault.py check`).
2. exit 0 → the vault is structurally sound. Done.
3. exit ≠0 → the output names each finding by its exact prefix. Allowed fixes (whitelist only):
   - "unfilled stub / TODO marker in <file>" → fill that note's `<!-- TODO -->` body from its
     `sources:` clipping.
   - "NO LOG ENTRY: <raw>" → re-run `vault ingest raw/<that-file>.md`.
   - "UNREACHABLE FROM MOC: <note>" → add a wikilink to it under the right
     `index/_map-of-content.md` section.
   - "BROKEN WIKILINK: [[x]] in <note>" → fix or remove that link (its target note must exist).
   - "ORPHAN NOTE: <note>" → add an inbound wikilink from a related note or the MOC.
   - anything else, or still failing after one pass → **STOP and report**. Do NOT edit `raw/`.
4. Re-run `vault check` until exit 0 or you hit the STOP condition.
