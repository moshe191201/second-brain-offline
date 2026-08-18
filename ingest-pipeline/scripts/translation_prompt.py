"""Prompt builders — extracted from translate.py (pure move)."""
from __future__ import annotations

import json
import re

from translation_chunking import chunk_markdown, glossary_for_chunk
from translation_invariants import extract_preservation_invariants


def build_prompt(chunk_text: str, section_path: str, glossary_rows: list[dict],
                 prev_tail: str = "", invariants: dict | None = None, term_map: list[dict] | None = None) -> str:
    # Sentinel contract (Task 3): when term_map provided, render Pre-translated block instead of glossary_block
    glossary_block = ""
    sentinel_block = ""
    if term_map is not None:
        if term_map:
            lines: list[str] = []
            for e in term_map:
                term_he = e.get("term_he", "") or ""
                eng = e.get("english", "") or ""
                occ = e.get("occurrences", 1)
                keep = e.get("keep_source", False)
                is_keep = keep is True or keep == 1 or str(keep) == "1"
                if is_keep:
                    from translation_common import build_keep_sentinel
                    sentinel = build_keep_sentinel(term_he)
                    lines.append(f"  - {sentinel} ← {term_he} (keep as Hebrew, appears {occ}×)")
                else:
                    from translation_common import build_glossary_sentinel
                    tid = e.get("id", 0)
                    try:
                        tid_int = int(tid)
                    except Exception:
                        tid_int = 0
                    sentinel = build_glossary_sentinel(tid_int, eng)
                    lines.append(f"  - {sentinel} ← {term_he} (appears {occ}×)")
            sentinel_block = "Pre-translated terms in this chunk:\n" + "\n".join(lines) + "\n\n"
    elif glossary_rows:
        lines = []
        for r in glossary_rows:
            term = r.get("term_he", "")
            eng = r.get("english", "")
            ks = r.get("keep_source", "0")
            if ks == "1":
                lines.append(f"- {term} → KEEP AS-IS (do not translate)")
            elif eng:
                lines.append(f"- {term} → {eng}")
            else:
                lines.append(f"- {term} → (translate per context)")
        glossary_block = "Glossary (use these exact renderings):\n" + "\n".join(lines) + "\n\n"

    prev_block = ""
    if prev_tail:
        prev_block = f"Previous chunk tail (context only, do not re-emit):\n{prev_tail[:800]}\n\n"

    # Preservation context: invariants the LLM sees verbatim and must copy exactly
    preserve_block = ""
    if invariants:
        parts: list[str] = []
        for cat, label in [("yaml_frontmatter", "YAML frontmatter (keep exactly, first block)"),
                           ("code_sections", "Code sections (fenced/inline — keep exactly, in order)"),
                           ("person_names", "Person names (Hebrew — keep exactly, in order)"),
                           ("english_spans", "English spans (Latin — keep verbatim, in order)"),
                           ("urls_and_paths", "URLs/file-paths (keep verbatim, in order)")]:
            items = invariants.get(cat) or []
            if items:
                # Cap to keep prompt small; full list still verified after
                shown = items[:30]
                # For yaml/code, trim long blocks for prompt but verification uses full value
                def _short(s: str) -> str:
                    return s[:300] + ("…(truncated)" if len(s) > 300 else "")
                shown_short = [_short(s) for s in shown]
                parts.append(f"{label}: {json.dumps(shown_short, ensure_ascii=False)}")
                if len(items) > 30:
                    parts[-1] += f" (+{len(items)-30} more)"
        if parts:
            preserve_block = "Preserve verbatim IN ORDER — these strings from the source MUST appear exactly and in the same relative order in the output (code/YAML frontmatter included):\n" + "\n".join(f"- {p}" for p in parts) + "\n\n"

    # Rules diverge for sentinel vs legacy glossary mode (preserve_block unchanged per task)
    if term_map is not None:
        rules_block = (
            f"Translate this Hebrew markdown chunk to faithful technical English.\n"
            f"Rules:\n"
            f"- Preserve headings, lists, tables, code fences exactly (same counts) and in the same order.\n"
            f"- Blocks of the form ⟦EN:{{id}}:{{English}}⟧ are pre-translated glossary terms — copy them VERBATIM including the ⟦EN: and ⟧ delimiters, do not translate, inflect, or reorder their interior English. Translate the surrounding Hebrew particles as normal English prepositions/pronouns.\n"
            f"- Blocks ⟦KEEP:{{Hebrew}}⟧ must be copied verbatim as Hebrew.\n"
            f"- Person names, English/URLs/code/YAML listed below must be copied verbatim and kept in the same relative order as in the source — do not translate, transliterate, reorder, or alter them.\n"
            f"- Never invent translations for unknown terms — list them in unknown_terms and emit ⟦he:term⟧.\n"
            f"- Output JSON: {{\"translation\": string, \"unknown_terms\": [string], \"notes\": [string]}}\n\n"
        )
        term_block_to_emit = sentinel_block
        glossary_to_emit = ""
    else:
        rules_block = (
            f"Translate this Hebrew markdown chunk to faithful technical English.\n"
            f"Rules:\n"
            f"- Preserve headings, lists, tables, code fences exactly (same counts) and in the same order.\n"
            f"- Use glossary renderings exactly where they appear.\n"
            f"- Person names, English/URLs/code/YAML listed below must be copied verbatim and kept in the same relative order as in the source — do not translate, transliterate, reorder, or alter them.\n"
            f"- Never invent translations for unknown terms — list them in unknown_terms.\n"
            f"- Output JSON: {{\"translation\": string, \"unknown_terms\": [string], \"notes\": [string]}}\n\n"
        )
        term_block_to_emit = ""
        glossary_to_emit = glossary_block

    return (
        f"{rules_block}"
        f"{term_block_to_emit}"
        f"{glossary_to_emit}"
        f"{preserve_block}"
        f"{prev_block}"
        f"Section: {section_path}\n\n"
        f"Chunk to translate:\n{chunk_text}\n"
    )


