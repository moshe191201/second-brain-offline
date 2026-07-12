# second-brain-vault-framework Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the vault framework (`CLAUDE.md`, the `vault-*` skills, `vault.py`, `lint_vault.py`, `instructions.md`, `eval/VAULT_TESTS.md`) into a pip-installable package `second-brain-vault-framework` that scaffolds and upgrades a user's vault directory in place.

**Architecture:** A `src/`-layout Python package holds the CLI (`vault`) plus a `payload/` of files copied into a vault via `importlib.resources`. A `manifest.json` declares framework-owned paths and user-zone markers. `vault scaffold <dir>` lays the payload into a new folder; `vault upgrade <dir>` re-lays framework-owned paths, preserves the `CLAUDE.md` user-zone, deletes orphaned framework files, and backs up any user-edited framework file before overwriting. The other commands (`ingest`/`new-note`/`check`/`register`/`status`) keep operating on the current directory as they do today.

**Tech Stack:** Python 3.10+ stdlib only (argparse, importlib.resources, importlib.metadata, hashlib, json, shutil, pathlib), setuptools build backend, pytest for tests.

**Source paths:**
- New package repo: `/Users/moshe/Desktop/Code/second-brain-vault-framework/` (a fresh git repo, separate from the live vault).
- Existing framework source to port from: `/Users/moshe/Desktop/Code/Moshe Vault/scripts/vault.py`, `scripts/lint_vault.py`, `scripts/templates/`, `CLAUDE.md`, `instructions.md`, `eval/VAULT_TESTS.md`.

The import package name is `second_brain_vault_framework`; the CLI command is `vault`.

---

## File Structure

```
second-brain-vault-framework/
├── pyproject.toml
├── README.md
├── src/second_brain_vault_framework/
│   ├── __init__.py                 # __version__ = "0.1.0"
│   ├── cli.py                      # argparse entry point → main()
│   ├── core.py                     # all command logic + manifest/user-zone/payload helpers
│   ├── manifest.json               # owned_paths + user_zones
│   └── payload/                    # files copied into a vault (no dotfiles/dotdirs — mapped on write)
│       ├── CLAUDE.md               # {{VAULT_NAME}} + USER ZONE markers
│       ├── instructions.md
│       ├── gitignore               # written to .gitignore at scaffold
│       ├── dot-claude/skills/vault-{setup,ingest,query,lint}/SKILL.md   # → .claude/skills/...
│       ├── scripts/vault.py        # thin shim → second_brain_vault_framework.cli
│       ├── scripts/lint_vault.py
│       └── eval/VAULT_TESTS.md
└── tests/
    ├── test_manifest.py
    ├── test_user_zone.py
    ├── test_scaffold.py
    ├── test_upgrade.py
    └── test_check.py
```

Responsibilities:
- `core.py` — pure functions + `cmd_*` handlers. No argparse. Testable directly against `tmp_path`.
- `cli.py` — argument parsing only; dispatches to `core.cmd_*`.
- `manifest.json` — single source of truth for owned paths + user-zone markers.
- `payload/` — verbatim files laid into a vault; `CLAUDE.md` carries `{{VAULT_NAME}}` and the user-zone block.

---

## Task 0: Bootstrap the package repo skeleton

**Files:**
- Create: `/Users/moshe/Desktop/Code/second-brain-vault-framework/pyproject.toml`
- Create: `/Users/moshe/Desktop/Code/second-brain-vault-framework/src/second_brain_vault_framework/__init__.py`
- Create: `/Users/moshe/Desktop/Code/second-brain-vault-framework/README.md`

- [ ] **Step 1: Create the repo and directory tree**

Run:
```bash
mkdir -p /Users/moshe/Desktop/Code/second-brain-vault-framework/src/second_brain_vault_framework/payload
mkdir -p /Users/moshe/Desktop/Code/second-brain-vault-framework/tests
cd /Users/moshe/Desktop/Code/second-brain-vault-framework && git init
```
Expected: `Initialized empty Git repository`.

- [ ] **Step 2: Write `__init__.py` (single source of version truth)**

Create `src/second_brain_vault_framework/__init__.py`:
```python
"""second-brain-vault-framework: scaffold and upgrade an air-gapped knowledge vault."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Write `pyproject.toml`**

Create `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[project]
name = "second-brain-vault-framework"
dynamic = ["version"]
description = "Scaffold and upgrade an air-gapped Obsidian knowledge vault."
requires-python = ">=3.10"
readme = "README.md"

[project.scripts]
vault = "second_brain_vault_framework.cli:main"

