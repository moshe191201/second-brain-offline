"""`vault` entry point. Argument parsing only — all behavior lives in core."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, core


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vault", description="Deterministic vault CLI.")
    p.add_argument("--version", action="version", version=f"vault {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sc = sub.add_parser("scaffold", help="create a new vault from the packaged payload")
    sc.add_argument("name")

    up = sub.add_parser("upgrade", help="re-lay framework-owned files in an existing vault")
    up.add_argument("dir", nargs="?", default=".")

    ing = sub.add_parser("ingest", help="stub out summary/registry/log for a raw clipping")
    ing.add_argument("raw_file")

    nn = sub.add_parser("new-note", help="stub out a concept note")
    nn.add_argument("slug")
    nn.add_argument("--source", required=True)

    ck = sub.add_parser("check", help="fail-closed vault health check")
    ck.add_argument("dir", nargs="?", default=".")

    reg = sub.add_parser("register", help="register vault folders as qmd collections")
    reg.add_argument("--dry-run", action="store_true")

    sub.add_parser("status", help="per-clipping ingest state")

    cl = sub.add_parser("classify", help="validate closed-vocabulary classification and patch frontmatter/ledger")
    cl.add_argument("--campaign", default="campaigns/example")
    cl.add_argument("--store", default="store")
    cl.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path.cwd()
    if args.command == "scaffold":
        return core.cmd_scaffold(root, args.name)
    if args.command == "upgrade":
        return core.cmd_upgrade(Path(args.dir).resolve())
    if args.command == "ingest":
        return core.cmd_ingest(root, Path(args.raw_file))
    if args.command == "new-note":
        return core.cmd_new_note(root, args.slug, args.source)
    if args.command == "check":
        return core.cmd_check(Path(args.dir).resolve())
    if args.command == "register":
        return core.cmd_register(root, dry_run=args.dry_run)
    if args.command == "status":
        return core.cmd_status(root)
    if args.command == "classify":
        return core.cmd_classify(root, campaign=Path(args.campaign), store=Path(args.store), dry_run=args.dry_run)
    return 2


if __name__ == "__main__":
    sys.exit(main())
