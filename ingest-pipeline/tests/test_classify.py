import json
import tempfile
from pathlib import Path
import unittest

import sys as _sys

ROOT = Path(__file__).resolve().parents[1]
_sys.path.insert(0, str(ROOT / "scripts"))
from classify import validate  # noqa: E402  (pipeline-local, not the framework)

# Classification templates moved out of the framework payload with the pipeline.
TEMPLATES = ROOT / "templates" / "classification"


class TestClassificationTemplates(unittest.TestCase):
    def test_taxonomy_exists_and_has_subdomains(self):
        p = TEMPLATES / "taxonomy.yaml"
        self.assertTrue(p.exists())
        txt = p.read_text(encoding="utf-8")
        # at least 5 subdomains in toy
        subs = [m for m in txt.splitlines() if m.startswith("  ") and m.strip().endswith(":") and m.strip().count(":") == 1]
        # count subdomain blocks (those under subdomains:)
        self.assertGreaterEqual(txt.count("definition:"), 5)

    def test_taxonomy_subdomains_in_payload_sync_with_judge_schema(self):
        # Judge schema enum must match taxonomy subdomains
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.judge import load_yaml_simple, build_schema
        tax_path = TEMPLATES / "taxonomy.yaml"
        _, subs = load_yaml_simple(tax_path)
        allowed = sorted(subs.keys())
        schema = build_schema(allowed)
        self.assertEqual(sorted(schema["properties"]["primary_subdomain"]["enum"]), allowed)
        self.assertEqual(schema["properties"]["confidence_bucket"]["enum"], ["SURE", "NEEDS_HUMAN_VALIDATION", "I_GUESSED"])
        self.assertEqual(schema["required"][0], "reasoning_brief")
        self.assertFalse(schema.get("additionalProperties", True))

    def test_glossary_keys_unique(self):
        p = TEMPLATES / "glossary.yaml"
        txt = p.read_text(encoding="utf-8")
        # extract keys under terms:
        import re
        keys = re.findall(r"^\s{2}(\w+):\s*\n", txt, flags=re.MULTILINE)
        # filter meta keys
        keys = [k for k in keys if k not in ("terms", "version", "campaign")]
        self.assertEqual(len(keys), len(set(keys)), "glossary keys must be unique")
        self.assertGreaterEqual(len(keys), 5)

    def test_policy_enums_valid(self):
        p = TEMPLATES / "policy.yaml"
        txt = p.read_text(encoding="utf-8")
        self.assertIn("first_window", txt)
        self.assertIn("SURE", txt)
        self.assertIn("primary_plus_secondary", txt)

    def test_label_studio_view_exists(self):
        p = TEMPLATES / "label_studio" / "view.xml"
        self.assertTrue(p.exists())
        txt = p.read_text(encoding="utf-8")
        self.assertIn("<HyperText", txt)
        self.assertIn('name="primary"', txt)


