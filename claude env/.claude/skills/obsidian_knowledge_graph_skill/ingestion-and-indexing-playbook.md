# Ingestion and indexing playbook

Use this playbook every time new material lands in `raw/` or when the graph needs a refresh.

## Inputs

Typical inputs:
- newly clipped articles
- a batch of saved web notes
- screenshots or transcripts converted to markdown
- a folder of imported source captures

## Step 1 — inventory the change

Determine:
- which files are new
- which files were edited
- which notes already exist that might overlap
- which topic areas are affected

## Step 2 — retrieve context with QMD

Search the vault before writing.

Suggested sequence:
- `qmd search "<keywords>"`
- `qmd query "<broader idea>"`
- `qmd vsearch "<concept>"` only when needed
- `qmd get "<path or docid>"` for full reading

Use QMD to answer:
- what already exists on this topic?
- what related notes should be linked?
- what phrasing or taxonomy is already established?
- what duplicate or near-duplicate notes should be merged?

## Step 3 — extract structure with Graphify

Run Graphify on the relevant scope.

Recommended outcomes:
- a graph output directory
- `graph.html` for interactive inspection
- `GRAPH_REPORT.md` for highlights, clusters, and gaps
- `graph.json` for structured machine use

Use the graph to identify:
- hubs
- orphan concepts
- repeated entities
- missing links
- promising index pages
- candidate evergreen notes

## Step 4 — write or update notes

Create notes only after retrieval and extraction.

Preferred actions:
- summarize the source in a source note
- create atomic wiki notes for reusable ideas
- update index notes for navigation
- add backlinks and outgoing links
- preserve source provenance

## Step 5 — verify graph quality

Check that:
- each important idea has a home
- there are no accidental duplicates
- source notes and wiki notes are connected
- index pages point to hubs, not everything
- uncertain claims are labeled as such

## Step 6 — leave a clean trail

Record what changed in a review note or short changelog note when useful.

A good update note includes:
- source folder processed
- notes created
- notes updated
- major link additions
- unresolved gaps

## Suggested operational pattern

For a batch of new raw clippings:

1. search existing notes with QMD
2. run Graphify over the batch or the relevant corpus
3. draft source summaries
4. promote reusable ideas into wiki notes
5. refresh index pages
6. stop and report any uncertainty rather than guessing

## What not to do

- do not overwrite source material
- do not create notes from snippets alone when the full source is available
- do not build a graph full of duplicates
- do not force every source into the same template if the source is genuinely different
- do not invent relationships that are not supported by the content