def format_qa_failures(checks: list[dict]) -> list[dict]:
    """Filter QA checks to failures only (status==fail)."""
    return [c for c in checks if c.get("status") == "fail"]


def build_fix_prompt(source_text: str, prev_translation: str, failures: list[dict],
                     glossary_rows: list[dict] | None = None,
                     invariants: dict | None = None, term_map: list[dict] | None = None) -> str:
    """Prompt for LLM to repair previous translation given QA failures."""
    src_cap = source_text[:12000]
    if len(source_text) > 12000:
        src_cap += f"\n…(truncated {len(source_text) - 12000} chars omitted — chunked fix should have been used)"
    prev_cap = prev_translation[:12000]
    if len(prev_translation) > 12000:
        prev_cap += f"\n…(truncated {len(prev_translation) - 12000} chars omitted — chunked fix should have been used)"
    _full_failure = json.dumps(failures, ensure_ascii=False, indent=2)
    failure_block = _full_failure[:6000]
    if len(_full_failure) > 6000:
        failure_block += "\n…(truncated)"
    glossary_block = ""
    if term_map is not None:
        if term_map:
            lines: list[str] = []
            for e in term_map[:20]:
                term_he = e.get("term_he", "") or ""
                eng = e.get("english", "") or ""
                occ = e.get("occurrences", 1)
                keep = e.get("keep_source", False)
                is_keep = keep is True or keep == 1 or str(keep) == "1"
                if is_keep:
                    from translation_common import build_keep_sentinel
                    sentinel = build_keep_sentinel(term_he)
                    lines.append(f"  - {sentinel} ← {term_he} (keep as Hebrew, appears {occ}×)")
                else:
                    from translation_common import build_glossary_sentinel
                    tid = e.get("id", 0)
                    try:
                        tid_int = int(tid)
                    except Exception:
                        tid_int = 0
                    sentinel = build_glossary_sentinel(tid_int, eng)
                    lines.append(f"  - {sentinel} ← {term_he} (appears {occ}×)")
            if lines:
                glossary_block = "Pre-translated terms in this chunk (fix — copy VERBATIM):\n" + "\n".join(lines)
                if len(term_map) > 20:
                    glossary_block += f"\n(+{len(term_map) - 20} more)"
                glossary_block += "\n\n"
    elif glossary_rows:
        lines = []
        for r in glossary_rows[:20]:
            term = r.get("term_he", "")
            eng = r.get("english", "")
            if term and eng:
                lines.append(f"- {term} → {eng}")
        if lines:
            glossary_block = "Glossary (must use exactly):\n" + "\n".join(lines)
            if glossary_rows and len(glossary_rows) > 20:
                glossary_block += f"\n(+{len(glossary_rows) - 20} more)"
            glossary_block += "\n\n"
    invariants_block = ""
    if invariants:
        parts = []
        for cat, items in invariants.items():
            if items:
                shown = items[:10]
                part = f"{cat}: {json.dumps(shown, ensure_ascii=False)}"
                if len(items) > 10:
                    part += f" (+{len(items) - 10} more)"
                parts.append(part)
        if parts:
            invariants_block = "Preserve verbatim in order:\n" + "\n".join(f"- {p}" for p in parts) + "\n\n"
    return (
        "You are repairing a Hebrew→English markdown translation that FAILED scripted QA checks.\n"
        "Fix ONLY the reported failures. Keep everything else identical.\n"
        "Rules:\n"
        "- Preserve headings, lists, tables, code fences exactly (same counts) and in order.\n"
        "- Use glossary renderings exactly where they appear.\n"
        "- Person names, English/URLs/code/YAML below must be copied verbatim and in order.\n"
        "- Never invent translations for unknown terms — use ⟦he:term⟧ and list in unknown_terms.\n"
        "- Output JSON: {\"translation\": string, \"unknown_terms\": [string], \"notes\": [string]}\n\n"
        f"{glossary_block}"
        f"{invariants_block}"
        f"QA failures to fix:\n{failure_block}\n\n"
        f"Original Hebrew source:\n{src_cap}\n\n"
        f"Previous translation (to repair):\n{prev_cap}\n"
    )


