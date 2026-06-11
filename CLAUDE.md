# CLAUDE.md — Vault Schema

> Full replication runbook: `instructions.md` · Design spec: `docs/superpowers/specs/2026-06-11-vault-improvements-and-eval-design.md`

## Three-layer model

| Layer | Folder | Rule |
|-------|--------|------|
| Source | `raw/` | **Immutable.** Never edit, rename, or delete. |
| Knowledge | `wiki/` | Atomic synthesized notes. One concept per file. |
| Navigation | `index/` | Maps, registry, log, takeaways. |

`eval/` — test fixtures. **Never register as a qmd collection.**

## Note conventions

- Filename: `kebab-case.md` (concept notes), `wiki/sources/slug.md` (summaries)
- Frontmatter required: `title`, `type` (concept | source-summary | analysis | index), `tags`, `sources` (wikilinks to raw clippings) — index-type notes exempt from `sources`
- Wikilinks over raw URLs for internal references
- One concept per note; **update existing notes before creating new ones**
- Search qmd first — never create a duplicate

### Note template (concept)

```yaml
---
title: "<Title>"
type: concept
tags: [tag1, tag2]
sources:
  - "[[Raw Clipping Filename Without Extension]]"
---

# Title

**One-sentence thesis in bold.**

Body. Dense [[wikilinks]] to sibling notes.

## Related
[[note-a]] · [[note-b]]
```

### Note template (source-summary)

```yaml
---
title: "Summary — <Article Title>"
type: source-summary
tags: [tag1]
sources:
  - "[[Raw Clipping Filename]]"
published: YYYY-MM-DD
---

# Summary — <Article Title>

**One-sentence thesis.**

~200 words: what the article argues.

## Key claims
- claim → [[derived-concept-note]]

## Derived concept notes
[[note-a]] · [[note-b]]
```

## Safety rules

- Never invent provenance, dates, authors, or claims
- Never collapse distinct concepts into one note
- Never create a duplicate — search qmd first, then update
- Mark uncertain extraction as uncertain and link to source

## Workflow — Ingest (new raw/ clipping)

1. `qmd search "<title keywords>" -n 5` — find existing related notes
2. Create `wiki/sources/<slug>.md` (source-summary template)
3. Create or update concept notes in `wiki/`
4. Update `index/_map-of-content.md` and `index/source-registry.md`
5. Append to `index/log.md`: `## [YYYY-MM-DD] ingest | <title>`
6. `qmd update && qmd embed`
7. `graphify raw/ --update` (re-extracts only changed files)

## Workflow — Query

1. `qmd search "<terms>" -n 5` for fast keyword lookup
2. `qmd query` with intent/lex/vec fields for conceptual questions
3. `graphify query "<question>"` for multi-hop entity traversal
4. `qmd get "#docid"` to fetch full document before making claims
5. **Write-back rule:** if answering produces novel cross-source synthesis
   not already in any note → save as `wiki/<slug>.md` with `type: analysis`,
   list source notes in `sources:`, link from MOC "Analyses" section,
   append `## [YYYY-MM-DD] analysis | <title>` to `index/log.md`

## Workflow — Lint

1. `python3 scripts/lint_vault.py` — fix all findings before proceeding
2. LLM pass: scan `wiki/` for contradictions between notes and stale claims
3. Re-run until exit 0
