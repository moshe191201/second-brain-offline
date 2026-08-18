# Glossary Deterministic Masking — Context-Preserving Design

**Date:** 2026-08-16
**Status:** Approved (approaches A/B/C reviewed, A selected)
**Scope:** PR #9 `feat/hebrew-translation-pipeline` — fixes §2 "verification ≠ guarantee" from `2026-08-16-ingest-pipeline-design-review.md`
**Depends on:** PR #13 `feat/domain-terms-moshe` (YAP `hebma` via `deps/yap/yap.exe`, LFS) — required for inflection-aware matching; translate fails closed if YAP missing
**Parent:** `2026-08-03-stage5-translation-design.md`, `2026-08-02-client-ingest-pipeline-design.md`

## 1. Problem

Domain glossary is currently **verification, not enforcement**:

```python
# translate.py:build_prompt — glossary_block injected as "use these exact renderings"
glossary_block = "Glossary (use these exact renderings):\n" + "\n".join(lines)
# translation_qa.py:check_glossary_retention
if eng in body: continue  # document-wide, at-least-once, position-blind
```

A term rendered correctly in paragraph 1 and paraphrased in the other 9 occurrences passes. Longer glossaries dilute attention ("worked at 50, flaky at 500"). The deterministic machinery exists but is wired only into `--mock` (`translate.py:1189 out.replace(term, eng)`). Goal: **100% correctness on domain terms** while keeping surrounding sentence context so the model can choose correct prepositions/articles/agreement.

User constraints: (a) full inflection — terms appear with proclitics `ה/ב/ל/מ/כ/ש/ו` and suffixes `ם/ות/יהם` etc. — so simple `str.replace` is insufficient, YAP root-key grouping required; (b) `C + spacing` — keep proclitic/suffix as spaced particles before/after the sentinel so the model translates them.

## 2. Decision — Approach A (selected)

**Bilingual inline sentinel with proclitic/suffix spacing.**

For each chunk, mask every glossary occurrence (incl. inflected variants) as `proclitic + "⟦EN:{id}:{English}⟧" + suffix` with added spaces. The English inside the sentinel is visible to the model so it shapes the surrounding grammar; the sentinel delimiters make the guarantee countable and order-aware. Rejected: B (English-only, ambiguous when two Hebrew terms share one English) and C (annotate + post-rewrite, paraphrase before replacement breaks guarantee). See brainstorm record 2026-08-16 for full trade-off table.

## 3. Architecture

```
chunk_text (Hebrew md)
 ├─ extract_preservation_invariants()  [existing: names, EN spans, URLs, code, yaml]
 ├─ glossary_for_chunk() → filtered rows (approved/keep_source only)
 ├─ NEW: mask_glossary_terms(chunk_text, glossary_rows, yap_roots)
 │        → masked_chunk, term_map [{id, term_he, english, keep_source, occurrences, src_spans}]
 ├─ build_prompt(masked_chunk, term_map, invariants, prev_tail)
 ├─ call_llm(masked_chunk) → {translation with ⟦EN:…⟧ preserved}
 ├─ qa: check_glossary_sentinel(term_map) — count + order, per-occurrence
 │        failure → bounded fix_rounds (chunked self-heal), else qa_failed
 └─ unmask: replace sentinel with english (or term_he for keep_source)
           ledger: model_id + glossary_version (hash) + term_map
```

Only `scripts/translate.py`, `scripts/translation_qa.py`, `scripts/translation_common.py` change. `mock_translate` reuses the same masking path (no special case). Content-addressed store `data/translations/<sha>/` unchanged.

## 4. Masking — `mask_glossary_terms()`

**Input:** `chunk_text: str`, `glossary_rows: list[dict]` (already filtered to `approved`/`keep_source`), YAP roots.
**Output:** `masked_chunk: str`, `term_map: list[dict]`

1. **Glossary normalization (once):** For each row, apply same normalization as `extract_domain_terms.py`: `mixed_split` for `הAPI`→`api`, proclitic stripping, then `hebrew_yap_stemmer.root_keys(tokens)` to get `root_key_seq` (e.g. `אבטחת מידע` → `["אבטח","מידע"]`). Store `root_key_seq`, `english`, `term_he`, `keep_source`. Collision check: duplicate `english` for different `root_key_seq` or same `term_he` with conflicting `english` → `RuntimeError` (M7 gate).

