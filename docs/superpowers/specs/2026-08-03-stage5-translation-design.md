# Stage 5 — Translation (Hebrew → English) with Expert Loop

**Date:** 2026-08-03
**Status:** Proposed
**Parent:** `2026-08-02-client-ingest-pipeline-design.md`
**Scope:** Per-campaign translation of documents that survived stage-4 filtering, from
Hebrew into the English the vault is written in, with the domain expert in the loop.

## Purpose

Produce English source documents faithful enough to build wiki notes from, while
spending expert time on **reusable assets** — a translation policy, a domain glossary,
and approved reference translations — rather than on per-document corrections.

## Non-goals

- **No classification.** Domain, document type, and trust tier are stage 6, after
  translation, on English text.
- **No security screening** (parent spec, client decision).
- **No stylistic polish.** The target is faithful, consistent, greppable technical
  English, not publication prose.
- **No per-document expert translation.** The expert approves assets and adjudicates
  flagged cases; they do not translate the corpus.

## Model routing

Both models are reachable in-gap over the same OpenAI-compatible API as `qmd-api`.

| Job | Model | Why |
|-----|-------|-----|
| Hebrew → English translation | **Dicta-LM 3.0 24B** | Hebrew-specialized open-weight model, already deployed in-gap |
| Gist translation (stage 4 titles/excerpts) | Dicta-LM 3.0 (short prompts) | Same strength, cheap calls |
| Term extraction, English-side QA, question drafting | MiniMax M2.7 or Dicta-LM | English-side work; whichever Phase 0 favors |

Model id, endpoint, and sampling parameters are recorded per translation in the ledger.
A model change invalidates affected translations the same way a policy change does.

## Phase 0 — calibration (before any campaign translates at volume)

### Reference documents

The expert produces **3–5 approved reference translations** spanning the corpus genres
(ISO-like specification, manufacturer document, academic essay, team knowledge page,
email/message thread). Workflow: LLM drafts, expert post-edits thoroughly and manually,
expert approves. Approved references are committed vault artifacts.

**Known bias, and how it is handled.** A reference drafted by model X and post-edited is
partly shaped by X's phrasing. Therefore:

- References are **not** used to rank models against each other.
- References **are** used as style ground truth for the policy document, and to fit the
  QA thresholds in the table below (script ratios, length bands, structural tolerances).
- Divergence from a reference is a **question for the expert**, never an automatic
  error — the reference is one approved rendering, not the only one.

### Model selection (blind)

For a handful of passages, each candidate configuration translates the same source; the
expert rates outputs **blind and side by side** (unlabeled, order shuffled), choosing
better/worse/equivalent and noting why. This avoids the reference-anchoring bias.
Candidates: Dicta-LM 3.0 24B at two prompt/temperature settings, MiniMax M2.7 as a
baseline, and (if available) Dicta-LM 12B for throughput comparison. Record the winner
and the ratings; re-run when a model version changes.

### Threshold fitting

The approved references supply the distributions behind every `(fit)` threshold in the
QA gate: residual-Hebrew ratio band, length-ratio band, structural tolerances.

## Expert-authored assets

All three are versioned vault artifacts, hashed into the ledger. A version bump marks
affected documents stale and schedules re-translation.

1. **Translation policy** (`campaigns/<campaign>/translation-policy.md`) — which terms
   stay Hebrew or transliterated versus translated; acronym handling; heading treatment;
   units, standards, and part-number references; org-internal names; how to render
   quoted or embedded English. One policy per domain; a campaign inherits and may
   override.
2. **Glossary** (`campaigns/<campaign>/glossary.md`) — one row per term:
   `term_he | english | notes | status (approved|proposed|keep_source) | first_seen_doc | approved_by | version_added`.
3. **Reference translations** (`campaigns/<campaign>/references/`).

## Glossary bootstrapping (front-loaded, not discovered per document)

Before a campaign translates anything:

1. A term-extraction pass over the campaign's Hebrew documents produces candidate terms
   ranked by **corpus frequency** and document spread (a term in 50 documents outranks
   one in 2), using frequency, acronym and quoted-string patterns, and out-of-vocabulary
   heuristics.
