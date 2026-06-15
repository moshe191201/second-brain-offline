# Vault conventions

## Folder roles

### `raw/`
Put untouched or minimally normalized source material here.

Examples:
- web clippings
- article captures
- transcripts
- screenshots with extracted text
- imported PDFs or OCR output notes

Rules:
- treat as source-of-truth evidence
- do not rewrite content for style
- only add metadata or a short wrapper note if necessary

### `wiki/`
Put synthesized evergreen notes here.

Rules:
- one note = one concept, claim, event, mechanism, or comparison
- notes should be short enough to scan but complete enough to stand alone
- every note should include links to related notes and at least one source reference

### `index/`
Put navigational notes, maps, review notes, and dashboards here.

Examples:
- `index.md`
- `topics.md`
- `people.md`
- `projects.md`
- `weekly-review.md`
- `graph-map.md`

Rules:
- use these notes to help a human or agent enter the vault from a topic
- include curated links, not every possible link
- keep them updated when the graph changes

## Suggested frontmatter

Use YAML frontmatter for derived notes when possible:

```yaml
---
type: source|wiki|index|review|map
title: Human readable title
created: 2026-06-10
updated: 2026-06-10
source_path: raw/path/to/source.md
source_kind: article|video|podcast|paper|note|other
tags:
  - tag-one
  - tag-two
status: draft|stable|review
graphify: true
qmd_indexed: true
---
```

## Recommended note structure

For a source summary note in `wiki/`:

1. What the source is about.
2. The 3 to 7 most important claims or ideas.
3. Related concepts and links.
4. Open questions or uncertainty.
5. Source provenance.

For an atomic concept note:

1. Definition or thesis.
2. Why it matters.
3. Links to related notes.
4. Evidence or example.
5. Source provenance.

For an index note:

1. Purpose of the index.
2. Curated list of hubs.
3. Subtopics and related entrypoints.
4. Recent updates or gaps.

## Naming conventions

Prefer stable, readable titles.

Good:
- `Semantic Search`
- `Source Ingestion Pipeline`
- `Daily Review`
- `Graph Maintenance`

Avoid:
- duplicate synonyms
- overly long titles
- vague titles like `Stuff` or `Misc`

If a note already exists under a close synonym, update it instead of creating another one.

## Link conventions

- Use `[[wikilinks]]`.
- Link source notes to derived notes.
- Link derived notes back to the source summary note.
- Link index notes to the strongest hubs only.
- Prefer meaningful links over mass-linking everything.

## Duplication rules

Before creating a new note:
1. search for the concept in the existing vault
2. inspect similar titles
3. update an existing note if it already covers the idea
4. create a new note only when the concept is distinct

## Quality bar

A good vault note should make it easier to answer:
- What is this?
- How does it relate to other things?
- Where did it come from?
- Why does it matter?
- What should be reviewed next?
