"""Tests for Hebrew translation pipeline: masking, chunking, QA, glossary, ledger."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class TestTranslationCommon(unittest.TestCase):
    def test_common_has_sentinel_helpers(self):
        from translate.translation_common import GLOSSARY_SENTINEL_RE, build_glossary_sentinel, parse_glossary_sentinel, check_glossary_collisions
        self.assertIsNotNone(GLOSSARY_SENTINEL_RE.search("⟦EN:0:Information Security⟧"))
        self.assertEqual(build_glossary_sentinel(0, "Information Security"), "⟦EN:0:Information Security⟧")
        self.assertEqual(parse_glossary_sentinel("⟦EN:0:Information Security⟧"), (0, "Information Security"))
        check_glossary_collisions([{"term_he": "אבטחת מידע", "english": "Information Security", "status": "approved"}])  # no raise

class TestMaskGlossaryTerms(unittest.TestCase):
    def test_mask_simple_and_spacing(self):
        import unittest.mock as mock
        import translate.translate as translate
        with mock.patch("translate.translate._yap_root_keys", side_effect=lambda toks: toks):
            rows = [{"term_he": "אבטחת מידע", "english": "Information Security", "status": "approved"}]
            masked, term_map = translate.mask_glossary_terms("באבטחת מידע חשובה", rows)
            self.assertIn("⟦EN:0:Information Security⟧", masked)
            self.assertTrue(masked.startswith("ב "), f"masked={masked!r} should start with 'ב '")
            self.assertEqual(term_map[0]["occurrences"], 1)

    def test_mask_hDBim_mixed_with_suffix(self):
        import unittest.mock as mock
        import translate.translate as translate
        def fake_roots(toks):
            mapping = {"הDBים": "DB", "המערכות": "מערכת", "מערכות": "מערכת", "מערכת": "מערכת", "DB": "DB"}
            return [mapping.get(t, t) for t in toks]
        with mock.patch("translate.translate._yap_root_keys", side_effect=fake_roots):
            with mock.patch("translate.translate._yap_analyze", return_value=[("הDBים", "DB", "ה", "ים")]):
                rows = [{"term_he": "DB", "english": "DB", "status": "approved"}]
                masked, term_map = translate.mask_glossary_terms("הDBים קרסו", rows)
                self.assertTrue("ה ⟦EN:0:DB⟧ ים" in masked or "ה ⟦EN:0:DB⟧" in masked, f"masked={masked!r}")
                self.assertEqual(term_map[0]["term_he"], "DB")

    def test_mask_hamaarachot_plural(self):
        import unittest.mock as mock
        import translate.translate as translate
        def fake_roots(toks):
            m = {"המערכות": "מערכת", "מערכות": "מערכת", "מערכת": "מערכת"}
            return [m.get(t, t) for t in toks]
        with mock.patch("translate.translate._yap_root_keys", side_effect=fake_roots):
            with mock.patch("translate.translate._yap_analyze", return_value=[("המערכות", "מערכת", "ה", "ות")]):
                rows = [{"term_he": "מערכת", "english": "system", "status": "approved"}]
                masked, term_map = translate.mask_glossary_terms("המערכות פועלות", rows)
                self.assertIn("⟦EN:0:system⟧", masked)
                self.assertIn("ה ", masked)
                self.assertEqual(term_map[0]["occurrences"], 1)

    def test_mask_longest_match_wins(self):
        import unittest.mock as mock
        import translate.translate as translate
        with mock.patch("translate.translate._yap_root_keys", side_effect=lambda toks: toks):
            rows = [
                {"term_he": "מידע", "english": "information", "status": "approved"},
                {"term_he": "אבטחת מידע", "english": "Information Security", "status": "approved"},
            ]
            masked, term_map = translate.mask_glossary_terms("אבטחת מידע", rows)
            self.assertIn("Information Security", masked)
            self.assertNotIn("information", masked.lower().replace("information security", ""))

    def test_mask_yap_missing_fail_closed(self):
        import unittest.mock as mock
        import translate.translate as translate
        with mock.patch("translate.translate._yap_root_keys", side_effect=FileNotFoundError("yap.exe not found")):
            rows = [{"term_he": "מערכת", "english": "system", "status": "approved"}]
            try:
                translate.mask_glossary_terms("מערכת", rows)
                self.fail("should have raised")
            except RuntimeError as e:
                self.assertIn("YAP required", str(e))


# Task 5: deterministic unmask + ledger fields (model_id, glossary_version, term_map)
import json as _json
import shutil as _shutil
import tempfile as _tempfile
import unittest.mock as _mock


def _ensure_person_names(vault: Path) -> None:
    """Copy real person-name lists into tmp vault (fail-closed guard)."""
    src = Path(__file__).resolve().parents[1] / "data" / "person_names"
    assert src.exists(), f"data/person_names missing at {src} — checkout incomplete"
    assert (src / "first_names.txt").exists() and (src / "last_names_ranked.txt").exists(), "person name fixtures missing — restore from 3396b68"
    _shutil.copytree(src, vault / "data" / "person_names", dirs_exist_ok=True)


class TestDeterministicMasking(unittest.TestCase):
    def test_unmask_deterministic_via_sentinels(self):
        import translate.translate as translate
        from translate.translation_common import build_glossary_sentinel, build_keep_sentinel

        # EN sentinel unmask
        term_map = [{"id": 0, "term_he": "אבטחת מידע", "english": "Information Security", "keep_source": False, "occurrences": 1}]
        sentinel = build_glossary_sentinel(0, "Information Security")
        assert sentinel == "⟦EN:0:Information Security⟧"
        llm_out = f"in {sentinel} the allows"
        unmasked = translate.unmask_glossary_terms(llm_out, term_map)
        assert unmasked == "in Information Security the allows"
        assert "⟦EN:" not in unmasked
        # KEEP sentinel unmask
        keep_map = [{"id": 0, "term_he": "שבת", "english": "", "keep_source": True, "occurrences": 1}]
        keep_sentinel = build_keep_sentinel("שבת")
        assert keep_sentinel == "⟦KEEP:שבת⟧"
        llm_keep = f"Keep {keep_sentinel} as is"
        assert translate.unmask_glossary_terms(llm_keep, keep_map) == "Keep שבת as is"

    def test_unmask_and_ledger_fields(self):
        import translate.translate as translate
        from translate.translation_common import compute_glossary_version

        # --- unmask unit ---
        term_map = [{"id": 0, "term_he": "אבטחת מידע", "english": "Information Security", "keep_source": False, "occurrences": 1}]
        llm_out = "in ⟦EN:0:Information Security⟧ the allows"
        unmasked = translate.unmask_glossary_terms(llm_out, term_map)
        assert unmasked == "in Information Security the allows"
        assert "⟦EN:" not in unmasked

        # --- ledger integration (mock translate, YAP mocked) ---
        with _tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "raw_md").mkdir(parents=True)
            (vault / "data" / "domain_terms").mkdir(parents=True)
            _ensure_person_names(vault)
            glossary_csv = vault / "data" / "domain_terms" / "glossary.csv"
            glossary_csv.write_text(
                "term_he,english,status\n"
                "אבטחת מידע,Information Security,approved\n",
                encoding="utf-8",
            )
            (vault / "convert_config.json").write_text(
                _json.dumps({"translation": {"model": "minimax-m2.7"}}), encoding="utf-8"
            )
            (vault / "raw_md" / "doc.md").write_text(
                "---\ntitle: test\n---\n\nאבטחת מידע חשובה מאוד.\n",
                encoding="utf-8",
            )
            # Mock YAP so masking succeeds without binary; tolerate qa_failed exit(1)
            with _mock.patch("translate.translate._yap_root_keys", side_effect=lambda toks: toks):
                try:
                    translate.main([str(vault), "--mock"])
                except SystemExit as e:
                    # qa_failed causes exit 1 — ledger is still written, continue to verify
                    if e.code not in (0, 1, None):
                        raise

            ledger_path = vault / "data" / "translations" / "ledger.jsonl"
            assert ledger_path.exists(), "ledger.jsonl not created"
            entries = [ _json.loads(l) for l in ledger_path.read_text(encoding="utf-8").splitlines() if l.strip() ]
            assert entries, "ledger empty"
            # Every ledger entry must carry model_id + glossary_version
            expected_gv = compute_glossary_version(glossary_csv)
            for e in entries:
                assert "model_id" in e, f"missing model_id in {e.get('event')}: {e}"
                assert e["model_id"] == "minimax-m2.7"
                assert "glossary_version" in e, f"missing glossary_version in {e}"
                assert e["glossary_version"] == expected_gv
                # glossary_version must be 12-char hash (or no-glossary), not legacy 10
                assert expected_gv == "no-glossary" or len(e["glossary_version"]) == 12
            # At least one terminal ledger event must contain term_map
            terminal = [e for e in entries if e.get("event") in ("translation_completed", "blocked_on_term", "qa_failed", "qa_result")]
            assert terminal, "no terminal ledger events"
            assert any("term_map" in e for e in terminal), f"no term_map in terminal events: {terminal[0].keys()}"
            # term_map must be a list of dicts with expected shape
            for e in terminal:
                if "term_map" in e:
                    assert isinstance(e["term_map"], list)
                    if e["term_map"]:
                        first = e["term_map"][0]
                        assert "term_he" in first and "english" in first and "occurrences" in first

    def test_e2e_mock_deterministic_with_fixtures(self):
        import translate.translate as translate, json, pathlib, re
        import unittest.mock as mock
        with _tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "raw_md").mkdir(parents=True)
            (vault / "data" / "domain_terms").mkdir(parents=True)
            _ensure_person_names(vault)
            # glossary as specified: מערכת->system, DB->DB, אבטחת מידע->Information Security
            (vault / "data" / "domain_terms" / "glossary.csv").write_text(
                "term_he,english,keep_source,notes,status,example_doc\n"
                "מערכת,system,0,,approved,\n"
                "DB,DB,0,,approved,\n"
                "אבטחת מידע,Information Security,0,,approved,\n",
                encoding="utf-8"
            )
            # doc with הDBים + המערכות (inflected)
            (vault / "raw_md" / "doc.md").write_text(
                "---\ntitle: test\n---\n\nהDBים של המערכות כוללים אבטחת מידע.\nהמערכות פועלות.\n",
                encoding="utf-8"
            )
            (vault / "convert_config.json").write_text('{"translation": {"model": "minimax-m2.7"}}', encoding="utf-8")

            # YAP mocks: need to handle mixed and plural forms as in Task2
            def fake_roots(toks):
                mapping = {
                    "הDBים": "DB",
                    "DB": "DB",
                    "המערכות": "מערכת",
                    "מערכות": "מערכת",
                    "מערכת": "מערכת",
                    "אבטחת": "אבטחת",
                    "מידע": "מידע",
                    "של": "של",
                    "כוללים": "כוללים",
                    "פועלות": "פועלות",
                }
                out = []
                for t in toks:
                    out.append(mapping.get(t, t))
                return out

            def fake_analyze(toks):
                out = []
                for t in toks:
                    if t == "הDBים":
                        out.append(("הDBים", "DB", "ה", "ים"))
                    elif t == "המערכות":
                        out.append(("המערכות", "מערכת", "ה", "ות"))
                    else:
                        # heuristic-like empty proclitic/suffix
                        out.append((t, t, "", ""))
                return out

            with mock.patch("translate.translate._yap_root_keys", side_effect=fake_roots):
                with mock.patch("translate.translate._yap_analyze", side_effect=fake_analyze):
                    try:
                        translate.main([str(vault), "--mock"])
                    except SystemExit as e:
                        # qa_failed may exit 1, but body is still written; allow 0 or 1
                        if e.code not in (0, 1, None):
                            raise
            out_files = list((vault / "data" / "translations").rglob("translation.md"))
            assert out_files, "no output"
            # Find the doc's translation (should be one)
            body = out_files[0].read_text(encoding="utf-8")
            # Extract body after frontmatter if present
            if body.startswith("---\n"):
                end = body.find("\n---\n", 4)
                if end != -1:
                    body_only = body[end+5:]
                else:
                    body_only = body
            else:
                body_only = body
            assert "DB" in body_only, f"DB missing in {body_only!r}"
            assert "system" in body_only, f"system missing in {body_only!r}"
            assert "Information Security" in body_only, f"Information Security missing in {body_only!r}"
            assert "⟦EN:" not in body_only, f"sentinel leak in {body_only!r}"
            # No Hebrew residue of glossary terms
            assert "אבטחת מידע" not in body_only, f"Hebrew residue אבטחת מידע in {body_only!r}"
            assert "הDBים" not in body_only, f"Hebrew residue הDBים in {body_only!r}"
            assert "המערכות" not in body_only, f"Hebrew residue המערכות in {body_only!r}"
            # Also ensure no raw Hebrew of those roots remains outside markers? At least not the exact terms
            # Check that term_map in frontmatter/ledger is correct
            ledger_path = vault / "data" / "translations" / "ledger.jsonl"
            assert ledger_path.exists()
            entries = [json.loads(l) for l in ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            # At least one entry should have term_map covering all 3 terms
            terminal = [e for e in entries if e.get("event") in ("translation_completed", "qa_failed", "qa_result", "blocked_on_term")]
            assert terminal, "no terminal events"
            # Find term_map with 3 entries
            found = False
            for e in terminal:
                tm = e.get("term_map") or []
                hes = {x.get("term_he") for x in tm}
                if {"מערכת", "DB", "אבטחת מידע"}.issubset(hes):
                    found = True
                    break
            # Also check frontmatter term_map
            if not found:
                # Check file frontmatter directly
                fm_text = body[:end] if body.startswith("---\n") and end!=-1 else ""
                try:
                    fm = json.loads(fm_text.strip()[3:-3].strip()) if fm_text else {}
                except Exception:
                    fm = {}
                tm = fm.get("term_map") or []
                hes = {x.get("term_he") for x in tm}
                if {"מערכת", "DB", "אבטחת מידע"}.issubset(hes):
                    found = True
            assert found, f"term_map missing expected terms: terminal maps {[e.get('term_map') for e in terminal]}" 


@unittest.skipUnless(importlib.util.find_spec("convert_to_md"), "convert_to_md ships in #3")
class TestYamlGuard(unittest.TestCase):
    def test_build_frontmatter_raises_if_no_yaml(self):
        # Mock heavy deps so convert_to_md can be imported in CI without them
        import sys as _sys
        for _mod in ("docling_convert", "hebrew_fix", "onenote_conversion", "vsdx_conversion"):
            if _mod not in _sys.modules:
                _sys.modules[_mod] = type(_sys)(_mod)
        import convert.convert_to_md as cmod
        orig_yaml = cmod.yaml
        try:
            cmod.yaml = None
            from datetime import datetime, timezone
            with self.assertRaises(RuntimeError):
                cmod.build_frontmatter("Title", datetime.now(timezone.utc), "file.txt", ".txt", False)
        finally:
            cmod.yaml = orig_yaml