[tool.setuptools.dynamic]
version = { attr = "second_brain_vault_framework.__version__" }

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
second_brain_vault_framework = ["manifest.json", "payload/**/*"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 4: Write a minimal README**

Create `README.md`:
```markdown
# second-brain-vault-framework

Pip-installable framework for an air-gapped Obsidian knowledge vault.

- `vault scaffold <dir>` — create a new vault
- `vault upgrade <dir>` — update framework files in an existing vault
- `vault check` — lint the vault in the current directory

See the vault's `instructions.md` (shipped in the payload) for the full runbook.
```

- [ ] **Step 5: Commit**

```bash
cd /Users/moshe/Desktop/Code/second-brain-vault-framework
git add -A
git commit -m "chore: bootstrap package skeleton"
```

---

## Task 1: Assemble the payload and manifest

**Files:**
- Copy into: `src/second_brain_vault_framework/payload/`
- Create: `src/second_brain_vault_framework/manifest.json`

> **Decide the canonical `CLAUDE.md` first.** Two versions exist: the detailed live root
> `CLAUDE.md` and the leaner `scripts/templates/CLAUDE.md`. The payload must ship the one that
> should govern *every* vault. Diff them (`diff "$SRC/CLAUDE.md" "$SRC/scripts/templates/CLAUDE.md"`)
> and copy whichever is authoritative into the payload below. The command as written copies the
> template; change the source path if the root file is the real contract. (Do not merge blindly —
> the payload `CLAUDE.md` is what overwrites consumers on every upgrade.)

- [ ] **Step 1: Copy the existing framework files into the payload**

Run (copies the current live-vault framework files verbatim):
```bash
SRC="/Users/moshe/Desktop/Code/Moshe Vault"
DST="/Users/moshe/Desktop/Code/second-brain-vault-framework/src/second_brain_vault_framework/payload"
cp "$SRC/scripts/templates/CLAUDE.md" "$DST/CLAUDE.md"
cp "$SRC/scripts/templates/gitignore" "$DST/gitignore"
cp "$SRC/instructions.md" "$DST/instructions.md"
mkdir -p "$DST/eval" && cp "$SRC/scripts/templates/eval/VAULT_TESTS.md" "$DST/eval/VAULT_TESTS.md"
mkdir -p "$DST/scripts" && cp "$SRC/scripts/lint_vault.py" "$DST/scripts/lint_vault.py"
# Store the skills under a NON-dotted "dot-claude/" dir so setuptools bundles them
# reliably (recursive package-data globs skip dot-directories). Mapped to ".claude/" on write.
for s in vault-setup vault-ingest vault-query vault-lint; do
  mkdir -p "$DST/dot-claude/skills/$s"
  cp "$SRC/scripts/templates/skills/$s/SKILL.md" "$DST/dot-claude/skills/$s/SKILL.md"
done
```
Expected: no errors; `find "$DST" -type f` lists CLAUDE.md, gitignore, instructions.md, eval/VAULT_TESTS.md, scripts/lint_vault.py, and four SKILL.md files under `dot-claude/skills/`.

- [ ] **Step 2: Add the USER ZONE block to the payload `CLAUDE.md`**

At the very end of `src/second_brain_vault_framework/payload/CLAUDE.md`, append:
```markdown

## Vault-specific configuration

<!-- USER ZONE START -->
<!-- Add vault-specific domain, tags, or rules here. `vault upgrade` preserves this block verbatim. -->
Vault: {{VAULT_NAME}}
<!-- USER ZONE END -->
```

- [ ] **Step 3: Write the payload `scripts/vault.py` shim**

Create `src/second_brain_vault_framework/payload/scripts/vault.py` (the copy that lands in a vault so in-vault skills stay self-contained; it delegates to the installed package, falling back to a clear error):
```python
#!/usr/bin/env python3
"""In-vault shim. Delegates to the installed second-brain-vault-framework package."""
import sys

try:
    from second_brain_vault_framework.cli import main
except ModuleNotFoundError:
    sys.stderr.write(
        "second-brain-vault-framework is not installed in this environment.\n"
        "Install it (pip install second-brain-vault-framework) or run the `vault` command directly.\n"
    )
    raise SystemExit(2)

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Write `manifest.json`**

Create `src/second_brain_vault_framework/manifest.json`:
```json
{
  "owned_paths": [
    "CLAUDE.md",
    "instructions.md",
    ".claude/skills/vault-setup/SKILL.md",
    ".claude/skills/vault-ingest/SKILL.md",
    ".claude/skills/vault-query/SKILL.md",
    ".claude/skills/vault-lint/SKILL.md",
    "scripts/vault.py",
    "scripts/lint_vault.py",
    "eval/VAULT_TESTS.md"
  ],
  "user_zones": {
    "CLAUDE.md": { "start": "<!-- USER ZONE START -->", "end": "<!-- USER ZONE END -->" }
  }
}
```

Note: `.gitignore` is intentionally NOT in `owned_paths` — it is written once at scaffold from the payload `gitignore` file but is thereafter the user's to edit; `upgrade` never touches it.

- [ ] **Step 5: Commit**

```bash
cd /Users/moshe/Desktop/Code/second-brain-vault-framework
git add -A
git commit -m "feat: assemble payload and manifest"
```

---

## Task 2: Port command logic into `core.py`

**Files:**
- Create: `src/second_brain_vault_framework/core.py`

- [ ] **Step 1: Create `core.py` with the payload/manifest access layer**

Create `src/second_brain_vault_framework/core.py`:
```python
"""Vault framework core: payload access, manifest, and command handlers. Stdlib only."""
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from importlib import resources
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

from . import __version__

STAMP_NAME = ".vault-framework.json"
BACKUP_DIR = ".vault-framework-backup"


def framework_version() -> str:
    """Installed distribution version, falling back to the in-tree __version__."""
    try:
        return _pkg_version("second-brain-vault-framework")
    except PackageNotFoundError:
        return __version__


def _payload_root():
    return resources.files("second_brain_vault_framework").joinpath("payload")


def load_manifest() -> dict:
    text = resources.files("second_brain_vault_framework").joinpath("manifest.json").read_text(
        encoding="utf-8")
    return json.loads(text)


def iter_payload_files() -> list[str]:
    """Return payload-relative POSIX paths of every file in the payload tree."""
    out: list[str] = []

    def walk(node, prefix: str) -> None:
        for child in node.iterdir():
            rel = f"{prefix}{child.name}"
            if child.is_dir():
                walk(child, rel + "/")
            else:
                out.append(rel)

    walk(_payload_root(), "")
    return out


def read_payload(rel: str) -> str:
    node = _payload_root()
    for part in rel.split("/"):
        node = node.joinpath(part)
    return node.read_text(encoding="utf-8")


def render(text: str, **vars: str) -> str:
    for key, value in vars.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

- [ ] **Step 2: Port the unchanged helpers and content commands from the old CLI**

Append to `core.py` the following functions **copied verbatim** from `/Users/moshe/Desktop/Code/Moshe Vault/scripts/vault.py`, with two edits noted below:
- `slugify` (old lines 13-16)
- `parse_frontmatter` (old lines 19-44)
- `INDEX_STARTERS` dict (old lines 88-108)
- `cmd_ingest` (old lines 140-181)
- `_raw_stem` (old lines 184-185)
- `cmd_new_note` (old lines 188-210)
- `_find_todo_markers` (old lines 213-218)
- `cmd_register` (old lines 245-262)
- `_summary_exists_for` (old lines 265-281)
- `cmd_status` (old lines 284-296)

Edit 1: these commands still take `root: Path` and operate on it exactly as before — no signature changes.
Edit 2: do NOT copy the old `render_template` or `TEMPLATES_DIR`; `cmd_ingest`/`cmd_new_note`/`cmd_register`/`cmd_status` do not use templates, so they port unchanged.

- [ ] **Step 3: Write manifest access tests**

Create `tests/test_manifest.py`:
```python
from second_brain_vault_framework import core


def test_load_manifest_has_owned_paths_and_zones():
    m = core.load_manifest()
    assert "CLAUDE.md" in m["owned_paths"]
    assert "instructions.md" in m["owned_paths"]
    assert m["user_zones"]["CLAUDE.md"]["start"] == "<!-- USER ZONE START -->"


def test_payload_contains_expected_files():
    payload = set(core.iter_payload_files())
    assert "CLAUDE.md" in payload
    assert "scripts/vault.py" in payload
    assert "dot-claude/skills/vault-setup/SKILL.md" in payload
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/moshe/Desktop/Code/second-brain-vault-framework && python -m pytest tests/test_manifest.py -v`
Expected: 2 passed.

- [ ] **Step 5: Verify the module imports**

Run:
```bash
python -c "import sys; sys.path.insert(0,'src'); import second_brain_vault_framework.core as c; print(c.framework_version()); print(len(c.iter_payload_files()), 'payload files'); print(c.load_manifest()['owned_paths'][0])"
```
Expected: prints `0.1.0`, a payload file count of 9 or more, and `CLAUDE.md`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: port core helpers and content commands"
```

---

## Task 3: User-zone extract/inject helpers (TDD)

**Files:**
- Modify: `src/second_brain_vault_framework/core.py`
- Test: `tests/test_user_zone.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_user_zone.py`:
```python
from second_brain_vault_framework import core

START = "<!-- USER ZONE START -->"
END = "<!-- USER ZONE END -->"


def wrap(inner: str) -> str:
    return f"# Doc\n\n{START}\n{inner}\n{END}\n"


def test_extract_returns_inner_content():
    text = wrap("Vault: alpha\nExtra: beta")
    assert core.extract_zone(text, START, END) == "Vault: alpha\nExtra: beta"


def test_extract_missing_markers_returns_none():
    assert core.extract_zone("# Doc\nno markers here\n", START, END) is None


def test_inject_replaces_inner_between_markers():
    new_doc = wrap("PLACEHOLDER")
    result = core.inject_zone(new_doc, START, END, "Vault: alpha")
    assert core.extract_zone(result, START, END) == "Vault: alpha"
    assert "PLACEHOLDER" not in result


def test_inject_no_markers_appends_zone():
    result = core.inject_zone("# Doc\nbody\n", START, END, "Vault: alpha")
    assert core.extract_zone(result, START, END) == "Vault: alpha"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/moshe/Desktop/Code/second-brain-vault-framework && python -m pytest tests/test_user_zone.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'extract_zone'`.

- [ ] **Step 3: Implement the helpers**

Append to `core.py`:
```python
def extract_zone(text: str, start: str, end: str) -> str | None:
    """Return the content strictly between the start and end markers, or None."""
    s = text.find(start)
    e = text.find(end)
    if s == -1 or e == -1 or e < s:
        return None
    inner = text[s + len(start):e]
    return inner.strip("\n")


def inject_zone(text: str, start: str, end: str, inner: str) -> str:
    """Replace the marked block's inner content with `inner`. Append a block if none exists."""
    s = text.find(start)
    e = text.find(end)
    if s == -1 or e == -1 or e < s:
        return text.rstrip("\n") + f"\n\n{start}\n{inner}\n{end}\n"
    return text[:s + len(start)] + "\n" + inner + "\n" + text[e:]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_user_zone.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: user-zone extract/inject helpers"
```

---

## Task 4: `scaffold` from payload (TDD)

**Files:**
- Modify: `src/second_brain_vault_framework/core.py`
- Test: `tests/test_scaffold.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_scaffold.py`:
```python
import json
from second_brain_vault_framework import core


def test_scaffold_lays_payload_and_stamp(tmp_path):
    target = tmp_path / "myvault"
    rc = core.cmd_scaffold(target, "myvault")
    assert rc == 0

    # framework files present at real paths
    assert (target / "CLAUDE.md").exists()
    assert (target / ".claude/skills/vault-setup/SKILL.md").exists()
    assert (target / "scripts/vault.py").exists()
    assert (target / "instructions.md").exists()

    # gitignore written from the payload "gitignore" file to ".gitignore"
    assert (target / ".gitignore").exists()

    # empty content dirs created
    for d in ["raw", "wiki/sources", "index", "eval"]:
        assert (target / d).is_dir()

    # index starters written
    assert (target / "index/_map-of-content.md").exists()

    # VAULT_NAME rendered, no leftover placeholder
    claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "{{VAULT_NAME}}" not in claude

    # stamp records version, owned_paths, vault_name, and file hashes
    stamp = json.loads((target / ".vault-framework.json").read_text(encoding="utf-8"))
    assert stamp["framework_version"] == core.framework_version()
    assert stamp["vault_name"] == "myvault"
    assert "CLAUDE.md" in stamp["owned_paths"]
    assert "CLAUDE.md" in stamp["file_hashes"]


def test_scaffold_refuses_nonempty_dir(tmp_path):
    target = tmp_path / "myvault"
    target.mkdir()
    (target / "something.md").write_text("x", encoding="utf-8")
    assert core.cmd_scaffold(target, "myvault") == 1


def test_path_mapping_round_trips():
    assert core._dest_rel("gitignore") == ".gitignore"
    assert core._dest_rel("dot-claude/skills/vault-setup/SKILL.md") == \
        ".claude/skills/vault-setup/SKILL.md"
    assert core._payload_src(".gitignore") == "gitignore"
    assert core._payload_src(".claude/skills/vault-setup/SKILL.md") == \
        "dot-claude/skills/vault-setup/SKILL.md"
    # every owned dest path maps to a real payload file
    payload = set(core.iter_payload_files())
    for dest in core.load_manifest()["owned_paths"]:
        assert core._payload_src(dest) in payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scaffold.py -v`
Expected: FAIL with `AttributeError: ... 'cmd_scaffold'`.

- [ ] **Step 3: Implement `cmd_scaffold` plus the shared write/stamp helpers**

Append to `core.py`:
```python
def _rendered_payload(rel: str, vault_name: str) -> str:
    """Payload file content as it should appear on disk (VAULT_NAME rendered)."""
    return render(read_payload(rel), VAULT_NAME=vault_name)


def _dest_rel(payload_rel: str) -> str:
    """Map a payload path to its on-disk path (payload has no dotfiles/dotdirs)."""
    if payload_rel == "gitignore":
        return ".gitignore"
    if payload_rel.startswith("dot-claude/"):
        return ".claude/" + payload_rel[len("dot-claude/"):]
    return payload_rel


def _payload_src(dest_rel: str) -> str:
    """Inverse of _dest_rel: on-disk path → payload path."""
    if dest_rel == ".gitignore":
        return "gitignore"
    if dest_rel.startswith(".claude/"):
        return "dot-claude/" + dest_rel[len(".claude/"):]
    return dest_rel


def _write_file(target: Path, dest_rel: str, content: str) -> None:
    dst = target / dest_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding="utf-8")


