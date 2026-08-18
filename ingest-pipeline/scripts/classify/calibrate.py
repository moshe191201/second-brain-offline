"""Calibration + ledger helpers.

Calibrate: per-bucket accuracy, confusion matrix, glossary-miss report.
Ledger: append-only JSONL helpers.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import sys


def calibrate(gold_path: Path, predictions_dir: Path):
    """Compare gold labels vs judge outputs."""
    if not gold_path.exists():
        print(f"calibrate: gold not found: {gold_path}", file=sys.stderr)
        return 1
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    # gold: list of {doc_id, true_primary, ...}
    by_bucket = collections.defaultdict(list)
    confusion = collections.Counter()
    total = 0
    correct = 0
    for row in gold:
        doc_id = row.get("doc_id", "")
        true_primary = row.get("true_primary", "")
        # find prediction sidecar
        pred = None
        for p in predictions_dir.rglob("*.judge.json"):
            if doc_id in p.name or doc_id in p.read_text(encoding="utf-8"):
                try:
                    pred = json.loads(p.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass
        # If no sidecar, try direct match by doc_id key in gold row's pred field
        if pred is None and "pred_primary" in row:
            pred = {"primary_subdomain": row["pred_primary"], "confidence_bucket": row.get("confidence_bucket", "NEEDS_HUMAN_VALIDATION")}
        if pred is None:
            continue
        total += 1
        bucket = pred.get("confidence_bucket", "NEEDS_HUMAN_VALIDATION")
        is_correct = pred.get("primary_subdomain") == true_primary
        if is_correct:
            correct += 1
        by_bucket[bucket].append(is_correct)
        confusion[(true_primary, pred.get("primary_subdomain", ""))] += 1

    print(f"calibrate: {correct}/{total} overall accuracy {correct/total:.2%}" if total else "calibrate: no matched docs")
    for bucket in ["SURE", "NEEDS_HUMAN_VALIDATION", "I_GUESSED"]:
        vals = by_bucket.get(bucket, [])
        if vals:
            acc = sum(vals)/len(vals)
            print(f"  {bucket}: {sum(vals)}/{len(vals)} = {acc:.2%} (n={len(vals)})")
        else:
            print(f"  {bucket}: n=0")
    if confusion:
        print("  Confusion (true -> pred):")
        for (t,p), c in confusion.most_common(10):
            if t != p:
                print(f"    {t} -> {p}: {c}")
    # Glossary-miss: I_GUESSED where true term likely in glossary but not mapped
    guessed = by_bucket.get("I_GUESSED", [])
    if guessed:
        miss_rate = 1 - (sum(guessed)/len(guessed)) if guessed else 0
        if miss_rate > 0.5:
            print(f"  Glossary-miss signal: I_GUESSED accuracy {sum(guessed)/len(guessed):.2%} — consider adding surface forms for thin docs")
    return 0


# Ledger helpers (minimal)
def ledger_append(ledger_path: Path, event: dict):
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def ledger_project(ledger_path: Path, doc_id: str | None = None):
    if not ledger_path.exists():
        print(f"ledger: not found: {ledger_path}", file=sys.stderr)
        return 1
    state: dict = {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if doc_id and ev.get("doc_id") != doc_id:
            continue
        state[ev.get("doc_id", "_global")] = ev
    print(json.dumps(state, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(description="Calibrate + ledger")
    sub = p.add_subparsers(dest="cmd")
    c1 = sub.add_parser("calibrate")
    c1.add_argument("--gold", required=True, help="gold JSON path")
    c1.add_argument("--store", default="store")
    c2 = sub.add_parser("ledger-append")
    c2.add_argument("--ledger", required=True)
    c2.add_argument("--event", required=True, help="JSON event string")
    c3 = sub.add_parser("ledger-project")
    c3.add_argument("--ledger", required=True)
    c3.add_argument("--doc-id", default=None)
    args = p.parse_args()
    if args.cmd == "calibrate":
        return calibrate(Path(args.gold), Path(args.store))
    elif args.cmd == "ledger-append":
        ledger_append(Path(args.ledger), json.loads(args.event))
        print(f"ledger: appended to {args.ledger}")
        return 0
    elif args.cmd == "ledger-project":
        return ledger_project(Path(args.ledger), args.doc_id)
    else:
        p.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