2. **Chunk analysis:** Tokenize with `RAW_WORD_RE` (keeps `ה-API` as one token). `analyze_tokens(tokens)` → per-token `(surface, lemma, proclitic, suffix)`; `root_keys(tokens)` → `root_sequence`. Map token offsets to `chunk_text` indices.

3. **N-gram scan longest-first:** Slide `n=3,2,1` over `root_sequence`, compare to glossary `root_key_seq`. On match, record `src_span`. Detach proclitic/suffix from YAP lattice for boundary tokens: `he_prefix_map` for `ב/ל/ה` etc., `FEATURES` for pronominal suffixes. Emit with **added spacing**: `f"{proclitic} " if proclitic else ""` + sentinel + `f" {suffix}" if suffix else ""`. Example: `באבטחתו` → `ב ⟦EN:0:Information Security⟧ ו` ; `המערכת באבטחת המידע` → `המערכת ב ⟦EN:0:Information Security⟧ ה מאפשרת`.

4. **Sentinel:** `⟦EN:{id}:{english}⟧` (`id` = index in `term_map`, stable per chunk). `keep_source` uses `⟦KEEP:{term_he}⟧`. `⟦`/`⟧` (`U+27E6`/`U+27E7`) already used by `PERSON_OPEN`/`HE_MARKER_FMT`; extend `_PERSON_SENTINEL_RE` family. English inside is verbatim glossary `english`.

5. **Overlap:** Longest match wins; masked interior tokens are skipped. `מידע` vs `אבטחת מידע` → longer wins.

6. **Code/YAML exclusion:** Run masking *after* `extract_preservation_invariants` masks yaml/code — glossary terms inside code fences are not masked (already protected as `code_sections`).

7. **Fail-closed on YAP:** If `yap.exe` not found or `hebma` non-zero/timeout, raise `RuntimeError` and exit 1 (no identity fallback `return [(w,w)]`). Matches `CLAUDE.md: Fail closed` and the `fix: fail closed when YAP missing` intent from PR #9 review. This makes PR #9 depend on PR #13 being merged or YAP vendored.

## 5. Prompt & sentinel contract

`build_prompt` replaces the old glossary block:

```
Translate this Hebrew markdown chunk to faithful technical English.

Rules:
- Preserve headings, lists, tables, code fences exactly (same counts) and in the same order.
- Blocks of the form ⟦EN:{id}:{English}⟧ are pre-translated glossary terms — copy them
  VERBATIM including the ⟦EN: and ⟧ delimiters, do not translate, inflect, or reorder
  their interior English. Translate the surrounding Hebrew particles (ב/ל/מ/כ/ש/ו/ה, suffixes) as normal English prepositions/pronouns.
- Blocks ⟦KEEP:{Hebrew}⟧ must be copied verbatim as Hebrew.
- Person names / English spans / URLs / code / YAML below must also be copied verbatim in the same relative order.
- Never invent translations for unknown terms — list them in unknown_terms and emit ⟦he:term⟧.
- Output JSON: {"translation": string, "unknown_terms": [string], "notes": [string]}

Pre-translated terms in this chunk:
  - ⟦EN:0:Information Security⟧  ← אבטחת מידע (appears 3× in this chunk)
  - ⟦EN:1:API⟧                   ← הAPI

[preserve_block: yaml/code/person_names/english_spans/urls — same as today]
[prev_tail / Section: path / Chunk to translate: masked_chunk]
```

The English inside the sentinel is the sense the model would have guessed, so verb agreement, article, and preposition choice are conditioned correctly.

## 6. Verification & deterministic substitution

**Replaces `translation_qa.py:check_glossary_retention` (`eng in body`):**

```python
def check_glossary_sentinel(translation: str, term_map: list[dict]) -> dict:
    violations = []
    for e in term_map:
        sentinel = f"⟦EN:{e.id}:{e.english}⟧" if not e.keep_source else f"⟦KEEP:{e.term_he}⟧"
        have = translation.count(sentinel)
        if have != e.occurrences:
            violations.append(f"{e.term_he!r}→{sentinel!r} expected {e.occurrences}× got {have}×")
    # order: reuse verify_ordered / verify_global_order over sentinel strings
    return {"check": "glossary_sentinel", "status": "fail" if violations else "pass", "violations": violations}
```

* Per-occurrence (3× in source → 3× `⟦EN:…⟧` required), not at-least-once. Paraphrase without sentinel fails. Position checked via `verify_ordered` over sentinel order.

* Residual `⟦he:⟧` markers: only allowed for unknown terms not in `term_map`. Known terms must be sentinels.