def _build_chunked_fix_prompts(source_text: str, prev_translation: str, failures: list[dict],
                               glossary_rows: list[dict] | None, invariants: dict | None,
                               chunk_chars: int,
                               first_names: set[str] | None = None, last_names: set[str] | None = None) -> list[str]:
    """Split large-doc fix into per-chunk prompts to avoid 12k truncation loss."""
    src_chunks = chunk_markdown(source_text, max_chars=chunk_chars)
    prev_chunks = chunk_markdown(prev_translation, max_chars=chunk_chars) if prev_translation.strip() else []
    n = max(len(src_chunks), len(prev_chunks), 1)
    fn = first_names if first_names is not None else set()
    ln = last_names if last_names is not None else set()
    prompts: list[str] = []
    for i in range(n):
        src = src_chunks[i]["chunk_text"] if i < len(src_chunks) else ""
        prev = prev_chunks[i]["chunk_text"] if i < len(prev_chunks) else ""
        section = src_chunks[i].get("section_path", "") if i < len(src_chunks) else f"chunk {i+1}/{n}"
        # Per-chunk filtering: only inject glossary terms that occur in this chunk
        if src and glossary_rows:
            cg = glossary_for_chunk(src, glossary_rows)
            chunk_glossary: list[dict] | None = cg  # [] means no terms in this chunk — keep empty
        elif src:
            chunk_glossary = None
        else:
            chunk_glossary = glossary_rows
        # Chunk-specific invariants with real person-name allowlist
        chunk_invariants = extract_preservation_invariants(src, fn, ln) if src else None
        if chunk_invariants is None:
            chunk_invariants = invariants
            if chunk_glossary is None:
                chunk_glossary = glossary_rows
        p = build_fix_prompt(src, prev, failures, chunk_glossary, chunk_invariants)
        # Annotate that failures are global — model should only fix those affecting its chunk
        global_note = "Note: QA failures above are global for the whole document — fix only those that affect your chunk's section, keep rest identical.\n\n"
        p = f"Chunk {i+1}/{n} — Section: {section}\n{global_note}" + p
        prompts.append(p)
    return prompts
