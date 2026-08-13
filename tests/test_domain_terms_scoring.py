"""Tests for domain term scoring."""

import unittest
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from extract_domain_terms import base_ngram_freq, _base_freq
from wordfreq import word_frequency


class TestBaseFreq(unittest.TestCase):
    def test_oov_floor(self):
        # invented token should floor to 1e-9, not skip
        f = _base_freq("zzqwert_nonexistent_xyz", "en")
        self.assertEqual(f, 1e-9)

    def test_known_word(self):
        f = _base_freq("the", "en")
        self.assertGreater(f, 1e-3)


class TestBaseNgramFreq(unittest.TestCase):
    def test_gmean(self):
        # gmean manual
        f1 = word_frequency("lora", "en")
        if f1 <= 0:
            f1 = 1e-9
        f2 = word_frequency("finetuning", "en")
        if f2 <= 0:
            f2 = 1e-9
        expected = math.exp((math.log(f1) + math.log(f2)) / 2)
        got = base_ngram_freq(["lora", "finetuning"], ["en", "en"])
        self.assertAlmostEqual(got, expected, places=10)

    def test_mixed_treated_as_en(self):
        got_en = base_ngram_freq(["api"], ["en"])
        got_mixed = base_ngram_freq(["api"], ["mixed"])
        self.assertAlmostEqual(got_en, got_mixed, places=10)

    def test_oov_in_ngram(self):
        # one OOV should floor, not crash
        got = base_ngram_freq(["lora", "zzqwert_nonexistent_xyz"], ["en", "en"])
        self.assertGreater(got, 0)
        self.assertLess(got, 1e-4)


class TestNgramStopwordSkipping(unittest.TestCase):
    def test_bigram_with_stopword_not_counted(self):
        # This is verified via scan_corpus e2e; here just sanity that scoring
        # doesn't explode on stopword-containing ngrams — caller should skip them
        # but scorer should still handle them if passed
        f = base_ngram_freq(["the", "model"], ["en", "en"])
        self.assertGreater(f, 0)


if __name__ == "__main__":
    unittest.main()
