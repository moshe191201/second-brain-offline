---
name: vault-query
description: Answer a question about this vault's domain by retrieving from the vault and citing it, never from prior knowledge alone. Use for any question the vault could plausibly cover.
---

# vault-query

Ground every answer in the vault. Never answer an in-domain question from training data alone.

## Minimal-model path (default)

1. `qmd search "<exact terms>" -n 5` for keyword leads.
2. If conceptual/fuzzy, `qmd query` with `intent:`/`lex:`/`vec:` fields you write yourself.
3. `qmd get "#<docid>"` to read the full note before making any claim.
4. For "how does X relate to Y", run `graphify query "<question>"`.
5. Answer ONLY from retrieved text. Cite the note or its raw source.
6. If retrieval finds nothing relevant, say: "The vault does not cover this." Do NOT fill the
   gap from training data.

## Capable-model path (opt-in)

If the answer is novel cross-source synthesis not in any note, additionally save it as
`wiki/<slug>.md` with `type: analysis` and `sources:` listing the contributing notes, link it
from the MOC "Analyses" section, and append an `## [date] analysis | <title>` line to
`index/log.md`. Then `python3 scripts/vault.py check`.
