"""Guards on the framework/ingest-pipeline boundary.

The split is only worth anything if it stays split. These are the executable
form of the rules in CLAUDE.md:

  - the framework is pure stdlib, so it survives an air gap with nothing installed
  - the framework has no knowledge that the pipeline exists
  - a vault owner never receives a pipeline file

Each of these was true by inspection when the split landed. Without a test they
stay true only until the next person adds an import.
"""
from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "second_brain_vault_framework"

_OWN_PACKAGE = "second_brain_vault_framework"


def _imported_top_level_modules(py: Path) -> set[str]:
    """Every top-level module name imported by a file."""
    mods: set[str] = set()
    for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    return mods


class TestFrameworkIsPureStdlib(unittest.TestCase):
    """`pyproject.toml` declares no runtime deps. This proves the code agrees."""

    def test_package_imports_stdlib_only(self):
        offenders = []
        for py in sorted(PKG.rglob("*.py")):
            for mod in _imported_top_level_modules(py) - {_OWN_PACKAGE}:
                if mod not in sys.stdlib_module_names:
                    offenders.append(f"{py.relative_to(ROOT)} imports {mod!r}")
        self.assertEqual(offenders, [], "framework must run with nothing installed")

    def test_framework_tests_import_stdlib_only(self):
        # A test dependency is still a dependency: if the suite needs a package,
        # CI can no longer prove the air-gap claim.
        offenders = []
        for py in sorted((ROOT / "tests").glob("*.py")):
            for mod in _imported_top_level_modules(py) - {_OWN_PACKAGE}:
                if mod not in sys.stdlib_module_names:
                    offenders.append(f"{py.relative_to(ROOT)} imports {mod!r}")
        self.assertEqual(offenders, [], "framework tests must run with nothing installed")

    def test_pyproject_declares_no_runtime_dependencies(self):
        txt = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", txt,
                      "adding a runtime dep breaks the air-gap guarantee")


class TestFrameworkDoesNotKnowAboutThePipeline(unittest.TestCase):
    _PIPELINE_MARKERS = ("ingest-pipeline", "ingest_pipeline")

    def test_no_manifest_path_belongs_to_the_pipeline(self):
        manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
        paths = manifest["owned_paths"] + manifest["scaffold_only_paths"]
        bad = [p for p in paths
               if any(m in p for m in self._PIPELINE_MARKERS)
               or "classification" in p or "vault-classify" in p]
        self.assertEqual(bad, [], "the pipeline must not ship into user vaults")

    def test_no_payload_file_belongs_to_the_pipeline(self):
        payload = PKG / "payload"
        bad = [str(f.relative_to(payload)) for f in payload.rglob("*")
               if f.is_file() and (any(m in str(f) for m in self._PIPELINE_MARKERS)
                                   or "classification" in str(f)
                                   or "vault-classify" in str(f))]
        self.assertEqual(bad, [], "payload is what a vault owner receives")

    def test_package_source_never_references_the_pipeline(self):
        bad = []
        for py in sorted(PKG.rglob("*.py")):
            txt = py.read_text(encoding="utf-8")
            for marker in (*self._PIPELINE_MARKERS, "cmd_classify"):
                if marker in txt:
                    bad.append(f"{py.relative_to(ROOT)} mentions {marker!r}")
        self.assertEqual(bad, [])


class TestManifestMatchesPayload(unittest.TestCase):
    """`owned_paths` is the only definition of what the framework owns, so a file
    present but unowned is never installed and a path owned but missing breaks
    `vault upgrade` in a consumer's repo rather than here."""

    def _payload_rel_paths(self) -> set[str]:
        payload = PKG / "payload"
        out = set()
        for f in payload.rglob("*"):
            if not f.is_file() or f.name == ".DS_Store":
                continue
            rel = f.relative_to(payload).as_posix()
            out.add(rel.replace("dot-claude/", ".claude/", 1) if rel.startswith("dot-claude/") else rel)
        return out

    def test_every_owned_path_exists_in_the_payload(self):
        manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
        present = self._payload_rel_paths()
        missing = [p for p in manifest["owned_paths"] + manifest["scaffold_only_paths"]
                   if p not in present]
        self.assertEqual(missing, [], "owned but not shipped — upgrade would never install it")



class TestExampleVaultIsCurrent(unittest.TestCase):
    """`payload/` is the source of truth; `example_vault/` is an artifact.

    CLAUDE.md has long claimed CI enforced this. It did not: the `example-vault`
    job ran `vault check` and then `git diff --exit-code`, without ever running
    `vault upgrade` — and on a fresh CI checkout that diff is trivially empty, so
    the check could never detect a stale example. A payload edit that was never
    laid down would have reached a consumer's repo before it failed here.

    Done as a temp-directory copy rather than by upgrading the real example and
    diffing: `.vault-framework.json` carries an `installed_at` wall-clock stamp
    rewritten on every upgrade, so a naive diff is red on every run regardless of
    drift.
    """

    _VOLATILE = ("installed_at",)

    def test_upgrading_example_vault_would_change_nothing(self):
        import shutil
        import tempfile
        from second_brain_vault_framework import core

        example = ROOT / "example_vault"
        self.assertTrue(example.is_dir(), "example_vault/ missing")

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "example_vault"
            shutil.copytree(example, copy)
            rc = core.cmd_upgrade(copy)
            self.assertEqual(rc, 0, "vault upgrade failed on example_vault")

            drifted = []
            for after in sorted(copy.rglob("*")):
                if not after.is_file():
                    continue
                rel = after.relative_to(copy)
                before = example / rel
                if not before.exists():
                    drifted.append(f"{rel} (upgrade would ADD it)")
                    continue
                a, b = after.read_bytes(), before.read_bytes()
                if a == b:
                    continue
                if rel.name == ".vault-framework.json":
                    ja, jb = json.loads(a), json.loads(b)
                    for k in self._VOLATILE:
                        ja.pop(k, None)
                        jb.pop(k, None)
                    if ja != jb:
                        drifted.append(f"{rel} (stamp/manifest drift)")
                    continue
                drifted.append(f"{rel} (upgrade would CHANGE it)")

            for before in sorted(example.rglob("*")):
                if before.is_file() and not (copy / before.relative_to(example)).exists():
                    drifted.append(f"{before.relative_to(example)} (upgrade would REMOVE it)")

            self.assertEqual(
                drifted, [],
                "example_vault is stale — run `vault upgrade example_vault` and commit")

if __name__ == "__main__":
    unittest.main()
