"""Shared helpers for translation pipeline.

Deduped from 5 places (check_glossary.py, glossary_translate.py,
translation_qa.py, translation_reviewer.py, translate.py).

This module is the single source of truth for:
- CSV comment stripping (strip # / empty lines before DictReader)
- Frontmatter stripping (--- block)
- GFM table cell splitting (escaped pipes)

Import from here instead of copy-pasting.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

GLOSSARY_SENTINEL_RE = re.compile(r"⟦EN:(\d+):[^⟧]+⟧")
GLOSSARY_KEEP_RE = re.compile(r"⟦KEEP:[^⟧]+⟧")
GLOSSARY_ANY_RE = re.compile(r"⟦(?:EN:\d+:[^⟧]+|KEEP:[^⟧]+)⟧")


def build_glossary_sentinel(idx: int, english: str) -> str:
    return f"⟦EN:{idx}:{english}⟧"


def build_keep_sentinel(term_he: str) -> str:
    return f"⟦KEEP:{term_he}⟧"


def parse_glossary_sentinel(s: str) -> tuple[int, str] | None:
    m = re.match(r"⟦EN:(\d+):([^⟧]+)⟧", s)
    if not m:
        return None
    return int(m.group(1)), m.group(2)


def compute_glossary_version(glossary_path: Path) -> str:
    if not glossary_path.exists():
        return "no-glossary"
    h = hashlib.sha256(glossary_path.read_bytes()).hexdigest()[:12]
    return h


def check_glossary_collisions(rows: list[dict]) -> None:
    """M7: fail if duplicate english for different term_he or vice versa."""
    seen_en: dict[str, str] = {}
    seen_he: dict[str, str] = {}
    for r in rows:
        he = (r.get("term_he") or "").strip()
        en = (r.get("english") or "").strip()
        st = (r.get("status") or "approved").strip()
        if st not in ("approved", "keep_source") or not he or not en:
            continue
        if en in seen_en and seen_en[en] != he:
            raise RuntimeError(f"glossary collision: english {en!r} maps to both {seen_en[en]!r} and {he!r}")
        if he in seen_he and seen_he[he] != en:
            raise RuntimeError(f"glossary collision: term {he!r} has conflicting english {seen_he[he]!r} vs {en!r}")
        seen_en[en] = he
        seen_he[he] = en


def strip_csv_comments(text: str) -> list[str]:
    """Strip empty and # comment lines — for in-memory CSV text."""
    return [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def read_csv_lines_skip_comments(path: Path) -> list[str]:
    """Read file and strip # comment / empty lines before DictReader."""
    text = path.read_text(encoding="utf-8")
    return strip_csv_comments(text)


def strip_frontmatter(text: str) -> tuple[str, str]:
    """Split --- frontmatter block from body.

    Returns (frontmatter_text, body). frontmatter_text includes trailing ---.
    Matches translation_qa.py and translation_reviewer.py implementations.
    """
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[: end + 5], text[end + 5 :]
    return "", text


def split_table_cells(row: str) -> list[str]:
    """Split a GFM row on unescaped pipes.

    Keeps \\ escaped pipes intact. Drops leading/trailing empties from
    outer pipes. Keep in sync — used by md_mask.py and translation_qa.py.
    """
    parts: list[str] = []
    cur = ""
    i = 0
    while i < len(row):
        if row[i] == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            cur += "\\|"
            i += 2
            continue
        if row[i] == "|":
            parts.append(cur)
            cur = ""
            i += 1
            continue
        cur += row[i]
        i += 1
    parts.append(cur)
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return parts


# Alias for translation_qa legacy name
split_row_cells = split_table_cells


def load_codenames(vault_root: Path) -> set[str]:
    """Load org codenames that must NOT be masked as person names.

    Codenames are Hebrew terms like ברק/דניאל that collide with common given names
    but have English equivalents in the glossary and must be translated.
    File: data/person_names/codenames.txt — one term per line, # comments ignored.
    """
    p = vault_root / "data" / "person_names" / "codenames.txt"
    if not p.exists():
        return set()
    try:
        return {line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")}
    except OSError:
        return set()


def load_person_names(vault_root: Path, exclude: set[str] | None = None) -> tuple[set[str], set[str]]:
    """Load person-name allowlists (fail-closed).

    Expects data/person_names/first_names.txt (593) and last_names_ranked.txt (818).
    Raises RuntimeError if files missing/empty — empty guard would silently translate names.
    """
    first_p = vault_root / "data" / "person_names" / "first_names.txt"
    last_p = vault_root / "data" / "person_names" / "last_names_ranked.txt"
    if not first_p.exists():
        raise RuntimeError(f"person name file missing: {first_p} — restore data/person_names/first_names.txt — fail-closed, refusing to run with empty guard")
    if not last_p.exists():
        raise RuntimeError(f"person name file missing: {last_p} — restore data/person_names/last_names_ranked.txt — fail-closed")
    first: set[str] = set()
    last: set[str] = set()
    for p, s in [(first_p, first), (last_p, last)]:
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                t = line.strip()
                if t:
                    s.add(t)
        except OSError as e:
            raise RuntimeError(f"cannot read {p}: {e}") from e
    if not first or not last:
        raise RuntimeError(f"person name files empty: {first_p} ({len(first)}), {last_p} ({len(last)}) — expected non-empty, fail-closed")
    codenames = load_codenames(vault_root)
    if exclude:
        codenames = codenames | exclude
    if codenames:
        first -= codenames
        last -= codenames
    return first, last
