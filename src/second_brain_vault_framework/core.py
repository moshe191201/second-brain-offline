"""Vault engine — importable, pure stdlib.

The authoritative implementation of every `vault` subcommand. A vault carries a
thin `scripts/vault.py` shim that imports this module, so a vault's behavior can
never drift from the installed package.

Design: docs/superpowers/specs/2026-07-12-vault-framework-package-distribution-design.md
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

# --------------------------------------------------------------------------- #
# Payload / manifest access
# --------------------------------------------------------------------------- #

PACKAGE = "second_brain_vault_framework"

# Wikilink targets that are intentionally not vault notes (author names, external refs).
KNOWN_EXTERNAL: set[str] = {"Miguel Otero Pedrido"}

STAMP_FILE = ".vault-framework.json"
BACKUP_DIR = ".vault-framework-backup"


def _pkg_root() -> Path:
    return Path(str(resources.files(PACKAGE)))


def payload_root() -> Path:
    return _pkg_root() / "payload"


def load_manifest() -> dict:
    """The ownership contract.

    Two tiers of framework file:
      * ``owned_paths``        — re-laid wholesale on every ``upgrade``.
      * ``scaffold_only_paths`` — written once by ``scaffold``, then left alone.
        ``tests/VAULT_TESTS.md`` lives here because every vault rewrites its T1–T3
        gold answers for its own corpus; re-laying it would destroy the eval.
    """
    return json.loads((_pkg_root() / "manifest.json").read_text(encoding="utf-8"))


def framework_version() -> str:
    from . import __version__

    return __version__


def payload_path_for(vault_rel: str) -> Path:
    """Map a vault-relative path to its file inside the payload.

    `.claude/` is shipped as `dot-claude/` because a leading dot makes the
    directory invisible to some packaging backends.
    """
    rel = vault_rel
    if rel.startswith(".claude/"):
        rel = "dot-claude/" + rel[len(".claude/"):]
    return payload_root() / rel


# --------------------------------------------------------------------------- #
# Small parsers
# --------------------------------------------------------------------------- #


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
    text = payload_path_for(rel_path).read_text(encoding="utf-8")
    for key, value in vars.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def wikilinks_in(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"\[\[([^\]|#]+)", text)]


# --------------------------------------------------------------------------- #
# scaffold
# --------------------------------------------------------------------------- #

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

CONTENT_DIRS = ["raw", "wiki/sources", "index", "tests", "scripts", ".claude/skills"]


def cmd_scaffold(root: Path, name: str) -> int:
    v = root / name
    if v.exists() and any(v.iterdir()):
        print(f"vault scaffold: {v} already exists and is non-empty; aborting.", file=sys.stderr)
        return 1
    manifest = load_manifest()
    for sub in CONTENT_DIRS:
        (v / sub).mkdir(parents=True, exist_ok=True)
    # Scaffold lays down both tiers; upgrade re-lays only the owned one.
    _lay_down_payload(v, manifest, vault_name=name,
                      paths=manifest["owned_paths"] + manifest.get("scaffold_only_paths", []))
    (v / ".gitignore").write_text(render_template("gitignore"), encoding="utf-8")
    for fname, content in INDEX_STARTERS.items():
        (v / "index" / fname).write_text(content, encoding="utf-8")
    _write_stamp(v, name)
    print(f"vault scaffold: created {v} (framework {framework_version()})")
    return 0


# --------------------------------------------------------------------------- #
# upgrade — manifest-driven re-lay of framework-owned paths
# --------------------------------------------------------------------------- #


def _write_stamp(vault: Path, vault_name: str) -> None:
    manifest = load_manifest()
    stamp = {
        "framework_version": framework_version(),
        "vault_name": vault_name,
        "installed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "manifest": manifest,
    }
    (vault / STAMP_FILE).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")


def vault_name_for(vault: Path, stamp: dict | None) -> str:
    """The name substituted into `{{VAULT_NAME}}`.

    Recorded at scaffold time so `upgrade` re-renders the same name even if the
    folder was since moved or renamed; falls back to the folder name for vaults
    that predate stamping.
    """
    return (stamp or {}).get("vault_name") or vault.name


def read_stamp(vault: Path) -> dict | None:
    f = vault / STAMP_FILE
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def extract_user_zone(text: str, start: str, end: str) -> str | None:
    """Return the content between the markers, or None if the block is absent."""
    i = text.find(start)
    j = text.find(end)
    if i == -1 or j == -1 or j < i:
        return None
    return text[i + len(start):j]


def inject_user_zone(text: str, start: str, end: str, zone: str) -> str:
    i = text.find(start)
    j = text.find(end)
    if i == -1 or j == -1 or j < i:
        return text  # payload has no markers; nothing to inject into
    return text[: i + len(start)] + zone + text[j:]


def _render(payload_text: str, vault_name: str, rel: str,
            preserved: dict[str, str] | None, zones: dict) -> str:
    """What this payload file should look like once laid into the vault.

    Drift detection compares against *this*, not the raw payload — otherwise a
    substituted name or a preserved user zone would read as an edit on every run.
    """
    text = payload_text.replace("{{VAULT_NAME}}", vault_name)
    if preserved and rel in preserved and rel in zones:
        text = inject_user_zone(text, zones[rel]["start"], zones[rel]["end"], preserved[rel])
    return text


def _lay_down_payload(vault: Path, manifest: dict, *, vault_name: str,
                      preserved: dict[str, str] | None = None,
                      paths: list[str] | None = None) -> list[str]:
    """Copy framework paths from the payload into the vault."""
    written = []
    zones = manifest.get("user_zones", {})
    for rel in (paths if paths is not None else manifest["owned_paths"]):
        src = payload_path_for(rel)
        if not src.exists():
            continue
        dst = vault / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(_render(src.read_text(encoding="utf-8"), vault_name, rel, preserved, zones),
                       encoding="utf-8")
        written.append(rel)
    return written


def cmd_upgrade(root: Path) -> int:
    vault = root
    manifest = load_manifest()
    stamp = read_stamp(vault)
    old_version = (stamp or {}).get("framework_version", "unknown")
    name = vault_name_for(vault, stamp)
    zones = manifest.get("user_zones", {})

    # 1. Preserve user zones out of the on-disk copies.
    preserved: dict[str, str] = {}
    for rel, markers in zones.items():
        f = vault / rel
        if f.exists():
            zone = extract_user_zone(f.read_text(encoding="utf-8"), markers["start"], markers["end"])
            if zone is not None:
                preserved[rel] = zone

    # 2. Back up any framework file that drifted from the shipped payload.
    backups = []
    for rel in manifest["owned_paths"]:
        f = vault / rel
        src = payload_path_for(rel)
        if f.exists() and src.exists() and f.read_text(encoding="utf-8") != _render(
                src.read_text(encoding="utf-8"), name, rel, preserved, zones):
            dest = vault / BACKUP_DIR / old_version / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            backups.append(rel)

    # 3. Re-lay the payload, re-injecting user zones.
    _lay_down_payload(vault, manifest, vault_name=name, preserved=preserved)

    # 4. Delete framework files that this version no longer ships. Content is
    #    never a candidate — only paths the *previous* manifest claimed.
    removed = []
    prev_owned = set(((stamp or {}).get("manifest") or {}).get("owned_paths", []))
    for rel in sorted(prev_owned - set(manifest["owned_paths"])):
        f = vault / rel
        if f.exists():
            f.unlink()
            removed.append(rel)

    _write_stamp(vault, name)
    print(f"vault upgrade: {old_version} → {framework_version()}")
    for rel in backups:
        print(f"  backed up (edited on disk): {BACKUP_DIR}/{old_version}/{rel}")
    for rel in removed:
        print(f"  removed (no longer shipped): {rel}")
    if preserved:
        print(f"  user zone preserved in: {', '.join(sorted(preserved))}")
    return 0


# --------------------------------------------------------------------------- #
# ingest / new-note
# --------------------------------------------------------------------------- #


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
    stem = Path(source).stem
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


# --------------------------------------------------------------------------- #
# lint / check
# --------------------------------------------------------------------------- #


def lint(root: Path) -> tuple[list[str], int]:
    """Structural lint. Returns (findings, notes_checked). Never raises on a clean vault."""
    RAW, WIKI, INDEX = root / "raw", root / "wiki", root / "index"
    LOG, MOC = INDEX / "log.md", INDEX / "_map-of-content.md"
    findings: list[str] = []

    def find(msg: str) -> None:
        findings.append(msg)

    stems: dict[str, Path] = {}
    for folder in [RAW, WIKI, WIKI / "sources", INDEX]:
        if folder.exists():
            for p in folder.glob("*.md"):
                stems[p.stem] = p

    # 1. Broken wikilinks
    for folder in [WIKI, INDEX]:
        for p in folder.rglob("*.md"):
            for link in wikilinks_in(p.read_text(encoding="utf-8")):
                if link not in stems and link not in KNOWN_EXTERNAL:
                    find(f"BROKEN WIKILINK: [[{link}]] in {p.relative_to(root)}")

    # 2. Orphan wiki notes (no inbound link from any wiki or index note)
    linked_to: set[str] = set()
    for folder in [WIKI, INDEX]:
        for p in folder.rglob("*.md"):
            linked_to.update(wikilinks_in(p.read_text(encoding="utf-8")))

    for p in WIKI.rglob("*.md"):
        if p.stem not in linked_to:
            find(f"ORPHAN NOTE: {p.relative_to(root)} has no inbound links")

    # 3. Raw clippings never referenced
    for p in RAW.glob("*.md"):
        if p.stem not in linked_to:
            find(f"UNREFERENCED RAW: {p.stem}")

    # 4. Wiki notes missing sources: frontmatter
    #    (index-type, analysis-type, and wiki/sources/ notes are exempt)
    for p in WIKI.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if "type: index" in text or "type: analysis" in text:
            continue
        if "sources:" not in text:
            find(f"MISSING SOURCES: {p.relative_to(root)}")

    # 5. Each raw clipping has an ingest entry in log.md
    if LOG.exists():
        log_text = LOG.read_text(encoding="utf-8")
        for p in RAW.glob("*.md"):
            if p.stem not in log_text:
                find(f"NO LOG ENTRY: {p.name} missing from index/log.md")
    else:
        find("MISSING FILE: index/log.md does not exist")

    # 6. Every wiki note reachable from MOC (transitive link closure)
    if MOC.exists():
        visited: set[Path] = set()
        queue = [MOC]
        while queue:
            current = queue.pop()
            if current in visited:
                continue
            visited.add(current)
            if not current.exists():
                continue
            for link in wikilinks_in(current.read_text(encoding="utf-8")):
                if link in stems:
                    queue.append(stems[link])
        reachable = {p.stem for p in visited}
        for p in WIKI.rglob("*.md"):
            if p.stem not in reachable:
                find(f"UNREACHABLE FROM MOC: {p.relative_to(root)}")
    else:
        find("MISSING FILE: index/_map-of-content.md does not exist")

    # 7. Duplicate stems across folders
    seen: dict[str, Path] = {}
    for folder in [RAW, WIKI, WIKI / "sources", INDEX]:
        if not folder.exists():
            continue
        for p in folder.glob("*.md"):
            if p.stem in seen:
                find(f"DUPLICATE STEM: '{p.stem}' in {p.relative_to(root)}"
                     f" and {seen[p.stem].relative_to(root)}")
            else:
                seen[p.stem] = p

    return findings, len(stems)


def _find_todo_markers(root: Path) -> list[Path]:
    hits = []
    for md in (root / "wiki").rglob("*.md"):
        if "<!-- TODO" in md.read_text(encoding="utf-8"):
            hits.append(md)
    return hits


def cmd_check(root: Path) -> int:
    failed = False

    # Layer 1 — structural lint.
    findings, total = lint(root)
    if findings:
        failed = True
        print(f"\n{'=' * 60}")
        print(f"VAULT LINT: {len(findings)} finding(s)  [{total} notes checked]")
        print("=" * 60)
        for f in findings:
            print(f"  • {f}")
        print()
    else:
        print(f"VAULT LINT: OK — no findings  [{total} notes checked]")

    # Layer 2 — stub completion (deterministic proxy for "the model did its job").
    todos = _find_todo_markers(root)
    if todos:
        failed = True
        print("vault check: unfilled stub / TODO marker in:", file=sys.stderr)
        for p in todos:
            print(f"  - {p.relative_to(root)} → fill its <!-- TODO --> body from its source.",
                  file=sys.stderr)

    # Layer 3 — framework drift.
    stamp = read_stamp(root)
    if stamp is None:
        print(f"vault check: no {STAMP_FILE} — run `vault upgrade` to stamp this vault.")
    elif stamp.get("framework_version") != framework_version():
        print(f"vault check: framework drift — vault is stamped "
              f"{stamp.get('framework_version')}, installed package is {framework_version()}. "
              f"Run `vault upgrade`.", file=sys.stderr)
        failed = True

    if failed:
        print("vault check: FAIL — fix the findings or STOP and report.", file=sys.stderr)
        return 1
    print("vault check: OK")
    return 0


# --------------------------------------------------------------------------- #
# register / status
# --------------------------------------------------------------------------- #


def cmd_register(root: Path, *, dry_run: bool = False, runner=subprocess.run) -> int:
    commands = [
        ["qmd", "collection", "add", "./raw", "--name", "sources"],
        ["qmd", "collection", "add", "./wiki", "--name", "concepts"],
        ["qmd", "collection", "add", "./index", "--name", "indices"],
        ["qmd", "update"],
        ["qmd", "embed"],
    ]
    # tests/ is intentionally absent: gold answers must never enter retrieval.
    for cmd in commands:
        print("vault register:", " ".join(cmd))
        if dry_run:
            continue
        result = runner(cmd, cwd=str(root))
        if getattr(result, "returncode", 1) != 0:
            print(f"vault register: command failed: {' '.join(cmd)}", file=sys.stderr)
            return 1
    return 0


def _summary_exists_for(root: Path, stem: str) -> bool:
    """A clipping is summarized if some wiki/sources note lists it in `sources:`.

    Detect by frontmatter rather than filename so it works regardless of how the
    summary is named (e.g. hand-curated short slugs vs. title slugs).
    """
    src_dir = root / "wiki" / "sources"
    if not src_dir.exists():
        return False
    for s in src_dir.glob("*.md"):
        fm, _ = parse_frontmatter(s.read_text(encoding="utf-8"))
        links = fm.get("sources", [])
        if isinstance(links, str):
            links = [links]
        if any(link.strip().strip("[]") == stem for link in links):
            return True
    return False


def cmd_status(root: Path) -> int:
    raws = sorted((root / "raw").glob("*.md"))
    reg = (root / "index" / "source-registry.md").read_text(encoding="utf-8")
    log = (root / "index" / "log.md").read_text(encoding="utf-8")
    print(f"{'clipping':40} {'summary':8} {'registry':8} {'log':5}")
    for r in raws:
        stem = r.stem
        print(f"{stem:40} {'yes' if _summary_exists_for(root, stem) else 'NO':8} "
              f"{'yes' if f'[[{stem}]]' in reg else 'NO':8} "
              f"{'yes' if stem in log else 'NO':5}")
    return 0


def _load_taxonomy_subdomains(campaign: Path, root: Path) -> set[str]:
    """Load allowed subdomains.

    Strict: campaign/taxonomy.yaml must exist for real campaigns.
    Fallback to payload template only when campaign file is genuinely absent (tests/check).
    Callers that require a frozen campaign (cmd_classify) should check campaign file existence first.
    """
    # Campaign-resolved path is passed already resolved (root/campaign when relative)
    txt = None
    if campaign.is_absolute():
        cand = campaign / "taxonomy.yaml" if campaign.is_dir() else campaign
        # if campaign is taxonomy.yaml itself or dir containing it
        if cand.is_dir():
            cand = cand / "taxonomy.yaml"
        if cand.exists():
            txt = cand.read_text(encoding="utf-8")
        elif (campaign / "taxonomy.yaml").exists():
            txt = (campaign / "taxonomy.yaml").read_text(encoding="utf-8")
    else:
        # campaign is vault-relative; caller should have resolved, but handle both
        for p in [root / campaign / "taxonomy.yaml", campaign / "taxonomy.yaml", payload_root() / "templates" / "classification" / "taxonomy.yaml"]:
            if p.exists():
                txt = p.read_text(encoding="utf-8")
                break
    # Fallback for tests: try payload directly if still none
    if txt is None:
        p = payload_root() / "templates" / "classification" / "taxonomy.yaml"
        if p.exists():
            txt = p.read_text(encoding="utf-8")
    if txt is None:
        return set()
    subs = set()
    for m in re.finditer(r"^\s{2}(\w+):\n", txt, flags=re.MULTILINE):
        name = m.group(1)
        if name not in ("subdomains", "version", "campaign"):
            subs.add(name)
    return subs


def cmd_classify(root: Path, *, campaign: Path, store: Path, dry_run: bool = False) -> int:
    """Closed-vocabulary validator: rejects primary/secondary not in taxonomy, patches frontmatter/ledger.

    Reads store/*.judge.json produced by scripts/classify/judge.py, validates against
    taxonomy.yaml, and on success patches the store md frontmatter with domains/doc_decision
    and appends a ledger event. Pure stdlib — no LLM call.
    """
    # Resolve campaign before taxonomy load (I3)
    campaign_resolved = (root / campaign) if not campaign.is_absolute() else campaign
    # Strict: real campaign must have its own taxonomy.yaml; fallback only for tests where campaign is dummy
    campaign_tax = campaign_resolved / "taxonomy.yaml" if campaign_resolved.is_dir() else campaign_resolved
    if campaign_resolved.is_dir() and not campaign_tax.exists():
        # Allow fallback only when no store exists yet (tests) — otherwise fail closed (C5)
        store_path_check = (root / store) if not store.is_absolute() else store
        if store_path_check.exists() and list(store_path_check.rglob("*.judge.json")):
            print(f"vault classify: no taxonomy found at {campaign_tax} — run questionnaire and freeze taxonomy first", file=sys.stderr)
            return 1
    allowed = _load_taxonomy_subdomains(campaign_resolved if campaign_resolved.exists() else campaign, root)
    if not allowed:
        print(f"vault classify: no taxonomy found (looked in {campaign_resolved}/taxonomy.yaml and payload template)", file=sys.stderr)
        return 1
    allowed_buckets = {"SURE", "NEEDS_HUMAN_VALIDATION", "I_GUESSED"}
    allowed_relations = {"none", "comparison", "relationship", "progression"}
    # Resolve store path relative to vault root if needed
    store_path = (root / store) if not store.is_absolute() else store
    if not store_path.exists():
        print(f"vault classify: store not found: {store_path}", file=sys.stderr)
        return 1
    judge_files = list(store_path.rglob("*.judge.json"))
    if not judge_files:
        print(f"vault classify: no judge outputs in {store_path} (run scripts/classify/judge.py first)", file=sys.stderr)
        return 1

    # Ledger path per backbone: campaigns/<campaign>/ledger.jsonl (or store-adjacent)
    ledger_path = campaign_resolved / "ledger.jsonl" if campaign_resolved.is_dir() else campaign_resolved.parent / "ledger.jsonl"
    # Load existing ledger for idempotency (I2)
    existing: set[tuple] = set()
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
                existing.add((ev.get("doc_id"), ev.get("primary")))
            except Exception:
                pass
    if dry_run:
        print(f"vault classify: dry-run — {len(judge_files)} judge files, allowed={sorted(allowed)}")
    failures = 0
    for jf in judge_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"vault classify: bad JSON {jf}: {e}", file=sys.stderr)
            failures += 1
            continue
        # Reject numeric confidence contamination (C4)
        if "confidence" in data and isinstance(data.get("confidence"), (int, float)):
            print(f"vault classify: {jf.name}: numeric confidence {data['confidence']} rejected — use confidence_bucket", file=sys.stderr)
            failures += 1
            continue
        primary = data.get("primary_subdomain", "")
        secondary = data.get("secondary_subdomains", [])
        bucket = data.get("confidence_bucket", "")
        relation = data.get("relation_type", "none")
        reasoning = data.get("reasoning_brief", "")
        # Strict bucket/relation/reasoning validation (C4)
        if bucket not in allowed_buckets:
            print(f"vault classify: {jf.name}: confidence_bucket '{bucket}' not in {sorted(allowed_buckets)} — rejected", file=sys.stderr)
            failures += 1
            continue
        if relation not in allowed_relations:
            print(f"vault classify: {jf.name}: relation_type '{relation}' not in {sorted(allowed_relations)} — rejected", file=sys.stderr)
            failures += 1
            continue
        if not reasoning or not reasoning.strip():
            print(f"vault classify: {jf.name}: reasoning_brief missing or empty — rejected", file=sys.stderr)
            failures += 1
            continue
        if primary not in allowed:
            print(f"vault classify: {jf.name}: primary '{primary}' not in taxonomy {sorted(allowed)} — rejected", file=sys.stderr)
            failures += 1
            continue
        for s in secondary:
            if s not in allowed:
                print(f"vault classify: {jf.name}: secondary '{s}' not in taxonomy", file=sys.stderr)
                failures += 1
                break
        else:
            base = jf.name[:-len(".judge.json")]
            sibling = jf.parent / f"{base}.md"
            # Idempotency: skip if already ledgered with same primary (I2)
            doc_id = sibling.stem if sibling.exists() else jf.stem.replace(".judge", "")
            if (doc_id, primary) in existing:
                print(f"vault classify: {jf.name} -> {primary} [{bucket}] (already ledgered, skipping)")
                continue
            if sibling.exists() and not dry_run:
                txt = sibling.read_text(encoding="utf-8")
                fm, body = parse_frontmatter(txt)
                fm["domains"] = [primary] + secondary
                fm["doc_decision"] = primary
                fm["decided_by"] = "model"
                fm_lines = ["---"]
                for k, v in fm.items():
                    if isinstance(v, list):
                        fm_lines.append(f"{k}:")
                        for item in v:
                            fm_lines.append(f"  - {item}")
                    else:
                        fm_lines.append(f'{k}: "{v}"' if isinstance(v, str) and " " in v else f"{k}: {v}")
                fm_lines.append("---")
                new_text = "\n".join(fm_lines) + "\n\n" + body
                tmp = sibling.with_suffix(sibling.suffix + ".tmp")
                tmp.write_text(new_text, encoding="utf-8")
                tmp.rename(sibling)
            if not dry_run:
                ledger_path.parent.mkdir(parents=True, exist_ok=True)
                event = {
                    "doc_id": doc_id,
                    "stage": "classify",
                    "status": "classified",
                    "primary": primary,
                    "secondary": secondary,
                    "relation_type": relation,
                    "confidence_bucket": bucket,
                    "method": "model",
                    "reasoning_brief": reasoning,
                    "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                }
                with ledger_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")
                existing.add((doc_id, primary))
            print(f"vault classify: {jf.name} -> {primary} [{bucket}]")
    if failures:
        print(f"vault classify: {failures} file(s) rejected (closed vocabulary)", file=sys.stderr)
        return 1
    print(f"vault classify: {len(judge_files) - failures} classified, ledger {ledger_path}")
    return 0
