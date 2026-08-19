# HANDOFF — Ingest Pipeline

**Written:** 2026-08-18 · **Updated:** 2026-08-18 (§4.1 fixes 1–2 landed) · **For:** a fresh
session picking up this work cold.
**Companion doc:** `docs/superpowers/specs/2026-08-16-ingest-pipeline-design-review.md`
(partly stale — see §7 below before trusting it).

---

## 1. Context

`moshe191201/second-brain-offline` is a **public monorepo containing two products**:

1. **`second_brain_vault_framework`** — a pip package (`vault` CLI) that lays a "payload" of files
   into user-owned Obsidian vaults. Pure stdlib, cross-platform.
2. **The ingest pipeline** — a four-stage Hebrew document pipeline living in root `scripts/`.
   **Windows-only. Not pure stdlib.** Not delivered via the payload.

The pipeline processes a ~3,800-page Hebrew Confluence corpus **inside an air gap**:

```
raw/  --[3] convert-->  raw_md/  --[4] terms-->  glossary  --[5] translate-->  English  --[6] classify-->  domains
```

| Stage | Script | Purpose |
|---|---|---|
| 3 | `scripts/convert_to_md.py` | PDF/DOCX/PPTX/HTML/email/VSDX/OneNote → markdown, + Hebrew OCR-reversal fix, dedup |
| 4 | `scripts/extract_domain_terms.py` | deterministic domain-term extraction (wordfreq ratios + YAP roots) |
| 5 | `scripts/translate.py` + `translation_*.py` | Hebrew→English with deterministic glossary masking |
| 6 | `scripts/classify/` + `core.py:cmd_classify` | subdomain classification against a frozen taxonomy |

**People.** Moshe (repo owner) and Yoni (domain expert, authored all the pipeline code). Yoni's
programming background is self-taught Python scripting and LLM work — strong instincts and very
problem-oriented, less experience with system design, contracts between components, and delivery.
He works **alone for ~1 month** starting now, inside the gap.

**The agreed goal.** Fully deterministic translation was judged overkill. What matters is
**100% correctness on domain-specific terms**, driven by a large hand-built glossary Yoni is
assembling in the gap. Everything else can be probabilistic with verification.

---

## 2. Current state

**All PRs are merged. Zero open.** `main` is at `a374970`.

| PR | Outcome |
|---|---|
| #3 conversion pipeline | merged |
| #4 domain terms | closed (broken history) → replaced by #13 |
| #9 translation + deterministic glossary | merged |
| #11 Hebrew presentation deck | merged |
| #12 classification | merged |
| #13 domain terms | merged |
| #15 chunk checkpointing (§4.1 fixes 1–2) | merged |

Verification on `main` right now:

```bash
PYTHONPATH=src python3 -m second_brain_vault_framework.cli check example_vault
# VAULT LINT: OK — no findings  [43 notes checked]

PYTHONPATH=src python3 -m unittest discover -s tests        # framework
# Ran 42 tests — OK          <- needs NOTHING installed

cd ingest-pipeline && python3 -m unittest discover -s tests  # pipeline
# Ran 194 tests — OK (skipped=2)   <- needs requirements.txt; skips are YAP
```

Both suites are green on all of ubuntu/macos/windows x py3.11/3.12 in CI. The old
"6 modules fail to import and 67 tests silently vanish" trap is gone with the split (§4.4).

**The headline win:** glossary handling went from "inject into the prompt, then check the English
appears *somewhere* in the document" (at-least-once, document-wide — a term translated right once
and paraphrased nine times passed) to YAP-root masking with **exact occurrence counts, order
verification, and hard failure on sentinel loss**. That was the one place the system could not
deliver the agreed goal. It now does.

---

## 3. Decisions already made — do not relitigate

