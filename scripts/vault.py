"""Deterministic vault CLI. Pure stdlib. See docs/superpowers/specs/2026-06-15-*."""
import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML-subset parser: top-level scalars and simple `- ` lists."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text
    fm: dict = {}
    current_key = None
    for raw in lines[1:end]:
        if re.match(r"^\s*-\s+", raw) and current_key is not None:
            fm.setdefault(current_key, [])
            if isinstance(fm[current_key], list):
                fm[current_key].append(raw.strip()[2:].strip().strip('"'))
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if m:
            key, val = m.group(1), m.group(2).strip()
            current_key = key
            if val == "":
                fm[key] = []  # may become a list on following `- ` lines
            else:
                fm[key] = val.strip('"')
    body = "\n".join(lines[end + 1:])
    return fm, body


def render_template(rel_path: str, **vars: str) -> str:
    text = (TEMPLATES_DIR / rel_path).read_text(encoding="utf-8")
    for key, value in vars.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vault", description="Deterministic vault CLI.")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("scaffold").add_argument("name")
    ing = sub.add_parser("ingest")
    ing.add_argument("raw_file")
    nn = sub.add_parser("new-note")
    nn.add_argument("slug")
    nn.add_argument("--source", required=True)
    sub.add_parser("check")
    reg = sub.add_parser("register")
    reg.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path.cwd()
    if args.command == "scaffold":
        return cmd_scaffold(root, args.name)
    if args.command == "ingest":
        return cmd_ingest(root, Path(args.raw_file))
    if args.command == "new-note":
        return cmd_new_note(root, args.slug, args.source)
    if args.command == "check":
        return cmd_check(root)
    if args.command == "register":
        return cmd_register(root, dry_run=args.dry_run)
    if args.command == "status":
        return cmd_status(root)
    return 2


INDEX_STARTERS = {
    "_map-of-content.md": (
        "---\ntitle: Map of Content\ntype: index\ntags: [moc, index]\n---\n\n"
        "# Map of Content\n\nEntry point for the vault.\n\n"
        "## Notes\n\n## Analyses\n\n*Write-back notes from synthesis queries.*\n\n"
        "## Other indices\n- [[source-registry]]\n- [[key-takeaways]]\n- [[log]]\n"
    ),
    "source-registry.md": (
        "---\ntitle: Source Registry\ntype: index\ntags: [sources, registry]\n---\n\n"
        "# Source Registry\n\n| # | Clipping (raw/) | Published | Summary | Wiki notes |\n"
        "|---|---|---|---|---|\n"
    ),
    "log.md": (
        "---\ntitle: Log\ntype: index\ntags: [log]\n---\n\n"
        "# Log\n\nAppend-only journal: `## [YYYY-MM-DD] <op> | <title>`.\n"
    ),
    "key-takeaways.md": (
        "---\ntitle: Key Takeaways\ntype: index\ntags: [takeaways, index]\n---\n\n"
        "# Key Takeaways\n\n"
    ),
}


def cmd_scaffold(root: Path, name: str) -> int:
    v = root / name
    if v.exists() and any(v.iterdir()):
        print(f"vault scaffold: {v} already exists and is non-empty; aborting.", file=sys.stderr)
        return 1
    for sub in ["raw", "wiki/sources", "index", "eval", "scripts/templates", ".claude/skills"]:
        (v / sub).mkdir(parents=True, exist_ok=True)
    # Copy the engine files so the new vault is self-sufficient and self-replicating.
    shutil.copy2(Path(__file__).resolve(), v / "scripts" / "vault.py")
    lint = Path(__file__).resolve().parent / "lint_vault.py"
    if lint.exists():
        shutil.copy2(lint, v / "scripts" / "lint_vault.py")
    shutil.copytree(TEMPLATES_DIR, v / "scripts" / "templates", dirs_exist_ok=True)
    # Render CLAUDE.md, .gitignore, eval, and the four skills.
    (v / "CLAUDE.md").write_text(render_template("CLAUDE.md", VAULT_NAME=name), encoding="utf-8")
    (v / ".gitignore").write_text(render_template("gitignore"), encoding="utf-8")
    (v / "eval" / "VAULT_TESTS.md").write_text(
        render_template("eval/VAULT_TESTS.md", VAULT_NAME=name), encoding="utf-8")
    for skill in ["vault-setup", "vault-ingest", "vault-query", "vault-lint"]:
        dst = v / ".claude" / "skills" / skill
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "SKILL.md").write_text(
            render_template(f"skills/{skill}/SKILL.md"), encoding="utf-8")
    for fname, content in INDEX_STARTERS.items():
        (v / "index" / fname).write_text(content, encoding="utf-8")
    print(f"vault scaffold: created {v}")
    return 0


