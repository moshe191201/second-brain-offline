"""LLM I/O — extracted from translate.py (pure move).

I/O boundary with retries, urllib, mock sentinel-aware Hebrew marking.
"""
from __future__ import annotations

import hashlib  # kept per Task 6 spec (parity with original LLM block)
import json
import re
import sys
import time
import urllib.error
import urllib.request

from translation_invariants import HE_MARKER_FMT, HEBREW_WORD_RE
from translation_masking import mask_glossary_terms, unmask_glossary_terms


def _mock_with_sentinels(masked_text: str, term_map: list[dict], invariants: dict | None = None) -> str:
    """Simulate LLM preserving sentinels: wrap Hebrew outside protected spans."""
    from translation_common import build_glossary_sentinel, build_keep_sentinel

    protected: list[str] = []
    if invariants:
        for cat in ("yaml_frontmatter", "code_sections", "person_names", "english_spans", "urls_and_paths"):
            for v in invariants.get(cat, []):
                if v and v not in protected:
                    protected.append(v)
    for e in term_map:
        if e.get("keep_source"):
            s = build_keep_sentinel(e.get("term_he", ""))
        else:
            try:
                tid = int(e.get("id", 0))
            except Exception:
                tid = 0
            s = build_glossary_sentinel(tid, e.get("english", ""))
        if s and s not in protected:
            protected.append(s)
    for delim in ("⟦SEG⟧", "⟦CELL⟧"):
        if delim in masked_text and delim not in protected:
            protected.append(delim)
    # Use single-char Hebrew pattern for mock to avoid residual single proclitic "ה" leak
    _he_single = re.compile(r"[א-ת]+")
    if protected:
        protected_sorted = sorted(protected, key=len, reverse=True)
        pat = re.compile("|".join(re.escape(p) for p in protected_sorted))
        parts = pat.split(masked_text)
        sentinels = pat.findall(masked_text)
        wrapped_parts: list[str] = []
        for i, seg in enumerate(parts):
            wrapped_parts.append(_he_single.sub(lambda m: HE_MARKER_FMT.format(term=m.group(0)), seg))
            if i < len(sentinels):
                wrapped_parts.append(sentinels[i])
        simulated = "".join(wrapped_parts)
    else:
        simulated = _he_single.sub(lambda m: HE_MARKER_FMT.format(term=m.group(0)), masked_text)
    return simulated


def call_llm(base_url: str, api_key: str, model: str, prompt: str, retries: int = 3) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode()

    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode())
            choices = data.get("choices") if isinstance(data, dict) else None
            choice = choices[0] if isinstance(choices, list) and choices else {}
            finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
            if finish_reason == "length":
                raise RuntimeError("LLM response truncated (finish_reason=length) — chunk too large or token limit hit")
            msg = choice.get("message") if isinstance(choice, dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            if not content:
                # Fallback: original direct access for compat
                content = data["choices"][0]["message"]["content"]
            obj = json.loads(content)
            return {
                "translation": str(obj.get("translation", "")).strip(),
                "unknown_terms": list(obj.get("unknown_terms", [])),
                "notes": list(obj.get("notes", [])),
            }
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode(errors="replace")[:300]
            except Exception:
                body = str(e)[:300]
            # Do not echo raw body to ledger verbatim — it may contain document content
            last_err = f"HTTP {e.code}"
            # Log body to stderr only (not persisted to ledger verbatim)
            print(f"LLM HTTP {e.code}: {body[:200]}", file=sys.stderr)
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(last_err) from e
        except RuntimeError:
            raise
        except Exception as e:
            last_err = str(e)
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"LLM call failed after {retries} attempts: {last_err}") from e
    raise RuntimeError(last_err or "LLM exhausted retries")


def mock_translate(chunk_text: str, glossary_rows: list[dict], invariants: dict | None = None) -> dict:
    # Deterministic mock via masking reuse: mask → simulate LLM (Hebrew wrapping, sentinels preserved) → unmask
    from translation_common import build_glossary_sentinel, build_keep_sentinel

    try:
        masked, term_map = mask_glossary_terms(chunk_text, glossary_rows)
    except RuntimeError:
        raise
    except FileNotFoundError as e:
        raise RuntimeError(f"YAP required for glossary masking — fail-closed: {e}") from e

    # Build protected list: invariants + sentinels + segment delimiters
    protected: list[str] = []
    if invariants:
        for cat in ("yaml_frontmatter", "code_sections", "person_names", "english_spans", "urls_and_paths"):
            for v in invariants.get(cat, []):
                if v and v not in protected:
                    protected.append(v)
    for e in term_map:
        if e.get("keep_source"):
            s = build_keep_sentinel(e.get("term_he", ""))
        else:
            try:
                tid = int(e.get("id", 0))
            except Exception:
                tid = 0
            s = build_glossary_sentinel(tid, e.get("english", ""))
        if s and s not in protected:
            protected.append(s)
    for delim in ("⟦SEG⟧", "⟦CELL⟧"):
        if delim in masked and delim not in protected:
            protected.append(delim)

    if protected:
        protected_sorted = sorted(protected, key=len, reverse=True)
        pat = re.compile("|".join(re.escape(p) for p in protected_sorted))
        parts = pat.split(masked)
        sentinels = pat.findall(masked)
        wrapped_parts: list[str] = []
        for i, seg in enumerate(parts):
            wrapped_parts.append(HEBREW_WORD_RE.sub(lambda m: HE_MARKER_FMT.format(term=m.group(0)), seg))
            if i < len(sentinels):
                wrapped_parts.append(sentinels[i])
        simulated = "".join(wrapped_parts)
    else:
        simulated = HEBREW_WORD_RE.sub(lambda m: HE_MARKER_FMT.format(term=m.group(0)), masked)

    out = unmask_glossary_terms(simulated, term_map)
    return {"translation": out, "unknown_terms": [], "notes": ["mock"]}
