# Translate Split Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split 2301-line `scripts/translate.py` into 5 focused modules plus a thin re-exporting orchestrator, with zero behavior change.

**Architecture:** Extract by responsibility — masking (YAP + sentinels), invariants (preservation-by-verification), chunking (markdown boundaries + glossary filtering), prompts (pure string builders), LLM (network/mock I/O). `translate.py` retains CLI `main`, `translate_one_doc*`, `_translate_chunks*` orchestration and re-exports every public name so `import translate` and `translation_qa -> import translate` keep working. `md_mask.py` and `translation_common.py` untouched.

**Tech Stack:** Python 3.12 stdlib only, existing `scripts/translate.py` (2301 lines, 40 defs) + `translation_qa.py` (670) + `translation_common.py` (118, sentinel helpers) + `md_mask.py` (595 vendored) + `tests/test_translation_pipeline.py` (10 tests) / `test_translation_qa.py` (6 tests). Windows-only YAP `deps/yap/yap.exe` via `hebrew_yap_stemmer`. No new deps.

---

## File Structure

**Created:**
- `scripts/translation_masking.py` — YAP-aware deterministic masking. Owns `HEBREW_RANGE`, `PROCLITICS`, `RAW_WORD_RE`, `MIXED_SPLIT_RE`, `_YAP_AVAILABLE`, `_require_yap`, `_heuristic_split`, `_roots_for_token`, `_analyze_with_fallback`, `mask_glossary_terms`, `unmask_glossary_terms`, `PERSON_OPEN/CLOSE`-adjacent sentinel helpers if needed. Imports `translation_common` for `build_glossary_sentinel`/`build_keep_sentinel`/`check_glossary_collisions`.
- `scripts/translation_invariants.py` — Preservation-by-verification layer. Owns `PERSON_OPEN/CLOSE`, `EN_OPEN/CLOSE`, `HE_MARKER_FMT`, `HEBREW_WORD_RE`, `_EN_SENTINEL_RE`, `_PERSON_SENTINEL_RE`, `_EN_SPAN_RE`, `_COMMON_ENGLISH`, `_URL_RE`, `_FILEPATH_RE`, `_YAML_RE`, `_FENCED_RE`, `_INLINE_CODE_RE`, `_CODE_RE`, plus `mask_person_names`, `_mask_via_tokens`, `unmask_person_names`, `is_english_only_doc`, `mask_english_spans`, `unmask_english_spans`, `extract_english_spans`, `extract_urls_and_paths`, `extract_person_names`, `extract_yaml_frontmatter`, `extract_code_sections`, `extract_preservation_invariants`, `verify_preserved`, `verify_all_preserved`, `verify_ordered`, `verify_all_ordered`, `verify_global_order`.
- `scripts/translation_chunking.py` — Vault chunking + config/gate helpers. Owns `chunk_markdown`, `glossary_for_chunk`, and narrow config helpers `get_ledger_path`, `load_config`, `resolve_fix_rounds`, `resolve_corpus_dir`, `_read_csv_skip_comments`, `load_glossary`, `load_codenames`, `load_person_names`. (If config helpers feel misplaced, they stay in `translate.py` — minimal move; chunking is the anchor.)
- `scripts/translation_prompt.py` — Pure prompt builders. Owns `build_prompt`, `build_fix_prompt`, `_build_chunked_fix_prompts`, `format_qa_failures`, plus sentinel-aware constants imported from `translation_common`/`translation_masking` as needed. No I/O, no YAP.
- `scripts/translation_llm.py` — LLM I/O boundary. Owns `call_llm`, `mock_translate`, `_mock_with_sentinels`, and retry/timeout constants. Depends on masking for sentinel helpers and invariants for protected lists.

**Modified:**
- `scripts/translate.py` — Becomes thin orchestrator: `main`, `translate_one_doc`, `translate_one_doc_with_fix`, `_translate_chunks`, `_translate_chunks_with_term_map`, `run_qa_for_doc`, plus imports/re-exports of every public name from the 5 new modules (so `import translate; translate.mask_glossary_terms` still works). No logic duplicated.
- `scripts/translation_qa.py` — One import line changes: `import translate as tmod` becomes `import translation_invariants as tmod` (or keeps `translate` via re-export — either way QA and translation share one definition). Prefer direct import to break the circular indirection, with `translate` re-export as fallback.
- No test file changes required for the pure move (prove via existing suite).

