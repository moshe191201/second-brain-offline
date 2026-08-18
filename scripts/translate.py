#!/usr/bin/env python3
"""Translate Hebrew markdown chunks to English with glossary + name guard.

- Structural chunking at heading/paragraph boundaries (never mid-sentence/table/code).
- English-only docs are skipped (no Hebrew → ledger skipped_english, no output file).
- Preservation by verification (not masking): person names, English spans, and
  URLs/file-paths are extracted from the source chunk, passed to the LLM as
  explicit verbatim-context, and verified to appear in the output.
- Filtered glossary: only terms occurring in chunk are injected.
- Person-name guard: exact-match against data/person_names/ (593 first + 818 last),
  extracted + verified (not masked).
- Structured output {translation, unknown_terms, notes} via response_format=json_object.
- Zero-guessing: unknown terms → ⟦he:<term>⟧ markers, blocked_on_term ledger.
- Content-addressed store data/translations/<sha>/translation.md + ledger.jsonl.
- Bounded retries (max 3).

Config: convert_config.json translation block:
  translation {base_url (\"\"), reviewer_base_url (\"\"), api_key_env (TRANSLATE_API_KEY),
               model (minimax-m2.7), reviewer_model (kimi-k2.7), chunk_chars (6000),
               review_sample (0.2), glossary_path (data/domain_terms/glossary.csv),
               fix_rounds (3)}
  Defaults: base_url \"\", reviewer_base_url \"\", chunk_chars 6000, review_sample 0.2,
            glossary_path data/domain_terms/glossary.csv, fix_rounds 3, model minimax-m2.7,
            reviewer_model kimi-k2.7, api_key_env TRANSLATE_API_KEY.
  Env precedence: TRANSLATE_BASE_URL primary, QMD_OPENAI_BASE_URL fallback;
  reviewer uses TRANSLATE_REVIEWER_BASE_URL override (see translation_reviewer.py).
  fix_rounds precedence: CLI --fix-rounds > TRANSLATE_FIX_ROUNDS env > config > 3 (0=disable).
Fail-fast if base_url missing. --mock for CI (mock is PERSON-sentinel aware: splits by
  ⟦PERSON_n⟧, only wraps remaining [א-ת]{2,} as ⟦he:…⟧ so sentinels are not marked).

CLI:
  python scripts/translate.py [vault_root] [--input DIR] [--glossary PATH] [--out DIR]
                              [--check] [--mock] [--force] [--resume] [--limit N] [--fix-rounds N]
  vault_root positional (default ".")
  --input DIR     corpus dir (default raw_md/raw auto-detect)
  --glossary PATH glossary.csv override (default translation.glossary_path or vault/data/domain_terms/glossary.csv)
  --out DIR       output store dir (default vault/data/translations, canonical ledger vault/data/translations/ledger.jsonl)
  --check         only check glossary gate, exit 1 if blocked
  --mock          offline mock (glossary substitution + sentinel-aware Hebrew marking)
  --force         retranslate even if cached (content-addressed <sha> already exists)
  --resume        same as default (resume by hash, kept for docs compat)
  --limit N       limit files (0=all)
  --fix-rounds N  max LLM fix rounds per doc after QA failures (default 3, 0=disable, env TRANSLATE_FIX_ROUNDS overrides config)
"""
from __future__ import annotations

import argparse
import csv
try:
    from translation_common import read_csv_lines_skip_comments as _shared_read_csv
    _HAS_SHARED = True
except ImportError:
    try:
        from scripts.translation_common import read_csv_lines_skip_comments as _shared_read_csv
        _HAS_SHARED = True
    except ImportError:
        _HAS_SHARED = False
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

try:
    import md_mask  # type: ignore
except ModuleNotFoundError:
    md_mask = None  # type: ignore

from translation_invariants import (
    PERSON_OPEN, PERSON_CLOSE, EN_OPEN, EN_CLOSE, HE_MARKER_FMT,
    HEBREW_WORD_RE,
    mask_person_names, _mask_via_tokens, unmask_person_names,
    is_english_only_doc, mask_english_spans, unmask_english_spans,
    extract_english_spans, extract_urls_and_paths, extract_person_names,
    extract_yaml_frontmatter, extract_code_sections,
    extract_preservation_invariants,
    verify_preserved, verify_all_preserved, verify_ordered, verify_all_ordered, verify_global_order,
)
# Keep private regex names re-exported for tests that patch via translate.* if any
import translation_invariants as _invariants
_EN_SPAN_RE = _invariants._EN_SPAN_RE
_COMMON_ENGLISH = _invariants._COMMON_ENGLISH
_URL_RE = _invariants._URL_RE
_FILEPATH_RE = _invariants._FILEPATH_RE
_YAML_RE = _invariants._YAML_RE
_CODE_RE = _invariants._CODE_RE


def get_ledger_path(vault_root: Path, out_root: Path | None = None) -> Path:
    """Canonical ledger path: vault_root/data/translations/ledger.jsonl.

    If out_root is an explicit custom dir outside the vault, use out_root/ledger.jsonl
    so --out tests still write locally. Otherwise always canonical.
    """
    canonical = vault_root / "data" / "translations" / "ledger.jsonl"
    if out_root is None:
        return canonical
    try:
        # If out_root is inside vault_root, prefer canonical to avoid split ledgers
        out_root.resolve().relative_to(vault_root.resolve())
        return canonical
    except ValueError:
        return out_root / "ledger.jsonl"


def load_config(vault_root: Path) -> dict:
    p = vault_root / "convert_config.json"
    if p.exists():
        raw = p.read_text(encoding="utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid convert_config.json ({p}): {e}", file=sys.stderr)
            raise RuntimeError(f"invalid convert_config.json: {e}") from e
    return {}


