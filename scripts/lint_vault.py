#!/usr/bin/env python3
"""Vault lint: exits non-zero if any finding is reported."""

import re
import sys
from pathlib import Path

VAULT = Path(__file__).parent.parent
RAW = VAULT / "raw"
WIKI = VAULT / "wiki"
INDEX = VAULT / "index"
LOG = INDEX / "log.md"
MOC = INDEX / "_map-of-content.md"

# Wikilinks that are intentionally not vault notes (author names, external refs)
KNOWN_EXTERNAL = {"Miguel Otero Pedrido"}

findings = []


def find(msg):
    findings.append(msg)


def all_stems():
    """All valid wikilink targets across raw/, wiki/, wiki/sources/, index/."""
    result = {}
    for folder in [RAW, WIKI, WIKI / "sources", INDEX]:
        if folder.exists():
            for p in folder.glob("*.md"):
                result[p.stem] = p
    return result


def wikilinks_in(text):
    return [m.group(1).strip() for m in re.finditer(r"\[\[([^\]|#]+)", text)]


stems = all_stems()

# 1. Broken wikilinks
for folder in [WIKI, INDEX]:
    for p in folder.rglob("*.md"):
        for link in wikilinks_in(p.read_text()):
            if link not in stems and link not in KNOWN_EXTERNAL:
                find(f"BROKEN WIKILINK: [[{link}]] in {p.relative_to(VAULT)}")

# 2. Orphan wiki notes (no inbound link from any wiki or index note)
linked_to = set()
for folder in [WIKI, INDEX]:
    for p in folder.rglob("*.md"):
        for link in wikilinks_in(p.read_text()):
            linked_to.add(link)

for p in WIKI.rglob("*.md"):
    if p.stem not in linked_to:
        find(f"ORPHAN NOTE: {p.relative_to(VAULT)} has no inbound links")

# 3. Raw clippings never referenced
for p in RAW.glob("*.md"):
    if p.stem not in linked_to:
        find(f"UNREFERENCED RAW: {p.stem}")

# 4. Wiki notes missing sources: frontmatter
#    (index-type, analysis-type, and wiki/sources/ notes are exempt)
for p in WIKI.glob("*.md"):
    text = p.read_text()
    if "type: index" in text or "type: analysis" in text:
        continue
    if "sources:" not in text:
        find(f"MISSING SOURCES: {p.relative_to(VAULT)}")

# 5. Each raw clipping has an ingest entry in log.md
if LOG.exists():
    log_text = LOG.read_text()
    for p in RAW.glob("*.md"):
        if p.stem not in log_text:
            find(f"NO LOG ENTRY: {p.name} missing from index/log.md")
else:
    find("MISSING FILE: index/log.md does not exist")

# 6. Every wiki note reachable from MOC (transitive link closure)
if MOC.exists():
    visited = set()
    queue = [MOC]
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        if not current.exists():
            continue
        for link in wikilinks_in(current.read_text()):
            if link in stems:
                queue.append(stems[link])
    reachable = {p.stem for p in visited}
    for p in WIKI.rglob("*.md"):
        if p.stem not in reachable:
            find(f"UNREACHABLE FROM MOC: {p.relative_to(VAULT)}")
else:
    find("MISSING FILE: index/_map-of-content.md does not exist")

# 7. Duplicate stems across folders
seen_stems: dict[str, Path] = {}
for folder in [RAW, WIKI, WIKI / "sources", INDEX]:
    if not folder.exists():
        continue
    for p in folder.glob("*.md"):
        if p.stem in seen_stems:
            find(
                f"DUPLICATE STEM: '{p.stem}' in {p.relative_to(VAULT)}"
                f" and {seen_stems[p.stem].relative_to(VAULT)}"
            )
        else:
            seen_stems[p.stem] = p

# Report
total = len(stems)
if findings:
    print(f"\n{'='*60}")
    print(f"VAULT LINT: {len(findings)} finding(s)  [{total} notes checked]")
    print("=" * 60)
    for f in findings:
        print(f"  • {f}")
    print()
    sys.exit(1)
else:
    print(f"VAULT LINT: OK — no findings  [{total} notes checked]")
    sys.exit(0)