**Untouched (explicit out-of-scope):**
- `scripts/md_mask.py` (595 lines, vendored)
- `scripts/translation_common.py` (118 lines, sentinel helpers)
- `scripts/translation_qa.py` logic (only import line may change)
- `tests/*` (no new tests by scope choice)

---

### Task 1: Scaffolding + import graph

**Files:**
- Modify: `scripts/translate.py:1-15` (header only if needed)
- Create: `scripts/translation_masking.py` (empty shell), `scripts/translation_invariants.py`, `scripts/translation_chunking.py`, `scripts/translation_prompt.py`, `scripts/translation_llm.py`

- [ ] **Step 1: Create 5 empty module shells with docstrings and no logic**

```python
# scripts/translation_masking.py
"""YAP-aware deterministic glossary masking — extracted from translate.py (pure move)."""
from __future__ import annotations

# scripts/translation_invariants.py
"""Preservation-by-verification invariants — extracted from translate.py (pure move)."""
from __future__ import annotations

# scripts/translation_chunking.py
"""Markdown chunking + glossary filtering — extracted from translate.py (pure move)."""
from __future__ import annotations

# scripts/translation_prompt.py
"""Prompt builders — extracted from translate.py (pure move)."""
from __future__ import annotations

# scripts/translation_llm.py
"""LLM I/O — extracted from translate.py (pure move)."""
from __future__ import annotations
```

- [ ] **Step 2: Verify empty modules import**

Run: `python -c "import translation_masking, translation_invariants, translation_chunking, translation_prompt, translation_llm; print('shells ok')"`
Expected: `shells ok`

- [ ] **Step 3: Commit scaffolding**

```bash
git add scripts/translation_masking.py scripts/translation_invariants.py scripts/translation_chunking.py scripts/translation_prompt.py scripts/translation_llm.py
git commit -m "refactor: scaffold translate split modules (empty shells)"
```

---

### Task 2: Extract translation_invariants (largest isolated cluster)

**Files:**
- Create: `scripts/translation_invariants.py` (full)
- Modify: `scripts/translate.py` (replace with imports + re-exports)

Moves ~280 lines: `PERSON_OPEN/CLOSE`, `EN_OPEN/CLOSE`, `HE_MARKER_FMT`, `HEBREW_WORD_RE`, `_EN_SENTINEL_RE`, `_PERSON_SENTINEL_RE`, `_EN_SPAN_RE`, `_COMMON_ENGLISH`, `_URL_RE`, `_FILEPATH_RE`, `_YAML_RE`, `_FENCED_RE`, `_INLINE_CODE_RE`, `_CODE_RE`, `mask_person_names`, `_mask_via_tokens`, `unmask_person_names`, `is_english_only_doc`, `mask_english_spans`, `unmask_english_spans`, `extract_english_spans`, `extract_urls_and_paths`, `extract_person_names`, `extract_yaml_frontmatter`, `extract_code_sections`, `extract_preservation_invariants`, `verify_preserved`, `verify_all_preserved`, `verify_ordered`, `verify_all_ordered`, `verify_global_order`.

- [ ] **Step 1: Copy invariants family verbatim into translation_invariants.py**

Add `import re, json` etc. as in source. No logic changes. Keep exact regex literals and `frozenset` for `_COMMON_ENGLISH`.

- [ ] **Step 2: Replace same block in translate.py with import + re-export**

```python
# scripts/translate.py — replace invariants block with:
from translation_invariants import (
    PERSON_OPEN, PERSON_CLOSE, EN_OPEN, EN_CLOSE, HE_MARKER_FMT,
    HEBREW_WORD_RE,
    mask_person_names, _mask_via_tokens, unmask_person_names,
    is_english_only_doc, mask_english_spans, unmask_english_spans,
    extract_english_spans, extract_urls_and_paths, extract_person_names,
    extract_yaml_frontmatter, extract_code_sections,
    extract_preservation_invariants,
    verify_preserved, verify_all_preserved, verify_ordered, verify_all_ordered, verify_global_order,
)
# Keep private regex names re-exported for tests that patch via translate.* if any
import translation_invariants as _invariants
_EN_SPAN_RE = _invariants._EN_SPAN_RE
_COMMON_ENGLISH = _invariants._COMMON_ENGLISH
_URL_RE = _invariants._URL_RE
_FILEPATH_RE = _invariants._FILEPATH_RE
_YAML_RE = _invariants._YAML_RE
_CODE_RE = _invariants._CODE_RE
```