def resolve_fix_rounds(cfg: dict, cli_value: int | None) -> int:
    """Resolve fix_rounds: CLI > env TRANSLATE_FIX_ROUNDS > config > default 3."""
    if cli_value is not None:
        try:
            v = int(cli_value)
            return max(0, v)
        except (TypeError, ValueError):
            pass
    env = os.environ.get("TRANSLATE_FIX_ROUNDS")
    if env is not None:
        try:
            return max(0, int(env.strip()))
        except (TypeError, ValueError):
            pass
    tcfg = cfg.get("translation", {}) if isinstance(cfg, dict) else {}
    raw = tcfg.get("fix_rounds", 3)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 3


def resolve_corpus_dir(vault_root: Path, explicit: Path | None = None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.is_dir():
            print(f"ERROR: input dir not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p
    for name in ("raw_md", "raw"):
        p = vault_root / name
        if p.is_dir() and any(p.rglob("*.md")):
            return p
    print(f"ERROR: neither raw_md/ nor raw/ with *.md under {vault_root}", file=sys.stderr)
    sys.exit(1)


def _read_csv_skip_comments(path: Path) -> list[str]:
    """Read CSV text stripping # comment and empty lines (matches check_glossary) — via translation_common."""
    if _HAS_SHARED:
        return _shared_read_csv(path)
    text = path.read_text(encoding="utf-8")
    return [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def load_glossary(glossary_path: Path) -> list[dict]:
    if not glossary_path.exists():
        return []
    lines = _read_csv_skip_comments(glossary_path)
    if not lines:
        return []
    reader = csv.DictReader(lines)
    if not reader.fieldnames:
        return []
    return list(reader)


# Person-name helpers — single source in translation_common.py (fail-closed)
from translation_common import load_codenames, load_person_names  # re-export


from translation_chunking import chunk_markdown, glossary_for_chunk


from translation_masking import (
    HEBREW_RANGE, PROCLITICS, RAW_WORD_RE, MIXED_SPLIT_RE,
    _require_yap, _heuristic_split, _roots_for_token, _analyze_with_fallback,
    mask_glossary_terms, unmask_glossary_terms,
)
import translation_masking as _masking
_YAP_AVAILABLE = _masking._YAP_AVAILABLE

# Proxy YAP mock targets so `mock.patch("translate._yap_root_keys")` propagates to masking
import types as _types_mask
class _TranslateMaskingProxy(_types_mask.ModuleType):
    def __setattr__(self, name, value):
        if name in ("_yap_root_keys", "_yap_analyze", "_YAP_AVAILABLE"):
            try:
                setattr(_masking, name, value)
            except Exception:
                pass
        super().__setattr__(name, value)
try:
    import sys as _sys_mask
    _sys_mask.modules[__name__].__class__ = _TranslateMaskingProxy
except Exception:
    pass
def __getattr__(name):  # PEP 562
    if name in ("_yap_root_keys", "_yap_analyze", "_YAP_AVAILABLE"):
        return getattr(_masking, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


from translation_llm import call_llm, mock_translate, _mock_with_sentinels

from translation_prompt import build_prompt, build_fix_prompt, _build_chunked_fix_prompts, format_qa_failures


def run_qa_for_doc(source_path: Path, trans_body: str, trans_meta: dict,
                   glossary: list[dict], vault_root: Path | None,
                   term_map: list[dict] | None = None) -> list[dict]:
    """Run scripted QA battery; returns list of check dicts. Falls back gracefully.

    term_map is threaded explicitly so document-level sentinel check gates the doc.
    If term_map is None, falls back to trans_meta.get("term_map") for compat.
    """
    try:
        import translation_qa as qa_mod
    except ImportError:
        return []
    try:
        return qa_mod.run_all(source_path, trans_body, trans_meta, glossary, vault_root=vault_root, term_map=term_map)
    except Exception as e:
        return [{"check": "qa_runner", "status": "fail", "error": str(e)[:500]}]


def _translate_chunks(raw_text: str, first_names: set[str], last_names: set[str],
                      glossary: list[dict], base_url: str, api_key: str, model: str,
                      mock: bool, chunk_chars: int, no_mask: bool,
                      name_candidates: set[str] | None) -> tuple[str, list[str], list[dict]]:
    """Translate raw_text chunk by chunk. Returns (full_translation, doc_unknown, chunk_notes).

    Also collects term_map across chunks for ledger determinism (Task 5).
    The fourth element (term_map list) is available via _translate_chunks_with_term_map;
    this wrapper keeps back-compat and attaches term_map via attribute.
    """
    # Delegate to version that also returns term_map
    full, unknown, notes, _tm = _translate_chunks_with_term_map(
        raw_text, first_names, last_names, glossary, base_url, api_key, model, mock, chunk_chars, no_mask, name_candidates
    )
    # Stash term_map on the function for caller inspection without breaking tuple unpack
    _translate_chunks.last_term_map = _tm  # type: ignore[attr-defined]
    return full, unknown, notes


def _translate_chunks_with_term_map(raw_text: str, first_names: set[str], last_names: set[str],
                      glossary: list[dict], base_url: str, api_key: str, model: str,
                      mock: bool, chunk_chars: int, no_mask: bool,
                      name_candidates: set[str] | None) -> tuple[str, list[str], list[dict], list[dict]]:
    """Inner impl that also returns aggregated term_map for ledger."""
    chunks = chunk_markdown(raw_text, max_chars=chunk_chars)
    chunk_translations: list[str] = []
    doc_unknown: list[str] = []
    all_notes: list[dict] = []
    # Aggregated term_map keyed by (term_he, english, keep_source) with summed occurrences
    agg_term_map: dict[tuple[str, str, bool], dict] = {}
    prev_tail = ""
    for ch in chunks:
        chunk_text = ch["chunk_text"]
        section_path = ch["section_path"]
        invariants = extract_preservation_invariants(chunk_text, first_names, last_names)
        if name_candidates is not None and invariants["person_names"]:
            name_candidates.update(invariants["person_names"])
        g_rows = glossary_for_chunk(chunk_text, glossary)
        # Deterministic masking: use full approved glossary to catch inflected forms (הDBים, המערכות)
        approved_for_mask = [r for r in glossary if (r.get("status") or "approved").strip() in ("approved", "keep_source") and (r.get("term_he") or "").strip()]
        chunk_term_map: list[dict] = []
        masked_chunk = chunk_text
        if approved_for_mask:
            try:
                masked_chunk, chunk_term_map = mask_glossary_terms(chunk_text, approved_for_mask)
                for e in chunk_term_map:
                    key = (e.get("term_he", ""), e.get("english", ""), bool(e.get("keep_source")))
                    if key not in agg_term_map:
                        agg_term_map[key] = {
                            "id": e.get("id", 0),
                            "term_he": e["term_he"],
                            "english": e["english"],
                            "keep_source": bool(e.get("keep_source")),
                            "occurrences": int(e.get("occurrences", 0)),
                            "src_order": int(e.get("src_order", 0)),
                        }
                    else:
                        agg_term_map[key]["occurrences"] += int(e.get("occurrences", 0))
                        # keep earliest src_order
                        if int(e.get("src_order", 0)) < agg_term_map[key]["src_order"]:
                            agg_term_map[key]["src_order"] = int(e.get("src_order", 0))
            except RuntimeError:
                raise
            except FileNotFoundError as e:
                raise RuntimeError(f"YAP required for glossary masking — fail-closed: {e}") from e
        use_mask = not no_mask
        if use_mask and md_mask is None:
            raise RuntimeError("md_mask missing — restore scripts/md_mask.py (table/placeholder masking required)")
        if use_mask:
            opts = md_mask.MdOptions(
                translate_frontmatter=False,
                translate_multiline_code=False,
                translate_latex=False,
                translate_link_text=True,
            )
            filt = md_mask.filter_markdown_lines(masked_chunk.split("\n"), opts)
            segs = md_mask.split_markdown_segments(filt.content_lines, filt.source_line_numbers)
            cell_texts = md_mask.get_table_cell_texts(filt.maps)
            SEG_DELIM = "⟦SEG⟧"
            if segs.texts_to_translate:
                seg_prompt = build_prompt(
                    SEG_DELIM.join(segs.texts_to_translate),
                    section_path,
                    g_rows,
                    prev_tail,
                    invariants,
                    term_map=chunk_term_map,
                )
                if mock:
                    simulated = _mock_with_sentinels(SEG_DELIM.join(segs.texts_to_translate), chunk_term_map, invariants)
                    if chunk_term_map:
                        try:
                            from translation_qa import check_glossary_sentinel
                            qa_res = check_glossary_sentinel(simulated, chunk_term_map)
                            if qa_res["status"] == "fail":
                                raise RuntimeError(f"glossary sentinel lost in mock segment: {qa_res['violations']}")
                        except RuntimeError:
                            raise
                        except Exception as e:
                            raise RuntimeError(f"glossary sentinel check error in mock segment: {e}") from e
                    translated_seg_text = unmask_glossary_terms(simulated, chunk_term_map)
                    res_seg = {"translation": translated_seg_text, "unknown_terms": [], "notes": ["mock"]}
                else:
                    res_seg = call_llm(base_url, api_key, model, seg_prompt)
                    translated_seg_text = res_seg["translation"]
                    if chunk_term_map:
                        try:
                            from translation_qa import check_glossary_sentinel
                            qa_res = check_glossary_sentinel(translated_seg_text, chunk_term_map)
                            if qa_res["status"] == "fail":
                                raise RuntimeError(f"glossary sentinel lost in segment: {qa_res['violations']}")
                        except RuntimeError:
                            raise
                        except Exception as e:
                            raise RuntimeError(f"glossary sentinel check error in segment: {e}") from e
                    translated_seg_text = unmask_glossary_terms(translated_seg_text, chunk_term_map)
                translated_segments = translated_seg_text.split(SEG_DELIM)
                if len(translated_segments) != len(segs.texts_to_translate):
                    raise RuntimeError(
                        f"Segment count mismatch: sent {len(segs.texts_to_translate)}, "
                        f"got {len(translated_segments)} — model did not preserve delimiters"
                    )
            else:
                translated_segments = []
                res_seg = {"unknown_terms": [], "notes": []}
            if cell_texts:
                if mock:
                    cell_delim = "⟦CELL⟧"
                    joined_cells = cell_delim.join(cell_texts)
                    simulated_cells = _mock_with_sentinels(joined_cells, chunk_term_map, None)
                    if chunk_term_map:
                        try:
                            from translation_qa import check_glossary_sentinel
                            qa_cell = check_glossary_sentinel(simulated_cells, chunk_term_map)
                            if qa_cell["status"] == "fail":
                                raise RuntimeError(f"glossary sentinel lost in mock table cell: {qa_cell['violations']}")
                        except RuntimeError:
                            raise
                        except Exception as e:
                            raise RuntimeError(f"glossary sentinel check error in mock table cell: {e}") from e
                    translated_cells_text = unmask_glossary_terms(simulated_cells, chunk_term_map)
                    translated_cells = translated_cells_text.split(cell_delim)
                    if len(translated_cells) != len(cell_texts):
                        raise RuntimeError(
                            f"Cell count mismatch: sent {len(cell_texts)}, got {len(translated_cells)}"
                        )
                else:
                    cell_delim = "⟦CELL⟧"
                    joined_cells = cell_delim.join(cell_texts)
                    cell_prompt = build_prompt(joined_cells, section_path, g_rows, "", None, term_map=chunk_term_map)
                    cr = call_llm(base_url, api_key, model, cell_prompt)
                    translated_cells_text = cr["translation"]
                    if chunk_term_map:
                        try:
                            from translation_qa import check_glossary_sentinel
                            qa_cell = check_glossary_sentinel(translated_cells_text, chunk_term_map)
                            if qa_cell["status"] == "fail":
                                raise RuntimeError(f"glossary sentinel lost in table cell: {qa_cell['violations']}")
                        except RuntimeError:
                            raise
                        except Exception as e:
                            raise RuntimeError(f"glossary sentinel check error in table cell: {e}") from e
                    translated_cells_text = unmask_glossary_terms(translated_cells_text, chunk_term_map)
                    translated_cells = translated_cells_text.split(cell_delim)
                    if len(translated_cells) != len(cell_texts):
                        raise RuntimeError(
                            f"Cell count mismatch: sent {len(cell_texts)}, got {len(translated_cells)} — model did not preserve delimiters"
                        )
                md_mask.inject_translated_table_cells(filt.maps, translated_cells)
            merged_lines = md_mask.merge_markdown_segments(segs.line_segments, translated_segments)
            trans = md_mask.restore_placeholders("\n".join(merged_lines), filt.maps)
            res = {
                "translation": trans,
                "unknown_terms": res_seg.get("unknown_terms", []),
                "notes": res_seg.get("notes", []),
            }
        else:
            prompt = build_prompt(masked_chunk, section_path, g_rows, prev_tail, invariants, term_map=chunk_term_map)
            if mock:
                simulated = _mock_with_sentinels(masked_chunk, chunk_term_map, invariants)
                if chunk_term_map:
                    try:
                        from translation_qa import check_glossary_sentinel
                        qa_res = check_glossary_sentinel(simulated, chunk_term_map)
                        if qa_res["status"] == "fail":
                            raise RuntimeError(f"glossary sentinel lost in mock whole-doc: {qa_res['violations']}")
                    except RuntimeError:
                        raise
                    except Exception as e:
                        raise RuntimeError(f"glossary sentinel check error in mock whole-doc: {e}") from e
                trans = unmask_glossary_terms(simulated, chunk_term_map)
                res = {"translation": trans, "unknown_terms": [], "notes": ["mock"]}
            else:
                res = call_llm(base_url, api_key, model, prompt)
                trans_sentinel = res["translation"]
                if chunk_term_map:
                    try:
                        from translation_qa import check_glossary_sentinel
                        qa_res = check_glossary_sentinel(trans_sentinel, chunk_term_map)
                        if qa_res["status"] == "fail":
                            raise RuntimeError(f"glossary sentinel lost in whole-doc: {qa_res['violations']}")
                    except RuntimeError:
                        raise
                    except Exception as e:
                        raise RuntimeError(f"glossary sentinel check error in whole-doc: {e}") from e
                trans = unmask_glossary_terms(trans_sentinel, chunk_term_map)
                res["translation"] = trans
        missing = verify_all_preserved(invariants, trans)
        if missing:
            for cat, items in missing.items():
                res.setdefault("notes", []).append(f"preserve_fail:{cat}:{items}")
            for items in missing.values():
                doc_unknown.extend(items)
        order_bad = verify_all_ordered(invariants, trans)
        global_bad = verify_global_order(chunk_text, invariants, trans)
        if order_bad:
            for cat, items in order_bad.items():
                res.setdefault("notes", []).append(f"order_fail:{cat}:{items}")
            for items in order_bad.values():
                doc_unknown.extend(items)
        if global_bad:
            res.setdefault("notes", []).append(f"global_order_fail:{global_bad}")
            doc_unknown.extend(global_bad)
        for ut in res.get("unknown_terms", []):
            ut = str(ut).strip()
            if ut and ut not in trans and ut in chunk_text:
                marker = HE_MARKER_FMT.format(term=ut)
                if marker not in trans:
                    trans = trans.rstrip() + f" {marker}"
            if ut:
                doc_unknown.append(ut)
        chunk_translations.append(trans)
        prev_tail = trans[-400:] if trans else ""
        if res.get("notes"):
            all_notes.append({"chunk": section_path, "notes": res["notes"]})
    full_translation = "\n\n".join(chunk_translations)
    # Preserve deterministic source order; keep original glossary ids for sentinel replay audit
    term_map = sorted(agg_term_map.values(), key=lambda x: (x.get("src_order", 0), x["id"]))
    return full_translation, doc_unknown, all_notes, term_map


def translate_one_doc(md_file: Path, vault_root: Path, out_root: Path,
                      glossary: list[dict], first_names: set[str], last_names: set[str],
                      base_url: str, api_key: str, model: str,
                      mock: bool, fix_rounds: int, chunk_chars: int,
                      no_mask: bool = False) -> dict:
    """Translate single file (no QA fix loop). Returns dict with translation,status etc."""
    _ = fix_rounds  # kept for caller compat; loop is in translate_one_doc_with_fix
    _ = out_root  # content-addressed store handled by caller (main)
    rel = md_file.relative_to(vault_root).as_posix() if md_file.is_relative_to(vault_root) else md_file.name
    raw_text = md_file.read_text(encoding="utf-8")
    if is_english_only_doc(raw_text):
        return {"skipped": True, "rel": rel, "source_hash": hashlib.sha256(raw_text.encode()).hexdigest(), "raw_text": raw_text}
    src_hash = hashlib.sha256(raw_text.encode()).hexdigest()
    name_candidates: set[str] = set()
    full_translation, doc_unknown, _notes, term_map = _translate_chunks_with_term_map(
        raw_text, first_names, last_names, glossary, base_url, api_key, model, mock, chunk_chars, no_mask, name_candidates)
    has_markers = "⟦he:" in full_translation
    status = "blocked_on_term" if (has_markers or doc_unknown) else "completed"
    return {
        "translation": full_translation,
        "status": status,
        "marker_count": full_translation.count("⟦he:"),
        "unknown_terms": sorted(set(doc_unknown)),
        "source_hash": src_hash,
        "rel": rel,
        "raw_text": raw_text,
        "name_candidates": name_candidates,
        "term_map": term_map,
    }


def translate_one_doc_with_fix(md_file: Path, vault_root: Path, out_root: Path,
                               glossary: list[dict], first_names: set[str], last_names: set[str],
                               base_url: str, api_key: str, model: str,
                               mock: bool, fix_rounds: int, chunk_chars: int,
                               no_mask: bool = False) -> dict:
    """Full doc translate + QA + bounded LLM fix rounds."""
    result = translate_one_doc(md_file, vault_root, out_root, glossary, first_names, last_names,
                               base_url, api_key, model, mock, fix_rounds, chunk_chars, no_mask)
    if result.get("skipped"):
        return result
    source_path = md_file
    trans_body = result["translation"]
    raw_text = result["raw_text"]
    doc_term_map = result.get("term_map", [])
    meta_stub = {"source_doc": result["rel"], "term_map": doc_term_map}
    full_invariants = extract_preservation_invariants(raw_text, first_names, last_names)
    checks = run_qa_for_doc(source_path, trans_body, meta_stub, glossary, vault_root, term_map=doc_term_map)
    failures = format_qa_failures(checks)
    fix_rounds_used = 0
    all_fix_attempts: list[dict] = []
    fix_unknown_terms: list[str] = []
    while failures and fix_rounds_used < fix_rounds:
        fix_rounds_used += 1
        if mock:
            # Deterministic mock via masking with full approved glossary (catch inflected forms)
            approved_for_fix = [r for r in glossary if (r.get("status") or "approved").strip() in ("approved", "keep_source") and (r.get("term_he") or "").strip()]
            if approved_for_fix:
                try:
                    masked_raw, fix_term_map = mask_glossary_terms(raw_text, approved_for_fix)
                    simulated_fix = _mock_with_sentinels(masked_raw, fix_term_map, full_invariants)
                    new_body = unmask_glossary_terms(simulated_fix, fix_term_map)
                    fixed = {"translation": new_body, "unknown_terms": [], "notes": ["mock fix"]}
                except RuntimeError:
                    raise
                except FileNotFoundError as e:
                    raise RuntimeError(f"YAP required for glossary masking — fail-closed: {e}") from e
            else:
                fixed = mock_translate(raw_text, [], full_invariants)
            new_body = fixed["translation"]
            fix_unknown_terms.extend(re.findall(r"⟦he:([^⟧]+)⟧", new_body))
        else:
            # For large docs, avoid silent 12k truncation by chunking the fix
            threshold = max(12000, chunk_chars * 2)
            is_large = len(raw_text) > threshold or len(trans_body) > threshold
            if is_large:
                prompts = _build_chunked_fix_prompts(raw_text, trans_body, failures,
                                                     glossary_for_chunk(raw_text, glossary),
                                                     full_invariants, chunk_chars,
                                                     first_names, last_names)
                # Log truncation avoidance
                print(f"  fix round {fix_rounds_used}: large doc ({len(raw_text)} src, {len(trans_body)} trans) — chunked into {len(prompts)} prompts", file=sys.stderr)
                chunk_translations: list[str] = []
                chunk_unknown: list[str] = []
                chunk_failed = False
                last_err = None
                for p_idx, p in enumerate(prompts):
                    try:
                        resp = call_llm(base_url, api_key, model, p)
                        ct = resp.get("translation", "")
                        chunk_translations.append(ct)
                        chunk_unknown.extend([str(x).strip() for x in resp.get("unknown_terms", []) if str(x).strip()])
                        chunk_unknown.extend(re.findall(r"⟦he:([^⟧]+)⟧", ct))
                    except Exception as e:
                        last_err = str(e)[:500]
                        chunk_failed = True
                        print(f"  fix chunk {p_idx+1}/{len(prompts)} failed: {last_err}", file=sys.stderr)
                        break
                if chunk_failed:
                    all_fix_attempts.append({"round": fix_rounds_used, "error": last_err or "chunk fix failed", "failures_before": failures, "chunked": True, "chunks": len(prompts), "src_len": len(raw_text), "trans_len": len(trans_body)})
                    break
                new_body = "\n\n".join(chunk_translations)
                fix_unknown_terms.extend(chunk_unknown)
                # Record that this round was chunked
                all_fix_attempts.append({"round": fix_rounds_used, "failures_before": failures, "chunked": True, "chunks": len(prompts), "src_len": len(raw_text), "trans_len": len(trans_body)})
                trans_body = new_body
                # Normalize ledger schema: also include chunked flag for non-chunked? handled below
                checks = run_qa_for_doc(source_path, trans_body, meta_stub, glossary, vault_root, term_map=doc_term_map)
                failures = format_qa_failures(checks)
                continue
            # Normal whole-doc fix for small docs
            fix_prompt = build_fix_prompt(raw_text, trans_body, failures,
                                          glossary_rows=glossary_for_chunk(raw_text, glossary),
                                          invariants=full_invariants)
            try:
                resp = call_llm(base_url, api_key, model, fix_prompt)
                new_body = resp.get("translation", "")
                fix_unknown_terms.extend([str(x).strip() for x in resp.get("unknown_terms", []) if str(x).strip()])
                fix_unknown_terms.extend(re.findall(r"⟦he:([^⟧]+)⟧", new_body))
            except Exception as e:
                all_fix_attempts.append({"round": fix_rounds_used, "error": str(e)[:500], "failures_before": failures, "chunked": False, "src_len": len(raw_text), "trans_len": len(trans_body)})
                break
        trans_body = new_body
        all_fix_attempts.append({"round": fix_rounds_used, "failures_before": failures, "chunked": False, "src_len": len(raw_text), "trans_len": len(trans_body)})
        checks = run_qa_for_doc(source_path, trans_body, meta_stub, glossary, vault_root, term_map=doc_term_map)
        failures = format_qa_failures(checks)
    if failures:
        final_status = "qa_failed"
    else:
        has_markers = "⟦he:" in trans_body
        final_status = "blocked_on_term" if has_markers else "completed"
    marker_terms = re.findall(r"⟦he:([^⟧]+)⟧", trans_body)
    recomputed_unknown = sorted(set(marker_terms + [str(x).strip() for x in fix_unknown_terms if str(x).strip()]))
    # When fix was attempted, merge original unknown_terms (preservation failures) with recomputed
    # so blocked docs aren't hidden if fix resolves QA but leaves invariant gaps
    if fix_rounds_used > 0:
        orig = result.get("unknown_terms", [])
        final_unknown = sorted(set(orig) | set(recomputed_unknown))
    else:
        final_unknown = result.get("unknown_terms", [])
    result.update({
        "translation": trans_body,
        "status": final_status,
        "marker_count": trans_body.count("⟦he:"),
        "unknown_terms": sorted(set(final_unknown)),
        "fix_rounds_used": fix_rounds_used,
        "fix_attempts": all_fix_attempts,
        "qa_checks": checks,
        "qa_failures": failures,
    })
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="Translate markdown chunks with glossary + name guard")
    ap.add_argument("vault_root", nargs="?", default=".", help="vault root")
    ap.add_argument("--input", dest="input_dir", default=None, help="corpus dir (default raw_md/raw)")
    ap.add_argument("--glossary", default=None, help="glossary.csv path")
    ap.add_argument("--out", dest="out_dir", default=None, help="output store dir")
    ap.add_argument("--check", action="store_true", help="only check glossary gate, exit 1 if blocked")
    ap.add_argument("--mock", action="store_true", help="offline mock (no LLM)")
    ap.add_argument("--force", action="store_true", help="retranslate even if cached")
    ap.add_argument("--resume", action="store_true", help="same as default (kept for docs compat)")
    ap.add_argument("--no-mask", action="store_true", help="disable md_mask placeholder masking (debug)")
    ap.add_argument("--limit", type=int, default=0, help="limit files (0=all)")
    ap.add_argument("--fix-rounds", type=int, default=None, help="max LLM fix rounds per doc after QA failures (default 3, 0=disable)")
    args = ap.parse_args(argv)

    vault_root = Path(args.vault_root).resolve()
    cfg = load_config(vault_root)
    tcfg = cfg.get("translation", {})
    fix_rounds = resolve_fix_rounds(cfg, args.fix_rounds)
    print(f"Fix rounds: {fix_rounds}")

    # Glossary gate — path from CLI > convert_config.json translation.glossary_path > default
    if args.glossary:
        glossary_path = Path(args.glossary)
    elif tcfg.get("glossary_path"):
        gp = Path(tcfg["glossary_path"])
        glossary_path = gp if gp.is_absolute() else vault_root / gp
    else:
        glossary_path = vault_root / "data" / "domain_terms" / "glossary.csv"
    # Fallback: glossary_proposed.csv if glossary.csv not yet created (pre-approval phase)
    if not glossary_path.exists() and glossary_path.name == "glossary.csv":
        alt = glossary_path.parent / "glossary_proposed.csv"
        if alt.exists():
            glossary_path = alt

    if args.check:
        # Use shared check
        try:
            from check_glossary import check_glossary
        except ImportError:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from check_glossary import check_glossary
        ok, errors = check_glossary(glossary_path)
        if ok:
            print(f"glossary OK: {glossary_path}")
            sys.exit(0)
        print(f"glossary BLOCKED: {glossary_path}", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("TRANSLATE_BASE_URL") or os.environ.get("QMD_OPENAI_BASE_URL") or tcfg.get("base_url", "")
    api_key = os.environ.get("TRANSLATE_API_KEY") or os.environ.get("QMD_OPENAI_API_KEY") or ""
    model = tcfg.get("model") or os.environ.get("TRANSLATE_MODEL") or "minimax-m2.7"

    if not args.mock and not base_url:
        print("ERROR: translation base_url missing. Set TRANSLATE_BASE_URL or QMD_OPENAI_BASE_URL or convert_config.json translation.base_url", file=sys.stderr)
        sys.exit(1)

    glossary = load_glossary(glossary_path)
    if glossary_path.exists():
        print(f"Glossary: {len(glossary)} rows from {glossary_path}")
    else:
        print(f"Glossary: none ({glossary_path} not found) — translating without glossary")

    # Codename-aware person names: exclude org codenames (static file + glossary terms)
    # so that a codename like ברק/דניאל is translated via glossary, not masked as PERSON.
    glossary_terms = {r.get("term_he", "").strip() for r in glossary if (r.get("status") or "").strip() in ("approved", "keep_source") and r.get("term_he", "").strip()}
    # Load with glossary exclusion (primary); codenames.txt is optional manual override
    # Keep separate counts for audit (glossary_terms may be hundreds of domain terms,
    # only those overlapping the allowlist are true codename exclusions).
    raw_first, raw_last = load_person_names(vault_root)
    raw_all = raw_first | raw_last
    codenames_file = load_codenames(vault_root)
    glossary_overlap = glossary_terms & raw_all
    codenames_overlap = codenames_file & raw_all
    first_names, last_names = load_person_names(vault_root, exclude=glossary_terms)
    total_excluded = codenames_overlap | glossary_overlap
    if total_excluded:
        print(f"Codenames excluded from PERSON guard: {len(total_excluded)} (file:{len(codenames_overlap)} glossary:{len(glossary_overlap)} — {', '.join(sorted(list(total_excluded))[:5])}{' ...' if len(total_excluded) > 5 else ''})")
    print(f"Person names: {len(first_names)} first, {len(last_names)} last (raw {len(raw_first)}/{len(raw_last)}, excluded {len(total_excluded)})")

    corpus_dir = resolve_corpus_dir(vault_root, Path(args.input_dir) if args.input_dir else None)
    md_files = sorted(corpus_dir.rglob("*.md"))
    if args.limit:
        md_files = md_files[:args.limit]
    print(f"Translating {len(md_files)} files from {corpus_dir}")

    out_root = Path(args.out_dir) if args.out_dir else vault_root / "data" / "translations"
    out_root.mkdir(parents=True, exist_ok=True)

    # Ledger (canonical: vault_root/data/translations/ledger.jsonl)
    ledger_path = get_ledger_path(vault_root, out_root)
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"warn: cannot create ledger dir {ledger_path.parent}: {e}", file=sys.stderr)
    # Task 5: deterministic ledger glossary_version via shared helper (12-char hash or no-glossary)
    try:
        from translation_common import compute_glossary_version as _compute_gv
        glossary_version = _compute_gv(glossary_path)
    except Exception:
        # Fallback to legacy inline (should not happen — translation_common is stdlib)
        glossary_version = ""
        if glossary_path.exists():
            try:
                glossary_version = hashlib.sha256(glossary_path.read_bytes()).hexdigest()[:12]
            except OSError:
                glossary_version = "no-glossary"
        else:
            glossary_version = "no-glossary"

    name_candidates: set[str] = set()
    translated = 0
    blocked = 0
    skipped_english = 0
    failed_docs: list[str] = []
    qa_failed = 0

    try:
        chunk_chars = int(tcfg.get("chunk_chars", 6000))
    except (TypeError, ValueError):
        chunk_chars = 6000

    for md_file in md_files:
        rel = md_file.relative_to(vault_root).as_posix() if md_file.is_relative_to(vault_root) else md_file.name
        try:
            raw_text = md_file.read_text(encoding="utf-8")
        except OSError as e:
            print(f" skip {rel}: {e}", file=sys.stderr)
            continue

        # Cache check (content-addressed) — do before any LLM work
        src_hash_pre = hashlib.sha256(raw_text.encode()).hexdigest()
        store_dir_pre = out_root / src_hash_pre[:2] / src_hash_pre
        out_file_pre = store_dir_pre / "translation.md"
        if out_file_pre.exists() and not args.force:
            # Fail-closed: cached qa_failed must still count toward exit 1
            try:
                cached_text = out_file_pre.read_text(encoding="utf-8")
                is_qa_failed = False
                # Robust frontmatter parse (not substring) — extract JSON between --- markers
                if cached_text.startswith("---\n"):
                    end = cached_text.find("\n---\n", 4)
                    if end != -1:
                        try:
                            fm = json.loads(cached_text[4:end].strip())
                            is_qa_failed = fm.get("status") == "qa_failed"
                        except (json.JSONDecodeError, ValueError):
                            is_qa_failed = bool(re.search(r'"status"\s*:\s*"qa_failed"', cached_text))
                    else:
                        is_qa_failed = bool(re.search(r'"status"\s*:\s*"qa_failed"', cached_text))
                else:
                    is_qa_failed = bool(re.search(r'"status"\s*:\s*"qa_failed"', cached_text))
                if is_qa_failed:
                    failed_docs.append(rel)
                    qa_failed += 1
                    print(f"  {rel}: qa_failed (cached)", file=sys.stderr)
            except OSError as e:
                print(f"warn: cannot read cached {out_file_pre}: {e}", file=sys.stderr)
            continue

        # Translate with QA fix loop (handles english-only internally)
        try:
            result = translate_one_doc_with_fix(
                md_file, vault_root, out_root, glossary, first_names, last_names,
                base_url, api_key, model, args.mock, fix_rounds, chunk_chars,
                no_mask=args.no_mask)
        except RuntimeError as e:
            # Hard failure like segment mismatch
            print(f"  {rel}: error {e}", file=sys.stderr)
            failed_docs.append(rel)
            event = {
                "event": "translation_error",
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_doc": rel,
                "source_hash": src_hash_pre,
                "model": model,
                "model_id": model,
                "glossary_version": glossary_version,
                "term_map": [],
                "status": "error",
                "error": str(e)[:500],
            }
            with open(ledger_path, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(event, ensure_ascii=False) + "\n")
            continue

        if result.get("skipped"):
            src_hash = result["source_hash"]
            event = {
                "event": "skipped_english",
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_doc": rel,
                "source_hash": src_hash,
                "model": model,
                "model_id": model,
                "glossary_version": glossary_version,
                "term_map": [],
                "status": "skipped_english",
            }
            with open(ledger_path, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(event, ensure_ascii=False) + "\n")
            skipped_english += 1
            print(f"  {rel}: skipped_english (no Hebrew)")
            continue

        # Aggregate name candidates
        if result.get("name_candidates"):
            name_candidates.update(result["name_candidates"])

        full_translation = result["translation"]
        status = result["status"]
        src_hash = result["source_hash"]
        fix_used = result.get("fix_rounds_used", 0)
        qa_failures = result.get("qa_failures", [])
        # Task 5: deterministic ledger term_map + model_id
        doc_term_map = result.get("term_map", [])
        # qa_checks retained for debugging but not written to frontmatter (failures are)
        _qa_checks = result.get("qa_checks", [])

        # Write content-addressed store
        store_dir = out_root / src_hash[:2] / src_hash
        store_dir.mkdir(parents=True, exist_ok=True)
        out_file = store_dir / "translation.md"
        frontmatter = {
            "source_doc": rel,
            "source_hash": src_hash,
            "model": model,
            "model_id": model,
            "glossary_version": glossary_version,
            "term_map": doc_term_map,
            "status": status,
            "marker_count": full_translation.count("⟦he:"),
            "unknown_terms": sorted(set(result.get("unknown_terms", []))),
            "fix_rounds_used": fix_used,
        }
        if qa_failures:
            frontmatter["qa_failures"] = qa_failures[:5]
        fm_text = "---\n" + json.dumps(frontmatter, ensure_ascii=False, indent=2) + "\n---\n\n"
        out_file.write_text(fm_text + full_translation, encoding="utf-8")

        # Ledger: fix attempts
        for attempt in result.get("fix_attempts", []):
            evt = {
                "event": "fix_attempt",
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_doc": rel,
                "source_hash": src_hash,
                "model": model,
                "model_id": model,
                "glossary_version": glossary_version,
                "term_map": doc_term_map,
                "round": attempt.get("round"),
                "failures_before": attempt.get("failures_before", [])[:3],
            }
            if "error" in attempt:
                evt["error"] = attempt["error"]
            for k in ("chunked", "src_len", "trans_len", "chunks"):
                if k in attempt:
                    evt[k] = attempt[k]
            # Ensure chunked is always present for schema consistency
            if "chunked" not in evt:
                evt["chunked"] = False
            with open(ledger_path, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(evt, ensure_ascii=False) + "\n")

        # Ledger: qa_result
        qa_event = {
            "event": "qa_result",
            "ts": datetime.now(timezone.utc).isoformat(),
            "source_doc": rel,
            "source_hash": src_hash,
            "model": model,
            "model_id": model,
            "glossary_version": glossary_version,
            "term_map": doc_term_map,
            "status": status,
            "fix_rounds_used": fix_used,
            "qa_failures": qa_failures[:5] if qa_failures else [],
        }
        with open(ledger_path, "a", encoding="utf-8") as lf:
            lf.write(json.dumps(qa_event, ensure_ascii=False) + "\n")

        # Ledger: translation event
        if status == "qa_failed":
            event = {
                "event": "qa_failed",
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_doc": rel,
                "source_hash": src_hash,
                "model": model,
                "model_id": model,
                "glossary_version": glossary_version,
                "term_map": doc_term_map,
                "status": status,
                "marker_count": frontmatter["marker_count"],
                "unknown_terms": frontmatter["unknown_terms"],
                "fix_rounds_used": fix_used,
                "qa_failures": qa_failures[:5],
            }
            failed_docs.append(rel)
            qa_failed += 1
        elif status == "blocked_on_term":
            event = {
                "event": "blocked_on_term",
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_doc": rel,
                "source_hash": src_hash,
                "model": model,
                "model_id": model,
                "glossary_version": glossary_version,
                "term_map": doc_term_map,
                "status": status,
                "marker_count": frontmatter["marker_count"],
                "unknown_terms": frontmatter["unknown_terms"],
                "fix_rounds_used": fix_used,
            }
            blocked += 1
        else:
            event = {
                "event": "translation_completed",
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_doc": rel,
                "source_hash": src_hash,
                "model": model,
                "model_id": model,
                "glossary_version": glossary_version,
                "term_map": doc_term_map,
                "status": status,
                "marker_count": frontmatter["marker_count"],
                "unknown_terms": frontmatter["unknown_terms"],
                "fix_rounds_used": fix_used,
            }
            translated += 1
        with open(ledger_path, "a", encoding="utf-8") as lf:
            lf.write(json.dumps(event, ensure_ascii=False) + "\n")

        # Console
        if status == "qa_failed":
            print(f"  {rel}: qa_failed after {fix_used} fix rounds: {qa_failures[:1]}", file=sys.stderr)
        else:
            chunk_info = f" ({fix_used} fix rounds)" if fix_used else ""
            print(f"  {rel}: {status}{chunk_info} ({frontmatter['marker_count']} markers)")

    # Log name candidates
    if name_candidates:
        cand_path = out_root / "name_candidates.txt"
        with open(cand_path, "w", encoding="utf-8") as f:
            for n in sorted(name_candidates):
                f.write(n + "\n")
        print(f"Name candidates: {len(name_candidates)} unique -> {cand_path}")

    print(f"Done: {translated} completed, {blocked} blocked_on_term, {skipped_english} skipped_english, {qa_failed} qa_failed -> {out_root}")
    if failed_docs:
        print(f"FAILED: {len(failed_docs)} docs still invalid after {fix_rounds} fix rounds: {failed_docs[:5]}", file=sys.stderr)
        print(f"Stop — fix budget exhausted. Inspect QA output and ledger, fix policy/glossary/prompt, retry with --fix-rounds N or --force.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


# Re-exports for `import translate; translate.X` compat (pure refactor, no new API)
__all__ = [
    "get_ledger_path","load_config","resolve_fix_rounds","resolve_corpus_dir",
    "load_glossary","load_codenames","load_person_names",
    "mask_person_names","unmask_person_names","is_english_only_doc",
    "mask_english_spans","unmask_english_spans",
    "extract_english_spans","extract_urls_and_paths","extract_person_names",
    "extract_yaml_frontmatter","extract_code_sections","extract_preservation_invariants",
    "verify_preserved","verify_all_preserved","verify_ordered","verify_all_ordered","verify_global_order",
    "chunk_markdown","glossary_for_chunk",
    "mask_glossary_terms","unmask_glossary_terms",
    "build_prompt","build_fix_prompt","_build_chunked_fix_prompts","format_qa_failures",
    "call_llm","mock_translate","_mock_with_sentinels",
    "run_qa_for_doc","translate_one_doc","translate_one_doc_with_fix","main",
    # constants
    "PERSON_OPEN","PERSON_CLOSE","EN_OPEN","EN_CLOSE","HE_MARKER_FMT",
    "HEBREW_RANGE","PROCLITICS","RAW_WORD_RE","MIXED_SPLIT_RE",
]
