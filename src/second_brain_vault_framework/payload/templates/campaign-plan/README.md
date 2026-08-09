# Campaign Plan — index

**Fill these in before any document is filtered, translated, or ingested.**
The answers become the campaign plan that drives the entire pipeline: what gets filtered
out, what order things are learned in, which source wins when two documents disagree.

The questionnaire is split into steps so that no single file has to be read — by a person
or by a model — in order to work on one subject. Each step is a folder holding the
questions for that subject, the guidance needed to answer them, and the compact artifact
the pipeline actually consumes.

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

**What the pipeline reads is the artifact, not the questionnaire.** Each step produces a
compact output — a scope card, a trust map, a type vocabulary, a glossary seed. Those are
what downstream stages consume. If a pipeline stage is loading these questionnaire files,
that is a defect in the stage, not a reason to shorten the questions.

---

## Steps

| # | Step | Covers | Needs first | Produces | Status |
|---|------|--------|-------------|----------|--------|
| 01 | [Domains](01-domains/QUESTIONS.md) | A, F, G, H | — (H1 needs B1) | Domain list, dependency graph, layer ordering, work sequence | |
| 02 | [Classification](02-classification/QUESTIONS.md) | B, E | A | Source inventory, trust tier map, document type vocabulary | |
| 03 | [Filtering](03-filtering/QUESTIONS.md) | C, D | A | Scope cards, filter seed rules, protect list | |
| 04 | [Translation](04-translation/QUESTIONS.md) | I | A | Translation policy, layered glossary seed | |
| 05 | [Success criteria](05-success-criteria/QUESTIONS.md) | J, K | A, E, H | Gold sample, reference set, acceptance tests, definition of done | |

**Fill order.** Start at 01 and work down; that order respects the dependencies above.
One exception: **B1 (the source inventory in step 02) is needed by H1 in step 01.** It is
a short, factual inventory with no prerequisites of its own, so answer B1 up front and
return to the rest of step 02 later.

Steps sign off independently. Filtering can be signed off and running while translation
is still open — that is the point of the split.

---

## What this produces

| Output | Built from | Used by |
|--------|-----------|---------|
| Domain list and scope cards | A, C | Filtering (scope judge), classification |
| Filter seed rules | D | Filtering (deterministic gates) |
| Trust tier map | B | Conflict resolution, ingest order |
| Document type vocabulary | E | Classification |
| Knowledge layer ordering | F | Ingest order within a work unit |
| Dependency graph and sequence | G, H | Work sequencing, overlap ownership |
| Translation policy and glossary seed | I | Translation |
| Pilot selection | J | Calibration (gold sample, reference translations) |
| Definition of done | K | Campaign QA gate |

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
