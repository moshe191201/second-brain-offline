"""Deterministic vault CLI. Pure stdlib. See docs/superpowers/specs/2026-06-15-*."""
import argparse
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


def cmd_ingest(root: Path, raw_file: Path) -> int: raise NotImplementedError
def cmd_new_note(root: Path, slug: str, source: str) -> int: raise NotImplementedError
def cmd_check(root: Path) -> int: raise NotImplementedError
def cmd_register(root: Path, *, dry_run: bool = False, runner=subprocess.run) -> int: raise NotImplementedError
def cmd_status(root: Path) -> int: raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
