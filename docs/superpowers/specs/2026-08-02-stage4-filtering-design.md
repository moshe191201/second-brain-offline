# Stage 4 — Entry Filtering (Design)

**Date:** 2026-08-02
**Status:** Proposed
**Parent:** `2026-08-02-client-ingest-pipeline-design.md` (backbone approved)
**Scope:** The corpus-wide entry filter that runs over `raw_md/` before any campaign
work. Decides, per document, whether it enters the pipeline at all.

## Purpose

Remove documents that carry no durable knowledge for the vault (case-ID pages, empty
shells, navigation and template debris, data dumps, duplicates) and route genuinely
uncertain cases to the domain expert — cheaply, before translation spends money and
expert time. Every decision is recorded with its evidence so the filter itself can be
analyzed and tuned later.

## Non-goals

- **No security or prompt-injection screening.** Client decision (2026-08-02): the
  corpus is trusted content from trusted authors on a permissioned platform inside an
  air gap. Do not add screening here.
- **No composite filter score.** Client decision (2026-08-02): decisions are binary;
  uncertainty routes to a human instead of accumulating into a number.
- **No classification.** Stage 4 answers "does this belong in the vault at all?" — not
  which domain, type, or trust tier it is. Coarse domain routing is a separate step.
- **No file moves.** Stage 4 writes decisions to the ledger. Folder views are generated.

## Decision model

Three lanes, all binary:

| Lane | Who decides | Effect when it fires |
|------|-------------|----------------------|
| `gate` | Deterministic code | Auto-reject with a reason code. No human pre-approval. |
| `evidence` | Deterministic code | Records a measurement. Never decides alone. Feeds the judge and the review card. |
| `judge` | MiniMax M2.7, binary rubric | `in` stands, `out` stands, `cant_tell` → expert queue. Low-confidence → expert queue. |

Gates run first and short-circuit: a gated document never reaches gist translation or
the judge. Evidence measurements are computed for every surviving document regardless of
whether anything fires, because their absence is informative to the reviewer too.

Rejections are never destructive. A rejected document keeps its ledger row, its
evidence, and its artifacts; "rejected" is a state, not a deletion.

## Order of operations

1. **Exact-duplicate collapse** — content hash. Duplicates are gated as
   `duplicate_of=<doc_id>`, not as irrelevant.
2. **Gates** — cheap deterministic rejects (below).
3. **Near-duplicate collapse** — MinHash LSH over 5-gram shingles across survivors.
   Canonical = newest export version, tie-break longest. Losers gated as
   `superseded_by=<doc_id>`.
4. **Evidence pass** — structural measurements on survivors.
5. **Gist translation** — Hebrew → English for the title *and* a lead excerpt (first
   ~600 chars of body prose, after markup stripping). Titles alone are known to be
   non-indicative in this corpus; the excerpt is mandatory, not optional.
6. **Judge** — binary rubric verdicts on gist + evidence.
7. **Routing** — accept / reject / expert queue; ledger events; batch report.

## Module layout

```
scripts/filters/
  __init__.py
  filters.py      # every deterministic filter + the registry
  judges.py       # judge rubrics and the MiniMax call contract
  FILTERS.md      # human documentation: what each filter catches, why, thresholds, judgements
  fixtures/       # per-filter keep/reject examples used as tests
```

### `filters.py` contract

One module holds all filters. Each is a plain function registered with metadata:

```python
Lane = Literal["gate", "evidence"]

@dataclass(frozen=True)
class Doc:
    doc_id: str
    title: str
    text: str          # raw_md content
    source_path: str

@dataclass(frozen=True)
class FilterDecision:
    filter_id: str
    version: int
    lane: Lane
    fired: bool
    measures: dict[str, float | int | str]   # the numbers behind the verdict
    samples: tuple[str, ...] = ()            # short excerpts that triggered it

@register(id="guid_filename_coverage", lane="gate", version=1)
def guid_filename_coverage(doc: Doc) -> FilterDecision:
    """One-line summary mirrored into FILTERS.md."""
```

Rules the contract enforces:

- **One filter, one concern.** No fused predicates (see MR critique below).
- **Always return measures**, even when `fired` is False. The measured value is what
  makes threshold tuning possible after the fact.