2. The expert defines the top slice in one sitting — this is the single highest-leverage
   hour in the stage.
3. Remaining unknowns surface during translation through the question queue below.

This replaces reactive, per-document term discovery: a term is answered once, before it
interrupts fifty documents.

## Translation execution

- **Structural chunking.** Split at heading boundaries; if a section exceeds the token
  budget, split at paragraph boundaries. Never split mid-sentence, mid-table, or
  mid-code-block. Fixed-character windows are not used.
- **Context header per chunk:** translated document title, section path, and the
  glossary entries whose terms occur in this chunk. The previous chunk's final paragraph
  may be supplied as context, explicitly marked as context-only, not to be re-emitted.
- **Structured output.** Both endpoints are OpenAI-compatible, so the model returns JSON
  (`translation`, `unknown_terms[]`, `notes[]`) rather than prose with sentinel strings
  to be regex-parsed.
- **Zero-guessing rule.** An unknown or ambiguous term is never invented. The model
  reports it in `unknown_terms`; the chunk is translated with the term preserved inline
  as `⟦he:<term>⟧` — greppable, countable, and resolvable later by a glossary pass. A
  document containing markers is translated and QA-checked but cannot pass to stage 6
  until its markers resolve or the expert accepts them.
- **RTL corruption** is detected deterministically in stage 4 (`rtl_corruption`
  evidence) and repaired before translation. The model is not asked to self-report
  corruption; see the prototype assessment below.
- **Bounded retries.** Every retry loop has a fixed maximum and records attempts; on
  exhaustion the document is quarantined for review, never silently re-attempted.

## Question queue

- **One question per term, per campaign** — deduplicated across documents, ranked by
  frequency and by how many documents it blocks.
- Documents waiting on a term sit in `blocked_on_term`, a normal state, not a failure.
- Answering a term bumps the glossary version and unblocks every waiting document in one
  batch re-run.
- Questions are delivered in the same plain-markdown packet format as the review packets
  below, with the term, its English gloss candidates if any, 2–3 real context sentences
  from different documents, occurrence count, and an answer box.

## QA gate (deterministic, runs on every translation)

Per the research finding that deterministic checks outperform an LLM judge, the battery
is scripted and the model does not grade itself.

| Check | Catches | Threshold |
|-------|---------|-----------|
| `residual_hebrew_ratio` | Untranslated spans; over-literal retention | Band *(fit)* per paragraph and per document |
| `untranslated_block` | Whole paragraphs left in Hebrew | Zero tolerance outside `⟦he:⟧` markers |
| `glossary_retention` | Glossary term rendered against the glossary | 100% |
| `glossary_consistency` | Same source term rendered differently across the campaign | 100% |
| `forbidden_term` | Renderings the policy explicitly bans | Zero |
| `heading_fidelity` | Heading count and nesting preserved | Exact |
| `structure_fidelity` | List item counts, table rows/columns, code blocks preserved | Exact |
| `numeric_fidelity` | Numbers, units, part numbers, standard references preserved | Exact |
| `length_ratio` | Truncation or hallucinated expansion | Band *(fit)* |
| `markup_integrity` | Broken markdown, orphaned fences, lost links | Zero |
| `marker_count` | Count of unresolved `⟦he:⟧` markers | Reported; gates stage 6 |

Any failure quarantines the document into the review queue. Nothing reaches the vault on
a failed gate.

## Reference-free sampling (AskQE-style)

On a sample per batch: generate questions from the Hebrew source, answer them from the
English translation, and compare answers. Divergence indicates dropped or distorted
content that structural checks cannot see. Sample size is set by batch size and
available throughput; findings route to the expert queue as flags, not auto-rejections.

## Expert review packets

Plain markdown files with answer boxes plus a parser — deliberately not a tool requiring
accounts, permissions, or write access. (A comparable production project lost two weeks
when review questions were delivered as issue checkboxes their reviewer lacked
permission to tick.)

Every flag resolves to exactly one disposition:

| Disposition | Effect |
|-------------|--------|
| `glossary` | New or corrected glossary entry; glossary version bumps |
| `policy` | Translation policy rule change; policy version bumps |
| `accept` | Accepted as-is, with a recorded rationale |