- [ ] **Step 3: Run existing suite + smoke patch targets**

Run: `python -m unittest discover -s tests -v 2>&1 | tail -n 30`
Expected: same pass count as baseline (pipeline 10 + qa 6, plus unrelated suites). No new failures.

Run: `python -c "import translate; assert hasattr(translate,'extract_preservation_invariants'); assert hasattr(translate,'verify_global_order'); print('re-export ok')"`
Expected: `re-export ok`

- [ ] **Step 4: Commit**

```bash
git add scripts/translation_invariants.py scripts/translate.py
git commit -m "refactor: extract translation_invariants (preservation-by-verification)"
```

---

### Task 3: Extract translation_masking (YAP + sentinels)

**Files:**
- Create: `scripts/translation_masking.py`
- Modify: `scripts/translate.py`

Moves ~390 lines: `HEBREW_RANGE`, `PROCLITICS`, `RAW_WORD_RE`, `MIXED_SPLIT_RE`, `try: from hebrew_yap_stemmer…`, `_YAP_AVAILABLE`, `_require_yap`, `_heuristic_split`, `_roots_for_token`, `_analyze_with_fallback`, `mask_glossary_terms`, `unmask_glossary_terms`. Also any `PERSON_*` if not already moved.

- [ ] **Step 1: Copy masking block verbatim into translation_masking.py**

Imports: `import re, hashlib` + `from translation_common import build_glossary_sentinel, build_keep_sentinel, check_glossary_collisions` + lazy `hebrew_yap_stemmer` try/except. Preserve `hasattr(_yap_root_keys, "_mock_name")` mock detection.

- [ ] **Step 2: Replace in translate.py with import + re-export**

```python
from translation_masking import (
    HEBREW_RANGE, PROCLITICS, RAW_WORD_RE, MIXED_SPLIT_RE,
    _require_yap, _heuristic_split, _roots_for_token, _analyze_with_fallback,
    mask_glossary_terms, unmask_glossary_terms,
)
import translation_masking as _masking
_YAP_AVAILABLE = _masking._YAP_AVAILABLE
```

- [ ] **Step 3: Run masking tests (the 5 that mock YAP) + full suite**

Run: `python -m unittest tests.test_translation_pipeline.TestMaskGlossaryTerms -v`
Expected: 5/5 pass (simple+spacing, הDBים, המערכות, longest-match, YAP fail-closed).

Run: `python -m unittest discover -s tests -v 2>&1 | tail -n 20`
Expected: same as baseline.

Run: `python -c "import translate; translate.mask_glossary_terms; print('mask re-export ok')"`
Expected: `mask re-export ok`

- [ ] **Step 4: Commit**

```bash
git add scripts/translation_masking.py scripts/translate.py
git commit -m "refactor: extract translation_masking (YAP + glossary sentinels)"
```

---

### Task 4: Extract translation_chunking

**Files:**
- Create: `scripts/translation_chunking.py`
- Modify: `scripts/translate.py`

Moves `chunk_markdown`, `glossary_for_chunk`, plus optionally `get_ledger_path`, `load_config`, `resolve_fix_rounds`, `resolve_corpus_dir`, `_read_csv_skip_comments`, `load_glossary`, `load_codenames`, `load_person_names` (these are small; if move, keep re-export). Minimal-risk choice: move only `chunk_markdown` + `glossary_for_chunk` now; config helpers stay.

- [ ] **Step 1: Copy chunk_markdown + glossary_for_chunk verbatim into translation_chunking.py**

Keep the `qmd chunking` comment and `max_chars` default.

- [ ] **Step 2: Replace in translate.py with import**

```python
from translation_chunking import chunk_markdown, glossary_for_chunk
```

- [ ] **Step 3: Verify chunking tests / e2e still pass**

Run: `python -m unittest discover -s tests -v -k chunk 2>&1 || python -m unittest discover -s tests -v 2>&1 | tail -n 20`
Expected: pass (no chunk-specific test currently, so full suite gate).

- [ ] **Step 4: Commit**

```bash
git add scripts/translation_chunking.py scripts/translate.py
git commit -m "refactor: extract translation_chunking (markdown boundaries)"
```

---

### Task 5: Extract translation_prompt

