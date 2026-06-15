# tests/test_vault.py
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vault", ROOT / "scripts" / "vault.py")
vault = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vault)


class TestHelpers(unittest.TestCase):
    def test_slugify_basic(self):
        self.assertEqual(vault.slugify("QLoRA Explained: 4-Bit!"), "qlora-explained-4-bit")

    def test_slugify_collapses_separators(self):
        self.assertEqual(vault.slugify("  A__B  C "), "a-b-c")

    def test_parse_frontmatter_scalars_and_list(self):
        text = (
            "---\n"
            "title: My Title\n"
            "author: Jane Doe\n"
            "tags:\n"
            "  - alpha\n"
            "  - beta\n"
            "---\n"
            "Body line 1\n"
        )
        fm, body = vault.parse_frontmatter(text)
        self.assertEqual(fm["title"], "My Title")
        self.assertEqual(fm["author"], "Jane Doe")
        self.assertEqual(fm["tags"], ["alpha", "beta"])
        self.assertEqual(body.strip(), "Body line 1")

    def test_parse_frontmatter_missing_returns_empty(self):
        fm, body = vault.parse_frontmatter("no frontmatter here\n")
        self.assertEqual(fm, {})
        self.assertEqual(body.strip(), "no frontmatter here")


import re as _re


class TestTemplates(unittest.TestCase):
    SKILLS = ["vault-setup", "vault-ingest", "vault-query", "vault-lint"]

    def test_skill_frontmatter_valid(self):
        for name in self.SKILLS:
            path = vault.TEMPLATES_DIR / "skills" / name / "SKILL.md"
            self.assertTrue(path.exists(), f"missing {path}")
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), f"{name}: no frontmatter fence")
            fm, _ = vault.parse_frontmatter(text)
            self.assertIn("name", fm, f"{name}: no name")
            self.assertIn("description", fm, f"{name}: no description")
            self.assertEqual(fm["name"], name)

    def test_skill_has_minimal_path(self):
        for name in self.SKILLS:
            text = (vault.TEMPLATES_DIR / "skills" / name / "SKILL.md").read_text("utf-8")
            self.assertIn("Minimal-model path", text, f"{name}: missing minimal path")


import tempfile