Asset version bumps mark affected documents stale; the ledger answers "which documents
used glossary v3?" as a query, and re-translation is scheduled automatically. The expert
never re-reviews an unchanged document.

## Artifacts and ledger events

- **Artifact:** English translation written to the content-addressed store, with
  frontmatter recording `source_doc_id`, source content hash, model id and parameters,
  policy version, glossary version, QA results, and marker count. The Hebrew source
  remains the provenance anchor and stays reachable.
- **Events:** `translation_started/completed` (with asset versions), `qa_result` per
  check, `blocked_on_term`, `question_asked/answered`, `disposition_recorded`,
  `retranslation_scheduled` with its cause.
- **Batch report:** QA pass rates per check, marker counts, glossary growth, question
  queue depth and age, blocked-document counts, re-translation volume.

## Testing

- **Fixture documents** exercising each QA check: a document with an untranslated
  paragraph, a dropped table, a glossary violation, an inconsistent term rendering, a
  truncated tail.
- **Seeded-error runs:** inject known errors into an approved reference translation and
  confirm the QA gate catches each one. This tests the tests.
- **Reference regression:** re-translating a reference source must stay within the fitted
  bands; drift means a model, policy, or prompt changed.
- **Determinism:** same source, same asset versions, same model parameters → same QA
  verdicts.

## Assessment of the client prototype's translation stage

Assessed after this design, per the parent spec's reference-only policy.

**Worth adopting (as concepts, reimplemented):**
- **Glossary filtering to entries relevant to the current document** before injection —
  keeps prompts small and focused. Directly reusable idea.
- **The zero-guessing clarification principle** — unknown terms stop the guess and ask a
  human. This design keeps the principle and changes the plumbing (dedup by term, inline
  markers, structured output).
- **Instruction-hash cache invalidation** — extended here to policy version, glossary
  version, and model id.
- **The Hebrew layout repair function** (`fix_hebrew_layout`) — corpus-specific work
  that already exists and should be salvaged as the repair half of stage 4's
  `rtl_corruption` handling.

**Not adopted, with reasons:**
- **Model-reported RTL corruption** (the `RTL_STATUS:` prefix protocol). Asking a weak
  model to self-diagnose layout corruption is exactly the judgement call the research
  says to make deterministic. Detection moves to a scripted stage-4 check; the repair
  function stays.
- **RTL detection on a 2000-character sample for long documents.** Corruption later in a
  long document is missed entirely, and the sample check runs on a different code path
  than the chunk loop that follows.
- **Fixed 4000-character chunking**, which splits mid-section and mid-sentence and
  destroys the context the translation needs. Replaced with structural chunking.
- **Regex-parsed freeform model output** (`Clarification Required`, `Term/Issue:`,
  `Context:`). Both endpoints support structured output; sentinel-string parsing fails
  silently when the model phrases things differently.
- **The rejected-review fallback that instructs the model to translate unknown terms
  "to the best of your ability."** This puts silently guessed domain terminology into
  the vault with no marker — the single most dangerous behavior for a knowledge base
  whose value is terminological precision. Replaced by `⟦he:⟧` markers, which are
  visible, countable, and resolvable.
- **Unbounded `while True` retry loops** around model calls.
- **Overwritable output files and DB-blob storage** for translations, which conflict
  with the immutability and content-addressed-store conventions.

## Open inputs

- Expert availability for the Phase 0 reference set and the glossary bootstrap sitting.
- Dicta-LM 3.0 endpoint parameters (context window, throughput) to size chunk budgets
  and batch scheduling.
- Whether Dicta-LM 12B is also available, for a throughput/quality trade-off option.

## Success criteria

- Phase 0 produces: a chosen model configuration with blind expert ratings, 3–5 approved
  references, a v1 policy, and a bootstrapped glossary.
- No silently guessed terminology reaches the vault — every unresolved term is a marker
  or a queued question.
- Expert time is spent on assets and adjudications; per-document correction volume
  trends down as glossary coverage rises.
- Every translation is reproducible from its recorded source hash, model, policy
  version, and glossary version.
- A glossary or policy change re-translates exactly the affected documents, identified
  by ledger query.
