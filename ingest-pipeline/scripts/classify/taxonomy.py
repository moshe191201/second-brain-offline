#!/usr/bin/env python3
"""Shared taxonomy parsing and template lookup for stage 6.

These lived in second_brain_vault_framework.core, with judge.py and retrieve.py
importing them behind a try/except that silently fell back to a local copy. Now
that the pipeline is decoupled from the framework that import can never succeed,
so the fallback was the only live path and the duplication was pure noise.

One definition, imported by validate.py, judge.py, retrieve.py and
export_label_studio.py. Pure stdlib.
"""
from __future__ import annotations

import re
from pathlib import Path

TAXONOMY_RE = re.compile(r"^\s{2}([\w-]+):\s*(?:\n|$)", re.MULTILINE)

# Keys that appear at subdomain indentation but are not subdomains.
_NON_SUBDOMAIN_KEYS = ("subdomains", "version", "campaign")


def parse_taxonomy_blocks(txt: str) -> dict[str, str]:
    """Map subdomain name -> its raw YAML block."""
    matches = list(TAXONOMY_RE.finditer(txt))
    blocks: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        if name in _NON_SUBDOMAIN_KEYS:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(txt)
        blocks[name] = txt[start:end]
    return blocks


def templates_root() -> Path:
    """Pipeline classification templates.

    Was ``payload_root()/templates/classification`` in the framework, and in the
    scripts a path relative to the CWD that only resolved when the process
    happened to start at the repo root. Resolved from this file instead.
    """
    return Path(__file__).resolve().parents[2] / "templates" / "classification"
