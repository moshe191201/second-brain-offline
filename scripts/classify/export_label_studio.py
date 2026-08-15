"""Export Label Studio tasks + render view.xml.

Reads store/*.md + sidecars (.retrieval.json, .judge.json),
renders markdown to HTML (minimal), writes tasks JSON.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
import sys


def md_to_html(md: str) -> str:
    # Minimal: headers, bold, code fences, paragraphs — enough for review
    # Strip frontmatter
    if md.startswith("---"):
        parts = md.split("---", 2)
        if len(parts) > 2:
            md = parts[2]
    # Escape then restore markdown markers
    esc = html.escape(md)
    esc = re.sub(r"^### (.*)", r"<h3>\1</h3>", esc, flags=re.MULTILINE)
    esc = re.sub(r"^## (.*)", r"<h2>\1</h2>", esc, flags=re.MULTILINE)
    esc = re.sub(r"^# (.*)", r"<h1>\1</h1>", esc, flags=re.MULTILINE)
    esc = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", esc)
    esc = re.sub(r"```(.*?)```", r"<pre>\1</pre>", esc, flags=re.DOTALL)
    esc = re.sub(r"\n\n+", r"</p><p>", esc)
    return f"<p>{esc}</p>"


def main():
    p = argparse.ArgumentParser(description="Export Label Studio tasks")
    p.add_argument("--campaign", default="campaigns/example")
    p.add_argument("--store", default="store")
    p.add_argument("--out", default="label_studio_tasks.json")
    p.add_argument("--view-out", default=None, help="rendered view.xml path")
    args = p.parse_args()

    camp = Path(args.campaign)
    tax_path = camp / "taxonomy.yaml"
    if not tax_path.exists():
        tax_path = Path("src/second_brain_vault_framework/payload/templates/classification/taxonomy.yaml")
    # Parse subdomain list for view rendering
    subs = []
    if tax_path.exists():
        for m in re.finditer(r"^\s{2}(\w+):\n", tax_path.read_text(encoding="utf-8"), flags=re.MULTILINE):
            n = m.group(1)
            if n not in ("subdomains", "version", "campaign"):
                subs.append(n)

    store_root = Path(args.store)
    docs = list(store_root.rglob("*.md")) if store_root.exists() else []
    # Filter out sidecars (already .md but with frontmatter source_doc_id)
    docs = [d for d in docs if d.suffix == ".md" and not d.name.endswith(".retrieval.json")]

    tasks = []
    for doc in docs[:5000]:
        text = doc.read_text(encoding="utf-8")
        html_text = md_to_html(text)
        # sidecars
        judge = {}
        jp = doc.with_suffix(".judge.json")
        if jp.exists():
            try:
                judge = json.loads(jp.read_text(encoding="utf-8"))
            except Exception:
                pass
        retrieval = {}
        rp = doc.with_suffix(".retrieval.json")
        if rp.exists():
            try:
                retrieval = json.loads(rp.read_text(encoding="utf-8"))
            except Exception:
                pass
        bucket = judge.get("confidence_bucket", "NEEDS_HUMAN_VALIDATION")
        cls_map = {"SURE": "sure", "NEEDS_HUMAN_VALIDATION": "needs", "I_GUESSED": "guessed"}
        tasks.append({
            "data": {
                "text_html": html_text,
                "filename": doc.name,
                "llm_primary": judge.get("primary_subdomain", ""),
                "llm_secondary": ", ".join(judge.get("secondary_subdomains", [])),
                "relation_type": judge.get("relation_type", "none"),
                "confidence_bucket": bucket,
                "confidence_class": cls_map.get(bucket, "needs"),
                "candidates": ", ".join(c.get("subdomain","") for c in retrieval.get("candidates", [])),
                "reasoning_brief": judge.get("reasoning_brief", ""),
            }
        })

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    tmp.rename(out_path)
    print(f"export: {len(tasks)} tasks -> {out_path}")

    # Render view.xml with N choices if requested
    if args.view_out and subs:
        tpl_path = Path("src/second_brain_vault_framework/payload/templates/classification/label_studio/view.xml")
        if tpl_path.exists():
            tpl = tpl_path.read_text(encoding="utf-8")
            # Render N choices for variable-N (I1): replace placeholder Choice blocks
            rendered = tpl
            for tag in ("primary", "secondary"):
                pat = re.compile(rf'(<Choices name="{tag}".*?>)(.*?)(</Choices>)', re.DOTALL)
                choices_str = "\n".join(f'        <Choice value="{s}" />' for s in subs)
                rendered = pat.sub(lambda m: f"{m.group(1)}\n{choices_str}\n      {m.group(3)}", rendered)
            Path(args.view_out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.view_out).write_text(rendered, encoding="utf-8")
            print(f"export: view.xml -> {args.view_out} (N={len(subs)} subs: {', '.join(subs)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