class TestScaffold(unittest.TestCase):
    def test_scaffold_creates_layout(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rc = vault.cmd_scaffold(root, "Test Vault")
            self.assertEqual(rc, 0)
            v = root / "Test Vault"
            for sub in ["raw", "wiki", "wiki/sources", "index", "eval", "scripts",
                        ".claude/skills/vault-ingest"]:
                self.assertTrue((v / sub).is_dir(), f"missing dir {sub}")
            self.assertTrue((v / "CLAUDE.md").exists())
            self.assertIn("Test Vault", (v / "CLAUDE.md").read_text("utf-8"))
            self.assertTrue((v / "scripts/vault.py").exists())
            self.assertTrue((v / "scripts/templates/CLAUDE.md").exists(),
                            "templates must travel for self-replication")
            self.assertTrue((v / ".claude/skills/vault-ingest/SKILL.md").exists())
            for stem in ["_map-of-content", "source-registry", "log", "key-takeaways"]:
                self.assertTrue((v / "index" / f"{stem}.md").exists(), stem)


class TestNewNote(unittest.TestCase):
    def _vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        return root / "V"

    def test_new_note_creates_concept_stub(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            (v / "raw" / "my-clip.md").write_text("---\ntitle: My Clip\n---\nbody\n", "utf-8")
            rc = vault.cmd_new_note(v, "low-rank-adapters", "raw/my-clip.md")
            self.assertEqual(rc, 0)
            note = v / "wiki" / "low-rank-adapters.md"
            self.assertTrue(note.exists())
            fm, _ = vault.parse_frontmatter(note.read_text("utf-8"))
            self.assertEqual(fm["type"], "concept")
            self.assertEqual(fm["sources"], ["[[my-clip]]"])
            self.assertIn("<!-- TODO", note.read_text("utf-8"))

    def test_new_note_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            (v / "raw" / "c.md").write_text("---\ntitle: C\n---\n", "utf-8")
            self.assertEqual(vault.cmd_new_note(v, "x", "raw/c.md"), 0)
            self.assertEqual(vault.cmd_new_note(v, "x", "raw/c.md"), 1)  # already exists


FIXTURE = ROOT / "tests" / "fixtures" / "sample-clipping.md"


class TestIngest(unittest.TestCase):
    def _vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        v = root / "V"
        (v / "raw" / "sample-clipping.md").write_text(FIXTURE.read_text("utf-8"), "utf-8")
        return v

    def test_ingest_creates_summary_registry_log(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            rc = vault.cmd_ingest(v, Path("raw/sample-clipping.md"))
            self.assertEqual(rc, 0)
            summary = v / "wiki" / "sources" / "understanding-low-rank-adapters.md"
            self.assertTrue(summary.exists())
            sfm, _ = vault.parse_frontmatter(summary.read_text("utf-8"))
            self.assertEqual(sfm["type"], "source-summary")
            self.assertEqual(sfm["sources"], ["[[sample-clipping]]"])
            reg = (v / "index" / "source-registry.md").read_text("utf-8")
            self.assertIn("[[sample-clipping]]", reg)
            self.assertIn("[[understanding-low-rank-adapters]]", reg)
            log = (v / "index" / "log.md").read_text("utf-8")
            self.assertIn("ingest | Understanding Low-Rank Adapters", log)
            self.assertIn("sample-clipping", log)

    def test_ingest_is_rerunnable(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            self.assertEqual(vault.cmd_ingest(v, Path("raw/sample-clipping.md")), 0)
            self.assertEqual(vault.cmd_ingest(v, Path("raw/sample-clipping.md")), 0)
            reg = (v / "index" / "source-registry.md").read_text("utf-8")
            self.assertEqual(reg.count("[[sample-clipping]]"), 1)  # no duplicate row


class TestCheck(unittest.TestCase):
    def _filled_vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        v = root / "V"
        (v / "raw" / "sample-clipping.md").write_text(FIXTURE.read_text("utf-8"), "utf-8")
        vault.cmd_ingest(v, Path("raw/sample-clipping.md"))
        vault.cmd_new_note(v, "low-rank-adapters", "raw/sample-clipping.md")
        (v / "wiki" / "sources" / "understanding-low-rank-adapters.md").write_text(
            '---\ntitle: "Summary — Understanding Low-Rank Adapters"\n'
            'type: source-summary\ntags: [lora]\nsources:\n  - "[[sample-clipping]]"\n'
            'published: 2026-01-15\n---\n\n'
            "# Summary — Understanding Low-Rank Adapters\n\n"
            "**LoRA trains small low-rank matrices on frozen weights.**\n\n"
            "The article explains low-rank adaptation, grounded in [[sample-clipping]].\n\n"
            "## Key claims\n- low-rank update -> [[low-rank-adapters]]\n\n"
            "## Derived concept notes\n[[low-rank-adapters]]\n", "utf-8")
        (v / "wiki" / "low-rank-adapters.md").write_text(
            '---\ntitle: "Low Rank Adapters"\ntype: concept\ntags: [lora]\n'
            'sources:\n  - "[[sample-clipping]]"\n---\n\n'
            "# Low Rank Adapters\n\n"
            "**LoRA adds trainable low-rank matrices to frozen weights.**\n\n"
            "Body grounded in [[sample-clipping]]. W' = W + (a/r)BA.\n\n"
            "## Related\n[[understanding-low-rank-adapters]]\n", "utf-8")
        return v

    def test_check_passes_when_filled(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._filled_vault(d)
            self.assertEqual(vault.cmd_check(v), 0)

    def test_check_fails_on_todo_marker(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._filled_vault(d)
            note = v / "wiki" / "low-rank-adapters.md"
            note.write_text(note.read_text("utf-8") + "\n<!-- TODO: extra -->\n", "utf-8")
            self.assertNotEqual(vault.cmd_check(v), 0)


class TestRegister(unittest.TestCase):
    def test_register_dry_run_excludes_eval(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            vault.cmd_scaffold(root, "V")
            v = root / "V"
            calls = []
            def fake_runner(cmd, **kw):
                calls.append(cmd)
                class R: returncode = 0
                return R()
            rc = vault.cmd_register(v, runner=fake_runner)
            self.assertEqual(rc, 0)
            flat = " ".join(" ".join(c) for c in calls)
            self.assertIn("collection add ./raw", flat)
            self.assertIn("collection add ./wiki", flat)
            self.assertIn("collection add ./index", flat)
            self.assertNotIn("eval", flat)  # eval/ must never be registered
            self.assertIn("qmd update", flat)
            self.assertIn("qmd embed", flat)


if __name__ == "__main__":
    unittest.main()
