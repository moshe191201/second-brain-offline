"""Tests for domain term tokenization / mixed normalization."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from extract_domain_terms import classify_token, normalize_mixed, normalize_en, RAW_WORD_RE, PROCLITICS


class TestClassifyToken(unittest.TestCase):
    def test_pure_en(self):
        self.assertEqual(classify_token("API"), "en")
        self.assertEqual(classify_token("Finetuning"), "en")

    def test_pure_he(self):
        self.assertEqual(classify_token("שלום"), "he")
        self.assertEqual(classify_token("מודל"), "he")

    def test_mixed_h_prefix(self):
        self.assertEqual(classify_token("הAPI"), "mixed")
        self.assertEqual(classify_token("והAPI"), "mixed")
        self.assertEqual(classify_token("לAPI"), "mixed")

    def test_mixed_with_hyphen(self):
        self.assertEqual(classify_token("ה-API"), "mixed")
        self.assertEqual(classify_token("וה-API"), "mixed")


class TestNormalizeMixed(unittest.TestCase):
    def test_strip_he(self):
        norm, prefix = normalize_mixed("הAPI")
        self.assertEqual(norm, "api")
        self.assertEqual(prefix, "ה")

    def test_strip_ve_he(self):
        norm, prefix = normalize_mixed("והAPI")
        self.assertEqual(norm, "api")
        self.assertEqual(prefix, "וה")

    def test_strip_with_hyphen(self):
        norm, prefix = normalize_mixed("ה-API")
        self.assertEqual(norm, "api")
        self.assertEqual(prefix, "ה")

    def test_strip_lamed(self):
        norm, prefix = normalize_mixed("לAPI")
        self.assertEqual(norm, "api")
        self.assertEqual(prefix, "ל")

    def test_non_proclitic_not_stripped(self):
        # ם is not a proclitic — should NOT strip
        norm, prefix = normalize_mixed("שלוםAPI")
        self.assertEqual(prefix, "")
        self.assertEqual(norm, "שלוםapi".lower())

    def test_k8s_mixed(self):
        norm, prefix = normalize_mixed("הK8s")
        self.assertEqual(norm, "k8s")
        self.assertEqual(prefix, "ה")


class TestRawWordRe(unittest.TestCase):
    def test_extract_mixed(self):
        text = "הAPI ו-API שלום Finetuning"
        toks = RAW_WORD_RE.findall(text)
        self.assertIn("הAPI", toks)
        self.assertIn("שלום", toks)
        self.assertIn("Finetuning", toks)

    def test_hyphen_kept(self):
        self.assertIn("ה-API", RAW_WORD_RE.findall("ה-API"))

    def test_digits_k8s(self):
        toks = RAW_WORD_RE.findall("K8s הK8s ל-K8s")
        self.assertIn("K8s", toks)
        self.assertIn("הK8s", toks)
        self.assertIn("ל-K8s", toks)


class TestNormalizeEn(unittest.TestCase):
    def test_lower(self):
        self.assertEqual(normalize_en("API"), "api")
        self.assertEqual(normalize_en("LoRA"), "lora")


if __name__ == "__main__":
    unittest.main()
