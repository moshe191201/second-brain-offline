# Campaign Planning Questionnaire

**Fill this in before any document is filtered, translated, or ingested.**
Its answers become the campaign plan that drives the entire pipeline: what gets filtered
out, what order things are learned in, which source wins when two documents disagree.

---

## How to use this

**Who fills it in:** the domain expert and the pipeline operator, together, in one or two
focused sessions. The expert owns the knowledge questions (A, C, E, F, G, I); the
operator owns the mechanical ones (B, D, H, J) and writes down what the expert says.

**How to answer:** write directly under each question. Tables are filled in as rows;
free-text questions take a paragraph. "I don't know yet" is a valid answer — mark it
`TBD` and note what would resolve it. A wrong guess costs more than an admitted gap.

**Question IDs (A1, B2, …) are stable.** Later documents, decisions, and filter rules
cite them, so don't renumber.

**What this produces**

| Output | Built from | Used by |
|--------|-----------|---------|
| Domain list and scope cards | A, C | Filtering (scope judge), classification |
| Filter seed rules | D | Filtering (deterministic gates) |
| Trust tier map | B | Conflict resolution, ingest order |
| Document type vocabulary | E | Classification |
| Knowledge layer ordering | F | Ingest order within a campaign |
| Campaign dependency graph | G, H | Campaign sequencing, overlap ownership |
| Translation policy and glossary seed | I | Translation |
| Pilot selection | J | Calibration (gold sample, reference translations) |
| Definition of done | K | Campaign QA gate |

---

## Part A — Domains

> *Why: the domain is the top-level partition of the vault. Domains are learned
> separately but queried together, so the boundaries decide what gets built when.*

### How to decide what is a domain and what is a subdomain

Do not try to settle this by subject matter — that argument has no end. Decide it by
**which artifacts the pipeline would have to duplicate.** Each domain gets exactly one
of each of these:

- a scope card (what belongs, what does not)
- a glossary and translation policy
- a trust map (which sources win when documents disagree)
- a concept namespace in the wiki
- an acceptance test (the questions it must answer)

**The test:** if two candidate areas would share all five, they are **one domain with two
subdomains**. If they would genuinely need different glossaries, different reading
conventions, and different trust maps, they are **two domains**.

Three corollaries that resolve most arguments:

1. **Size is not a criterion.** A domain that is too big to process at once stays one
   domain and is processed in several ordered work units. Splitting a domain to make it
   smaller duplicates its shared core, which is the outcome you least want.
2. **"You need A to understand B" means A and B are in the same domain**, ordered
   foundational-first — or A is a separate domain that B *hard-depends* on (A6). Mutual
   prerequisite knowledge is the strongest evidence of a single domain.
3. **Teams are not domains, and depth is not a domain.** Several teams may work across
   the same domain, and the same domain may be known at different depths by different
   audiences. Depth is recorded per note as a knowledge level, never as a separate
   domain — otherwise the same concept exists twice.
4. **If comparing two things is a primary use case, they belong in one namespace.**
   Comparison across domains is a join; comparison inside a domain is a lookup. Never
   split apart the very things the team exists to compare.

### Subject domains versus system domains

Most corpora contain two different kinds of knowledge, and separating them is usually
the highest-value cut available:

- **Subject domains** describe external reality — the things being studied. Test:
  *would this still be true if we replaced our own systems tomorrow?* If yes, it is
  subject knowledge.
- **System domains** describe the organization's own machinery — collection, processing,
  storage, tooling, outputs. Test: *would this fact change if we rebuilt our stack?* If
  yes, it is system knowledge.

**Do not mirror one into the other.** It is common to find that the system's structure
echoes the subject's structure (a processing path per subject family, a tool per subject
area). Resist creating a shadow domain per subject inside the system half: the shadows
duplicate the subject vocabulary and then drift out of step with it. Keep **one** system
domain per lifecycle stage, and have its notes **link** to the subject concepts they
handle. The insight that "understanding our processing deepens understanding of the
subject" is real, and it is delivered by those links and by joint querying — not by
parallel hierarchies.

### Cross-cutting domains: split the core from the body