def _write_stamp(target: Path, manifest: dict, vault_name: str, hashes: dict) -> None:
    stamp = {
        "framework_version": framework_version(),
        "vault_name": vault_name,
        "owned_paths": manifest["owned_paths"],
        "user_zones": manifest.get("user_zones", {}),
        "file_hashes": hashes,
        "installed_at": datetime.date.today().isoformat(),
    }
    (target / STAMP_NAME).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")


def cmd_scaffold(target: Path, name: str) -> int:
    if target.exists() and any(target.iterdir()):
        print(f"vault scaffold: {target} exists and is non-empty; aborting.", file=sys.stderr)
        return 1
    for sub in ["raw", "wiki/sources", "index", "eval"]:
        (target / sub).mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    hashes: dict[str, str] = {}
    # Lay every payload file down at its real path.
    for rel in iter_payload_files():
        content = _rendered_payload(rel, name)
        dest = _dest_rel(rel)
        _write_file(target, dest, content)
        if dest in manifest["owned_paths"]:
            hashes[dest] = sha256(content)

    for fname, content in INDEX_STARTERS.items():
        (target / "index" / fname).write_text(content, encoding="utf-8")

    _write_stamp(target, manifest, name, hashes)
    print(f"vault scaffold: created {target}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scaffold.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: scaffold a vault from the payload"
```

---

## Task 5: `upgrade` an existing vault (TDD)

**Files:**
- Modify: `src/second_brain_vault_framework/core.py`
- Test: `tests/test_upgrade.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_upgrade.py`:
```python
import json
from second_brain_vault_framework import core

START = "<!-- USER ZONE START -->"
END = "<!-- USER ZONE END -->"


def _scaffold(tmp_path):
    target = tmp_path / "v"
    assert core.cmd_scaffold(target, "v") == 0
    return target


def test_upgrade_preserves_content(tmp_path):
    target = _scaffold(tmp_path)
    (target / "raw" / "clip.md").write_text("my clipping", encoding="utf-8")
    assert core.cmd_upgrade(target) == 0
    assert (target / "raw" / "clip.md").read_text(encoding="utf-8") == "my clipping"


def test_upgrade_preserves_user_zone(tmp_path):
    target = _scaffold(tmp_path)
    claude = target / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8")
    edited = core.inject_zone(text, START, END, "Domain: security advisories")
    claude.write_text(edited, encoding="utf-8")

    assert core.cmd_upgrade(target) == 0
    assert core.extract_zone(claude.read_text(encoding="utf-8"), START, END) == \
        "Domain: security advisories"


def test_upgrade_backs_up_drifted_framework_file(tmp_path):
    target = _scaffold(tmp_path)
    lint = target / "scripts" / "lint_vault.py"
    lint.write_text("# user tampered\n", encoding="utf-8")

    assert core.cmd_upgrade(target) == 0
    # original payload restored
    assert lint.read_text(encoding="utf-8") != "# user tampered\n"
    # backup captured the tampered version
    backups = list((target / core.BACKUP_DIR).rglob("scripts/lint_vault.py"))
    assert backups and backups[0].read_text(encoding="utf-8") == "# user tampered\n"


def test_upgrade_removes_orphaned_framework_file(tmp_path):
    target = _scaffold(tmp_path)
    # Simulate an old version that owned an extra skill now dropped from the manifest.
    orphan = target / ".claude/skills/vault-old/SKILL.md"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("old skill", encoding="utf-8")
    stamp = json.loads((target / core.STAMP_NAME).read_text(encoding="utf-8"))
    stamp["owned_paths"].append(".claude/skills/vault-old/SKILL.md")
    (target / core.STAMP_NAME).write_text(json.dumps(stamp), encoding="utf-8")

    assert core.cmd_upgrade(target) == 0
    assert not orphan.exists()


def test_upgrade_missing_stamp_backs_up_then_stamps(tmp_path):
    target = _scaffold(tmp_path)
    (target / core.STAMP_NAME).unlink()
    (target / "CLAUDE.md").write_text("hand-made\n", encoding="utf-8")

    assert core.cmd_upgrade(target) == 0
    assert (target / core.STAMP_NAME).exists()
    backups = list((target / core.BACKUP_DIR).rglob("CLAUDE.md"))
    assert backups  # pre-existing framework file was backed up before overwrite
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_upgrade.py -v`
Expected: FAIL with `AttributeError: ... 'cmd_upgrade'`.

- [ ] **Step 3: Implement `cmd_upgrade`**

Append to `core.py`:
```python
def _read_stamp(target: Path) -> dict | None:
    p = target / STAMP_NAME
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _backup(target: Path, dest_rel: str, version: str) -> None:
    src = target / dest_rel
    dst = target / BACKUP_DIR / version / dest_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def cmd_upgrade(target: Path) -> int:
    if not target.exists():
        print(f"vault upgrade: {target} does not exist.", file=sys.stderr)
        return 1

    manifest = load_manifest()
    owned = manifest["owned_paths"]
    zones = manifest.get("user_zones", {})
    stamp = _read_stamp(target)
    old_owned = stamp["owned_paths"] if stamp else []
    old_hashes = stamp.get("file_hashes", {}) if stamp else {}
    old_version = stamp.get("framework_version", "unknown") if stamp else "unknown"
    vault_name = stamp.get("vault_name") if stamp else None
    vault_name = vault_name or target.name

    # 1. Delete framework files this version no longer owns.
    for rel in old_owned:
        if rel not in owned and (target / rel).exists():
            (target / rel).unlink()
            print(f"vault upgrade: removed orphaned {rel}")

    # 2. Re-lay each owned file.
    new_hashes: dict[str, str] = {}
    for rel in owned:  # rel is an on-disk (dest) path
        new_content = _rendered_payload(_payload_src(rel), vault_name)
        dst = target / rel
        zone = zones.get(rel)

        if dst.exists():
            current = dst.read_text(encoding="utf-8")
            if zone:
                inner = extract_zone(current, zone["start"], zone["end"])
                if inner is not None:
                    # Preserve the user's zone; never treat a zone edit as drift.
                    new_content = inject_zone(new_content, zone["start"], zone["end"], inner)
                elif sha256(current) != sha256(new_content):
                    # No markers to preserve (legacy/hand-made file) — back up before overwrite.
                    _backup(target, rel, old_version)
                    print(f"vault upgrade: backed up unmarked {rel} → "
                          f"{BACKUP_DIR}/{old_version}/{rel}")
            else:
                # Back up if the user edited a non-zone framework file.
                recorded = old_hashes.get(rel)
                drifted = recorded is None or sha256(current) != recorded
                if drifted and sha256(current) != sha256(new_content):
                    _backup(target, rel, old_version)
                    print(f"vault upgrade: backed up edited {rel} → "
                          f"{BACKUP_DIR}/{old_version}/{rel}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(new_content, encoding="utf-8")
        new_hashes[rel] = sha256(new_content)

    _write_stamp(target, manifest, vault_name, new_hashes)
    print(f"vault upgrade: {target} → {framework_version()}")
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_upgrade.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: upgrade re-lays framework, preserves zone + content, backs up drift"
```

---

## Task 6: `check` — version + drift reporting (TDD)

**Files:**
- Modify: `src/second_brain_vault_framework/core.py`
- Test: `tests/test_check.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_check.py`:
```python
import json
from second_brain_vault_framework import core


def test_check_reports_version_drift(tmp_path, capsys):
    target = tmp_path / "v"
    core.cmd_scaffold(target, "v")
    # Force a stale recorded version.
    stamp = json.loads((target / core.STAMP_NAME).read_text(encoding="utf-8"))
    stamp["framework_version"] = "0.0.1"
    (target / core.STAMP_NAME).write_text(json.dumps(stamp), encoding="utf-8")

    core.cmd_check(target)
    out = capsys.readouterr().out + capsys.readouterr().err
    # The check output mentions the version mismatch.
    assert "0.0.1" in out or "version" in out.lower()


def test_check_clean_scaffold_has_no_todos(tmp_path):
    target = tmp_path / "v"
    core.cmd_scaffold(target, "v")
    # No wiki notes yet → no TODO markers → the stub-completion check passes.
    assert core._find_todo_markers(target) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_check.py -v`
Expected: FAIL with `AttributeError: ... 'cmd_check'`.

- [ ] **Step 3: Implement `cmd_check`**

Append to `core.py` (ports the old `cmd_check` and adds version/drift reporting):
```python
def cmd_check(root: Path) -> int:
    failed = False

    # Framework version + drift notice (non-fatal — informational).
    stamp = _read_stamp(root)
    if stamp is not None:
        recorded = stamp.get("framework_version", "unknown")
        installed = framework_version()
        if recorded != installed:
            print(f"vault check: framework version drift — vault {recorded} vs "
                  f"installed {installed}. Run `vault upgrade` to update.", file=sys.stderr)
        for rel, h in stamp.get("file_hashes", {}).items():
            f = root / rel
            if f.exists() and sha256(f.read_text(encoding="utf-8")) != h and \
                    rel not in stamp.get("user_zones", {}):
                print(f"vault check: framework file edited on disk: {rel}", file=sys.stderr)

    # Layer 1+structural: reuse the shipped lint if present.
    lint = root / "scripts" / "lint_vault.py"
    if lint.exists():
        result = subprocess.run([sys.executable, str(lint)], cwd=str(root))
        if result.returncode != 0:
            print("vault check: lint_vault.py reported findings (see above).", file=sys.stderr)
            failed = True

    # Layer 2: stub-completion.
    todos = _find_todo_markers(root)
    if todos:
        failed = True
        print("vault check: unfilled stub / TODO marker in:", file=sys.stderr)
        for p in todos:
            print(f"  - {p.relative_to(root)} → fill its <!-- TODO --> body from its source.",
                  file=sys.stderr)

    if failed:
        print("vault check: FAIL — fix the findings or STOP and report.", file=sys.stderr)
        return 1
    print("vault check: OK")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_check.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests pass (user-zone 4, scaffold 2, upgrade 5, check 2).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: check reports version + framework-file drift"
```

---

## Task 7: Wire the `cli.py` entry point

**Files:**
- Create: `src/second_brain_vault_framework/cli.py`
- Test: `tests/test_check.py` (add a CLI smoke test)

- [ ] **Step 1: Write the failing CLI test**

Append to `tests/test_check.py`:
```python
def test_cli_scaffold_then_check(tmp_path):
    from second_brain_vault_framework import cli
    target = tmp_path / "cliv"
    assert cli.main(["scaffold", str(target)]) == 0
    assert (target / "CLAUDE.md").exists()
    # check runs against a given directory via --path
    assert cli.main(["check", "--path", str(target)]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_check.py::test_cli_scaffold_then_check -v`
Expected: FAIL with `ModuleNotFoundError: ... cli`.

- [ ] **Step 3: Implement `cli.py`**

Create `src/second_brain_vault_framework/cli.py`:
```python
"""Argument parsing for the `vault` command. Dispatches to core.cmd_*."""
import argparse
from pathlib import Path

from . import core


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vault", description="Vault framework CLI.")
    sub = p.add_subparsers(dest="command", required=True)

    sc = sub.add_parser("scaffold", help="Create a new vault directory.")
    sc.add_argument("dir")

    up = sub.add_parser("upgrade", help="Update framework files in an existing vault.")
    up.add_argument("dir")

    ck = sub.add_parser("check", help="Lint the vault.")
    ck.add_argument("--path", default=".")

    ing = sub.add_parser("ingest")
    ing.add_argument("raw_file")
    ing.add_argument("--path", default=".")

    nn = sub.add_parser("new-note")
    nn.add_argument("slug")
    nn.add_argument("--source", required=True)
    nn.add_argument("--path", default=".")

    reg = sub.add_parser("register")
    reg.add_argument("--dry-run", action="store_true")
    reg.add_argument("--path", default=".")

    st = sub.add_parser("status")
    st.add_argument("--path", default=".")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scaffold":
        return core.cmd_scaffold(Path(args.dir), Path(args.dir).name)
    if args.command == "upgrade":
        return core.cmd_upgrade(Path(args.dir))
    if args.command == "check":
        return core.cmd_check(Path(args.path))
    if args.command == "ingest":
        return core.cmd_ingest(Path(args.path), Path(args.raw_file))
    if args.command == "new-note":
        return core.cmd_new_note(Path(args.path), args.slug, args.source)
    if args.command == "register":
        return core.cmd_register(Path(args.path), dry_run=args.dry_run)
    if args.command == "status":
        return core.cmd_status(Path(args.path))
    return 2
```

Note: `scaffold` derives the vault name from the target directory's basename, matching the stamp's `vault_name`. The content commands gain an optional `--path` (default `.`) so they still work when the in-vault shim runs them from the vault root.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_check.py::test_cli_scaffold_then_check -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: cli entry point wiring"
```

---

## Task 8: Editable install + end-to-end smoke

**Files:** none (verification task)

- [ ] **Step 1: Install the package editable and confirm the entry point**

Run:
```bash
cd /Users/moshe/Desktop/Code/second-brain-vault-framework
pip install -e .
vault --help
```
Expected: help text listing `scaffold`, `upgrade`, `check`, `ingest`, `new-note`, `register`, `status`.

- [ ] **Step 2: Scaffold a throwaway vault and inspect**

Run:
```bash
cd /tmp && rm -rf smoke && vault scaffold /tmp/smoke && ls -A /tmp/smoke && cat /tmp/smoke/.vault-framework.json
```
Expected: framework files + content dirs present; stamp shows `framework_version`, `vault_name: smoke`, `owned_paths`, `file_hashes`.

- [ ] **Step 3: Edit the user-zone + a content file, then upgrade**

Run:
```bash
cd /tmp/smoke
printf 'hello' > raw/x.md
python - <<'PY'
from pathlib import Path
from second_brain_vault_framework import core
p = Path("CLAUDE.md"); t = p.read_text()
p.write_text(core.inject_zone(t, "<!-- USER ZONE START -->", "<!-- USER ZONE END -->", "Domain: smoke-test"))
PY
vault upgrade /tmp/smoke
grep -A1 "USER ZONE START" CLAUDE.md
cat raw/x.md
```
Expected: user-zone still shows `Domain: smoke-test`; `raw/x.md` still says `hello`.

- [ ] **Step 4: Run check**

Run: `vault check --path /tmp/smoke`
Expected: `vault check: OK` (a freshly scaffolded vault has no TODO markers and no lint findings; if `lint_vault.py` reports pre-existing template findings, note them but they are not introduced by this work).

- [ ] **Step 5: Commit any fixes made during smoke testing**

```bash
cd /Users/moshe/Desktop/Code/second-brain-vault-framework
git add -A && git commit -m "test: e2e smoke fixes" --allow-empty
```

---

## Task 9: Dogfood — upgrade the live "Moshe Vault"

**Files:**
- Modify (generated): files under `/Users/moshe/Desktop/Code/Moshe Vault/` framework paths

- [ ] **Step 1: Snapshot the live vault's git state**

Run:
```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault" && git status --short && git rev-parse HEAD
```
Expected: clean tree (or only expected changes). Record the HEAD sha.

- [ ] **Step 2: Add a stamp so upgrade treats it as a known vault (first-time adoption)**

Because the live vault predates the package, it has no `.vault-framework.json`. Run `upgrade` — it will back up any framework file that differs from the new payload, then write a fresh stamp:
```bash
vault upgrade "/Users/moshe/Desktop/Code/Moshe Vault"
```
Expected: prints backups for any drifted framework files and `vault upgrade: … → 0.1.0`.

- [ ] **Step 3: Verify content is untouched**

Run:
```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
git status --short -- raw/ wiki/ index/ graphify-out/
```
Expected: **no changes** under `raw/`, `wiki/`, `index/`, `graphify-out/`. Only framework paths and the new `.vault-framework.json` / `.vault-framework-backup/` may appear.

- [ ] **Step 4: Review the framework diff and the backups**

Run:
```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
git diff -- CLAUDE.md instructions.md scripts/ .claude/
ls -R .vault-framework-backup 2>/dev/null || echo "no drift backups"
```
Expected: the diff reflects only intended framework changes (e.g. the new USER ZONE block in `CLAUDE.md`). **Pay special attention to `CLAUDE.md`:** if the payload shipped the template version but the live root was richer, this diff will show real content loss — the pre-upgrade copy is safe in `.vault-framework-backup/`, but do NOT commit until you've confirmed the payload `CLAUDE.md` (chosen in Task 1) is the one you want governing all vaults. If it isn't, revert (`git checkout -- CLAUDE.md`), fix the payload source in the package, rebuild, and re-run upgrade.

- [ ] **Step 5: Decide + commit (human checkpoint)**

If the diff is acceptable, add `.vault-framework-backup/` to `.gitignore` and commit the adoption:
```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
grep -qxF ".vault-framework-backup/" .gitignore || printf "\n.vault-framework-backup/\n" >> .gitignore
git add -A
git commit -m "chore: adopt second-brain-vault-framework package (dogfood upgrade)"
```
Expected: commit succeeds. The live vault is now a managed consumer of the package.

---

## Task 10: Package build + offline install proof (air-gap smoke)

**Files:** none (verification task)

- [ ] **Step 1: Build the wheel**

Run:
```bash
cd /Users/moshe/Desktop/Code/second-brain-vault-framework
python -m pip install --upgrade build
python -m build
ls dist/
```
Expected: `dist/second_brain_vault_framework-0.1.0-py3-none-any.whl` and a `.tar.gz`.

- [ ] **Step 2: Confirm the payload is bundled in the wheel**

Run:
```bash
python -c "import zipfile; z=zipfile.ZipFile('dist/second_brain_vault_framework-0.1.0-py3-none-any.whl'); print('\n'.join(n for n in z.namelist() if 'payload' in n or n.endswith('manifest.json')))"
```
Expected: lists `.../payload/CLAUDE.md`, the four `payload/dot-claude/skills/vault-*/SKILL.md` files, `payload/scripts/lint_vault.py`, `payload/scripts/vault.py`, `payload/eval/VAULT_TESTS.md`, `payload/instructions.md`, and `manifest.json`. If any are missing (dot-directories are the usual culprit — confirm the `dot-claude/` rename from Task 1 was applied), add a `MANIFEST.in` with `recursive-include src/second_brain_vault_framework/payload *` plus `[tool.setuptools] include-package-data = true` in `pyproject.toml` and rebuild.

- [ ] **Step 3: Install the wheel into a clean venv with networking disabled**

Run:
```bash
cd /tmp && python -m venv airgap-venv
./airgap-venv/bin/pip install --no-index --no-build-isolation \
  /Users/moshe/Desktop/Code/second-brain-vault-framework/dist/second_brain_vault_framework-0.1.0-py3-none-any.whl
./airgap-venv/bin/vault scaffold /tmp/airgap-vault
ls -A /tmp/airgap-vault
```
Expected: install succeeds using only the local wheel (no network); scaffold produces a full vault. This proves the offline install path used inside the air gap.

- [ ] **Step 4: Final commit + tag**

```bash
cd /Users/moshe/Desktop/Code/second-brain-vault-framework
git add -A && git commit -m "chore: buildable wheel with bundled payload" --allow-empty
git tag v0.1.0
```
Expected: tag `v0.1.0` created. This is the artifact to `airgap-pack` and publish to the internal index per `instructions.md` → "Maintainer — cutting and shipping a release".

---

## Notes for the executor

- **`airgap-pack`** (the skill) is invoked at release time on the built `dist/` — it is out of scope for this plan, which stops at a proven-buildable, offline-installable wheel.
- **The live vault's `scripts/templates/`** becomes redundant once the package is the source of truth. Leave it in place for now (Task 9 does not delete it); a follow-up cleanup can remove `scripts/templates/` from the vault after a few releases confirm the package path works. Do not delete it in this plan.
- **Windows:** the plan's commands are shown for macOS/Linux; the package itself is OS-agnostic (pure `pathlib`). Windows install uses `py -m pip install` and `vault` on PATH, per `instructions.md`.