def cmd_ingest(root: Path, raw_file: Path) -> int:
    src = root / raw_file
    if not src.exists():
        print(f"vault ingest: {raw_file} not found.", file=sys.stderr)
        return 1
    fm, _ = parse_frontmatter(src.read_text(encoding="utf-8"))
    title = fm.get("title", src.stem)
    published = fm.get("published") or fm.get("created") or ""
    stem = src.stem
    summary_slug = slugify(title)
    # 1. Summary stub (idempotent), named by title slug to avoid colliding with the raw stem.
    summary = root / "wiki" / "sources" / f"{summary_slug}.md"
    if not summary.exists():
        summary.write_text(
            f'---\ntitle: "Summary — {title}"\ntype: source-summary\ntags: []\n'
            f'sources:\n  - "[[{stem}]]"\n'
            + (f"published: {published}\n" if published else "")
            + f'---\n\n# Summary — {title}\n\n'
            f'<!-- TODO: one-sentence thesis -->\n\n'
            f'<!-- TODO: ~200 words on what the source argues, grounded in [[{stem}]] -->\n\n'
            f'## Key claims\n<!-- TODO: - claim → [[derived-concept-note]] -->\n\n'
            f'## Derived concept notes\n<!-- TODO: [[note-a]] · [[note-b]] -->\n',
            encoding="utf-8")
    # 2. Registry row (idempotent).
    reg = root / "index" / "source-registry.md"
    reg_text = reg.read_text(encoding="utf-8")
    if f"[[{stem}]]" not in reg_text:
        row = f"| | [[{stem}]] | {published} | [[{summary_slug}]] | |\n"
        reg.write_text(reg_text.rstrip("\n") + "\n" + row, encoding="utf-8")
    # 3. Log entry (idempotent on title+op). Includes the raw stem so lint's
    #    per-clipping log check (which searches for the raw stem) passes.
    log = root / "index" / "log.md"
    log_text = log.read_text(encoding="utf-8")
    if f"ingest | {title}" not in log_text:
        entry = (f"## [{datetime.date.today().isoformat()}] ingest | {title}\n\n"
                 f"- source: [[{stem}]]\n")
        log.write_text(log_text.rstrip("\n") + "\n\n" + entry, encoding="utf-8")
    print(f"vault ingest: {stem} — summary stub ready in wiki/sources/{summary_slug}.md.")
    print("Now: read the clipping, then create one concept note per idea via:")
    print(f"  python3 scripts/vault.py new-note <slug> --source {raw_file}")
    print("Then fill all <!-- TODO --> blanks and run: python3 scripts/vault.py check")
    return 0


def _raw_stem(source: str) -> str:
    return Path(source).stem


def cmd_new_note(root: Path, slug: str, source: str) -> int:
    slug = slugify(slug)
    src_path = root / source
    if not src_path.exists():
        print(f"vault new-note: source {source} not found.", file=sys.stderr)
        return 1
    note = root / "wiki" / f"{slug}.md"
    if note.exists():
        print(f"vault new-note: {note.relative_to(root)} already exists; not overwriting.",
              file=sys.stderr)
        return 1
    stem = _raw_stem(source)
    content = (
        f'---\ntitle: "{slug.replace("-", " ").title()}"\ntype: concept\ntags: []\n'
        f'sources:\n  - "[[{stem}]]"\n---\n\n'
        f'# {slug.replace("-", " ").title()}\n\n'
        f'<!-- TODO: one-sentence thesis in bold, grounded in [[{stem}]] -->\n\n'
        f'<!-- TODO: body. Dense [[wikilinks]] to sibling notes. -->\n\n'
        f'## Related\n<!-- TODO: [[sibling-note]] · [[sibling-note]] -->\n'
    )
    note.write_text(content, encoding="utf-8")
    print(f"vault new-note: created wiki/{slug}.md — fill its TODO blanks, then add a MOC link.")
    return 0


def _find_todo_markers(root: Path) -> list[Path]:
    hits = []
    for md in (root / "wiki").rglob("*.md"):
        if "<!-- TODO" in md.read_text(encoding="utf-8"):
            hits.append(md)
    return hits


def cmd_check(root: Path) -> int:
    failed = False
    # Layer 1+structural: reuse the existing lint if present.
    lint = root / "scripts" / "lint_vault.py"
    if lint.exists():
        result = subprocess.run([sys.executable, str(lint)], cwd=str(root))
        if result.returncode != 0:
            print("vault check: lint_vault.py reported findings (see above).", file=sys.stderr)
            failed = True
    # Layer 2: stub-completion (deterministic proxy for "model did its job").
    todos = _find_todo_markers(root)
    if todos:
        failed = True
        print("vault check: unfilled stub / TODO marker in:", file=sys.stderr)
        for p in todos:
            print(f"  - {p.relative_to(root)} → fill its <!-- TODO --> body from its source.",
                  file=sys.stderr)
    if failed:
        print("vault check: FAIL — fix the findings or STOP and report.", file=sys.stderr)
        return 1
    print("vault check: OK")
    return 0


def cmd_register(root: Path, *, dry_run: bool = False, runner=subprocess.run) -> int:
    commands = [
        ["qmd", "collection", "add", "./raw", "--name", "sources"],
        ["qmd", "collection", "add", "./wiki", "--name", "concepts"],
        ["qmd", "collection", "add", "./index", "--name", "indices"],
        ["qmd", "update"],
        ["qmd", "embed"],
    ]
    # eval/ is intentionally absent: gold answers must never enter retrieval.
    for cmd in commands:
        print("vault register:", " ".join(cmd))
        if dry_run:
            continue
        result = runner(cmd, cwd=str(root))
        if getattr(result, "returncode", 1) != 0:
            print(f"vault register: command failed: {' '.join(cmd)}", file=sys.stderr)
            return 1
    return 0
def cmd_status(root: Path) -> int:
    raws = sorted((root / "raw").glob("*.md"))
    reg = (root / "index" / "source-registry.md").read_text(encoding="utf-8")
    log = (root / "index" / "log.md").read_text(encoding="utf-8")
    print(f"{'clipping':40} {'summary':8} {'registry':8} {'log':5}")
    for r in raws:
        stem = r.stem
        fm, _ = parse_frontmatter(r.read_text(encoding="utf-8"))
        summary_slug = slugify(fm.get("title", stem))
        has_summary = (root / "wiki" / "sources" / f"{summary_slug}.md").exists()
        has_reg = f"[[{stem}]]" in reg
        has_log = stem in log
        print(f"{stem:40} {'yes' if has_summary else 'NO':8} "
              f"{'yes' if has_reg else 'NO':8} {'yes' if has_log else 'NO':5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
