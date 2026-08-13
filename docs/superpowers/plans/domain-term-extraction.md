# Plan: Domain Term Extraction (Hebrew + English + Mixed) from raw_md

## Context

User extracts domain-specific terms from `raw_md/` (fallback `raw/`) — bilingual Hebrew/English with productive mixing like `הAPI`, `ל-K8s`. Current `scripts/hot_words.py` already does `wordfreq` ratio ranking (`corpus_count / word_frequency`) and works well for pure English/Hebrew unigrams, but has no handling for mixed tokens, no n-grams, and no outputs shaped for the three downstream uses: translation dictionary seed, code-word list, keyword-based subdomain classification. Requirement: deterministic only, no deep learning, dependencies are hard requirements (fail if missing), work in a separate worktree, normalize mixed terms while preserving the original surface for correctness.

Demo vault today: `raw/` has 11 English finetuning papers, `raw_md/` is a generated artifact (from `convert_to_md.py`) that may not exist locally — code must auto-resolve which directory to scan and handle nested mirrors (`raw/a/b/file.docx → raw_md/a/b/file.md`).

## Approach

**Create a new script `scripts/extract_domain_terms.py` in a dedicated worktree; keep `hot_words.py` as the unigram baseline for regression.**

### 1. Worktree setup

```bash
git worktree add .claude/worktrees/domain-terms -b feat/domain-term-extraction feat/document-conversion-pipeline
# all edits below happen inside that worktree
```

### 2. Script `scripts/extract_domain_terms.py`

**CLI:** `python scripts/extract_domain_terms.py [vault_root] [--input PATH] [--top-n 1000] [--min-count 3] [--ngrams 1,2,3]`
Follows `convert_to_md.py` conventions: `vault_root` positional, `Path` I/O, `sys.exit(1)` on missing deps.

**Fail-fast guards (top of `main`):**
- `wordfreq 3.1.1` import check — `sys.exit("wordfreq 3.1.1 required")` if missing.
- YAP binary check via `hebrew_yap_stemmer._find_yap_exe()` — `sys.exit` if not found (do not silently fall back to identity).
- `sklearn` import gated only if subdomain clustering is requested; otherwise warn and skip that projection.

**Corpus resolution:**
```python
def resolve_corpus_dir(vault_root, explicit=None) -> Path:
    # prefer raw_md if it exists and has any *.md via rglob, else raw
    # rglob (not flat glob) because convert_to_md mirrors subtrees
    # raise if neither exists
```
Reuse `convert_to_md` frontmatter/markdown cleanup (strip `---` YAML, `![]()`, unwrap `[]()`, strip `<tags>` and emails).

**Tokenization — three classes:**

- Extraction regex (keeps optional hyphen so `ה-API` stays one token):
  `RAW_WORD_RE = re.compile(r"[A-Za-z֐-׿]{2,}(?:-[A-Za-z֐-׿]+)?")`

- Classifier per token:
  ```python
  def classify(tok):  # -> "he" | "en" | "mixed"
      he = count Hebrew chars; en = count Latin chars
      if he>0 and en>0: return "mixed"
      if he/len >=0.6: return "he"
      return "en"
  ```
  Fixes current bug where `הAPI` (1 Hebrew / 4 letters = 25%) is mis-routed to English.

- Normalizers (all populate `variant_map[normalized][surface] +=1`):
  - `en`: `tok.lower()`, filtered by `_ENGLISH_STOP_WORDS` (imported from `hot_words.py`).
  - `he`: batch through `hebrew_yap_stemmer.analyze_tokens` → lemma → `_strip_hb_suffix` + weak-letter skeleton (reuse `root_keys` logic), filtered by `_HB_STOP_WORDS`.
  - `mixed` — core fix for `הAPI`:
    ```python
    PROCLITICS = set("הלבמושכ")  # ה ל ב מ ו ש כ — combinations like וה handled iteratively
    MIXED_RE = re.compile(r"^([֐-׿]+)-?([A-Za-z][A-Za-z0-9_\-]+)")
    def normalize_mixed(tok) -> (normalized_en, he_prefix):
        # split leading Hebrew run from English stem
        # validate he_prefix chars are all in PROCLITICS; if any char outside, DO NOT strip
        # (e.g. שלוםAPI stays as surface, goes to ambiguous bucket)
        # require en_stem[0] is Latin and len>=2, consume optional hyphen
        # normalized = en_stem.lower()
    ```
    Examples: `הAPI→api (ה)`, `וה-API→api (וה)`, `לAPI→api (ל)`, `שלוםAPI→ no strip (non-proclitic ם)`.

Order-preserving scan per file so n-grams respect document order.

**Counting & n-grams:**

- Unigrams: `Counter[normalized]` + `variant_map` + `doc_freq`.
- Bigrams/trigrams: slide window over normalized token stream in document order, skip any window containing a stopword or `len<=1` token, count `Counter` per n. Mixed tokens contribute their normalized English stem.
- Quotas: `min_count` per n = `unigram 3 / bigram 2 / trigram 2`; configurable. Pool will be up to ~1k terms.

**Scoring (deterministic, wordfreq-based):**

