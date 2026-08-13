#!/usr/bin/env python3
"""Extract domain-specific terms (Hebrew + English + mixed like הAPI) from raw_md.

Deterministic, no deep learning.  Uses wordfreq for internet baselines (same
ratio as hot_words.py) and extends to bigrams/trigrams + mixed-token
normalization.

Mixed-token rule: Hebrew proclitic prefix (ה/ל/ב/מ/ו/ש/כ and combos like וה)
optionally hyphenated, attached to an English stem (e.g. הAPI -> api).  The
original surface is preserved in variants.json for correctness.

Outputs (under data/domain_terms/):
  terms.csv, variants.json, translation_seed.csv, code_words.txt/.csv,
  subdomain_keywords.json, report.json

All dependencies are required — script fails fast if wordfreq/YAP is missing.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Fail-fast dependency checks
# ---------------------------------------------------------------------------
try:
    import wordfreq  # noqa: F401
    from wordfreq import word_frequency
except ImportError:
    print("ERROR: wordfreq 3.1.1 required — pip install wordfreq==3.1.1", file=sys.stderr)
    sys.exit(1)

# Ensure scripts/ is on path for sibling imports (needed when imported via tests)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# YAP — hard dependency (do not silently fall back)
try:
    from hebrew_yap_stemmer import _find_yap_exe as _yap_find  # noqa: F401
    _yap_find()
except FileNotFoundError as _e:
    print(f"ERROR: YAP binary missing — {_e}", file=sys.stderr)
    sys.exit(1)

from hebrew_yap_stemmer import root_keys as _hb_root_keys  # noqa: E402
from hebrew_yap_stemmer import analyze_tokens as _hb_analyze  # noqa: E402

from hot_words import _ENGLISH_STOP_WORDS, _HB_STOP_WORDS  # noqa: E402

# sklearn is optional unless subdomain clustering requested
_SKLEARN_AVAILABLE = False
try:
    import sklearn  # noqa: F401
    _SKLEARN_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HEBREW_RANGE = "֐-׿"
HEBREW_CHAR_RE = re.compile(f"[{HEBREW_RANGE}]")

# Extraction: keeps optional hyphen so ה-API stays one token.
# Single-char proclitic + hyphen + English (ה-API) must be kept, so allow
# 1-char prefix before hyphen as alternative.
RAW_WORD_RE = re.compile(rf"(?:[A-Za-z{HEBREW_RANGE}]{{2,}}(?:-[A-Za-z{HEBREW_RANGE}]{{1,}})?|[A-Za-z{HEBREW_RANGE}]-[A-Za-z{HEBREW_RANGE}]{{1,}})")

# Proclitic letters that can attach to English stems
PROCLITICS = set("הלבמושכ")
# Mixed: leading Hebrew run + optional hyphen + English stem
MIXED_SPLIT_RE = re.compile(rf"^([{HEBREW_RANGE}]+)-?([A-Za-z][A-Za-z0-9_\-]*)")

# Code-word patterns
_RE_ACRONYM = re.compile(r"^[A-Z]{2,}$")
_RE_CAMEL = re.compile(r"^[a-z]+([A-Z][a-z]+)+$")
_RE_SNAKE = re.compile(r"^[a-z]+_[a-z_]+$")
_RE_KEBAB = re.compile(r"^[a-z]+-[a-z\-]+$")

OOV_FLOOR = 1e-9

# ---------------------------------------------------------------------------
# Token classification & normalization
# ---------------------------------------------------------------------------

def classify_token(tok: str) -> str:
    """Return 'he' | 'en' | 'mixed' for a raw token."""
    he = sum(1 for c in tok if HEBREW_CHAR_RE.match(c))
    en = sum(1 for c in tok if ("A" <= c <= "Z" or "a" <= c <= "z"))
    if he > 0 and en > 0:
        return "mixed"
    letters = [c for c in tok if c.isalpha()]
    if not letters:
        return "en"
    he_ratio = sum(1 for c in letters if HEBREW_CHAR_RE.match(c)) / len(letters)
    return "he" if he_ratio >= 0.6 else "en"


def normalize_en(tok: str) -> str:
    return tok.lower()


def normalize_mixed(tok: str) -> tuple[str, str]:
    """Return (normalized_en, he_prefix) for a mixed token.

    Strips only if prefix is exclusively proclitic letters and remainder is
    a valid English stem.  Otherwise returns (tok.lower(), '') so surface is
    preserved without corrupting.
    """
    m = MIXED_SPLIT_RE.match(tok)
    if not m:
        return tok.lower(), ""
    he_prefix, en_stem = m.group(1), m.group(2)
    if len(en_stem) < 2:
        return tok.lower(), ""
    # Validate prefix chars are all proclitics
    if any(c not in PROCLITICS for c in he_prefix):
        return tok.lower(), ""
    return en_stem.lower(), he_prefix


# ---------------------------------------------------------------------------
# Corpus helpers
# ---------------------------------------------------------------------------

def resolve_corpus_dir(vault_root: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        p = Path(explicit)
        if not p.is_dir():
            print(f"ERROR: explicit input dir not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p
    raw_md = vault_root / "raw_md"
    raw = vault_root / "raw"
    if raw_md.is_dir() and any(raw_md.rglob("*.md")):
        return raw_md
    if raw.is_dir() and any(raw.rglob("*.md")):
        return raw
    print(f"ERROR: neither raw_md/ nor raw/ with *.md found under {vault_root}", file=sys.stderr)
    sys.exit(1)


def _strip_frontmatter(text: str) -> str:
    lines = text.split("\n")
    body_lines: list[str] = []
    in_fm = False
    for line in lines:
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if not in_fm:
            body_lines.append(line)
    return "\n".join(body_lines)


def _clean_body(body: str) -> str:
    body = re.sub(r"!\[[^]]*\]\([^)]*\)", "", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"[^\s]+@[^\s]+", "", body)
    return body


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def scan_corpus(corpus_dir: Path):
    """Scan corpus_dir recursively, return counts + metadata.

    Returns dict with:
      unigram_counts, bigram_counts, trigram_counts, variant_map,
      he_prefix_map, doc_freq, doc_terms, file_count, total_chars,
      input_dir
    """
    md_files = sorted(corpus_dir.rglob("*.md"))
    if not md_files:
        print(f"ERROR: no markdown files in {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    unigram_counts: Counter = Counter()
    bigram_counts: Counter = Counter()
    trigram_counts: Counter = Counter()
    variant_map: dict[str, Counter] = defaultdict(Counter)
    he_prefix_map: dict[str, Counter] = defaultdict(Counter)
    doc_freq: Counter = Counter()
    doc_terms: list[set[str]] = []  # per-doc normalized unigram sets for TF-IDF
    doc_names: list[str] = []
    # For code-word backtick detection
    backtick_terms: set[str] = set()

    total_chars = 0
    # Collect Hebrew surfaces for batched YAP
    # We process per-file to keep variant_map accurate, but YAP batch is per-file too
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        body = _clean_body(_strip_frontmatter(text))
        total_chars += len(body)

        # Detect terms inside backticks for code-word signal
        bt_raw = re.findall(r"`([^`]+)`", body)
        bt_norms: set[str] = set()
        for bt in bt_raw:
            for w in re.findall(r"[A-Za-z]{2,}", bt):
                bt_norms.add(w.lower())

        raw_tokens = RAW_WORD_RE.findall(body)
        if not raw_tokens:
            doc_terms.append(set())
            doc_names.append(str(md_file.relative_to(corpus_dir)))
            continue

        # Classify and normalize in order
        normalized_stream: list[str] = []
        norm_langs: list[str] = []  # parallel lang for each normalized token
        he_surfaces: list[str] = []
        he_positions: list[int] = []  # index in normalized_stream where he will go

        # First pass: handle en/mixed immediately, collect he
        # We need to emit in order, so track placeholder for he
        temp_stream: list[str | None] = []
        temp_langs: list[str | None] = []
        he_surface_by_pos: dict[int, str] = {}

        for tok in raw_tokens:
            cls = classify_token(tok)
            if cls == "en":
                norm = normalize_en(tok)
                if norm in _ENGLISH_STOP_WORDS or len(norm) <= 1 or norm.isdigit():
                    continue
                temp_stream.append(norm)
                temp_langs.append("en")
                variant_map[norm][tok] += 1
            elif cls == "mixed":
                norm, prefix = normalize_mixed(tok)
                # If prefix stripped, norm is English stem; else norm is lowercased surface
                # Still check stopwords on the English side only if stripped
                if prefix:
                    if norm in _ENGLISH_STOP_WORDS or len(norm) <= 1:
                        continue
                    temp_stream.append(norm)
                    temp_langs.append("mixed")
                    variant_map[norm][tok] += 1
                    he_prefix_map[norm][prefix] += 1
                else:
                    # Non-proclitic mixed: keep surface lowercased, treat as mixed
                    if len(norm) <= 1:
                        continue
                    temp_stream.append(norm)
                    temp_langs.append("mixed")
                    variant_map[norm][tok] += 1
            else:  # he
                if tok in _HB_STOP_WORDS or len(tok) <= 1:
                    continue
                # Placeholder — resolve via YAP batch
                pos = len(temp_stream)
                temp_stream.append(None)  # type: ignore
                temp_langs.append(None)  # type: ignore
                he_surfaces.append(tok)
                he_positions.append(pos)
                he_surface_by_pos[pos] = tok

        # Batch YAP for Hebrew in this file
        if he_surfaces:
            try:
                # Map surface -> normalized root key via YAP
                # Use root_keys for grouping but also keep lemma mapping
                pairs = _hb_analyze(he_surfaces)
                # pairs is (original, lemma); map original index
                lemma_by_surface: dict[str, str] = {}
                for orig, lemma in pairs:
                    lemma_by_surface[orig] = lemma
                # Also compute root_keys for all surfaces
                keys = _hb_root_keys(he_surfaces)
                # root_keys returns set, need per-surface mapping.
                # Recompute per-surface via same logic as root_keys but per token
                # For correctness, compute per-token root key
                # We'll approximate: for each surface, get its lemma then apply skeleton
                # Reuse _hb_root_keys internals by calling per token via single batch already done,
                # but root_keys collapses — so recompute skeleton per lemma
                import hebrew_yap_stemmer as _hys
                per_surface_norm: dict[str, str] = {}
                for surf in he_surfaces:
                    lemma = lemma_by_surface.get(surf, surf)
                    reduced = _hys._strip_hb_suffix(lemma)
                    weak = {"א", "ה", "ו", "י"}
                    strong = [c for c in reduced if "א" <= c <= "ת" and c not in weak]
                    if len(strong) >= 3:
                        per_surface_norm[surf] = "".join(strong[:3])
                    else:
                        per_surface_norm[surf] = reduced
                for pos in he_positions:
                    surf = he_surface_by_pos[pos]
                    norm = per_surface_norm.get(surf, surf)
                    if norm in _HB_STOP_WORDS or len(norm) <= 1:
                        temp_stream[pos] = ""  # mark for removal
                        continue
                    temp_stream[pos] = norm
                    temp_langs[pos] = "he"
                    variant_map[norm][surf] += 1
            except Exception as e:
                print(f"[WARN] YAP failed for file {md_file}: {e}", file=sys.stderr)
                # Fall back to surface as normalized
                for pos in he_positions:
                    surf = he_surface_by_pos[pos]
                    temp_stream[pos] = surf
                    temp_langs[pos] = "he"
                    variant_map[surf][surf] += 1

        # Remove placeholders that were stopwords
        normalized_stream = [t for t in temp_stream if t]  # type: ignore
        norm_langs = [l for t, l in zip(temp_stream, temp_langs) if t]  # type: ignore

        # Update unigram counts and doc freq
        seen_in_doc: set[str] = set()
        for norm in normalized_stream:
            unigram_counts[norm] += 1
            seen_in_doc.add(norm)
            if norm in bt_norms:
                backtick_terms.add(norm)
        for norm in seen_in_doc:
            doc_freq[norm] += 1
        doc_terms.append(seen_in_doc)
        doc_names.append(str(md_file.relative_to(corpus_dir)))

        # N-grams from normalized stream (skip windows with stopwords — already filtered)
        for i in range(len(normalized_stream) - 1):
            bg = f"{normalized_stream[i]} {normalized_stream[i+1]}"
            bigram_counts[bg] += 1
        for i in range(len(normalized_stream) - 2):
            tg = f"{normalized_stream[i]} {normalized_stream[i+1]} {normalized_stream[i+2]}"
            trigram_counts[tg] += 1

    return {
        "unigram_counts": unigram_counts,
        "bigram_counts": bigram_counts,
        "trigram_counts": trigram_counts,
        "variant_map": variant_map,
        "he_prefix_map": he_prefix_map,
        "doc_freq": doc_freq,
        "doc_terms": doc_terms,
        "doc_names": doc_names,
        "backtick_terms": backtick_terms,
        "file_count": len(md_files),
        "total_chars": total_chars,
        "input_dir": str(corpus_dir),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _base_freq(term: str, lang: str) -> float:
    """wordfreq baseline for a single term, with OOV floor."""
    try:
        f = word_frequency(term, lang)
    except (KeyError, ValueError):
        f = 0.0
    return f if f > 0 else OOV_FLOOR


def base_ngram_freq(terms: list[str], langs: list[str]) -> float:
    """Geometric mean of constituent wordfreq baselines."""
    freqs: list[float] = []
    for w, lang in zip(terms, langs):
        eff_lang = "en" if lang == "mixed" else lang
        # For n-gram constituents that are Hebrew root keys, wordfreq with 'he'
        # may be valid; try he first, fall back to floor
        f = _base_freq(w, eff_lang)
        freqs.append(f)
    # geometric mean
    log_sum = sum(math.log(f) for f in freqs)
    return math.exp(log_sum / len(freqs))


def _detect_lang(term: str, variant_map, he_prefix_map) -> str:
    """Detect lang for a normalized term (unigram) via variant evidence."""
    if term in he_prefix_map and he_prefix_map[term]:
        return "mixed"
    # Check if any variant contains Hebrew
    for surf in variant_map.get(term, {}):
        if HEBREW_CHAR_RE.search(surf):
            # If term itself is Hebrew chars -> he, else mixed
            if HEBREW_CHAR_RE.search(term):
                return "he"
            return "mixed"
    if HEBREW_CHAR_RE.search(term):
        return "he"
    return "en"


def _ngram_lang(ngram: str, variant_map, he_prefix_map) -> str:
    parts = ngram.split()
    langs = [_detect_lang(p, variant_map, he_prefix_map) for p in parts]
    if len(set(langs)) == 1:
        return langs[0]
    if "mixed" in langs:
        return "mixed"
    return "multi"


def score_terms(scan: dict, top_n: int = 1000, min_count_uni: int = 3,
                min_count_bi: int = 2, min_count_tri: int = 2):
    scored: list[dict] = []

    variant_map = scan["variant_map"]
    he_prefix_map = scan["he_prefix_map"]
    doc_freq = scan["doc_freq"]

    # Unigrams
    for term, cnt in scan["unigram_counts"].items():
        if cnt < min_count_uni:
            continue
        lang = _detect_lang(term, variant_map, he_prefix_map)
        eff_lang = "en" if lang == "mixed" else lang
        base = _base_freq(term, eff_lang)
        # For he/mixed that are English stems via mixed, base is en; for pure he, base is he
        # If term is Hebrew root key but wordfreq returns floor, still keep it
        ratio = cnt / base
        log_ratio = math.log10(ratio) if ratio > 0 else 0
        scored.append({
            "term": term, "n": 1, "lang": lang, "corpus_count": cnt,
            "doc_freq": doc_freq.get(term, 0), "base_freq": base,
            "ratio": ratio, "log_ratio": log_ratio,
        })

    # Bigrams
    for term, cnt in scan["bigram_counts"].items():
        if cnt < min_count_bi:
            continue
        parts = term.split()
        langs = [_detect_lang(p, variant_map, he_prefix_map) for p in parts]
        base = base_ngram_freq(parts, langs)
        ratio = cnt / base
        log_ratio = math.log10(ratio) if ratio > 0 else 0
        scored.append({
            "term": term, "n": 2, "lang": _ngram_lang(term, variant_map, he_prefix_map),
            "corpus_count": cnt, "doc_freq": 0, "base_freq": base,
            "ratio": ratio, "log_ratio": log_ratio,
        })

    # Trigrams
    for term, cnt in scan["trigram_counts"].items():
        if cnt < min_count_tri:
            continue
        parts = term.split()
        langs = [_detect_lang(p, variant_map, he_prefix_map) for p in parts]
        base = base_ngram_freq(parts, langs)
        ratio = cnt / base
        log_ratio = math.log10(ratio) if ratio > 0 else 0
        scored.append({
            "term": term, "n": 3, "lang": _ngram_lang(term, variant_map, he_prefix_map),
            "corpus_count": cnt, "doc_freq": 0, "base_freq": base,
            "ratio": ratio, "log_ratio": log_ratio,
        })

    scored.sort(key=lambda x: (-x["log_ratio"], -x["corpus_count"], x["term"]))
    return scored[:top_n]


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_terms_csv(scored: list[dict], variant_map, path: Path):
    fieldnames = ["rank", "term", "n", "lang", "corpus_count", "doc_freq", "base_freq", "ratio", "log_ratio", "variants"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i, row in enumerate(scored, 1):
            variants = ";".join(sorted(variant_map.get(row["term"].split()[0], {}).keys())[:5]) if row["n"] == 1 else ""
            # For n>1, variant summary is less meaningful — leave blank
            if row["n"] == 1:
                variants = ";".join(sorted(variant_map.get(row["term"], {}).keys()))
            w.writerow({
                "rank": i, "term": row["term"], "n": row["n"], "lang": row["lang"],
                "corpus_count": row["corpus_count"], "doc_freq": row["doc_freq"],
                "base_freq": row["base_freq"], "ratio": row["ratio"], "log_ratio": row["log_ratio"],
                "variants": variants,
            })


def write_variants_json(scored: list[dict], variant_map, he_prefix_map, path: Path):
    out: dict = {}
    for row in scored:
        term = row["term"]
        if row["n"] != 1:
            continue
        variants = variant_map.get(term, {})
        if not variants:
            continue
        entry: dict = {
            "normalized": term,
            "lang": row["lang"],
            "corpus_count": row["corpus_count"],
            "variants": dict(variants),
        }
        if term in he_prefix_map and he_prefix_map[term]:
            entry["he_prefixes"] = dict(he_prefix_map[term])
        out[term] = entry
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def write_translation_seed(scored: list[dict], variant_map, scan: dict, path: Path):
    fieldnames = ["term", "lang", "surface_variants", "corpus_count", "log_ratio", "needs_translation", "suggested_en", "example_doc"]
    # Build example_doc map: first doc containing term
    term_to_doc: dict[str, str] = {}
    for term in [r["term"] for r in scored if r["n"] == 1 and r["lang"] in ("he", "mixed")]:
        for idx, doc_set in enumerate(scan["doc_terms"]):
            if term in doc_set:
                term_to_doc[term] = scan["doc_names"][idx]
                break
    rows = []
    for row in scored:
        if row["n"] != 1 or row["lang"] not in ("he", "mixed"):
            continue
        term = row["term"]
        variants = ";".join(sorted(variant_map.get(term, {}).keys()))
        suggested = term if row["lang"] == "mixed" else ""
        rows.append({
            "term": term, "lang": row["lang"], "surface_variants": variants,
            "corpus_count": row["corpus_count"], "log_ratio": row["log_ratio"],
            "needs_translation": "true", "suggested_en": suggested,
            "example_doc": term_to_doc.get(term, ""),
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_code_words(scored: list[dict], variant_map, backtick_terms: set[str], out_txt: Path, out_csv: Path):
    code_rows: list[dict] = []
    for row in scored:
        if row["n"] != 1:
            continue
        term = row["term"]
        lang = row["lang"]
        base = row["base_freq"]
        cnt = row["corpus_count"]
        matched = ""
        is_code = False
        if lang == "mixed":
            is_code = True
            matched = "mixed"
        elif base < 1e-7 and cnt >= 3:
            is_code = True
            matched = "rare"
        elif _RE_ACRONYM.match(term):
            is_code = True
            matched = "acronym"
        elif _RE_CAMEL.match(term):
            is_code = True
            matched = "camelCase"
        elif _RE_SNAKE.match(term):
            is_code = True
            matched = "snake"
        elif _RE_KEBAB.match(term):
            is_code = True
            matched = "kebab"
        elif term in backtick_terms:
            is_code = True
            matched = "backtick"
        if is_code:
            example = next(iter(sorted(variant_map.get(term, {}).keys())), term)
            code_rows.append({
                "term": term, "corpus_count": cnt, "log_ratio": row["log_ratio"],
                "pattern_matched": matched, "example_surface": example,
            })
    code_rows.sort(key=lambda x: -x["log_ratio"])
    with open(out_txt, "w", encoding="utf-8") as f:
        for r in code_rows:
            f.write(r["term"] + "\n")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["term", "corpus_count", "log_ratio", "pattern_matched", "example_surface"])
        w.writeheader()
        w.writerows(code_rows)


def write_subdomain_keywords(scored: list[dict], scan: dict, path: Path):
    top_terms = [r["term"] for r in scored if r["n"] == 1][:500]
    if not top_terms or len(scan["doc_terms"]) < 2:
        # Fallback: simple doc_freq buckets
        result = {
            "num_clusters": 0,
            "clusters": [],
            "unclustered_keywords": top_terms[:20],
            "note": "not enough docs for clustering",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    if not _SKLEARN_AVAILABLE:
        # Quartile fallback
        result = {
            "num_clusters": 0,
            "clusters": [],
            "unclustered_keywords": top_terms[:50],
            "note": "sklearn not available — quartile fallback",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    from sklearn.feature_extraction.text import TfidfTransformer
    import numpy as np

    # Build doc-term count matrix for top_terms
    n_docs = len(scan["doc_terms"])
    n_terms = len(top_terms)
    term_idx = {t: i for i, t in enumerate(top_terms)}
    import numpy as _np
    mat = _np.zeros((n_docs, n_terms), dtype=float)
    for doc_i, doc_set in enumerate(scan["doc_terms"]):
        # Count occurrences per doc: approximate via scan unigram counts distributed?
        # We have doc_terms as sets, so use binary presence; TF-IDF will still separate
        for t in doc_set:
            if t in term_idx:
                mat[doc_i, term_idx[t]] = 1.0

    transformer = TfidfTransformer()
    tfidf = transformer.fit_transform(mat).toarray()

    # Deterministic KMeans
    from sklearn.cluster import KMeans
    n_clusters = min(5, n_docs)
    if n_clusters < 2:
        n_clusters = 2 if n_docs >= 2 else 1
    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=1)
    labels = kmeans.fit_predict(tfidf)

    clusters = []
    for cid in range(n_clusters):
        doc_indices = [i for i, l in enumerate(labels) if l == cid]
        # Top keywords for cluster: highest mean tf-idf
        mean_tfidf = tfidf[doc_indices].mean(axis=0) if doc_indices else _np.zeros(n_terms)
        top_idx = _np.argsort(mean_tfidf)[::-1][:8]
        keywords = [top_terms[i] for i in top_idx if mean_tfidf[i] > 0][:8]
        docs = [scan["doc_names"][i] for i in doc_indices]
        label_hint = "-".join(keywords[:3]) if keywords else f"cluster-{cid}"
        clusters.append({
            "id": f"subdomain_{cid}",
            "label_hint": label_hint,
            "keywords": keywords,
            "doc_count": len(doc_indices),
            "docs": docs,
        })

    # Unclustered: terms not in any cluster top keywords
    clustered_terms = {k for c in clusters for k in c["keywords"]}
    unclustered = [t for t in top_terms if t not in clustered_terms][:20]

    result = {"num_clusters": n_clusters, "clusters": clusters, "unclustered_keywords": unclustered}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract domain terms (he/en/mixed) from raw_md")
    parser.add_argument("vault_root", nargs="?", default=".", help="Vault root (contains raw/ and raw_md/)")
    parser.add_argument("--input", dest="input_dir", default=None, help="Explicit corpus dir override")
    parser.add_argument("--output-dir", default=None, help="Output dir (default: <vault>/data/domain_terms)")
    parser.add_argument("--top-n", type=int, default=1000)
    parser.add_argument("--min-count", type=int, default=3, help="Unigram min count (bigram/trigram use 2)")
    parser.add_argument("--ngrams", default="1,2,3", help="Comma-separated n values, e.g. 1,2")
    args = parser.parse_args()

    vault_root = Path(args.vault_root).resolve()
    corpus_dir = resolve_corpus_dir(vault_root, Path(args.input_dir) if args.input_dir else None)

    output_dir = Path(args.output_dir) if args.output_dir else vault_root / "data" / "domain_terms"
    output_dir.mkdir(parents=True, exist_ok=True)

    n_vals = {int(x.strip()) for x in args.ngrams.split(",") if x.strip()}
    print(f"=== Scanning corpus: {corpus_dir} ===")
    scan = scan_corpus(corpus_dir)
    print(f"Processed {scan['file_count']} markdown files ({scan['total_chars']:,} chars)")
    print(f"Unique unigrams: {len(scan['unigram_counts'])}  bigrams: {len(scan['bigram_counts'])}  trigrams: {len(scan['trigram_counts'])}")

    if not scan["unigram_counts"]:
        print("No terms found after filtering.", file=sys.stderr)
        sys.exit(1)

    print("\n=== Scoring ===")
    scored = score_terms(scan, top_n=args.top_n, min_count_uni=args.min_count)
    # Filter by requested n
    scored = [r for r in scored if r["n"] in n_vals]
    scored = scored[:args.top_n]
    print(f"Scored {len(scored)} terms (top {min(len(scored), 10)} shown):")
    for i, r in enumerate(scored[:10], 1):
        print(f"  {i:>3} {r['term']:<30} n={r['n']} {r['lang']:>6} cnt={r['corpus_count']:>4} log_ratio={r['log_ratio']:.2f}")

    # Write outputs
    write_terms_csv(scored, scan["variant_map"], output_dir / "terms.csv")
    write_variants_json(scored, scan["variant_map"], scan["he_prefix_map"], output_dir / "variants.json")
    write_translation_seed(scored, scan["variant_map"], scan, output_dir / "translation_seed.csv")
    write_code_words(scored, scan["variant_map"], scan["backtick_terms"], output_dir / "code_words.txt", output_dir / "code_words.csv")
    write_subdomain_keywords(scored, scan, output_dir / "subdomain_keywords.json")

    # Report
    ngram_counts = {
        "unigram": len(scan["unigram_counts"]),
        "bigram": len(scan["bigram_counts"]),
        "trigram": len(scan["trigram_counts"]),
    }
    report = {
        "input_dir": scan["input_dir"],
        "file_count": scan["file_count"],
        "total_chars": scan["total_chars"],
        "unique_terms": len(scan["unigram_counts"]),
        "ngram_counts": ngram_counts,
        "top_n": args.top_n,
        "min_count": args.min_count,
        "ngrams": sorted(n_vals),
        "scored_count": len(scored),
        "warnings": [],
    }
    if ngram_counts["trigram"] < 10:
        report["warnings"].append(f"only {ngram_counts['trigram']} trigrams — corpus may be small")
    with open(output_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nOutputs written to: {output_dir}")
    print(f"  terms.csv, variants.json, translation_seed.csv, code_words.txt/.csv, subdomain_keywords.json, report.json")


if __name__ == "__main__":
    main()
