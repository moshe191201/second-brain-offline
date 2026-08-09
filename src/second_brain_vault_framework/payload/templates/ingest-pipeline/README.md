# Ingest pipeline — planning

**Fill these in before any document is filtered, translated, or ingested.**
The answers drive the entire pipeline: what gets filtered out, what order things are
learned in, which source wins when two documents disagree.

The planning is split into steps so that no single file has to be read — by a person or
by a model — in order to work on one subject. Each step is a folder holding the questions
for that subject, the guidance needed to answer them, and its own sign-off.

---

## How to use this

**Who fills it in:** the domain expert and the pipeline operator, together, one step per
focused session. The expert owns the knowledge questions; the operator owns the
mechanical ones and writes down what the expert says.

**How to answer:** write directly under each question. Tables are filled in as rows;
free-text questions take a paragraph. "I don't know yet" is a valid answer — mark it
`TBD` and note what would resolve it. A wrong guess costs more than an admitted gap.

**Question IDs (A1, B2, …) are stable and are not renumbered when steps move.** Later
documents, decisions, filter rules, and open tasks cite them. Reference a question by
step and ID — `03-filtering/C3` — so the reference says where to look without changing
what it points at.

**`GUIDANCE.md` is read once, by a person.** It holds the reasoning needed to make hard
calls. It is not needed while filling in answers and should not be loaded as context
during pipeline work.

**What the pipeline reads is the artifact, not the questions.** Each step produces a
compact output — a scope card, a trust map, a type vocabulary, a glossary seed. Those are
what downstream stages consume. If a pipeline stage is loading these question files, that
is a defect in the stage, not a reason to shorten the questions.

---

## Shared artifacts

Two outputs are needed by nearly every step, so they live at this level rather than
inside the step that produces them:

| File | Produced by | Read by |
|------|------------|---------|
| [`domains.md`](domains.md) | `01-domains/A1` | 02, 03, 04, 05 |
| [`sources.md`](sources.md) | `02-classification/B1` | `01-domains/H1`, 03 |

> **One copy only.** Never restate either list inside a step file. A second copy drifts
> the moment the completeness loop in `A7` adds a domain, and then two steps are scoped
> to different maps. Link to the shared file instead.

---

## Steps

| # | Step | Covers | Needs first | Produces | Status |
|---|------|--------|-------------|----------|--------|
| 01 | [Domains](01-domains/QUESTIONS.md) | A, F, G, H | `sources.md` for H | `domains.md`, dependency graph, layer ordering, work sequence | |
| 02 | [Classification](02-classification/QUESTIONS.md) | B, E | `domains.md` | `sources.md`, trust tier map, document type vocabulary | |
| 03 | [Filtering](03-filtering/QUESTIONS.md) | C, D | `domains.md`, `sources.md` | Scope cards, filter seed rules, protect list | |
| 04 | [Translation](04-translation/QUESTIONS.md) | I | `domains.md` | Translation policy, layered glossary seed | |
| 05 | [Success criteria](05-success-criteria/QUESTIONS.md) | J, K | `domains.md`, E1, H3 | Gold sample, reference set, acceptance tests, definition of done | |

**Fill order.** Start at 01 and work down. One exception: **`B1` in step 02 produces
`sources.md`, which step 01's Part H reads.** B1 is a short factual inventory with no
prerequisites, so fill it up front and return to the rest of step 02 later.

Steps sign off independently. Filtering can be signed off and running while translation
is still open — that is the point of the split.

---

## What this produces

| Output | Built from | Used by |
|--------|-----------|---------|
| Domain list | A1 → `domains.md` | Every stage |
| Source inventory | B1 → `sources.md` | Work-unit definition, filtering |
| Scope cards | A3, C | Filtering (scope judge), classification |
| Filter seed rules | D | Filtering (deterministic gates) |
| Trust tier map | B2–B4 | Conflict resolution, ingest order |
| Document type vocabulary | E | Classification |
| Knowledge layer ordering | F | Ingest order within a work unit |
| Dependency graph and sequence | A6, G, H | Work sequencing, overlap ownership |
| Translation policy and glossary seed | I | Translation |
| Pilot selection | J | Calibration (gold sample, reference translations) |
| Definition of done | K | Work unit QA gate |

---

## Open items across all steps

Anything marked `TBD` in any step, with what would resolve it.

| Step | ID | Blocked on | Owner |
|------|----|-----------|-------|

## Overall sign-off

Only complete when every step is signed off in its own file.

| Field | Value |
|-------|-------|
| Domain expert | |
| Pipeline operator | |
| Date completed | |
| Version | 1 |