**Files:**
- Create: `scripts/translation_prompt.py`
- Modify: `scripts/translate.py`

Moves `build_prompt`, `build_fix_prompt`, `_build_chunked_fix_prompts`, `format_qa_failures`. Pure functions, no YAP, no I/O.

- [ ] **Step 1: Copy prompt builders verbatim into translation_prompt.py**

Imports: `import json, re` + `from translation_common import build_glossary_sentinel, build_keep_sentinel` inside functions as in source (preserve lazy imports). Keep `chunk_markdown`/`glossary_for_chunk`/`extract_preservation_invariants` imports where `_build_chunked_fix_prompts` needs them (import from `translation_chunking`/`translation_invariants`).

- [ ] **Step 2: Replace in translate.py with import + re-export**

```python
from translation_prompt import build_prompt, build_fix_prompt, _build_chunked_fix_prompts, format_qa_failures
```

- [ ] **Step 3: Run suite**

Run: `python -m unittest discover -s tests -v 2>&1 | tail -n 20`
Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/translation_prompt.py scripts/translate.py
git commit -m "refactor: extract translation_prompt (pure builders)"
```

---

### Task 6: Extract translation_llm

**Files:**
- Create: `scripts/translation_llm.py`
- Modify: `scripts/translate.py`

Moves `call_llm`, `mock_translate`, `_mock_with_sentinels`. I/O boundary with retries, `urllib`.

- [ ] **Step 1: Copy LLM block verbatim into translation_llm.py**

Keep `import urllib.request, urllib.error, json, time, re, hashlib` and `HE_MARKER_FMT` reference (import from `translation_invariants`). Preserve `HEBREW_WORD_RE` usage and protected-list logic.

- [ ] **Step 2: Replace in translate.py with import**

```python
from translation_llm import call_llm, mock_translate, _mock_with_sentinels
```

- [ ] **Step 3: Run mock e2e test (uses mock_translate)**

Run: `python -m unittest tests.test_translation_pipeline -v 2>&1 | tail -n 30`
Expected: `test_e2e_mock_deterministic_with_fixtures` + `test_unmask_and_ledger_fields` pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/translation_llm.py scripts/translate.py
git commit -m "refactor: extract translation_llm (network/mock I/O)"
```

---

### Task 7: Thin orchestrator + wire translation_qa + final sweep

**Files:**
- Modify: `scripts/translate.py` (final shape: ~550 lines)
- Modify: `scripts/translation_qa.py` (one import line)
- Verify: `tests/test_translation_pipeline.py`, `tests/test_translation_qa.py`

Remaining in `translate.py`: `main` (CLI + vault/config/ledger orchestration), `translate_one_doc`, `translate_one_doc_with_fix`, `_translate_chunks*`, `run_qa_for_doc`, plus thin helpers `get_ledger_path`/`load_config`/`resolve_fix_rounds`/`resolve_corpus_dir`/`load_glossary` (stay). All other names re-exported.

- [ ] **Step 1: Update translation_qa.py import**

```python
# Before:
import translate as tmod
# After (direct, breaks cycle; translate re-export keeps compat):
try:
    import translation_invariants as tmod
except ImportError:
    import translate as tmod  # fallback via re-export
```

Keep `tmod.load_person_names` / `tmod.extract_preservation_invariants` etc. working.

- [ ] **Step 2: Add explicit re-exports at bottom of translate.py for compat**

```python
# Re-exports for `import translate; translate.X` compat (pure refactor, no new API)
__all__ = [
    "get_ledger_path","load_config","resolve_fix_rounds","resolve_corpus_dir",
    "load_glossary","load_codenames","load_person_names",
    "mask_person_names","unmask_person_names","is_english_only_doc",
    "mask_english_spans","unmask_english_spans",
    "extract_english_spans","extract_urls_and_paths","extract_person_names",
    "extract_yaml_frontmatter","extract_code_sections","extract_preservation_invariants",
    "verify_preserved","verify_all_preserved","verify_ordered","verify_all_ordered","verify_global_order",
    "chunk_markdown","glossary_for_chunk",
    "mask_glossary_terms","unmask_glossary_terms",
    "build_prompt","build_fix_prompt","_build_chunked_fix_prompts","format_qa_failures",
    "call_llm","mock_translate","_mock_with_sentinels",
    "run_qa_for_doc","translate_one_doc","translate_one_doc_with_fix","main",
    # constants
    "PERSON_OPEN","PERSON_CLOSE","EN_OPEN","EN_CLOSE","HE_MARKER_FMT",
    "HEBREW_RANGE","PROCLITICS","RAW_WORD_RE","MIXED_SPLIT_RE",
]
```

