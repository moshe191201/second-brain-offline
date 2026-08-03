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

### A1 — What domains does this team's knowledge cover?
List them with a one-line description each. A domain is a body of knowledge someone
could be expert in, not an organizational unit.

| Domain | One-line description | In scope for the vault? |
|--------|---------------------|------------------------|
| | | |

### A2 — For each in-scope domain, what subdomains does it break into?
Only go one level down. If a subdomain feels like it could stand alone as a domain,
say so.

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
