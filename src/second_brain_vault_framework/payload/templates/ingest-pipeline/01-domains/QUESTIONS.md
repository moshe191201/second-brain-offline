# Step 01 — Domains

**Covers:** Parts A, F, G, H
**Read first:** [`GUIDANCE.md`](GUIDANCE.md) — the rules for deciding what is a domain
**Needs first:** nothing, except **H1, which reads [`../sources.md`](../sources.md)** —
fill that (via `02-classification/B1`) before answering Part H
**Produces:** [`../domains.md`](../domains.md), plus the dependency graph, knowledge layer
ordering, and work sequence held in this file

---

## Part A — Domains

> *Why: the domain is the top-level partition of the vault. Domains are learned
> separately but queried together, so the boundaries decide what gets built when.*

### A1 — What domains does the vault need to cover?
Build this list from **several independent angles**, not one pass — the point is to catch
what a single top-down attempt forgets. Work through each angle, then merge:

- **From the business:** what does this campaign do, what are its outputs and missions?
- **From the corpus:** what do the source folders, space trees, and recurring title terms
  cluster into? Include clusters that match no domain you had thought of.
- **From the people:** what does each team or expert know, and what do they get asked?
- **From the questions:** what do people actually come to this team to find out?

**Record the result in [`../domains.md`](../domains.md)** — the single copy every other
step reads. Do not restate the list here.

### A2 — For each in-scope domain, what subdomains does it break into?
Only one level down. Subdomains share the domain's glossary, scope card, and trust map —
if a candidate subdomain would need its own, revisit A5.

| Domain | Subdomains |
|--------|-----------|
| | |

### A3 — Which domains are explicitly out of scope, and why?
Name them. Out-of-scope domains that appear in the corpus are the hardest filtering
case — well-formed documents about the wrong subject — so the filter needs to know
what they look like.

### A4 — Who is the authority for each in-scope domain?
The person who adjudicates when the pipeline asks a question. If it is the same person
for everything, say so; if a domain has no available authority, flag it now.

| Domain | Authority | Availability |
|--------|-----------|--------------|

### A5 — Apply the test to every candidate split you argued about.
For each area where you debated one domain versus several, record the decision and the
reason. This is the record that stops the argument being reopened every month.

| Candidate split | Shared glossary? | Shared scope card? | Shared trust map? | Decision | Why |
|-----------------|-----------------|-------------------|------------------|----------|-----|

### A6 — Classify the dependencies between domains as hard or soft.
This distinction controls sequencing, and getting it wrong is expensive in both
directions — too many hard edges and nothing can start, too few and shallow notes get
written before the foundations that should have shaped them.

- **Hard (prerequisite):** the dependent domain cannot be understood without it. Creates
  a real ordering constraint — the prerequisite is ingested first.
- **Soft (enriching):** the dependent domain can be known well without it, but it adds
  depth. **Creates no ordering constraint.** The connection is made by links between
  concepts, and joint querying surfaces it whenever both are present.

| Domain A | Domain B | A is prerequisite / enriching for B | Evidence |
|----------|----------|-------------------------------------|----------|

> Only hard edges go into the sequencing plan in Part H. Broad, basic domains are
> frequently *enriching* rather than prerequisite; treating them as prerequisites
> front-loads a large amount of work that the priority domains do not actually need.

### A7 — Completeness check (repeat until stable)
Do not rely on memory to be sure the map is complete. Close the loop against the corpus:

1. Route a sample of the corpus against the current domain list.
2. Inspect everything that lands in **unassigned**.
3. Each unassigned document is one of: junk (a filter rule), out of scope (A3), or
   **evidence of a domain you forgot** (add it and repeat).

| Iteration | Date | Unassigned share | Domains added | Notes |
|-----------|------|-----------------|---------------|-------|

> Adding a domain later is cheap — a scope card, a glossary, and a re-run of a
> deterministic routing pass. The map has to be good enough to start the pilot, not
> perfect before it.

---

## Part F — Knowledge layers

> *Why: ingestion runs from foundational to advanced, so that later documents attach to
> concepts that already exist instead of creating duplicates.*

### F1 — For each domain, what is the foundational layer?
The documents that define the base vocabulary and concepts — what a newcomer must read
first. Usually standards, specifications, or formal internal documentation.

| Domain | Foundational sources or documents |
|--------|----------------------------------|

### F2 — What builds on top of that foundation, and in what order?
Sketch the layers: foundation → applied/analytical → team practice → informal notes.
Where a layer depends on another domain's foundation, say so.

### F3 — Are there documents that only make sense after specific others?
Name the pairs. These become explicit ordering constraints.

### F4 — What must be true before a domain is worth querying at all?
The minimum set of concepts that has to exist for answers to be useful.

---

## Part G — Overlaps between work units

> *Why: two sources covering the same subject is the main risk of duplicate or
> contradictory notes. Deciding ownership up front turns the overlap into the
> connection that makes cross-domain querying work.*

### G1 — Which pairs of domains or sources cover overlapping subject matter?

| A | B | What overlaps | Which should be ingested first | Why |
|---|---|--------------|-------------------------------|-----|

### G2 — For each overlap, what should happen when the second work unit arrives?
The default is: the existing note is extended, sources are added, and any disagreement
is flagged for you. Say where that is wrong.

### G3 — Are there concepts that genuinely mean different things in different domains?
Same word, different meaning. These must stay as separate notes, and the pipeline needs
to know so it doesn't merge them.

---

## Part H — Work units and sequencing

> *Why: a work unit is one batch — filtered, translated, classified, ingested, and
> checked together. Their order is the project plan.*

### H1 — Define the work units.
A work unit is usually one domain, sometimes one source, sometimes a slice of both — so
this reads both [`../domains.md`](../domains.md) and [`../sources.md`](../sources.md).

| Work unit | Definition (which documents) | Rough volume | Depends on |
|-----------|------------------------------|--------------|-----------|

### H2 — What is the order, and what forces it?
Hard dependencies from A6, layer ordering from F, overlap ownership from G, expert
availability, client priority.

### H3 — Which work unit is the pilot, and why?
Pick one that is valuable enough to prove the system and small enough to finish.

### H4 — What is the deadline or demo pressure, if any?

---

## Sign-off — Step 01

| Field | Value |
|-------|-------|
| Domain expert | |
| Pipeline operator | |
| Date completed | |

Unanswered questions and `TBD`s, with what would resolve each:

| ID | Blocked on | Owner |
|----|-----------|-------|