- Unigram: identical to `hot_words.rank_hot_words`: `base = word_frequency(term, lang)`, `ratio = count/base`, `log_ratio = log10(ratio)`. Keep that function for regression.
- N-gram: `base_ngram = gmean(word_frequency(w_i, lang_i))` for constituent tokens (geometric mean so length doesn't spuriously dominate; product would make trigrams artificially rare). `mixed` constituents score as `en`. OOV floor `1e-9` instead of skipping `base<=0` (current hot_words skips OOV, but code words like `qlora`/`snac` at `~1e-8` and invented `zzqwert` must be ranked, not dropped). Then `ratio/log_ratio` as above.
- Unified ranking: pool all n, sort by `log_ratio desc, corpus_count desc, term asc` (deterministic tiebreak). Optional per-n quota (e.g. 700/200/100) via `--quota`.

**Outputs under `data/domain_terms/` (waived, like `raw_md/` and `data/hebrew_dict.json`):**

| File | Schema | Downstream use |
|---|---|---|
| `terms.csv` | `rank,term,n,lang,corpus_count,doc_freq,base_freq,ratio,log_ratio,variants` (`variants` = `;`-joined summary) | canonical ranked list |
| `variants.json` | `{normalized: {lang, corpus_count, variants:{surface:count}, he_prefixes?:{prefix:count}, root_key?}}` indented UTF-8 `ensure_ascii=False` | correctness preservation |
| `translation_seed.csv` | `term,lang,surface_variants,corpus_count,log_ratio,needs_translation,suggested_en,example_doc` filtered to `lang in (he,mixed)` plus `mixed.en_stem` as hint | translation dictionary |
| `code_words.txt` + `code_words.csv` | `txt` one term/line by log_ratio; `csv` adds `corpus_count,log_ratio,pattern_matched,example_surface` — qualifies if: `mixed` always, or `base_freq<1e-7` & `count>=3`, or matches `acronym/camel/snake/kebab` regex, or seen inside backticks | code-word finder |
| `subdomain_keywords.json` | `{num_clusters, clusters:[{id,label_hint,keywords,doc_count,docs}], unclustered_keywords}` via `TfidfTransformer` on doc-term count matrix + `KMeans(random_state=0, n_init=1)` over top ~500 terms | keyword classification |
| `report.json` | `{input_dir, files, total_chars, total_tokens, unique_terms, ngram_counts, warnings, errors}` | run metadata |

Reuse stopword sets and `_is_hebrew` from `hot_words.py`; import `hebrew_yap_stemmer.root_keys/analyze_tokens`.

### 3. Tests (`unittest`, style of `test_hebrew_fix.py`)

- `tests/test_domain_terms_tokenization.py` — pure en/he/mixed classification, hyphens, proclitic validation, stopword filtering, `RAW_WORD_RE` extraction.
- `tests/test_domain_terms_scoring.py` — unigram ratio matches `hot_words.rank_hot_words` on same input; bigram gmean within 1%; OOV floor; stopword n-gram skipping.
- `tests/test_domain_terms_e2e.py` — temp vault with `raw/a.md: "הAPI של המודל. Finetuning LoRA."`; asserts `terms.csv` has `api (mixed)` with variant `הAPI`, Hebrew grouping `שמירה/שומרים→שמר`; `raw_md` preference over `raw`; fallback when `raw_md` missing; `variants.json` round-trip.

Add `tests/fixtures/domain_terms/` with 2 synthetic bilingual md files for fixtures. No real vault data copied.

### 4. Docs

- Append row to `docs/superpowers/plans/document_convertion_pipeline.md` module table for new script.
- Add short usage section to `instructions.md` if present.

## Files to Modify / Create

- **Create** `scripts/extract_domain_terms.py` (primary change, ~400 lines)
- **Create** `tests/test_domain_terms_tokenization.py`, `tests/test_domain_terms_scoring.py`, `tests/test_domain_terms_e2e.py`, `tests/fixtures/domain_terms/*.md`
- **Modify** `docs/superpowers/plans/document_convertion_pipeline.md` (one table row)
- **Generated (gitignored/waived)** `data/domain_terms/{terms.csv,variants.json,translation_seed.csv,code_words.*,subdomain_keywords.json,report.json}` — do not commit

## Risks

- YAP is Windows `deps/yap/yap.exe` — Linux CI will fail fast; document platform gate or vendor Linux binary.
- Over-stripping `שלAPI` where `ם` is not a proclitic — guarded by prefix validation → ambiguous bucket.
- N-gram sparsity on 11-file demo vault — adaptive `min_count` (2 for bigrams) and warn in `report.json` if <10 trigrams.
- Wordfreq OOV floor could surface inventeds — mitigated by `corpus_count >=3` gate.

## Verification

```bash
# in worktree .claude/worktrees/domain-terms
python scripts/extract_domain_terms.py . --top-n 200
cat data/domain_terms/terms.csv | head -20
cat data/domain_terms/variants.json | head -40
# mixed correctness
python -c "from scripts.extract_domain_terms import normalize_mixed; print(normalize_mixed('הAPI')); print(normalize_mixed('וה-API'))"
pytest tests/test_domain_terms*.py -v
pytest tests/test_hebrew_yap_stemmer.py tests/test_hot_words.py -v  # regression: existing hot_words unchanged
# compare baseline
diff <(cut -d, -f2 data/hot_words.csv | head -20) <(cut -d, -f2 data/domain_terms/terms.csv | head -20) || true
```

Manual checks: confirm `הAPI` variants map to `api`, `code_words.txt` contains `api/lora/qlora`, `translation_seed.csv` lists `mixed` terms with `suggested_en`, `subdomain_keywords.json` is deterministic across two runs (`diff` identical).
