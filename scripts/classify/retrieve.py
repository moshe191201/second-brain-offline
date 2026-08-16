"""Top-k retriever — embedding filter before LLM judge.

Builds per-subdomain centroid from taxonomy examples, calls OpenAI-compatible
/v1/embeddings, ranks by cosine, returns top-k per doc.

Offline-friendly: if no endpoint, falls back to deterministic hashing so tests pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import sys
import urllib.request, urllib.error

TOP_K_MIN, TOP_K_MAX = 1, 10


def cosine(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def hash_embed(text: str, dim=64):
    # Deterministic stub for tests / offline: hash words into vector
    vec = [0.0]*dim
    for w in re.findall(r"\w+", text.lower())[:200]:
        h = int(hashlib.sha256(w.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    n = math.sqrt(sum(x*x for x in vec)) or 1.0
    return [x/n for x in vec]


def call_embeddings(texts, base_url, api_key, model):
    url = base_url.rstrip("/") + "/v1/embeddings"
    body = json.dumps({"model": model, "input": texts}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
        # OpenAI shape: data[].embedding
        return [row["embedding"] for row in data["data"]]


def load_taxonomy(path: Path):
    txt = path.read_text(encoding="utf-8")
    subs = {}
    try:
        from second_brain_vault_framework.core import _parse_taxonomy_blocks
        blocks = _parse_taxonomy_blocks(txt)
    except Exception:
        _local_re = re.compile(r"^\s{2}([\w-]+):\s*(?:\n|$)", re.MULTILINE)
        matches = list(_local_re.finditer(txt))
        blocks = {}
        for i, m in enumerate(matches):
            name = m.group(1)
            if name in ("subdomains", "version", "campaign"):
                continue
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(txt)
            blocks[name] = txt[start:end]
    for name, block in blocks.items():
        # Support text: "quoted", text: 'single', text: | multiline (first line)
        examples = re.findall(r'text:\s*"(.*?)"', block)
        examples += re.findall(r"text:\s*'(.*?)'", block)
        # multiline literal: text: | then indented line
        for mm in re.finditer(r"text:\s*\|\n\s+(.+)", block):
            examples.append(mm.group(1).strip())
        subs[name] = examples
    return subs


def main():
    p = argparse.ArgumentParser(description="Top-k retriever")
    p.add_argument("--campaign", default="campaigns/example")
    p.add_argument("--store", default="store")
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    policy_path = Path(args.campaign) / "policy.yaml"
    tax_path = Path(args.campaign) / "taxonomy.yaml"
    if not tax_path.exists():
        # fallback to payload template
        tax_path = Path("src/second_brain_vault_framework/payload/templates/classification/taxonomy.yaml")
    top_k = args.top_k or 4
    # policy override
    if policy_path.exists():
        m = re.search(r"top_k:\s*(\d+)", policy_path.read_text(encoding="utf-8"))
        if m and args.top_k is None:
            top_k = int(m.group(1))
    top_k = max(TOP_K_MIN, min(TOP_K_MAX, top_k))

    subs = load_taxonomy(tax_path)
    if not subs:
        print(f"retrieve: no subdomains in {tax_path}", file=sys.stderr)
        return 1

    base_url = os.environ.get("CLASSIFY_EMBED_BASE_URL") or os.environ.get("QMD_OPENAI_BASE_URL") or ""
    api_key = os.environ.get("CLASSIFY_EMBED_API_KEY") or os.environ.get("QMD_OPENAI_API_KEY") or ""
    model = os.environ.get("CLASSIFY_EMBED_MODEL") or "embeddinggemma-300M"

    # Build centroids
    centroids = {}
    centroid_dim = None
    for name, examples in subs.items():
        if not examples:
            continue
        # Embed examples
        if base_url:
            try:
                vecs = call_embeddings(examples, base_url, api_key, model)
            except Exception as e:
                # Fail-closed when endpoint configured (I6): outage must not silently use hash stub in prod
                # Hash fallback only when base_url == "" (tests). With base_url set, exit non-zero.
                print(f"retrieve: embedding API failed ({e}) — failing closed (endpoint configured)", file=sys.stderr)
                return 1
        else:
            vecs = [hash_embed(t) for t in examples]
        # centroid = mean
        dim = len(vecs[0])
        if centroid_dim is None:
            centroid_dim = dim
        elif dim != centroid_dim:
            print(f"retrieve: embedding dim mismatch {dim} vs {centroid_dim} — failing closed", file=sys.stderr)
            return 1
        cent = [sum(v[i] for v in vecs)/len(vecs) for i in range(dim)]
        n = math.sqrt(sum(x*x for x in cent)) or 1.0
        centroids[name] = [x/n for x in cent]

    store_root = Path(args.store)
    docs = list(store_root.rglob("*.md")) if store_root.exists() else []
    if not docs:
        print(f"retrieve: no docs in {store_root}", file=sys.stderr)
        if args.dry_run:
            print(f"[dry-run] would rank {len(subs)} subdomains top_k={top_k}")
            return 0
        return 1

    for doc in docs[:1000]:  # cap per run
        text = doc.read_text(encoding="utf-8")
        # strip frontmatter for embedding
        if text.startswith("---"):
            parts = text.split("---", 2)
            body = parts[2] if len(parts) > 2 else text
        else:
            body = text
        if base_url:
            try:
                qvec = call_embeddings([body[:4000]], base_url, api_key, model)[0]
            except Exception as e:
                print(f"retrieve: embedding API failed for doc {doc.name} ({e}) — failing closed", file=sys.stderr)
                return 1
            if len(qvec) != centroid_dim:
                print(f"retrieve: query dim {len(qvec)} vs centroid dim {centroid_dim} mismatch — failing closed", file=sys.stderr)
                return 1
        else:
            qvec = hash_embed(body[:4000], dim=centroid_dim)
        scores = [(name, cosine(qvec, cent)) for name, cent in centroids.items()]
        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[:top_k]
        if args.dry_run:
            print(f"[dry-run] {doc.name}: top-{top_k} = {', '.join(f'{n}({s:.2f})' for n,s in top)}")
        else:
            # write sidecar .retrieval.json next to doc
            sidecar = doc.with_suffix(".retrieval.json")
            tmp = sidecar.with_suffix(".retrieval.json.tmp")
            tmp.write_text(json.dumps({"doc": doc.name, "top_k": top_k, "candidates": [{"subdomain": n, "score": s} for n,s in top]}, indent=2), encoding="utf-8")
            tmp.rename(sidecar)
            print(f"retrieve: {doc.name} -> {', '.join(n for n,_ in top)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