| ID | Decision | Notes |
|---|---|---|
| **D1** | **Windows-only.** No Linux/macOS support for the pipeline. | Every machine in the project and the gap is Windows. Only upside of Linux was testing on a Mac; not worth it. `yap.exe` and its lookup are correct as written. |
| **D2** | **Glossary is enforced, not verified.** | Implemented and merged. Deterministic masking in `scripts/translation_masking.py`. |
| **D3** | **Monorepo, two products.** The pipeline is NOT framework-owned. | It gets its own top-level project dir eventually. It does **not** go in `payload/`/`manifest.json`. |
| **D4** | **282 MB of YAP binaries: removed entirely**, not LFS'd. | `deps/yap/` is in no branch. YAP now arrives via the air-gap bundle using the `YAP_DIR` env var. |
| **D5** | **Stage 6 (classification) is frozen.** | Merged and good. No further investment until stages 3 and 5 work on the real corpus. |

---

## 4. Outstanding work

### P0 — before/while Yoni is in the gap

**4.1 Chunk-level checkpointing for large documents.** — **fixes 1 and 2 DONE (PR #15)**

A 100–200 page PDF becomes 300–600k chars of markdown → **~67 chunks** at `chunk_chars: 6000`.
`translate.py:572` is `for ch in chunks:` — strictly sequential, one LLM call per chunk (two if
the chunk has table cells), plus one YAP subprocess per chunk. The per-chunk work itself now lives
in `_translate_one_chunk`, with `_translate_chunk_with_retry` and the checkpoint lookup around it.

The problem was not speed, it was **all-or-nothing failure**. Both the sentinel check and the
segment delimiter check `raise`, which aborted the entire document:

```python
if len(translated_segments) != len(segs.texts_to_translate):
    raise RuntimeError("Segment count mismatch — model did not preserve delimiters")
```

Across 67 chunks this compounds: at 99% per-chunk reliability a document survived ~51% of the time;
at 95%, ~3%. One dropped delimiter in chunk 43 destroyed ~40 minutes of work. The content-addressed
store skipped completed **documents**, not completed **chunks**, so there was no partial credit.
A failure now costs one chunk; `tests/test_translation_checkpoint.py` pins the 67-chunk case.

Fixes, in value order:

1. ~~Checkpoint each translated chunk in the content-addressed store keyed by chunk hash.~~
   **DONE.** `scripts/translation_checkpoint.py`; chunks land in
   `data/translations/chunks/<key[:2]>/<key>.json`. The key covers chunk text, section path,
   `prev_tail`, a glossary fingerprint, the model, the mock/no-mask flags, a fingerprint of the
   curated person-name lists, and a fingerprint of the pipeline source. Every input is a
   **required** argument — a forgotten one silently replays chunks produced under different
   rules, and the cached output looks perfectly well-formed.
2. ~~Make sentinel loss fail *that chunk* and retry it.~~ **DONE.** `chunk_retries`, default 2,
   resolved CLI `--chunk-retries` > `TRANSLATE_CHUNK_RETRIES` > config, exactly like
   `fix_rounds`. Retries cover **model non-compliance only** — `sentinel lost`,
   `Segment count mismatch`, `Cell count mismatch`. Missing YAP or missing `md_mask` are
   environment faults and stay fail-closed.
3. **STILL OPEN.** Move QA per-chunk where possible. `check_preserved_invariants` currently re-extracts invariants
   from the whole source and does `s not in translation` per invariant — O(invariants × length),
   and since both grow with page count it is effectively **O(pages²)**. It runs once per QA pass,
   and there are up to 4 passes (initial + 3 fix rounds).
4. **STILL OPEN.** Dedupe and index invariants instead of n× substring scans.
5. **STILL OPEN.** Parallelize chunk translation (chunks are independent apart from `prev_tail`).

**Fixes 3–5 are throughput, not survival, and are still gated on measuring the page-size
distribution of the 3,800-page corpus** — which can only be done inside the gap. If 100–200 page
docs are a handful of outliers, fixes 1–2 are enough and 3–5 are not worth the work.

Two follow-ups discovered while implementing 1–2, neither addressed:

- **The QA fix loop still operates on the whole document.** A resumed document replays its chunks
  from checkpoints but then re-runs QA from scratch. Cheap next to 67 LLM calls, but it caps what
  checkpointing buys and it interacts with fix 3 above.
- **Nothing prunes the chunk store.** Editing the glossary or any tracked pipeline module
  invalidates every checkpoint and lays down a fresh generation (~1,500 chunks for the corpus)
  without removing the old one. Disk only — `chunks/` is invisible to consumers, which all
  `rglob("translation.md")` — but unbounded on a machine nobody is watching.

Other deliberate limitations are documented in the `scripts/translation_checkpoint.py` module
docstring (`base_url` is not part of the key; no retry backoff; orphaned `.tmp-*.json` files after
a SIGKILL are never cleaned up).

**4.2 Build and prove the offline dependency bundle.** *(Yoni — worst failure mode on the list)*

Must be built **on Windows** — `pip download` on macOS fetches the wrong wheels, and you only find
out on the far side of the gap.

Python packages: `pyyaml`, `requests`, `pypdfium2`, `markitdown`, `extract_msg`, `vsdx`,
`python-docx`, `python-pptx`, `beautifulsoup4`, `wordfreq==3.1.1`, and optionally
`scikit-learn`+`numpy` (stage 4 clustering only — drop if unused).

Binaries/services: Python 3.12 · `pandoc` ≥3.0 · `docling-serve` + models (~506 MB) + tessdata ·
.NET SDK 8.0.424+ (builds the OneNote helper once) + NuGet `OfficeIMO.OneNote` 3.2.2 ·
**YAP + its model data** (`YAP_DIR`) · a local OpenAI-compatible LLM server (vLLM) serving
`minimax-m2.7` and `kimi-k2.7` · an embedding model for stage 6 retrieval.

> ⚠️ **Translation now depends on YAP.** It used to be pure stdlib. `mask_glossary_terms` calls
> `_require_yap()` and fails closed. Stage 5 cannot run without the YAP stack.

Prove it: install from the bundle on a clean Windows machine **with networking disabled**, then run
the smoke test in §5. An untested bundle is not a bundle. There is an `airgap-pack` skill that
automates this.

### P1 — Moshe, needs none of Yoni's time — **all done (PRs #16, #17)**

**4.3 Remove the vestigial Git LFS setup.** — **DONE (PR #16)**. `.gitattributes` is deleted
(verified: zero objects matching `deps/yap` in any ref), and the local `filter.lfs` config — whose
`required = true` is what hard-fails a checkout — is gone.

> **The four hooks are NOT fixed by the merge.** `.git/hooks/` is not version-controlled, so every
> clone gets them again from whoever ran `git lfs install`. They `exit 2` when git-lfs is absent,
> which is the silent merge/checkout abort in §6.3. On a fresh clone, run:
>
> ```bash
> rm -f .git/hooks/post-checkout .git/hooks/post-commit .git/hooks/post-merge .git/hooks/pre-push
> ```

**4.4 Implement the D3 test split.** — **DONE (PR #16)**, and it went further than a test split:
the pipeline is now its own product at `ingest-pipeline/` with its own `scripts/`, `tests/`,
`templates/`, `skills/`, `data/` and `requirements.txt`.

```bash
python3 -m unittest discover -s tests                      # framework: 42, needs NOTHING installed
cd ingest-pipeline && python3 -m unittest discover -s tests # pipeline: 194, needs requirements.txt
```

The framework gate no longer needs a single package, so the old failure — 6 modules failing to
import and 67 tests silently not running behind a plausible-looking `Ran 155 tests` — cannot
recur: those modules live in the other suite now, and a failed install there turns the pipeline
lane red rather than quietly shrinking the count.

`manifest.json` went 25 -> 8 owned paths; a freshly scaffolded vault is 15 files with zero trace
of the pipeline. `core.cmd_classify` moved to `ingest-pipeline/scripts/classify/validate.py` and
`vault classify` is gone from the CLI.

**4.5 Set up GitHub Actions CI.** — **DONE (PR #17)**. Two workflows: `framework.yml`
(ubuntu/macos/windows x py3.11/3.12, running the suite with **nothing installed** so the
air-gap claim is actually proven, plus packaging, wheel-payload and `mkdocs --strict` jobs)
and `pipeline.yml` (windows-latest gating per D1, ubuntu advisory).

Before it, eight PRs had merged with zero automated checks — including #15, which added the
checkpoint store this pipeline's survivability depends on.

Two things that surfaced while building it, both now fixed:

- **The `example-vault` staleness check never checked anything.** It ran
  `git diff --exit-code example_vault` *without* first running `vault upgrade`, so on a fresh
  checkout the diff was empty by construction. `CLAUDE.md` had described the rule as
  CI-enforced the entire time. The repo's one structural rule — `payload/` is the source of
  truth, `example_vault/` is an artifact — was unenforced for as long as it had been written
  down. It is now `tests/test_boundary.py::TestExampleVaultIsCurrent`.
- **`vault check` cannot detect an un-laid-down payload edit.** `cmd_check` only compares the
  stamp's `framework_version` against the installed version, so it exits 0 on a stale vault.
  Several docs claimed otherwise. Two lanes: framework (cross-platform,
pure stdlib) and pipeline (Windows runner, full deps).

**4.6 Update `CLAUDE.md`.** — **DONE (PR #16)**. Both halves:

- It no longer opens *"This repo is the framework, not a vault"*. It is now
  `# CLAUDE.md — Monorepo`, leading with a table of the two products and the rule that they do
  not import each other.
- The repo-wide **"Pure stdlib"** rule is scoped: *"Pure stdlib — the framework only"*, with an
  explicit note that it does **not** apply to `ingest-pipeline/`, whose ~11 packages live in
  `ingest-pipeline/requirements.txt` and never in `pyproject.toml`.

`tests/test_boundary.py` (PR #17) now enforces both claims rather than leaving them as prose:
the package and its tests are asserted to import stdlib only, and `pyproject.toml` is asserted
to declare no runtime dependencies.

### P2 — worth doing, not urgent

- **4.7 Glossary schema.** The dataset is the actual asset; the schema is 6 columns and an example
  row. No versioning, provenance, or approval trail. Design it before it gets large enough that
  migrating hurts.
- **4.8 Stage handoff contracts.** Stage 4 writes `translation_seed.csv`, stage 5 reads it by path
  convention; nothing versions or validates the handoff. *One page* documenting what each stage
  emits and consumes is how Yoni avoids breaking stage 5 when he changes stage 4 with nobody
  watching.
- **4.9 Collision detection at the gate.** `check_glossary_collisions` raises at mask time, per
  chunk, mid-run — so a collision surfaces after N documents are already translated. Also run it in
  `scripts/check_glossary.py` so it fails before any work starts.
- **4.10 Measure or drop the 20% kimi reviewer.** Second model through the gap, no evidence it
  catches anything the deterministic QA misses.
- **4.11 Keep raw docling output beside the Hebrew-fixed version.** The OCR-reversal fixer rewrites
  in place and keeps only a list of changed words. 3,800 pages are converted **once**. If the
  dictionary is subtly wrong you cannot detect or reverse it later.

---

## 5. End-to-end testing (not built yet — highest-value missing artifact)

Every stage has unit tests. **Nothing tests that the stages compose.**

### 5.1 Golden corpus (~half a day, outlives every script)

10–12 small real-shaped documents, each chosen to probe a seam, each with hand-written expected
output:

- Hebrew PDF with known-reversed OCR text
- Hebrew DOCX with **correct** text — must come out unchanged (guards against the fixer corrupting
  non-OCR text)
- mixed Hebrew/English with `הAPI`-style proclitics
- GFM table + code fence + YAML frontmatter
- `.eml` with an attachment
- English-only doc (must be skipped, not translated)
- exact duplicate of another file (dedup path)
- **3 known glossary terms, each used 5+ times** ← the detector for the at-least-once class of bug
- `קריאה/כתיבה`-style Hebrew slash pairs (invariant-regex class)
- a person name that is also an org codename
- **one 100+ page document** ← §4.1's detector. PR #15 pins the 67-chunk resume case with a stubbed
  LLM (`TestLargeDocumentSurvival`); what is still missing is the same case through the *real*
  chain, where a genuine model drops a genuine delimiter.

### 5.2 Boundary assertions

| Boundary | Assert |
|---|---|
| after stage 3 | every input has an output or an explicit report entry; the correct-Hebrew DOCX is unchanged |
| after stage 4 | `translation_seed.csv` has expected columns; known terms present |
| after stage 5 | **every glossary term appears the correct number of times**; no `⟦…⟧` sentinel leaks; table/heading/code counts match source |
| ledger | exactly one terminal state per document; none missing |

### 5.3 Two tiers

`--mock` exists and is sentinel-aware, so the whole chain runs with no model.

- **smoke** — mock mode, whole chain, <60s, every commit
- **e2e** — real local model; run before entering the gap and as the bundle acceptance test

---

## 6. Gotchas a fresh session will hit

1. **`PYTHONPATH=src` is required for the framework suite.** Without it,
   `second_brain_vault_framework` may resolve through an editable install pointing at another
   checkout. **Not a real failure.** The pipeline suite does not need it — run it from
   `ingest-pipeline/`, which puts `scripts/` on the path itself.
2. **Run the right suite from the right directory.** `discover -s tests` at the repo root now
   runs the *framework* only (42 tests, no dependencies). The pipeline's 194 live in
   `ingest-pipeline/tests/`. Before the split a bare checkout printed `Ran 155 tests` while 6
   modules silently failed to import and 67 tests never ran; that trap is gone, but a green
   framework run is no longer evidence the pipeline is healthy.
3. **git-lfs hook aborts merges.** If a merge or worktree checkout behaves oddly, use
   `git -c core.hooksPath=/dev/null`. Always confirm a test-merge actually applied
   (`test -f .git/MERGE_HEAD`) before trusting test output — a silently-aborted merge yields
   `main`'s baseline numbers, which look plausible.
4. **Verify claims against the code, not commit messages.** Both real regressions found during
   review were in branches that looked healthy: one rebase silently dropped 7 files including the
   entire person-name guard dataset, and the guard degraded to empty sets *without warning*.
5. **A passing run prints the word `FAILED`.** `test_unmask_and_ledger_fields` deliberately drives
   a document to `qa_failed` to check the ledger, and `translate.main()` writes
   `FAILED: 1 docs still invalid after 3 fix rounds: ['raw_md/doc.md']` to stderr from inside that
   *passing* test. unittest does not capture it, so it lands directly above the summary line. It is
   not a failure. Worth fixing before §4.5 puts this in CI, where someone will scan a green log and
   see `FAILED:` in it.
6. **Check merge-base age before reviewing a diff.** A two-month-old base produced a bogus
   762-file / +32,960 diff that looked like an accidental commit of someone's local config. It was
   an artifact.

---

## 7. What is stale in the design review

`docs/superpowers/specs/2026-08-16-ingest-pipeline-design-review.md` is the fuller write-up, but
these parts are now out of date:

- **§2 / D2** — described as an open problem. It is **implemented and merged**.
- **§4 D4** — recommends Git LFS. Superseded: the binaries were **deleted entirely**.
- **§5** — states stages 5 and 6 are pure stdlib and the dependency surface is confined to stages 3
  and 4. **Wrong now**: translation requires YAP.
- **§3B I1** — the payload question is resolved (D3, monorepo).
- Verdict tables and merge order throughout — all PRs are merged.

- Any statement that a chunk failure aborts the document — fixed by PR #15, see §4.1.

§6 (end-to-end testing) and §3A M3 (irreversible Hebrew fix) are still accurate and still open.

---

## 8. If you do only one thing

**§4.2 — build and prove the offline dependency bundle.** It is the only remaining item with a
hard deadline, and the only one whose failure mode is discovered on the far side of the gap.
It must be built **on Windows** (`pip download` on macOS resolves the wrong wheels), it must be
proven by installing on a clean machine **with networking disabled**, and stage 5 now cannot run
at all without the YAP stack. `ingest-pipeline/requirements.txt` is the pip surface; the
non-pip pieces are listed in §4.2 and at the bottom of that file.

§4.1 (checkpointing) and §4.5 (CI) — the two previous answers to this question — are done.

> The very first Windows CI run is the moment to watch. Every pipeline test to date has only
> ever run on macOS, so `pipeline.yml`'s gating job is the first real evidence the pipeline
> works on the platform it ships on. Expect it to need attention rather than to be green.

> Deps were installed on a Mac during the §4.1 work to get the suite fully green. Those are
> **macOS arm64 wheels** (`pypdfium2-5.13.0-macosx_13_0_arm64`) — useful for local testing,
> worth nothing toward §4.2.
