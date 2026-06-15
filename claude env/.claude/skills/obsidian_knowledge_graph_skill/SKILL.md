name obsidian-knowledge-graph
description Index and maintain an Obsidian second brain from raw clippings, wiki notes, and index maps using QMD for retrieval, Graphify for graph extraction, and Obsidian CLI/open formats for safe vault edits.

# Obsidian Knowledge Graph Skill

Use this skill to turn an existing Obsidian vault with `raw/`, `wiki/`, and `index/` folders into a reliable knowledge graph.

## What this skill optimizes for

- Preserve source clippings in `raw/` as the immutable evidence layer.
- Convert useful ideas into evergreen, atomic notes in `wiki/`.
- Maintain navigational and topical entrypoints in `index/`.
- Use `qmd` first for local retrieval and deduplication.
- Use `graphify` to discover entities, relationships, clusters, and missing links.
- Use Obsidian CLI and Obsidian-flavored Markdown to update the vault safely.

## Core working model

Think of the vault as three layers:

1. `raw/` = source material, clippings, transcripts, imported articles, untouched or lightly normalized.
2. `wiki/` = synthesized knowledge, one idea per note, richly linked.
3. `index/` = maps, dashboards, and review notes that help the agent and the human navigate the graph.

## Primary loop

When asked to ingest, index, refresh, or improve the vault:

1. Discover the new or changed files in `raw/` and relevant nearby notes in `wiki/` and `index/`.
2. Search the existing vault with `qmd` before creating anything new.
3. Run `graphify` on the relevant folder or corpus to extract entities, links, clusters, and a report.
4. Update or create derived notes in `wiki/` and `index/`.
5. Re-run local search awareness mentally: ensure every new note links to related concepts and the source note.
6. Leave the `raw/` source untouched unless the user explicitly asks for normalization or cleanup.

## Search strategy

Prefer this order:

- `qmd search` for fast keyword lookup.
- `qmd query` for best-quality hybrid retrieval when the question is broad or ambiguous.
- `qmd vsearch` only when keyword search misses the concept and semantic similarity is needed.
- `qmd get` or `qmd multi-get` to read the full document(s) before making decisions.

Use search to answer these questions before writing:

- Has this idea already been captured in `wiki/`?
- Which notes should this source link to?
- Is this a new concept, a refinement, or a duplicate?
- Which index page should include this note?

## Graphify strategy

Use `graphify` to discover structure and missing connections.

Default pattern:

- extract a relevant folder or subset
- inspect `graphify-out/GRAPH_REPORT.md`
- inspect `graphify-out/graph.json`
- use the report to identify high-value hubs, orphan notes, and candidate links
- then update `wiki/` and `index/` notes accordingly

Treat `graphify` output as a synthesis aid, not as the final source of truth. The final truth is the vault content you maintain.

## Obsidian editing rules

When writing notes:

- Use Obsidian-flavored Markdown.
- Use wikilinks instead of raw URLs when possible.
- Preserve and extend existing note names rather than creating near-duplicates.
- Prefer atomic notes with a single clear claim, pattern, or concept.
- Give each synthesized note enough context to stand alone.
- Add backlinks and outgoing links deliberately.
- Keep source provenance visible in frontmatter and/or a source section.

## Safety rules for the vault

- Never delete or overwrite a user’s source clipping unless explicitly asked.
- Never collapse distinct concepts into one note just to reduce note count.
- Never create duplicate notes when an existing note can be updated.
- Never invent provenance, dates, authors, or claims.
- If extraction is uncertain, mark it as uncertain and link to the source.
- If there are competing interpretations, keep both and link them together.

## Output expectations

For every ingestion session, aim to produce:

- 1 refreshed or created source summary note in `wiki/`
- 0 or more atomic concept notes in `wiki/`
- 1 updated topical map or dashboard in `index/`
- 1 updated source registry or review note in `index/` when relevant

## How to use this skill

When Claude reads this skill, it should:

- consult the local vault before writing
- use graph extraction to improve structure
- write durable, linked notes
- keep the knowledge graph reliable and maintainable