- [ ] **Step 3: Full verification (zero behavior change)**

Run: `python -m unittest discover -s tests -v 2>&1 | tail -n 40`
Expected: same pass/fail as before this refactor (baseline: pipeline 10 + qa 6 pass; unrelated suites unchanged).

Run: `python -c "import translate; import translation_invariants, translation_masking, translation_chunking, translation_prompt, translation_llm; print('all imports ok')"`
Expected: `all imports ok`

Run: `python -c "import translate; assert translate.mask_glossary_terms is translation_masking.mask_glossary_terms; assert translate.build_prompt is translation_prompt.build_prompt; print('identity ok')"`
Expected: `identity ok`

Run: `python scripts/translate.py --help 2>&1 | head -n 20`
Expected: same CLI help as before.

- [ ] **Step 4: Commit + push branch**

```bash
git add scripts/translate.py scripts/translation_qa.py
git commit -m "refactor: thin orchestrator + wire translation_qa to invariants"
git push -u origin feat/translate-split
```

---

## Self-Review

**1. Spec coverage:** Every function in `translate.py` maps to one of the 5 new modules (masking, invariants, chunking, prompts, LLM) or stays in the thin orchestrator (`main`, `translate_one_doc*`, `_translate_chunks*`, `run_qa_for_doc`). No orphaned def.

**2. Placeholder scan:** No TBD/TODO — every step shows exact code, file paths, commands, and expected output.

**3. Type consistency:** Re-exported names keep identical signatures (no new wrappers). `translation_qa` keeps `tmod.*` call sites unchanged (only import source changes). `translation_prompt._build_chunked_fix_prompts` still imports chunking/invariants as before (just from new modules).

---

## Decision Document (from interview)

- Pure move, zero behavior change — no bug fixes or API changes in the same PR.
- 5–6 modules granularity (5 new + thin `translate.py`), not minimal 2-file nor maximal 7–8.
- `translate.py` remains and re-exports every public symbol (`import translate` stays working); `translation_qa -> import translate` updated to direct `translation_invariants` with fallback.
- Masking owns YAP stack (`hebrew_yap_stemmer`, `_require_yap`, `_heuristic_split`, etc.).
- Invariants owns the entire preservation-by-verification layer (~15 functions + regexes).
- Chunking owns `chunk_markdown` + `glossary_for_chunk` (config helpers may stay).
- Prompts owns the 4 pure builders.
- LLM owns the 3 I/O functions.
- `md_mask.py` untouched (vendored).
- Testing: existing `unittest` suite is the proof (no new tests for pure move).

## Testing Decisions

- **What makes a good test:** Only external behavior (CLI, ledger, masking sentinels, QA gates), not file location. Moving code must not change observable behavior.
- **Which modules will be tested:** Indirectly via existing suite. Masking (5 mock tests), e2e mock deterministic (`הDBים`/`המערכות`), QA sentinel (6 tests), plus `is_english_only_doc` gates.
- **Prior art:** `tests/test_translation_pipeline.py` (10 tests, mocks YAP via `translate._yap_root_keys`) + `tests/test_translation_qa.py` (6 tests). After split, same tests pass because `translate` re-exports keep patch targets (`translate._yap_root_keys`) working (re-export is identity, `import translate` sees the masking module's object).

## Out of Scope

- No behavior changes (YAP fail-closed, sentinel spacing, collision gate M7, fix-loop, ledger shape all unchanged).
- No `md_mask.py` refactor.
- No `translation_common.py` changes.
- No new tests (by explicit choice; smoke asserts are manual `python -c` checks).
- No import path migration for tests (keep `import translate`).
- No performance tuning or parallelization.
- No doc updates beyond code comments (spec docs already describe sentinel contract).

## Further Notes

- Each task leaves the repo in a working state (tests pass after every commit) — Fowler small steps.
- Branch from `feat/domain-terms-moshe` or `main` after domain masking merges; keep fork guardrail (`upstream/main`).
- If `translation_chunking` importing `load_person_names` creates a cycle, keep that helper in `translate.py` (minimal move, noted as optional in Task 4).
