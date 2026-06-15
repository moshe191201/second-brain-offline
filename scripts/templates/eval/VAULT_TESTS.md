# Vault Test Checklist — {{VAULT_NAME}}

> ⚠ `eval/` is **never** a qmd collection. These answers must not contaminate retrieval.

## T0 — Deterministic check
Run: `python3 scripts/vault.py check` (Windows: `py scripts\vault.py check`). Pass: exit 0.

## T1 — Known-answer recall (author per corpus)
For 5–10 facts you can verify against a raw clipping, ask the question in a fresh session.
Pass per item: correct fact AND the gold note/raw source cited. Group pass: ≥80%.

## T2 — Negative controls (author per corpus)
Ask about 3 topics you have confirmed are ABSENT from `raw/`.
Pass: the agent says "not covered" each time. **Any fabrication fails the whole group.**

## T3 — Cross-source synthesis (author per corpus)
2 questions whose answer spans two clippings. Pass: connection drawn + both sources cited.

| Date | T0 | T1 | T2 | T3 | Notes |
|------|----|----|----|----|-------|
| —    | —  | —  | —  | —  | (first run pending) |
