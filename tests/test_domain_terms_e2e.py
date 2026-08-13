"""E2E tests for domain term extraction."""

import json
import tempfile
import unittest
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from extract_domain_terms import scan_corpus, score_terms, resolve_corpus_dir


class TestResolveCorpusDir(unittest.TestCase):
    def test_prefers_raw_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "raw").mkdir()
            (vault / "raw" / "a.md").write_text("# hello", encoding="utf-8")
            (vault / "raw_md").mkdir()
            (vault / "raw_md" / "b.md").write_text("# from raw_md", encoding="utf-8")
            got = resolve_corpus_dir(vault)
            self.assertEqual(got, vault / "raw_md")

    def test_fallback_to_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "raw").mkdir()
            (vault / "raw" / "a.md").write_text("# hello", encoding="utf-8")
            got = resolve_corpus_dir(vault)
            self.assertEqual(got, vault / "raw")

    def test_explicit_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            custom = Path(tmp) / "custom"
            custom.mkdir()
            (custom / "x.md").write_text("hello", encoding="utf-8")
            got = resolve_corpus_dir(vault, custom)
            self.assertEqual(got, custom)


class TestScanCorpusMixed(unittest.TestCase):
    def test_mixed_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            (corpus / "a.md").write_text("הAPI של המודל. The API is here. Finetuning LoRA. Finetuning LoRA again. Finetuning third.", encoding="utf-8")
            scan = scan_corpus(corpus)
            # הAPI should normalize to api and merge with API
            self.assertIn("api", scan["unigram_counts"])
            self.assertGreaterEqual(scan["unigram_counts"]["api"], 2)
            # variant map preserves surface
            self.assertIn("הAPI", scan["variant_map"]["api"])
            # he_prefix_map
            self.assertIn("ה", scan["he_prefix_map"]["api"])

    def test_variant_map_hebrew(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            (corpus / "a.md").write_text("שמירה שומרים שימרתי שמירה שומרים", encoding="utf-8")
            scan = scan_corpus(corpus)
            # All should collapse to same root key (שמר or similar)
            # At least variant map has one key with multiple surfaces
            found_multi = any(len(v) > 1 for v in scan["variant_map"].values())
            self.assertTrue(found_multi, f"variant_map: {dict(scan['variant_map'])}")


class TestScoreTerms(unittest.TestCase):
    def test_scoring_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            (corpus / "a.md").write_text("Finetuning LoRA QLoRA finetuning LoRA QLoRA finetuning", encoding="utf-8")
            scan = scan_corpus(corpus)
            scored = score_terms(scan, top_n=10)
            self.assertGreater(len(scored), 0)
            terms = [r["term"] for r in scored]
            self.assertIn("finetuning", terms)


class TestNgramCounting(unittest.TestCase):
    def test_bigram_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            (corpus / "a.md").write_text("Finetuning LoRA Finetuning LoRA Finetuning LoRA", encoding="utf-8")
            scan = scan_corpus(corpus)
            self.assertIn("finetuning lora", scan["bigram_counts"])


if __name__ == "__main__":
    unittest.main()