Some domains touch everything (collection sources, device or platform knowledge,
shared infrastructure). Treating such a domain as a prerequisite for every other domain
front-loads an enormous amount of work; treating it as purely enriching lets avoidable
misreadings through. Split it instead:

- a **small prerequisite core** — the minimum without which other domains' documents
  would be misread (typically 5–15% of the domain), ingested early
- the **enriching body** — the rest, ingested on its own schedule, connected by links

### Foundations domain

If several domains share genuinely common concepts that none of them owns naturally,
create one small **foundations** domain for them. Keep it disciplined with a
promotion-only rule: a concept moves to foundations when **two or more domains need it
and neither is its natural home** — never by default. Started otherwise, it becomes a
dumping ground.

### A1 — What domains does the vault need to cover?
Build this list from **several independent angles**, not one pass — the point is to catch
what a single top-down attempt forgets. Work through each angle, then merge:

- **From the business:** what does this campaign do, what are its outputs and missions?
- **From the corpus:** what do the source folders, space trees, and recurring title terms
  cluster into? Include clusters that match no domain you had thought of.
- **From the people:** what does each team or expert know, and what do they get asked?
- **From the questions:** what do people actually come to this team to find out?

| Domain | One-line description | Found via | In scope? |
|--------|---------------------|-----------|-----------|
| | | | |

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

## Part B — Sources and trust

> *Why: trust comes from where a document came from, not from a model's opinion of it.
> This map is what resolves contradictions between documents later.*

### B1 — What sources feed this corpus?
One row per source: a Confluence space, a file-share directory tree, a mailbox export,
a document library.

| Source | What it is | Rough volume | Owner |
|--------|-----------|--------------|-------|

### B2 — Assign each source category a trust tier.
Starter ladder — adapt the labels, keep the ordering meaningful:

| Tier | Meaning | Typical sources |
|------|---------|----------------|
| T1 | Global authority — external standards, manufacturer specifications | |
| T2 | Verified internal — approved procedures, controlled documents | |
| T3 | Expert analysis — academic essays, research summaries, opinionated but rigorous | |
| T4 | Team knowledge — internal notes, wiki pages, summaries | |
| T5 | Informal — emails, chat exports, drafts, scratch notes | |

### B3 — When two documents contradict each other, what should happen?
Default rule is "higher tier wins, and the conflict is recorded in the note." Say where
that default is wrong. For example: does recent team knowledge override an older
standard when the standard is known to be outdated in practice?

### B4 — Are there sources that are authoritative for one subject but unreliable for others?
Name them and the split. This is common with vendor documentation.

---

## Part C — Scope boundaries

> *Why: this becomes the scope card the filter's judge reads for every document. Concrete
> examples work far better than abstract criteria.*

### C1 — In one paragraph per domain: what does a document have to be about to belong?

### C2 — Give 5–10 examples of documents that clearly BELONG.
Titles or paths, with a word on why.

### C3 — Give 5–10 examples of documents that clearly DO NOT belong.
Titles or paths, with a word on why. Include the tempting near-misses — documents that
look relevant but aren't.

### C4 — What subjects sit right on the boundary?
The cases where you would want to be asked rather than have the pipeline decide.

---

## Part D — Corpus quirks and known junk

> *Why: every pattern named here becomes a deterministic filter rule, which is cheaper
> and more reliable than asking a model.*

### D1 — What kinds of pages carry no knowledge at all?
Examples from this corpus: case-ID pages with a UUID title and no body, navigation and
index pages, blank templates, attachment stubs, archived duplicates.

| Pattern | How to recognize it | Rough share of corpus |
|---------|--------------------|-----------------------|

### D2 — Are there systematic conversion defects?
Text reversal or layout corruption, mangled tables, dropped images, unconverted macros,
encoding damage. **Attach or link 3–5 real examples of each** — these become the test
fixtures for the filter and the repair code.

### D3 — Is there heavy duplication, and where does it come from?
Page copies, exported versions of the same document, templates reused verbatim,
attachments duplicated across spaces. Which copy should win — newest, longest, a
particular location?

### D4 — Are there documents that must never be filtered out, whatever the rules say?
An explicit protect list. Filters check it before anything else.

---

## Part E — Document types

> *Why: the type decides how a document is read — what assumptions to make, how literally
> to take it. The list is frozen before classification starts and grows only by review.*