class TestChunker(unittest.TestCase):
    def test_first_window_respects_window(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.chunk import chunk_first_window, chunk_header_aware, extract_headers
        body = "# Title\n\n" + ("word " * 500) + "\n\n## Section\n" + ("content " * 300)
        out = chunk_first_window(body, window=200, include_outline=True)
        # ~800 chars for 200 tokens + outline
        self.assertLessEqual(len(out), 200 * 4 + 300)
        self.assertIn("Title", out)

    def test_header_aware_skips_code_fences(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.chunk import extract_headers
        body = "# Real\n```\n# not a header\n```\n# Also real\n"
        headers = extract_headers(body)
        self.assertIn("# Real", headers)
        self.assertIn("# Also real", headers)
        self.assertNotIn("# not a header", headers)

    def test_chunk_atomic_write(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.chunk import atomic_write
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a" / "b" / "out.md"
            atomic_write(p, "hello")
            self.assertTrue(p.exists())
            self.assertEqual(p.read_text(encoding="utf-8"), "hello")


class TestJudgeSchema(unittest.TestCase):
    def test_reasoning_brief_first(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.judge import build_schema
        schema = build_schema(["a", "b"])
        keys = list(schema["properties"].keys())
        self.assertEqual(keys[0], "reasoning_brief")

    def test_numeric_confidence_not_in_schema(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.judge import build_schema
        schema = build_schema(["a", "b"])
        # schema must not have numeric confidence field
        self.assertNotIn("confidence", schema["properties"])
        self.assertIn("confidence_bucket", schema["properties"])

    def test_call_llm_envelope_in_source(self):
        p = ROOT / "scripts" / "classify" / "judge.py"
        txt = p.read_text(encoding="utf-8")
        self.assertIn("json_schema", txt)
        self.assertIn("guided_json", txt)
        self.assertIn('"strict": True', txt)


class TestCoreClassifyValidator(unittest.TestCase):
    def test_closed_vocab_rejects_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            v = root / "V"
            v.mkdir()
            # Create a minimal campaign taxonomy (use payload toy as campaign)
            camp = v / "campaigns" / "test"
            camp.mkdir(parents=True)
            # Copy payload taxonomy as campaign taxonomy (so allowed = 5 subs)
            import shutil
            shutil.copy(TEMPLATES / "taxonomy.yaml", camp / "taxonomy.yaml")
            store = v / "store"
            store.mkdir()
            # Create a judge file with unknown primary
            (store / "abc.judge.json").write_text(json.dumps({
                "reasoning_brief": "test reason for unknown primary",
                "primary_subdomain": "not_a_subdomain",
                "confidence_bucket": "SURE",
                "relation_type": "none",
                "secondary_subdomains": []
            }), encoding="utf-8")
            (store / "abc.md").write_text("---\ntitle: t\n---\nbody", encoding="utf-8")
            rc = validate.cmd_classify(v, campaign=Path("campaigns/test"), store=Path("store"))
            self.assertNotEqual(rc, 0)

    def test_rejects_numeric_confidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            v = root / "V"
            v.mkdir()
            camp = v / "campaigns" / "test"
            camp.mkdir(parents=True)
            import shutil
            shutil.copy(TEMPLATES / "taxonomy.yaml", camp / "taxonomy.yaml")
            store = v / "store"
            store.mkdir()
            (store / "xyz.judge.json").write_text(json.dumps({
                "reasoning_brief": "numeric confidence test",
                "primary_subdomain": "cardiology",
                "confidence": 0.73,
                "confidence_bucket": "SURE",
                "relation_type": "none",
            }), encoding="utf-8")
            (store / "xyz.md").write_text("---\ntitle: t\n---\nbody", encoding="utf-8")
            rc = validate.cmd_classify(v, campaign=Path("campaigns/test"), store=Path("store"))
            self.assertNotEqual(rc, 0)


class TestLabelStudioView(unittest.TestCase):
    def test_view_renders_for_N(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.export_label_studio import md_to_html
        # Test N=5 and N=20 by checking template Choice count
        tpl = (TEMPLATES / "label_studio" / "view.xml").read_text(encoding="utf-8")
        self.assertGreaterEqual(tpl.count("<Choice"), 10)  # 5+5
        # Test export rendering path with temp taxonomy
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / "camp"
            camp.mkdir()
            # Create 20-subdomain taxonomy
            subs = "\n".join(f"  sub{i}:\n    definition: \"def {i}\"\n    examples:\n      - text: \"ex {i}\"" for i in range(20))
            (camp / "taxonomy.yaml").write_text(f"version: 1\nsubdomains:\n{subs}\n", encoding="utf-8")
            store = Path(d) / "store"
            store.mkdir()
            (store / "doc.md").write_text("---\ntitle: t\n---\nbody", encoding="utf-8")
            out = Path(d) / "tasks.json"
            view_out = Path(d) / "view.xml"
            import sys as _sys
            _sys.path.insert(0, str(ROOT / "scripts"))
            from classify.export_label_studio import main as export_main
            import argparse
            # Simulate args via direct call to rendering logic
            from classify.export_label_studio import md_to_html as _md
            # Instead, test the rendering function directly by calling export with --view-out
            import subprocess
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "classify" / "export_label_studio.py"),
                                     "--campaign", str(camp), "--store", str(store), "--out", str(out), "--view-out", str(view_out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            rendered = view_out.read_text(encoding="utf-8")
            self.assertIn('value="sub0"', rendered)
            self.assertIn('value="sub19"', rendered)


class TestLedger(unittest.TestCase):
    def test_ledger_append_and_project(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from classify.calibrate import ledger_append, ledger_project
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / "ledger.jsonl"
            ledger_append(ledger, {"doc_id": "a", "primary": "x"})
            ledger_append(ledger, {"doc_id": "b", "primary": "y"})
            self.assertTrue(ledger.exists())
            lines = ledger.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
