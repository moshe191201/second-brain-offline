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


if __name__ == "__main__":
    unittest.main()
