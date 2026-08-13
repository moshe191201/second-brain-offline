#!/usr/bin/env python3
"""Find the 1k words with the highest corpus-vs-internet frequency ratio.

Uses wordfreq for internet baselines. Supports English (exact words) and
Hebrew (consonant-skeleton root-key grouping via YAP heuristic).

Output: CSV sorted by ratio desc -- word, lang, corpus_count, ratio, base_freq
"""

from __future__ import annotations

import csv
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# wordfreq imports
# ---------------------------------------------------------------------------
from wordfreq import tokenize, word_frequency

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
_HEBREW_RE = re.compile(r"[֐-׿]")


def _is_hebrew(word: str) -> bool:
    """Return True when >= 60 % of alpha chars are Hebrew."""
    letters = [c for c in word if c.isalpha()]
    if not letters:
        return False
    he = sum(1 for c in letters if _HEBREW_RE.match(c))
    return he / len(letters) >= 0.6


# ---------------------------------------------------------------------------
# YAP morphological analysis (hard dependency)
# ---------------------------------------------------------------------------
from hebrew_yap_stemmer import root_keys as _hb_root_keys


# ---------------------------------------------------------------------------
# English helpers
# ---------------------------------------------------------------------------
_ENGLISH_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "this",
    "that", "these", "those", "it", "its", "i", "me", "my", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "they", "them",
    "their", "what", "which", "who", "whom", "where", "when", "how",
    "not", "no", "nor", "so", "if", "then", "than", "too", "very",
    "just", "about", "above", "after", "again", "all", "am", "any",
    "because", "before", "between", "both", "each", "few", "further",
    "get", "got", "here", "into", "more", "most", "other", "out", "over",
    "own", "same", "such", "there", "through", "under", "until", "up",
    "also", "well", "back", "even", "new", "now", "like", "come",
    "said", "make", "much", "many", "go", "one", "two", "three",
    "down", "still", "since", "while", "used", "use", "using",
    "http", "https", "www", "com", "org", "net", "io", "edu",
})


def _filter_english(tokens: list[str]) -> list[str]:
    result = []
    for t in tokens:
        low = t.lower()
        if low in _ENGLISH_STOP_WORDS:
            continue
        if len(low) <= 1 or low.isdigit():
            continue
        result.append(low)
    return result


# ---------------------------------------------------------------------------
# Hebrew stop words (common function words to exclude)
# ---------------------------------------------------------------------------
_HB_STOP_WORDS = frozenset({
    # Basic particles & prepositions
    "ו", "ב", "כ", "ל", "ש", "מ", "נ", "ת", "א", "ד", "ע", "ה", "ר", "י",
    "כן", "לא", "אבל", "או", "איפה", "מתי", "מי", "מה", "למה", "כמה",
    "אז", "רק", "גם", "עוד", "עכשיו", "קודם", "יכול", "כל", "כמו",
    "אמר", "אומרים", "עושה", "אין", "יש", "של", "לה", "לו", "לי",
    "עם", "כדי", "בין", "לפני", "אחרי", "דרך", "כאשר", "אשר", "אם",
    "בערך", "כרגע", "מאוד", "מעט", "קצת", "יותר", "הכי", "אפשר",
    "בטוח", "בוודאות", "כבר", "עדיין", "אולי", "למשל", "עדיף",
    "חשוב", "צריך", "מצד", "אחד", "אחר", "חלק", "כולל", "לבד",
    "ביחד", "כך", "ככה", "כיצד", "אופן", "מין", "סוג", "נקודה",
    "מידע", "רעיון", "דעה", "תפיסה", "גישה", "כיוון", "למעשה",
    "בפועל", "מעשית", "כנראה", "כאילו",
    # Pronouns & demonstratives
    "הוא", "היא", "הם", "הן", "אני", "אתה", "את", "אנחנו", "אתם",
    "אותו", "אותה", "אותם", "אותן",
    # Common verbs (infinitive/participle)
    "היה", "היו", "עושים", "עשוי", "רוצה", "רוצים", "נתן", "נותן",
    "נותנים", "קיבל", "מקבל", "מקבלים", "עושות",
    # Common adjectives
    "גדול", "גדולה", "גדולים", "קטן", "קטנה", "קטנים", "חדש", "חדשה",
    "חדשים", "ישן", "ישנה", "טוב", "טובה", "טובים", "רע", "מיוחד",
    "מיוחדת", "מיוחדים", "אחר", "אחרת", "אחרים", "אחרות",
    "קל", "קלה", "קלים", "קלות", "קשה", "קשים", "ארוך", "ארוכה",
    "ארוכים", "ארוכות", "אמיתי", "אמיתית", "אמיתיים", "אמיתיות",
    "חשוב", "חשובה", "חשובים", "חשובות", "חזק", "חזקה", "חזקים",
    "חלש", "חלשה", "חלשים", "עיקרי", "עיקרית", "עיקריים", "עיקריות",
    # Adverbs & connectors
    "אפילו", "עדיין", "כעת", "כאן", "שם", "כבר", "עוד", "כמעט",
    "מעולם", "תמיד", "לעיתים", "פעמים", "לפחות", "אחרי", "לפני",
    "אז", "אזכר", "אזכור",
    # Question words
    "למה", "איזה", "איזו", "אילו", "כמה", "מי", "מה",
    "מתי", "איפה", "איך", "האם",
})