- **Filters are pure** — no I/O, no DB, no network. The runner handles persistence.
- **Version integers.** Changing a filter's logic or threshold requires bumping
  `version`; the ledger stores `filter_id@version`, so stale decisions recompute
  automatically on the next run. (The MR's filter stage stores no version and no
  instruction hash, so edited filter logic silently reuses old verdicts.)
- **Thresholds live in one `THRESHOLDS` dict** with per-campaign overrides, each entry
  documented in FILTERS.md with how it was derived.

### `FILTERS.md` contract

Hand-written, expert-readable. One section per filter and per judge:
ID · lane · what it catches · why it matters for this corpus · threshold and its
derivation · keep/reject examples · version history. A test asserts every registered
ID appears in FILTERS.md and vice versa, so documentation cannot drift out of sync.

## Filter catalog v1

Derived from the client's existing pipeline plus the corpus problems named in design
discussion. Thresholds marked *(fit)* are set from the Phase-0 gold sample, not guessed.

**Gates**

| ID | Catches | Notes |
|----|---------|-------|
| `exact_duplicate` | Identical content hash | Records `duplicate_of` |
| `near_duplicate` | MinHash similarity ≥ 0.9 *(fit)* | Records `superseded_by` |
| `whole_doc_json` | Body parses as JSON | Split out of the MR's fused check |
| `whole_doc_xml` | Body parses as XML | Split out of the MR's fused check |
| `fenced_data_only` | Body is a single json/xml code fence | Split out of the MR's fused check |
| `guid_filename_coverage` | GUID + filename spans cover ≥ 0.80 *(fit)* of non-whitespace | The MR's best piece; keep its merged-span logic |
| `uuid_title_thin_body` | UUID-shaped title + body under floor | The case-page class named by the client |
| `empty_shell` | Body under floor after stripping markup, links, boilerplate | |
| `attachment_stub` | Body is only "see attachment" + filename | |

**Evidence**

| ID | Measures |
|----|----------|
| `hex_char_ratio` | Hex-character density (see MR critique — evidence, not a gate) |
| `numeric_table_heavy` | Digit/table density; protects legitimate spec tables from `hex_char_ratio` |
| `nav_page` | Link density vs prose characters |
| `toc_page` | Heading-to-prose ratio, child-page listing shape |
| `template_page` | Similarity to known blank-template exemplars |
| `macro_debris` | Ratio of unconverted Confluence macro markup |
| `rtl_corruption` | Reversed-word/sentence indicators — **pending client examples** |
| `encoding_slop` | Mojibake and replacement-character density |
| `archive_marker` | Archive/deprecated markers in title or header |
| `prose_density` | Sentence-like prose per total characters — the general "is there content here" measure |

## Judges

Two to start, both binary, both fed gist title + gist excerpt + the evidence
measurements:

- **`domain_scope`** — "Does this document record knowledge inside the scope below?"
  against the campaign's scope card. Answers: `in` / `out` / `cant_tell`. This is the
  check no deterministic rule can make: a perfectly well-formed document about an
  out-of-scope subject.
- **`durable_knowledge`** — "Does this teach or record something durable, or is it
  purely ephemeral coordination (logistics, announcements, chatter)?" Same answer set.

Contract: answers come from a fixed token set; anything unparseable is treated as
`cant_tell` and queued, never guessed. Rubric text lives in `judges.py` and is
documented in FILTERS.md; it is hashed into the ledger so rubric edits invalidate
affected verdicts.

## Human review

Review cards are generated markdown, batched (~50 docs), Obsidian-friendly. Each card
shows: gist title, gist excerpt, source path, which filters fired with their measured
values, judge verdict and confidence, and a one-character decision field
(`K`eep / `R`eject / `D` + domain code for re-routing). A parser writes decisions back
to the ledger with `decided_by: human`.

Batches are ordered by campaign priority, then by judge uncertainty — the least
confident cases first, since those teach the most about where the rubric is weak.

The client's existing repo has a queue mechanism (per-item markdown files with editable
frontmatter, `list`/`apply`/`clean` CLI). It is a candidate to adapt when shared
pipeline infrastructure is designed; stage 4 does not depend on that decision.

## Audit sampling

Each batch sends ~5% of *rejects* (both gate and judge) to the expert as an audit
sample, mixed into the normal review queue and marked as audit. At expected volumes
this is a handful of cards per batch. False-reject rate is reported per filter; the
rate may taper to 1% once several batches come back clean. This is the only safety net
for auto-rejects, so it does not get skipped.