### E1 — What document types do you expect to find?
Think about how you would *read* each type differently, not about file formats.

| Type | How it should be read | Typical trust tier | Example from the corpus |
|------|----------------------|-------------------|------------------------|

### E2 — Which types carry durable knowledge, and which are ephemeral coordination?
Ephemeral types (logistics, scheduling, announcements) may be filtered or ingested at
low priority. Say which is which.

### E3 — Are there types where only part of the document matters?
For example: meeting minutes where only decisions matter, or reports where only the
findings section is durable.

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

## Part G — Overlaps between campaigns

> *Why: two sources covering the same subject is the main risk of duplicate or
> contradictory notes. Deciding ownership up front turns the overlap into the
> connection that makes cross-domain querying work.*

### G1 — Which pairs of domains or sources cover overlapping subject matter?

| A | B | What overlaps | Which should be ingested first | Why |
|---|---|--------------|-------------------------------|-----|

### G2 — For each overlap, what should happen when the second campaign arrives?
The default is: the existing note is extended, sources are added, and any disagreement
is flagged for you. Say where that is wrong.

### G3 — Are there concepts that genuinely mean different things in different domains?
Same word, different meaning. These must stay as separate notes, and the pipeline needs
to know so it doesn't merge them.

---

## Part H — Campaigns and sequencing

> *Why: a campaign is one unit of work — filtered, translated, classified, ingested, and
> checked as a batch. Their order is the project plan.*

### H1 — Define the campaigns.
A campaign is usually one domain, sometimes one source, sometimes a slice of both.

| Campaign | Definition (which documents) | Rough volume | Depends on |
|----------|------------------------------|--------------|-----------|

### H2 — What is the order, and what forces it?
Dependencies from F and G, expert availability, client priority.

### H3 — Which campaign is the pilot, and why?
Pick one that is valuable enough to prove the system and small enough to finish.

### H4 — What is the deadline or demo pressure, if any?

---

## Part I — Language and terminology

> *Why: this becomes the translation policy and the first glossary. Getting it wrong
> means re-translating the corpus later.*

### I1 — Which terms must stay in the source language?
Terms where translating would lose meaning or break searchability: product names,
internal project names, standard identifiers, part numbers.

| Term | Why it stays | Preferred rendering |
|------|-------------|--------------------|

### I2 — Which terms have an established English equivalent that must be used?
The start of the glossary. Add as many as you can now — every term answered here is a
question the pipeline will not have to ask later.

| Source term | English | Notes |
|-------------|---------|-------|

### I3 — How should acronyms be handled?
Expanded on first use, kept as-is, translated? Are there acronyms that collide with
common English ones?

### I4 — Are there terms used inconsistently across sources?
Where two teams call the same thing different names, or the same name means different
things. Name the canonical form.

### I5 — Any conventions for units, dates, standards references, or numbers?

---

## Part J — Pilot selection

> *Why: calibration needs a small, representative set. These choices determine how well
> every automated threshold is tuned.*

### J1 — Pick 3–5 documents for reference translation.
They should span the genres in E1 — one formal specification, one analytical document,
one team-knowledge page, one informal thread. The expert translates these carefully
(drafting with a model is fine, but review every line); they become the style ground
truth.

| Document | Genre it represents |
|----------|--------------------|

### J2 — Can you label a sample of ~100 documents as in-scope or out-of-scope?
This is what tunes the filter. Documents should be drawn across sources and include
borderline cases, not just obvious ones.

### J3 — Name 5–10 questions the vault must answer correctly for the pilot domain.
With the answers you expect. These become the campaign's acceptance test.

| Question | Expected answer | Source document |
|----------|----------------|-----------------|

---

## Part K — Definition of done

### K1 — What does "this campaign is finished" mean?
Coverage, question accuracy, remaining review queue depth?

### K2 — What would make you say the vault is working?

### K3 — What would make you say it is not?
The failure you would most want to catch early.

---

## Sign-off

| Field | Value |
|-------|-------|
| Domain expert | |
| Pipeline operator | |
| Date completed | |
| Version | 1 |

Unanswered questions and `TBD`s are listed here, with what would resolve each:

| ID | Blocked on | Owner |
|----|-----------|-------|
