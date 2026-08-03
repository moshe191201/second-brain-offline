#!/usr/bin/env python3
"""Grade a recorded vault answer against the gold rows in `tests/VAULT_TESTS.md`.

Framework-owned, do not edit. Pure stdlib, no network, no model.

The eval in `tests/VAULT_TESTS.md` is run by asking a *fresh* Claude Code session
the question verbatim and recording its answer. This script turns the mechanical
half of scoring that answer into something deterministic and repeatable:

  * **citation** — is the gold note (or its raw source) actually cited? Fully
    deterministic, and the part a hallucinating agent fails.
  * **negative control (T2)** — does the answer explicitly say the topic is not
    covered, rather than answering it? Deterministic on the refusal phrasing.
  * **gold fact** — reported for the human to compare, with a token-overlap hint.
    Never asserted as pass/fail: paraphrase is legitimate and only a reader can
    judge it.

Exit code is 0 only when every deterministic check passes, so it can gate CI.

Usage
-----
    python3 scripts/check_vault_answer.py --list
    python3 scripts/check_vault_answer.py T1 3 --answer answer.md
    claude -p "<question>" | python3 scripts/check_vault_answer.py T2 1 --answer -
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TESTS_FILE = Path(__file__).resolve().parent.parent / "tests" / "VAULT_TESTS.md"

# An answer passes a negative control only by saying, in some form, "not here".
NEGATIVE_MARKERS = [
    "not covered", "does not cover", "doesn't cover", "not in this vault",
    "no note", "no notes", "not present", "absent", "does not appear",
    "doesn't appear", "nothing in this vault", "not indexed", "no coverage",
    "not found in the vault", "no source in this vault",
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "for", "that",
    "this", "with", "as", "at", "by", "on", "from", "be", "are", "was", "were",
    "than", "then", "its", "per", "also", "not", "but", "into", "each", "what",
}


# --------------------------------------------------------------------------- #
# Parsing tests/VAULT_TESTS.md
# --------------------------------------------------------------------------- #

def _split_row(line: str) -> list[str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def _section(text: str, group: str) -> str:
    """Return the body of the `## <group> — ...` section."""
    m = re.search(rf"^##\s+{re.escape(group)}\b.*?$(.*?)(?=^##\s|\Z)",
                  text, re.MULTILINE | re.DOTALL)
    if not m:
        raise SystemExit(f"check_vault_answer: no '## {group}' section in {TESTS_FILE.name}")
    return m.group(1)


def _rows(body: str) -> dict[str, list[str]]:
    """Numbered markdown table rows in a section, keyed by the leading number."""
    out: dict[str, list[str]] = {}
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _split_row(line)
        if cells and re.fullmatch(r"\d+", cells[0]):
            out[cells[0]] = cells
    return out


def load_case(group: str, number: str) -> dict:
    if not TESTS_FILE.exists():
        raise SystemExit(f"check_vault_answer: {TESTS_FILE} not found — run from a vault.")
    text = TESTS_FILE.read_text(encoding="utf-8")
    rows = _rows(_section(text, group))
    if number not in rows:
        raise SystemExit(f"check_vault_answer: {group} has no question #{number} "
                         f"(have: {', '.join(sorted(rows, key=int)) or 'none'})")
    cells = rows[number]
    case = {"group": group, "number": number, "question": cells[1]}
    if group == "T1":
        case["gold_fact"] = cells[2]
        case["expected"] = _backticked(cells[3])
    elif group == "T2":
        case["gold_fact"] = cells[2]
        case["expected"] = []
    elif group == "T3":
        case["gold_fact"] = cells[2]
        case["expected"] = _backticked(cells[3])
    else:
        raise SystemExit(f"check_vault_answer: unknown group {group} (expected T1, T2 or T3)")
    return case


def _backticked(cell: str) -> list[str]:
    """Note stems named in a gold cell, e.g. '`lora` + `kv-cache`' → [lora, kv-cache]."""
    return re.findall(r"`([^`]+)`", cell)


# --------------------------------------------------------------------------- #
# Grading
# --------------------------------------------------------------------------- #

def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-]*", text.lower())
            if w not in STOPWORDS and len(w) > 2}


def cites(answer: str, stem: str) -> bool:
    """Was this note cited? Accepts a wikilink, a path, or the bare stem."""
    a = answer.lower()
    s = stem.lower()
    return any(form in a for form in (f"[[{s}]]", f"{s}.md", s))


def grade(case: dict, answer: str) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    if case["group"] == "T2":
        hit = next((m for m in NEGATIVE_MARKERS if m in answer.lower()), None)
        if hit:
            lines.append(f"  PASS  negative control — answer states absence (\"{hit}\")")
        else:
            ok = False
            lines.append("  FAIL  negative control — no explicit 'not covered' statement. "
                         "An answer here is a hallucination, not a hit.")
        lines.append(f"  note  verified absent: {case['gold_fact']}")
        return ok, lines

    missing = [s for s in case["expected"] if not cites(answer, s)]
    # T3 gold cells offer alternatives ("x + y (or z)"); one miss out of >2 is tolerated.
    tolerance = 1 if case["group"] == "T3" and len(case["expected"]) > 2 else 0
    if len(missing) <= tolerance:
        lines.append(f"  PASS  citation — cites {', '.join(case['expected'])}")
    else:
        ok = False
        lines.append(f"  FAIL  citation — missing {', '.join(missing)} "
                     f"(expected {', '.join(case['expected'])})")

    gold_tokens = _tokens(case["gold_fact"])
    overlap = gold_tokens & _tokens(answer)
    pct = round(100 * len(overlap) / len(gold_tokens)) if gold_tokens else 0
    lines.append(f"  ----  gold fact ({pct}% token overlap — advisory, judge by reading):")
    lines.append(f"        {case['gold_fact']}")
    return ok, lines


# --------------------------------------------------------------------------- #

def cmd_list() -> int:
    text = TESTS_FILE.read_text(encoding="utf-8")
    for group in ("T1", "T2", "T3"):
        try:
            rows = _rows(_section(text, group))
        except SystemExit:
            continue
        print(f"\n{group}")
        for n in sorted(rows, key=int):
            print(f"  {n:>2}. {rows[n][1][:96]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="check_vault_answer", description=__doc__.splitlines()[0])
    p.add_argument("group", nargs="?", help="T1, T2 or T3")
    p.add_argument("number", nargs="?", help="question number within the group")
    p.add_argument("--answer", help="file holding the recorded answer, or - for stdin")
    p.add_argument("--list", action="store_true", help="list every question and exit")
    args = p.parse_args(argv)

    if args.list:
        return cmd_list()
    if not args.group or not args.number:
        p.error("group and number are required (or use --list)")
    if not args.answer:
        p.error("--answer is required")

    answer = (sys.stdin.read() if args.answer == "-"
              else Path(args.answer).read_text(encoding="utf-8"))
    case = load_case(args.group.upper(), args.number)

    print(f"{case['group']}#{case['number']}  {case['question']}")
    ok, lines = grade(case, answer)
    for line in lines:
        print(line)
    print("  ====  " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