## Calibration (Phase 0)

Before the filter runs corpus-wide, the expert labels a stratified sample (~100 docs):
relevant yes/no, plus coarse domain. Then:

1. Every gate is checked against the labels. A gate that rejects anything the expert
   kept is demoted to evidence or fixed — gates must be effectively zero false-reject.
2. `(fit)` thresholds are chosen from the sample's own measure distributions, not
   imported constants.
3. Judge agreement rates set how much the judge is trusted; disagreement bands become
   the queue-routing boundary.
4. The labeled sample is kept as the standing regression test for the filter, runnable
   inside the gap whenever filters change.

## Outputs

- **Ledger events** — one event per filter decision (`doc_id, filter_id@version, lane,
  fired, measures`), one document-decision event (`doc_decision, decided_by,
  reason_code`), dedup links. "Filter decision" is per filter; "document decision" is
  the accept/reject/queue outcome for the whole document.
- **Batch filter report** — per-filter fire counts, decision breakdown, queue size,
  dedup statistics, audit results, and the measure distributions behind each `(fit)`
  threshold. Generated from ledger events alone.

## Testing

- **Per-filter fixtures** in `fixtures/`: at least one keep and one reject example each,
  drawn from the real corpus (the client's RTL-slop examples land here when provided).
- **Doc coverage test:** registry IDs ↔ FILTERS.md sections.
- **Version discipline test:** changed filter logic without a version bump fails.
- **Gold-sample regression:** filter output vs expert labels, with a false-reject
  ceiling that fails the build.

## Prior art — what stage 4 takes from the client's existing pipeline

The client's `second-brain-offline` PR #1 has a working filtering stage. It is
explicitly a quick-and-dirty prototype; stage 4 takes its *knowledge*, not its code.

**Taken:**
- The **merged-span coverage technique** in `check_guid_filename_ratio` — collecting
  GUID and filename matches, merging overlapping spans, and measuring coverage against
  non-whitespace characters. This is the right shape for `guid_filename_coverage`.
- The **filename extension list**, including corpus-specific formats (`.32fc`, `.16c`,
  `.32f`, `.one`) — real evidence about what the file-share listings contain.
- The **0.80 coverage threshold** as a starting point, now to be re-fit on the gold
  sample rather than assumed.
- The **JSON/XML/fenced-data detections** as three separate gates.

**Deliberately not taken, with reasons:**
- **The fused predicate.** One function named `check_guid_filename_ratio` actually
  performs five unrelated checks (JSON, XML, fenced data, hex density, span coverage)
  behind a single boolean and a single shared threshold. Nothing downstream can tell
  which check fired, so no tuning or analysis is possible. Stage 4 splits these.
- **The bare boolean return.** The stage stores only `"true"`/`"false"`; measured
  values are discarded. Stage 4 always persists measures.
- **The hex-ratio check as a gate.** Digits are hex characters, so a document that is
  mostly a numeric table — exactly what manufacturer and ISO-like specifications
  contain — can cross the 0.80 threshold and be auto-rejected. In stage 4 hex density
  becomes evidence, paired with `numeric_table_heavy` to distinguish a real data dump
  from a legitimate parameter table. A gate on binary junk, if wanted later, must
  require both very high hex density *and* near-absence of prose.
- **Output deletion on filter.** The stage unlinks the derived output file when a
  document is filtered. This violates the pipeline's immutability and recoverability
  conventions; stage 4 marks state and deletes nothing.
- **No version or instruction hash on the filter stage.** Filter results cache with a
  null instructions hash, so editing filter logic does not invalidate prior verdicts.
  Stage 4 versions every filter and rubric.

## Open inputs

- Client's RTL/Hebrew corruption examples → `rtl_corruption` fixtures and thresholds.
- Confluence macro-debris samples → `macro_debris` patterns.
- Blank-template exemplars → `template_page` similarity baseline.

## Success criteria

- Every rejected document has a reason code, the measures behind it, and is reversible.
- Gates show zero false rejects on the gold sample; the audit sample confirms this on
  live batches.
- Expert queue volume per batch fits the review time actually available.
- Filter behavior is reproducible: same corpus + same filter versions → same decisions.
- The batch report answers "what did the filter do and why" without reading any code.
