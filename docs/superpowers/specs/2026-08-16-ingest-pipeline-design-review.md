# Ingest Pipeline — Design Review & Decision Memo

**Date:** 2026-08-16 · **Scope:** PRs #3, #4, #9, #11, #12 · **Audience:** Moshe + Yoni
**Status:** superseded in part — see the update below. Kept as the decision record.

> ## Update — 2026-08-19
>
> **All five decisions are resolved.** D1 and D3 on 2026-08-16; D2, D4 and D5 since.
>
> | | Resolution |
> |---|---|
> | **D2** glossary enforce vs verify | **Option A, shipped** (PR #9). YAP-root masking with exact occurrence counts, order verification, and hard failure on sentinel loss. §2 below describes the problem it solved. |
> | **D4** the 282 MB | **Neither LFS nor vendoring — deleted outright.** YAP now arrives through the air-gap bundle via `YAP_DIR`. The LFS residue that outlived it was removed in PR #16. |
> | **D5** freeze stage 6 | **Merged, then frozen** (PR #12). No further investment until stages 3 and 5 run on the real corpus. |
>
> Also landed since: chunk-level checkpointing and per-chunk retry (#15), the monorepo split
> into `second_brain_vault_framework` + `ingest-pipeline/` (#16), and GitHub Actions CI with
> boundary guards (#17). That resolves I1, I2, I4, I6, I8, I10, M1, M7 and the `example_vault`
> staleness gap. §8's table carries the per-item status.
>
> **Still open, and now the top of the list: M4 — the air-gap bundle** (§5). It is the only
> item whose failure is discovered on the far side of the gap. §6 (end-to-end testing) and
> M3 (irreversible Hebrew fix) remain accurate and open.
>
> Current state and open work live in `HANDOFF.md`, which supersedes §7's priority grid.

---

## 1. Background

Five PRs landed in one week, built by one author with no review until 15 Aug. Reviews are
posted on each PR; this document is the system-level view that no single PR review could give.

**What we agreed the pipeline should be:** not fully deterministic translation — that was judged
overkill — but **100% correctness on domain-specific terms**, driven by a large hand-built
glossary being assembled inside the gap.

**The design principle the author chose** is *preservation-by-verification*: instead of replacing
fragile spans with sentinels before translation, extract them, show them to the model as
verbatim context, and verify afterwards that they survived. This is the harder path and it is
mostly the right one — sentinels destroy the grammatical context Hebrew translation needs, and
a dropped sentinel fails silently, whereas a failed verification is loud and recoverable.

The engineering craft inside each script is good: ordered-invariant verification (catches an LLM
that reorders a document while preserving every token), instrumented fix rounds, a three-state
terminal enum (`completed` / `blocked_on_term` / `qa_failed`) so "I don't know" is representable,
content-addressed output, an append-only ledger, and a human gate on terminology.

**The gap is architectural, not craft.** The principle above was applied *uniformly* where the
situation called for splitting it — see §2.

---

## 2. The central problem: verification ≠ guarantee

> **Resolved (D2, PR #9).** The code below is the *old* behaviour, kept because it explains why
> the fix was necessary. `scripts/translation_masking.py` now masks each glossary term to a
> `⟦EN:<id>:<english>⟧` sentinel before translation and restores it after, so the English is
> substituted rather than hoped for. The at-least-once, document-wide check described here —
> under which a term translated correctly once and paraphrased nine times passed — is gone.

Domain terms are handled by injecting the glossary into the prompt:

```python
glossary_block = "Glossary (use these exact renderings):\n" + "\n".join(lines)
```

and then checking afterwards:

```python
if eng in body:
    continue        # pass
```

Three consequences:

1. **At-least-once, document-wide.** A term rendered correctly in paragraph 1 and paraphrased in
   the other nine occurrences **passes**.
2. **Position is never checked.** The English string need only appear *somewhere*.
3. **It asks rather than enforces.** Prompt compliance at `temperature=0.2`, verified by substring.

It also **degrades as the dataset grows** — longer injected glossaries dilute model attention, so
this will feel like "worked at 50 terms, flaky at 500."

The deterministic machinery already exists and is wired only into the mock path:

```
scripts/translate.py:1189
    # Deterministic mock: apply glossary substitutions, wrap Hebrew remainder.
```

**This is the one axis we agreed must be 100%, and it is the one axis that is probabilistic.**

---

## 3. Problems in the current design

### 3A — MVP-blocking (correctness of Yoni's own dataset)

| # | Problem | Example |
|---|---|---|
| ~~M1~~ | ~~Glossary is verified, not enforced~~ | ✅ **resolved (D2, PR #9)** — deterministic masking, exact counts |
| M2 | Glossary gate is all-or-nothing | one `proposed` row blocks *every* document; the tempting unblock is to mass-mark `approved`, which destroys the gate |
| M3 | Hebrew OCR fix is irreversible | raw docling output is not kept beside the fixed file; 3,800 pages are converted **once**, in the gap |
| **M4** | Air-gap dependency bundle unproven | **STILL OPEN — now the single highest priority.** See §5 and its correction. A missing wheel inside the gap is a full stop |
| M5 | Windows-only is a docstring, not a contract | decision accepted (D1) — but nothing enforces or documents it outside one docstring in `hebrew_yap_stemmer.py` |
| **M6** | Stages never run end to end | **STILL OPEN.** Every stage has unit tests (42 framework + 194 pipeline, green on ubuntu/macos/windows); nothing tests that the stages *compose*. See §6 |
| ~~M7~~ | ~~No glossary collision detection~~ | ✅ **resolved** — `check_glossary_collisions` runs at mask time *and* at the gate (`check_glossary.py:89`), so a collision fails before any document is translated |

### 3B — Infra / long-term (reusability, template value)

| # | Problem | Example |
|---|---|---|
| ~~I1~~ | ~~Pipeline lives in root `scripts/` with no project identity~~ | ✅ **resolved (PR #16)** — `ingest-pipeline/` with its own scripts/tests/templates/data/requirements |
| ~~I2~~ | ~~282 MB of binaries in public git history~~ | ✅ **resolved (D4)** — deleted; zero objects matching `deps/yap` in any ref |
| I3 | No contract between stages | #4 writes `translation_seed.csv`, #9 reads it by path convention; nothing versions or validates the handoff |
| ~~I4~~ | ~~No CI on GitHub~~ | ✅ **resolved (PR #17)** — two lanes; found on its first run that `vault upgrade` had never worked on Windows |
| I5 | Glossary schema under-designed | the dataset is the actual asset; schema is 6 columns + an example row — no versioning, provenance, or approval trail |
| ~~I6~~ | ~~`convert_config.json` is a shared god-config at repo root~~ | ✅ **resolved (PR #16)** — moved to `ingest-pipeline/`, out of the framework's way |
| I7 | Module boundaries | **partially open.** `translate.py` is 1,175 lines and the `translation_*.py` split landed, but `call_llm` **still exists in 3 copies** (`translation_llm.py`, `translation_reviewer.py`, `classify/judge.py`) — a protocol fix still has 3 places to miss |
| ~~I8~~ | ~~Model drift unrecorded~~ | ✅ **resolved** — `translate.py` records `model_id` and a `glossary_version` in every terminal ledger event |
| I9 | Unmeasured complexity | 20% kimi-k2.7 reviewer sampling: second model through the gap, no evidence it catches what deterministic QA misses |

---

## 4. Decisions

### ✅ D1 · Windows-only — **RESOLVED 2026-08-16: accepted**

Every machine in the project and in the gap is Windows. The only upside of Linux support was
testing on a Mac, which does not justify the work. PR #4's `yap.exe` and its
`_find_yap_exe` lookup are correct as written.

**Follow-ups this creates:**
- Make it a real contract, not a docstring: state it in the pipeline README, and add a startup
  platform check that fails with a clear message rather than a confusing `FileNotFoundError`.
- CI for the pipeline must use a `windows-latest` runner. The vault framework stays cross-platform.
- **The offline bundle must be built on Windows** — `pip download` on a Mac fetches the wrong
  wheels. See §5.

### ✅ D3 · Repo shape — **RESOLVED 2026-08-16: monorepo, two frameworks**

The ingest pipeline is **not** framework-owned. It is a **separate framework living in the same
repo** — a monorepo with two products. Not payload, not a separate repo.

**Consequences to implement:**

| What | Change |
|---|---|
| Layout | `scripts/` → its own top-level project dir (e.g. `ingest/`) with README, `tests/`, and room for a `pyproject.toml` later |
| Config | `convert_config.json` moves into that project (closes most of I6) |
| `CLAUDE.md` | currently opens *"This repo is the framework, not a vault"* — must become "monorepo, two products", with the layout and the boundary between them |
| **Pure-stdlib rule** | currently reads repo-wide; **must be scoped to the vault framework only.** The pipeline already depends on ~10 packages and that is legitimate |
| Tests | split `tests/` (framework) from `ingest/tests/` (pipeline) |
| CI | two lanes — framework (cross-platform) and pipeline (Windows) |
| payload/manifest | untouched. **I1 closes as won't-do, by design** |

Structure it now so packaging is a later `pyproject.toml` addition, not another file move.

### ✅ D2 · Glossary: enforce or verify? — **RESOLVED: Option A, shipped in PR #9**

| Option | Cost | Result |
|---|---|---|
| **A. Deterministic substitution** (recommended) | ~50 lines, reuses `mask_person_names` machinery | mask term → translate around it → substitute approved English. Genuinely 100% on the agreed axis |
| B. Strengthen verification | ~1 day | count occurrences, check every instance. Still probabilistic; more fix rounds |
| C. Leave as is | 0 | we don't get what we agreed on |

**Recommendation: A.** Everything else stays probabilistic exactly as agreed — this makes
deterministic only the axis we said must be.

> **Outcome:** A, as recommended. `mask_glossary_terms` fails closed if YAP is unavailable, which
> means stage 5 now depends on the YAP stack — see the correction in §5.

### ✅ D4 · The 282 MB — **RESOLVED: deleted entirely, not LFS'd or vendored**

Options: Git LFS · gitignore + vendoring script (the pattern `deps/docling-models/` already uses)
· leave it. **Recommendation: gitignore + vendoring script, before #4 merges.** Unaffected by D1 —
the binaries are the *right* binaries now, but they are still 282 MB of permanent public history.
Also confirm the BGU lexicon and YAP model redistribution terms — the repo is public.

> **Outcome: none of the three.** `deps/yap/` was removed outright and exists in no branch. YAP is
> located at runtime through `YAP_DIR` and crosses the gap in the bundle instead. The redistribution
> question is moot for the repo, but **still applies to whoever assembles the bundle**.
>
> A `.gitattributes` LFS rule for `deps/yap/**` outlived the binaries by two months, along with
> four `git-lfs` hooks that `exit 2` when git-lfs is absent — silently aborting checkouts and
> merges. Removed in PR #16; the hooks are not version-controlled and must be deleted per clone.

### ✅ D5 · Freeze stage 6 (classification, #12)? — **RESOLVED: merged, then frozen**

#12 is the most polished PR and the least connected to the MVP. **Recommendation: merge it, then
freeze.** No further investment until PDF conversion and translation work on the real corpus.

> **Outcome:** merged and frozen, as recommended. One change since, forced by the monorepo split:
> `core.cmd_classify` was framework code reading stage-6 output, so it moved to
> `ingest-pipeline/scripts/classify/validate.py` and `vault classify` left the CLI (PR #16).
> Behaviour is unchanged; the framework simply no longer knows the pipeline exists.

---

## 5. What has to cross the gap (M4)

Yoni owns building and proving this bundle.

> **Correction (2026-08-19).** The paragraph below is **wrong now**, and the way it is wrong is
> the dangerous direction. Implementing D2 made `mask_glossary_terms` call `_require_yap()` and
> **fail closed**, so *stage 5 cannot run at all without the YAP stack* — it is no longer pure
> stdlib and no longer needs "only a reachable LLM endpoint". The dependency surface is not
> confined to stages 3 and 4.
>
> The pip surface is now declared in `ingest-pipeline/requirements.txt` rather than in prose;
> build the bundle from that file, **on Windows**, and note the non-pip pieces listed at the
> bottom of it. Stage 4's `scikit-learn` + `numpy` are guarded at import but not optional in the
> gap: without them subdomain clustering silently returns `num_clusters=0` with the explanation
> buried in output JSON.

The good news from the audit: **stages 3 and 4 carry
the entire dependency surface — PR #9 (translate) and PR #12 (classify) are pure stdlib**, needing
only a reachable LLM endpoint. The heavy lifting is concentrated in conversion and term extraction.

### Python packages

| Package | Needed by | Note |
|---|---|---|
| `pyyaml` | #3 | frontmatter |
| `requests` | #3 | docling-serve HTTP client |
| `pypdfium2` | #3 | page count, splitting, PDF metadata |
| `markitdown` | #3 | `.txt` / `.csv` |
| `extract_msg` | #3 | `.msg` |
| `vsdx` | #3 | Visio |
| `python-docx` | #3 | docx metadata |
| `python-pptx` | #3 | pptx metadata |
| `beautifulsoup4` | #3 | HTML `<title>` |
| `wordfreq` | #3, #4 | pin `==3.1.1`; pulls `regex`, `langcodes`, `msgpack` |
| `scikit-learn` + `numpy` | #4 | **optional** — subdomain clustering only. Drop if unused |

> Transitive dependencies are the real risk — resolve them with a full `pip download`, not by hand.

### Binaries, services, models

| Item | Version | Note |
|---|---|---|
| Python | 3.12, Windows | matches the tested environment |
| `pandoc` | ≥3.0 | HTML/MHT. Hard dependency — #3 fails fast without it |
| `docling-serve` + models | any | ~506 MB bundle + `tessdata` |
| `.NET SDK` | 8.0.424+ | builds the OneNote helper once; published output is self-contained |
| `OfficeIMO.OneNote` | 3.2.2 | NuGet — needs an offline package source |
| YAP + model data | — | `yap.exe` + ~282 MB (`hebmd.b32`, `dep.b64`, `bgulex`) |
| Local LLM server | OpenAI-compatible | vLLM serving `minimax-m2.7`, `kimi-k2.7` |
| Embedding model | — | #12 retrieval filter |
| Label Studio | optional | #12 export target only |

### Building the bundle

1. Build **on Windows**, targeting Windows — `pip download` on macOS fetches the wrong wheels.
2. Include NuGet packages and the docling models, not just pip wheels.
3. **Prove it:** install from the bundle on a clean Windows machine with networking disabled, then
   run the smoke test in §6.3. An untested bundle is not a bundle.

There is an `airgap-pack` skill available that automates steps 1–3.

---

## 6. End-to-end testing

Today every PR has unit tests and **nothing tests that the stages compose.** That is where the
remaining bugs almost certainly are.

### 6.1 Golden corpus (build once, ~half a day)

`ingest/tests/fixtures/e2e_corpus/` — 10–12 small real-shaped documents chosen to cover the seams:

- 1 Hebrew PDF with known-reversed OCR text
- 1 Hebrew DOCX (correct text — must come out **unchanged**; guards the M3 class of bug)
- 1 mixed Hebrew/English with `הAPI`-style proclitics
- 1 with a GFM table + code fence + YAML frontmatter
- 1 `.eml` with an attachment
- 1 English-only doc (must be skipped, not translated)
- 1 duplicate of another file (dedup path)
- 1 containing 3 known glossary terms, each used **5+ times** — this is the M1 detector
- 1 with `קריאה/כתיבה`-style Hebrew slash pairs (invariant-regex class)
- 1 with a person name that is also an org codename

Each with a hand-written expected-output file. **This corpus is the most valuable artifact in the
plan — it outlives every script.**

### 6.2 Stage-boundary assertions

Run `#3 → #4 → #9` in sequence in one test, asserting at each seam:

| Boundary | Assert |
|---|---|
| after #3 | every input has an output or an explicit report entry; no file silently vanishes; the correct-Hebrew DOCX is **unchanged** in its Hebrew content |
| after #4 | `translation_seed.csv` has the expected columns; known domain terms present |
| after #9 | **every glossary term appears the correct number of times**; no `⟦…⟧` sentinel leaks into output; table/heading/code counts match source |
| ledger | exactly one terminal state per document; no document missing |

### 6.3 Two tiers

`--mock` already exists and is sentinel-aware, so the whole chain runs in CI with no model.

- **`smoke`** — mock mode, whole chain, < 60s. Every commit.
- **`e2e`** — real local model. Manually, before entering the gap, and as the bundle acceptance test.

### 6.4 The one-hour version, if nothing else gets done

A batch script that runs the three stages over the 10-doc corpus and diffs against expected output.
No framework, no fixture library. It catches compose-time bugs, which is 90% of the value.

---

## 7. Priority

> **Superseded — see `HANDOFF.md` §8.** The grid below is the 2026-08-16 picture and is kept as
> the record. Everything in the "This week" column is now resolved. The current answer to
> "if you do only one thing" is **M4, the air-gap bundle**.

**Importance ↑ · Urgency →** (urgency = cost of deferring, not how loud it is)

|  | This week | This month | Later |
|---|---|---|---|
| **Critical** | D2 glossary decision · M4 bundle | M1 enforce glossary · M3 keep raw output · M6 e2e run | — |
| **High** | D4 282 MB | M2 per-doc gate · M7 collisions · T1 golden corpus · M5 platform contract | I3 stage contracts |
| **Medium** | D5 freeze #12 | D3 layout move · I4 CI · I8 model_id | I5 glossary schema · I7 modules |
| **Low** | — | I9 measure the kimi reviewer | I6 config split |

**Ownership:** M-items are Yoni's (they protect his dataset). I-items are Moshe's and mostly need
no author time — CI, git history surgery, the `ingest/` move, and repo docs can run in parallel.

**Looks like infra, actually MVP:** D4 (history cost compounds) and I3 in its cheapest form — *one
page* listing what each stage emits and consumes, which is how Yoni avoids breaking #9 when he
changes #4 three weeks from now with nobody watching.

---

## 8. Summary table

| ID | Item | Class | Owner | Effort | Priority |
|---|---|---|---|---|---|
| ~~D1~~ | ~~Windows or Linux~~ | Decision | — | — | ✅ **resolved: Windows-only** |
| ~~D3~~ | ~~Is the pipeline framework-owned~~ | Decision | — | — | ✅ **resolved: monorepo, 2nd framework** |
| ~~D2~~ | ~~Glossary: enforce vs verify~~ | Decision | — | — | ✅ **resolved: enforce (PR #9)** |
| ~~D4~~ | ~~282 MB out of git history~~ | Decision | — | — | ✅ **resolved: deleted outright** |
| ~~D5~~ | ~~Merge #12 then freeze scope~~ | Decision | — | — | ✅ **resolved: merged + frozen** |
| ~~M1~~ | ~~Deterministic glossary substitution~~ | MVP | — | — | ✅ **done (PR #9)** |
| M2 | Per-document glossary gate | MVP | Yoni | ~5 LOC | P1 |
| M3 | Keep raw docling output beside fixed | MVP | Yoni | 0.5 d | **P0** |
| **M4** | Offline bundle, built + proven on Windows | MVP | Yoni | 1 d | **P0 — now the top item** |
| M5 | Windows constraint: README + startup check | MVP | Yoni | 1 h | P1 |
| M6 | One manual end-to-end run | MVP | Yoni | 2 h | **P0** |
| ~~M7~~ | ~~Glossary collision detection~~ | MVP | — | — | ✅ **done** — at mask time and at the gate |
| T1 | Golden 10-doc corpus + expected output | MVP | Yoni | 0.5 d | P1 |
| T2 | `smoke` — mock chain in CI | Infra | Moshe | 0.5 d | P2 |
| ~~I1~~ | ~~Move to `ingest/`~~ | Infra | — | — | ✅ **done (PR #16)** — `ingest-pipeline/` |
| ~~I2~~ | ~~282 MB history surgery~~ | Infra | — | — | ✅ **done (D4)** |
| I3 | One-page stage handoff contract | Infra | Yoni | 1 h | P1 |
| ~~I4~~ | ~~GitHub Actions CI (2 lanes, Windows for pipeline)~~ | Infra | — | — | ✅ **done (PR #17)** |
| I5 | Glossary schema: version + provenance | Infra | Both | 0.5 d | P2 |
| ~~I6~~ | ~~Config into `ingest/`~~ | Infra | — | — | ✅ **done (PR #16)** |
| I7 | Extract verification + shared `call_llm` | Infra | Yoni | 0.5 d | P3 — **partial**: modules split, 3 `call_llm` copies remain |
| ~~I8~~ | ~~Record `model_id` in translation ledger~~ | Infra | — | — | ✅ **done** |
| I9 | Measure or drop the 20% kimi reviewer | Infra | Yoni | 0.5 d | P3 |
| ~~I10~~ | ~~`CLAUDE.md`: monorepo + scope pure-stdlib rule~~ | Infra | — | — | ✅ **done (PR #16)**, and `tests/test_boundary.py` now enforces it |

**P0 = settle or start before the month apart.**

> **As of 2026-08-19:** every Decision is resolved and the only remaining **P0 is M4**, the
> air-gap bundle. Two items were added by work done since and are tracked in `HANDOFF.md`
> rather than here — chunk-level checkpointing (§4.1, fixes 1–2 shipped in PR #15; 3–5 still
> gated on measuring the corpus page-size distribution) and pruning the chunk checkpoint store.