**After QA passes — deterministic substitution:**

```python
for e in term_map:
    sentinel = f"⟦EN:{e.id}:{e.english}⟧"
    translation = translation.replace(sentinel, e.english)  # keep_source: replace with term_he
```

Proclitic particles (`ב ` etc.) remain as Hebrew that the model has already rendered as `in`/`to`/`from` in surrounding English. No Hebrew source term leaks.

**Failure path:** `glossary_sentinel` fail → `format_qa_failures` → `build_fix_prompt` now includes `term_map` (truncated 20) + `invariants` → chunked self-heal (`fix_rounds=3`, `finish_reason==length` already handled). Exhaustion → `qa_failed` ledger entry. `blocked_on_term` remains only for truly unknown terms; deterministically masked glossary terms never produce `blocked_on_term`.

**Gate interaction (`check_glossary.py`):** All-or-nothing `proposed` block stays — `proposed` rows produce no sentinel, their Hebrew becomes `⟦he:⟧` → `blocked_on_term` as today. + `model_id` recorded in `ledger.jsonl` (closes I8) alongside `glossary_version` (sha256 of `glossary.csv`) and `term_map`.

## 7. Error handling

- **YAP missing/corrupt:** `FileNotFoundError` / non-zero `hebma` → `RuntimeError("YAP required for glossary masking — fail-closed")`, exit 1. No fallback.
- **Glossary collisions (M7):** duplicate `english` for different Hebrew roots, or one `term_he` with two `english` → `RuntimeError` at load, before any doc translates.
- **Sentinel count/order mismatch:** `glossary_sentinel` fail → fix round. After 3 rounds still failing → `qa_failed`, human review queue (`docs/human-review-queue.md`), not silent pass.
- **Windows-only:** YAP path is `deps/yap/yap.exe` or `YAP_DIR`; `_find_yap_exe()` already Windows-only. Translate startup checks `platform.system()=="Windows"` or YAP presence and fails with clear message (D1 contract).
- **Large glossaries:** `term_map` is per-chunk filtered (only terms whose `root_key_seq` occurs in that chunk), so prompt stays bounded; only 20 entries shown in fix prompt, full list verified after.

## 8. Testing

- **Unit `tests/test_translation_pipeline.py`:** `mask_glossary_terms` with mocked YAP — proclitic+space, suffix+space, longest-match, overlap (`מידע` vs `אבטחת מידע`), mixed `הAPI`, `keep_source` (`⟦KEEP:…⟧`), sentinel count/order, duplicate-English collision, YAP-missing fail-closed. Existing `TestYamlGuard` gets `skipUnless(find_spec("convert_to_md"))` (follow-up review blocker).
- **QA `tests/test_translation_qa.py`:** `check_glossary_sentinel` — 1/5 occurrences, wrong English, missing sentinel, reordered sentinels, `⟦he:⟧` for known term, `keep_source` path.
- **Golden `ingest/tests/fixtures/e2e_corpus/` (per §6.1 of design review):** 10-doc corpus including a doc with 3 known terms each 5+ times (M1 detector), `קריאה/כתיבה` slash pair, `הAPI` proclitic, GFM table, attachment mail, English-only skip, duplicate, person-name codename collision. `mock` mode exercises full mask→preserve→unmask chain; `e2e` with real `minimax-m2.7`/`kimi-k2.7` is bundle acceptance test.
- **E2E assertion:** after `translate.py --mock --glossary glossary.csv`, every `approved` term appears exactly `occurrences` times, no `⟦EN:` leak, no Hebrew of that root remains, table/heading/code counts match source.

## 9. Rollout & dependencies

1. **Merge PR #13** (or vendor `deps/yap/` via LFS) before this lands — translate must be able to `import hebrew_yap_stemmer` and run `yap.exe hebma`.
2. **No new runtime deps** beyond YAP + `wordfreq==3.1.1` (already required). Pipeline remains stdlib otherwise (`ingest/` later).
3. **Back-compat:** glossary CSV schema unchanged; old ledgers without `term_map`/`model_id` remain readable, new docs get new fields.
4. **Docs:** update `docs/superpowers/plans/hebrew-translation-pipeline.md` and `stage5-translation-spec-addendum.md` to describe sentinel contract; update `convert_config.json` translation block docs.

## 10. Open items (not in scope for this change)

- D4 `deps/yap` LFS vs vendoring script (decided in PR #13).
- D5 freeze stage 6 (#12) — independent.
- Glossary schema versioning/provenance (I5) — follow-up.

