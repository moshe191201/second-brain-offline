#!/usr/bin/env python3
"""Assert the built wheel carries exactly the payload the manifest describes.

A wheel missing payload files installs cleanly and only fails later at
`vault scaffold`, in a consumer's environment. The check used to be
`len(payload) >= 8` against 10 real files, so two could vanish -- including any
single SKILL.md -- and still pass. Derived from the manifest instead, so it is
exact and updates itself when the payload does.

Pure stdlib, run by both CI providers.
"""
from __future__ import annotations

import glob
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src" / "second_brain_vault_framework"
# payload/gitignore is written directly by cmd_scaffold and is in no manifest
# list; it still has to be inside the wheel. See tests/test_boundary.py.
UNMANIFESTED = {"gitignore"}


def expected_payload_names() -> set[str]:
    manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
    names = set(manifest["owned_paths"]) | set(manifest["scaffold_only_paths"]) | UNMANIFESTED
    # vault-relative -> payload-relative (packaging backends skip dot-dirs)
    return {n.replace(".claude/", "dot-claude/", 1) if n.startswith(".claude/") else n
            for n in names}


def main() -> int:
    wheels = glob.glob(str(ROOT / "dist" / "*.whl"))
    if not wheels:
        print("no wheel in dist/", file=sys.stderr)
        return 1
    inside = {f.split("/payload/", 1)[1]
              for f in zipfile.ZipFile(wheels[0]).namelist() if "/payload/" in f}
    expected = expected_payload_names()
    missing = sorted(expected - inside)
    extra = sorted(inside - expected - {".DS_Store"})
    for f in sorted(expected & inside):
        print(f"  ok      {f}")
    for f in missing:
        print(f"  MISSING {f}", file=sys.stderr)
    for f in extra:
        print(f"  EXTRA   {f} (in the wheel but in no manifest list)", file=sys.stderr)
    print(f"{len(inside)} payload files in wheel, {len(expected)} expected")
    return 1 if (missing or extra) else 0


if __name__ == "__main__":
    sys.exit(main())
