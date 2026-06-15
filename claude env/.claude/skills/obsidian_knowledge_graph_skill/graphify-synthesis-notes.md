# Graphify synthesis notes

This file tells Claude how to use Graphify output when improving an Obsidian knowledge graph.

## What Graphify gives you

Graphify produces a graph bundle that can include:
- `graph.html`
- `GRAPH_REPORT.md`
- `graph.json`

Use the bundle to understand:
- clusters
- entities
- relationships
- orphan nodes
- candidate hub notes
- missing index coverage

## How to interpret it

Treat Graphify as a structural lens.

Good uses:
- identify topics that deserve an index note
- surface notes that should be linked together
- detect duplicate concepts that need consolidation
- find isolated source notes that should be promoted into wiki notes

Bad uses:
- blindly trust every inferred edge
- replace note-writing judgment with graph output alone
- create noisy links just because a connection exists

## Decision rules

When Graphify shows a strong cluster:
- create or refresh an index note for that cluster
- add explicit links among the strongest related wiki notes
- ensure the cluster has a human-readable entrypoint

When Graphify shows an orphan:
- decide whether it belongs in an existing index
- create a bridge note only if the orphan is important and reusable
- otherwise keep it as a source note until it earns promotion

When Graphify shows duplicate entities:
- merge toward the existing canonical note
- preserve backlinks from the obsolete variant
- do not let the vault drift into synonym sprawl

## Promotion ladder

A source usually moves through these stages:

1. `raw/` clipping
2. source summary note
3. atomic wiki note
4. index note or hub link

Only promote when the information is stable enough to reuse.

## Suggested note patterns

### Source summary note
Best for:
- one article
- one transcript
- one imported document

### Atomic wiki note
Best for:
- a single framework
- a principle
- a mechanism
- a concrete concept worth linking repeatedly

### Index note
Best for:
- topic hubs
- library pages
- review pages
- maps of content

## Example update language for Claude

Use phrasing like:
- "I checked the existing vault first."
- "I found the nearest canonical note."
- "I promoted the recurring idea into a wiki note."
- "I kept the raw clipping untouched."
- "I updated the index to point to the cluster hub."

## Reliability checklist

Before finishing, verify:
- no duplicate note was introduced unnecessarily
- source provenance is present
- new notes have at least a few meaningful links
- the index is useful to a human, not just the model
- the update can be explained later from the notes alone
