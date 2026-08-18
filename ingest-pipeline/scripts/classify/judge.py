"""Judge — reasoning-first closed-choice LLM classifier.

Builds prompt from taxonomy+glossary+top-k candidates+chunk text,
calls OpenAI-compatible /v1/chat/completions with guided_json enum enforcement,
emits JSON with reasoning_brief FIRST.

Temp 0, categorical confidence buckets.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import sys
import urllib.request

BUCKETS = ["SURE", "NEEDS_HUMAN_VALIDATION", "I_GUESSED"]
RELATIONS = ["none", "comparison", "relationship", "progression"]


try:  # package import (from classify.x import ...)
    from .taxonomy import TAXONOMY_RE as _TAXONOMY_RE, parse_taxonomy_blocks as _parse_blocks, templates_root
except ImportError:  # direct script run (python scripts/classify/x.py)
    from taxonomy import TAXONOMY_RE as _TAXONOMY_RE, parse_taxonomy_blocks as _parse_blocks, templates_root


def _local_parse_blocks(txt: str) -> dict[str, str]:
    matches = list(_TAXONOMY_RE.finditer(txt))
    blocks: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        if name in ("subdomains", "version", "campaign"):
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(txt)
        blocks[name] = txt[start:end]
    return blocks


def load_yaml_simple(path: Path):
    if not path.exists():
        return "", {}
    txt = path.read_text(encoding="utf-8")
    blocks = _parse_blocks(txt)
    subs: dict = {}
    for name, block in blocks.items():
        def_m = re.search(r"definition:\s*\"(.*?)\"", block, flags=re.DOTALL)
        examples = re.findall(r"text:\s*\"(.*?)\"", block)
        subs[name] = {"definition": def_m.group(1) if def_m else "", "examples": examples}
    return txt, subs


def build_prompt(chunk_text, taxonomy_subs, glossary_text, candidates, policy_text, few_shot_per_topk=3):
    glossary_header = ""
    if glossary_text:
        glossary_header = "Domain knowledge (surface form → subdomain):\n" + glossary_text[:2000] + "\n\n"
    # Only candidates
    cand_defs = ""
    for c in candidates:
        sub = taxonomy_subs.get(c, {})
        cand_defs += f"- {c}: {sub.get('definition','')}\n"
        for ex in sub.get("examples", [])[:few_shot_per_topk]:
            cand_defs += f"  example: \"{ex[:200]}\"\n"

    system = (
        "You are a subdomain classifier. Think step by step BEFORE choosing.\n"
        "First write reasoning_brief mapping evidence to subdomain via domain_knowledge — be thorough, no length limit.\n"
        "Then pick primary_subdomain from the candidates only.\n"
        + glossary_header
        + f"Candidates:\n{cand_defs}\n"
        + "Buckets: SURE=explicit+primary focus no comparator; NEEDS_HUMAN_VALIDATION=implicit or comparison or close runner-up; I_GUESSED=thin generic.\n"
        + "If the doc compares 2+ subdomains, set primary to main focus and list others in secondary_subdomains with relation_type.\n"
    )
    user = f"Headers + body to classify:\n{chunk_text[:6000]}"
    return system, user


def build_schema(allowed_subdomains):
    # reasoning_brief listed first in properties so vLLM guided_json tends to emit it first; not a JSON Schema guarantee (L2).
    return {
        "type": "object",
        "properties": {
            "reasoning_brief": {"type": "string", "description": "Thorough reasoning, evidence → subdomain, no length limit"},
            "primary_subdomain": {"type": "string", "enum": allowed_subdomains},
            "secondary_subdomains": {"type": "array", "items": {"type": "string", "enum": allowed_subdomains}},
            "relation_type": {"type": "string", "enum": RELATIONS},
            "confidence_bucket": {"type": "string", "enum": BUCKETS},
        },
        "required": ["reasoning_brief", "primary_subdomain", "confidence_bucket"],
        "additionalProperties": False,
    }


def call_llm(system, user, base_url, api_key, model, schema):
    url = base_url.rstrip("/") + "/v1/chat/completions"
    # vLLM expects extra_body.guided_json, OpenAI expects response_format.json_schema
    body_dict = {
        "model": model,
        "temperature": 0.0,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if schema:
        body_dict["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "classification", "schema": schema, "strict": True},
        }
        body_dict["extra_body"] = {"guided_json": schema}
    else:
        body_dict["response_format"] = {"type": "json_object"}
    body = json.dumps(body_dict).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError:
            # Unparseable -> I_GUESSED fallback per spec
            return {"reasoning_brief": content if isinstance(content, str) else "parse error", "primary_subdomain": "", "confidence_bucket": "I_GUESSED", "relation_type": "none", "secondary_subdomains": []}


def main():
    p = argparse.ArgumentParser(description="Reasoning-first judge")
    p.add_argument("--campaign", default="campaigns/example")
    p.add_argument("--store", default="store")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--taxonomy", default=None)
    args = p.parse_args()

    camp = Path(args.campaign)
    tax_path = Path(args.taxonomy) if args.taxonomy else camp / "taxonomy.yaml"
    if not tax_path.exists():
        tax_path = (templates_root() / "taxonomy.yaml")
    gloss_path = camp / "glossary.yaml"
    if not gloss_path.exists():
        gloss_path = (templates_root() / "glossary.yaml")

    _, subs = load_yaml_simple(tax_path)
    gloss_text = gloss_path.read_text(encoding="utf-8") if gloss_path.exists() else ""
    allowed = sorted(subs.keys())
    if not allowed:
        print(f"judge: no subdomains in {tax_path}", file=sys.stderr)
        return 1

    schema = build_schema(allowed)
    # Validate schema invariant: numeric score must be impossible
    assert "confidence_bucket" in schema["properties"]
    assert schema["properties"]["confidence_bucket"]["enum"] == BUCKETS

    if args.dry_run:
        print(json.dumps(schema, indent=2))
        print("\n--- Example prompt preview (first candidate) ---")
        cand = allowed[:4]
        few_shot = 3
        _pol_path = Path(args.campaign) / "policy.yaml" if not Path(args.campaign).is_absolute() else Path(args.campaign) / "policy.yaml"
        if not _pol_path.exists():
            _pol_path = (templates_root() / "policy.yaml")
        try:
            if _pol_path.exists():
                _m = re.search(r"few_shot_per_topk:\s*(\d+)", _pol_path.read_text(encoding="utf-8"))
                if _m:
                    few_shot = int(_m.group(1))
        except Exception:
            pass
        sys_p, usr_p = build_prompt("Example doc body about HbA1c...", subs, gloss_text, cand, "", few_shot)
        print(sys_p[:800])
        return 0

    base_url = os.environ.get("CLASSIFY_LLM_BASE_URL") or os.environ.get("QMD_OPENAI_BASE_URL") or ""
    api_key = os.environ.get("CLASSIFY_LLM_API_KEY") or os.environ.get("QMD_OPENAI_API_KEY") or ""
    model = os.environ.get("CLASSIFY_LLM_MODEL") or "minimax-m2.7"

    if not base_url:
        print("judge: no CLASSIFY_LLM_BASE_URL / QMD_OPENAI_BASE_URL — failing closed (no LLM endpoint configured)", file=sys.stderr)
        return 1

    # few_shot_per_topk from policy.yaml (default 3)
    few_shot_per_topk = 3
    _policy_path_for_fewshot = Path(args.campaign) / "policy.yaml"
    if not _policy_path_for_fewshot.exists():
        _policy_path_for_fewshot = (templates_root() / "policy.yaml")
    try:
        if _policy_path_for_fewshot.exists():
            _mf = re.search(r"few_shot_per_topk:\s*(\d+)", _policy_path_for_fewshot.read_text(encoding="utf-8"))
            if _mf:
                few_shot_per_topk = int(_mf.group(1))
    except Exception:
        pass

    store_root = Path(args.store)
    docs = list(store_root.rglob("*.md"))
    for doc in docs[:2000]:
        # load candidates from sidecar if exists
        sidecar = doc.with_suffix(".retrieval.json")
        if sidecar.exists():
            cands = [c["subdomain"] for c in json.loads(sidecar.read_text(encoding="utf-8"))["candidates"]]
        else:
            cands = allowed[:4]
        text = doc.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            body = parts[2] if len(parts) > 2 else text
        else:
            body = text
        system, user = build_prompt(body, subs, gloss_text, cands, "", few_shot_per_topk)
        try:
            out = call_llm(system, user, base_url, api_key, model, schema)
        except Exception as e:
            print(f"judge: {doc.name} failed: {e}", file=sys.stderr)
            out = {"reasoning_brief": f"LLM error: {e}", "primary_subdomain": cands[0], "confidence_bucket": "I_GUESSED", "relation_type": "none", "secondary_subdomains": []}
        # validate closed vocab
        if out.get("primary_subdomain") not in allowed:
            print(f"judge: {doc.name} primary not in taxonomy: {out.get('primary_subdomain')}", file=sys.stderr)
            out["confidence_bucket"] = "I_GUESSED"
        out_path = doc.with_suffix(".judge.json")
        tmp = out_path.with_suffix(".judge.json.tmp")
        tmp.write_text(json.dumps(out, indent=2), encoding="utf-8")
        tmp.rename(out_path)
        print(f"judge: {doc.name} -> {out.get('primary_subdomain')} [{out.get('confidence_bucket')}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