def _filter_hebrew(tokens: list[str]) -> list[str]:
    """Remove stopwords, apply YAP-based root-key grouping, return reduced tokens."""
    # Batch root-key computation — one subprocess call for all Hebrew words
    non_trivial = [t for t in tokens if t not in _HB_STOP_WORDS and len(t) > 1]
    if not non_trivial:
        return []
    keys = _hb_root_keys(non_trivial)
    return sorted(keys)


# ---------------------------------------------------------------------------
# Corpus scanning
# ---------------------------------------------------------------------------

def scan_corpus(raw_dir: str) -> dict[str, int]:
    """Scan all .md files in raw_dir and return {reduced_form: count}.

    English: filtered surface forms.
    Hebrew: reduced root keys (suffix-stripped + consonant skeleton).
    """
    counts = Counter()
    md_files = sorted(Path(raw_dir).glob("*.md"))
    total_chars = 0

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")

        # Skip YAML frontmatter (lines between --- delimiters)
        lines = text.split("\n")
        body_lines = []
        in_frontmatter = False
        for line in lines:
            if line.strip() == "---":
                in_frontmatter = not in_frontmatter
                continue
            if not in_frontmatter:
                body_lines.append(line)

        body = "\n".join(body_lines)
        total_chars += len(body)

        # Remove markdown image references, unwrap link text
        body = re.sub(r"!\[[^]]*\]\([^)]*\)", "", body)
        body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
        # Remove HTML tags and email addresses
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"[^\s]+@[^\s]+", "", body)

        # Extract alphanumeric sequences (Latin + Hebrew + digits)
        words_raw = re.findall(r"[A-Za-z0-9֐-׿]{2,}", body)

        for word in words_raw:
            if _is_hebrew(word):
                tokens = tokenize(word, "he")
                filtered = _filter_hebrew(tokens)
                for tok in filtered:
                    counts[tok] += 1
            else:
                tokens = tokenize(word, "en")
                filtered = _filter_english(tokens)
                for tok in filtered:
                    counts[tok] += 1

    print(f"Processed {len(md_files)} markdown files ({total_chars:,} chars)")
    print(f"Total words after filtering: {sum(counts.values()):,}")
    print(f"Unique words: {len(counts)}")
    return dict(counts)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def rank_hot_words(corpus_counts: dict[str, int], top_n: int = 1000, min_count: int = 3) -> list[dict]:
    """Compute corpus/internet frequency ratio for every unique word.

    For each word w:
        ratio = corpus_count(w) / internet_base_freq(w)

    Words must appear >= min_count times AND have a positive wordfreq
    baseline so the comparison is meaningful.

    Returns top-N words sorted by log10(ratio) descending.
    """
    scored = []

    for word, corp_count in corpus_counts.items():
        if corp_count < min_count:
            continue

        lang = "he" if _is_hebrew(word) else "en"

        try:
            base_freq = word_frequency(word, lang)
        except (KeyError, ValueError):
            continue

        if base_freq <= 0:
            # No positive frequency — skip these (too obscure for baselines)
            continue

        ratio = corp_count / base_freq
        log_ratio = math.log10(ratio) if ratio > 0 else 0

        scored.append({
            "word": word,
            "lang": lang,
            "corpus_count": corp_count,
            "base_freq": base_freq,
            "ratio": ratio,
            "log_ratio": log_ratio,
        })

    scored.sort(key=lambda x: x["log_ratio"], reverse=True)
    return scored[:top_n]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_csv(results: list[dict], path: str) -> None:
    fieldnames = ["rank", "word", "lang", "corpus_count", "base_freq", "ratio", "log_ratio"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(results, 1):
            writer.writerow({"rank": i, **{k: row[k] for k in fieldnames[1:]}})


def print_table(results: list[dict], max_display: int = 100) -> None:
    header = f"{'Rank':>5} {'Word':<30} {'Lang':>4} {'Corpus':>7} {'BaseFreq':>12} {'Log(Ratio)':>12}"
    print(header)
    print("-" * len(header))

    for i, row in enumerate(results[:max_display], 1):
        freq_str = f"{row['base_freq']:.2e}" if row['base_freq'] < 1 else f"{row['base_freq']:.4f}"
        print(f"{i:>5} {row['word']:<30} {row['lang']:>4} {row['corpus_count']:>7} {freq_str:>12} {row['log_ratio']:>12.2f}")

    if len(results) > max_display:
        print(f"\n... and {len(results) - max_display} more (see CSV for full list)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    raw_dir = os.path.join(os.path.dirname(__file__), "..", "raw")
    raw_dir = os.path.abspath(raw_dir)

    if not os.path.isdir(raw_dir):
        print(f"ERROR: raw directory not found: {raw_dir}", file=sys.stderr)
        sys.exit(1)

    print("=== Scanning corpus ===")
    corpus_counts = scan_corpus(raw_dir)

    if not corpus_counts:
        print("No words found. Check that raw/ contains markdown files.", file=sys.stderr)
        sys.exit(1)

    print("\n=== Ranking hot words ===")
    results = rank_hot_words(corpus_counts, top_n=1000)

    print(f"\n=== Top {min(len(results), 100)} hot words ===\n")
    print_table(results)

    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "hot_words.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_csv(results, output_path)
    print(f"\nFull results written to: {output_path}")


if __name__ == "__main__":
    main()
