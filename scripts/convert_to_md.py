#!/usr/bin/env python3
"""Batch-convert a vault's raw/ tree to markdown in raw_md/.

Usage:
    python scripts/convert_to_md.py <vault_root> [--force] [--config PATH]

Routing (one converter per extension, no cross-library retry):
    .pdf .docx .pptx     -> docling-serve HTTP API (see docling_convert.py)
    .html .htm           -> pandoc  (pandoc -f html -t gfm --wrap=none)
    .txt                 -> markitdown
    .msg                 -> extract_msg
    .eml                 -> stdlib email
    everything else      -> skipped

Two passes: textual formats first (they feed the persistent Hebrew
dictionary), then PDFs (OCR output is checked against that dictionary but
never feeds it). Hebrew reversal fixing lives in hebrew_fix.py.

Config: <vault>/convert_config.json (see DEFAULT_CONFIG for all keys).
"""
from __future__ import annotations

import argparse
import email
import email.utils
import hashlib
import json
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docling_convert
import hebrew_fix

DOCLING_EXTS = {".pdf", ".docx", ".pptx"}
ROUTING = {**{e: "docling" for e in DOCLING_EXTS},
           ".txt": "markitdown", ".msg": "msg", ".eml": "email",
           ".html": "pandoc", ".htm": "pandoc"}

DEFAULT_CONFIG = {
    "docling": {"url": "http://localhost:5001", "workers": 1,
                "timeout": 300, "retry_delay": 1.0},
    "pdf": {"split_threshold": 100, "chunk_pages": 50},
    "hebrew": {"dict_path": "data/hebrew_dict.json", "ambiguity_margin": 2.0},
}

RECENT_WINDOW = timedelta(hours=24)


# ---------------------------------------------------------------- config

def load_config(vault_root: Path, config_path: Path | None = None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    path = Path(config_path) if config_path else Path(vault_root) / "convert_config.json"
    if path.exists():
        user = json.loads(path.read_text(encoding="utf-8"))
        for section, values in user.items():
            if isinstance(values, dict) and isinstance(cfg.get(section), dict):
                cfg[section].update(values)
            else:
                cfg[section] = values
    return cfg


# ------------------------------------------------------- frontmatter/meta

def build_frontmatter(title: str, created: datetime | None,
                      original_file: str, original_ext: str,
                      hebrew_fixed: bool) -> str:
    meta = {"title": title}
    if created is not None:
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > RECENT_WINDOW:
            # Store as datetime so yaml emits a plain timestamp (no quotes around isoformat string)
            meta["created"] = created
    meta["original_file"] = original_file
    meta["original_ext"] = original_ext
    if hebrew_fixed:
        meta["hebrew_fixed"] = True
    return "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n"


def _first_heading(md: str) -> str | None:
    for line in md.splitlines():
        m = re.match(r"^#+\s+(.+)", line)
        if m:
            return m.group(1).strip()
    return None


def _parse_pdf_date(raw: str) -> datetime | None:
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", raw or "")
    if not m:
        return None
    return datetime(*map(int, m.groups()), tzinfo=timezone.utc)


def extract_metadata(path: Path) -> tuple[str | None, datetime | None]:
    """Best-effort (title, created) from embedded doc metadata."""
    ext = path.suffix.lower()
    try:
        if ext == ".docx":
            import docx
            props = docx.Document(str(path)).core_properties
            return props.title or None, props.created
        if ext == ".pptx":
            import pptx
            props = pptx.Presentation(str(path)).core_properties
            return props.title or None, props.created
        if ext == ".html" or ext == ".htm":
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(path.read_text(encoding="utf-8",
                                                errors="replace"), "html.parser")
            return (soup.title.string.strip() if soup.title and soup.title.string
                    else None), None
        if ext == ".pdf":
            import pypdfium2 as pdfium
            with pdfium.PdfDocument(str(path)) as pdf:
                meta = pdf.get_metadata_dict()
            return meta.get("Title") or None, _parse_pdf_date(meta.get("CreationDate"))
    except Exception:  # noqa: BLE001 - metadata is best-effort
        pass
    return None, None


def resolve_title(meta_title: str | None, md: str, path: Path) -> str:
    return meta_title or _first_heading(md) or path.stem


def resolve_created(meta_created: datetime | None, path: Path) -> datetime | None:
    if meta_created is not None:
        return meta_created
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


# ------------------------------------------------------------ converters

def convert_txt(path: Path) -> str:
    try:
        from markitdown import MarkItDown
        return MarkItDown().convert(str(path)).text_content
    except ImportError:
        return Path(path).read_text(encoding="utf-8", errors="replace")


def convert_html(path: Path) -> str:
    """Convert HTML/HTM via pandoc (required dependency — fails if missing)."""
    import shutil
    import subprocess

    if shutil.which("pandoc") is None:
        raise RuntimeError(
            "pandoc not found: install pandoc (https://pandoc.org/installing.html) "
            "— required for .html/.htm conversion"
        )
    result = subprocess.run(
        ["pandoc", "-f", "html", "-t", "gfm", "--wrap=none", str(path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed for {path.name}: {result.stderr.strip()[:500]}")
    return result.stdout


def _email_md(subject, sender, to, date, body) -> str:
    header = [f"Subject: {subject or ''}", f"From: {sender or ''}",
              f"To: {to or ''}", f"Date: {date or ''}"]
    return "\n".join(header) + "\n\n" + (body or "")


def convert_eml(path: Path):
    """Return (markdown, meta, attachments[(filename, bytes)])."""
    with open(path, "rb") as fh:
        msg = email.message_from_bytes(fh.read(), policy=email.policy.default)
    subject = str(msg.get("Subject") or "")
    date_raw = str(msg.get("Date") or "")
    try:
        created = email.utils.parsedate_to_datetime(date_raw) if date_raw else None
    except (TypeError, ValueError):
        created = None
    body = msg.get_body(("plain",))
    body_text = body.get_content() if body else ""
    attachments = [(a.get_filename() or "attachment", a.get_payload(decode=True) or b"")
                   for a in msg.iter_attachments()]
    md = _email_md(subject, msg.get("From"), msg.get("To"), date_raw, body_text)
    return md, (subject, created), attachments


def convert_msg(path: Path):
    """Return (markdown, meta, attachments[(filename, bytes)])."""
    import extract_msg
    msg = extract_msg.Message(str(path))
    created = None
    if msg.date:
        try:
            created = email.utils.parsedate_to_datetime(msg.date)
        except (TypeError, ValueError):
            pass
    md = _email_md(msg.subject, msg.sender, msg.to, msg.date, msg.body)
    attachments = [(a.longFilename or a.shortFilename or "attachment", a.data or b"")
                   for a in msg.attachments]
    return md, (msg.subject, created), attachments


def dispatch_convert(path: Path, client: docling_convert.DoclingClient,
                     cfg: dict, routing_ext: str | None = None):
    """Convert one file per the routing table.
    Returns (markdown, (meta_title, meta_created), attachments, converter_name).
    Raises on converter failure (caller records it; no cross-library retry)."""
    ext = (routing_ext if routing_ext is not None else path.suffix).lower()
    kind = ROUTING.get(ext)
    if kind is None:
        raise ValueError(f"unsupported extension: {ext}")
    if kind == "docling":
        pdf_cfg = {"split_threshold": cfg["pdf"]["split_threshold"],
                   "chunk_pages": cfg["pdf"]["chunk_pages"]}
        return (docling_convert.convert(path, client, pdf_cfg),
                extract_metadata(path), [], "docling")
    if kind == "pandoc":
        return convert_html(path), extract_metadata(path), [], "pandoc"
    if kind == "markitdown":
        return convert_txt(path), (None, None), [], "markitdown"
    if kind == "email":
        md, meta, atts = convert_eml(path)
        return md, meta, atts, "email"
    md, meta, atts = convert_msg(path)
    return md, meta, atts, "msg"


# -------------------------------------------------------------- pipeline

def should_skip(src: Path, dst: Path, force: bool) -> bool:
    if force or not dst.exists():
        return False
    return dst.stat().st_mtime >= src.stat().st_mtime


def _out_path(raw_root: Path, out_root: Path, src: Path) -> Path:
    rel = src.relative_to(raw_root)
    return (out_root / rel).with_suffix(".md")


def _file_hash(path: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def run(vault_root: Path, force: bool = False,
        config_path: Path | None = None) -> dict:
    vault_root = Path(vault_root)
    cfg = load_config(vault_root, config_path)
    raw_root = vault_root / "raw"
    out_root = vault_root / "raw_md"
    out_root.mkdir(parents=True, exist_ok=True)

    client = docling_convert.DoclingClient(
        cfg["docling"]["url"], timeout=cfg["docling"]["timeout"],
        retry_delay=cfg["docling"].get("retry_delay", 1.0))
    margin = cfg["hebrew"]["ambiguity_margin"]
    dict_path = vault_root / cfg["hebrew"]["dict_path"]

    all_files = sorted(p for p in raw_root.rglob("*") if p.is_file())
    report: dict = {"files": {}}

    seen: dict[str, str] = {}  # hash -> canonical rel posix
    _att_md_by_hash: dict[str, str] = {}  # attachment hash -> md relative link
    _att_rel_by_hash: dict[str, str] = {}  # attachment hash -> canonical att_rel
    todo, results = [], {}
    for src in all_files:
        rel = src.relative_to(raw_root).as_posix()
        ext = src.suffix.lower()
        if ext not in ROUTING:
            report["files"][rel] = {"status": "skipped",
                                    "reason": f"unsupported extension {ext}"}
            continue
        # Content-hash deduplication (before skip/force)
        file_hash = _file_hash(src)
        if file_hash is not None:
            if file_hash in seen:
                report["files"][rel] = {"status": "duplicate", "duplicate_of": seen[file_hash], "hash": file_hash}
                continue
            seen[file_hash] = rel
        dst = _out_path(raw_root, out_root, src)
        if should_skip(src, dst, force):
            report["files"][rel] = {"status": "skipped", "reason": "up to date"}
            continue
        todo.append(src)

    def convert_one(src, routing_ext: str | None = None):
        try:
            md, meta, atts, converter = dispatch_convert(src, client, cfg, routing_ext=routing_ext)
            return src, {"md": md, "meta": meta, "attachments": atts,
                         "converter": converter}
        except Exception as e:  # noqa: BLE001 - recorded, never retried elsewhere
            return src, {"error": str(e)}

    workers = max(1, int(cfg["docling"].get("workers", 1)))

    # Pass 1: textual formats (their converted text feeds the dictionary).
    pass1 = [s for s in todo if s.suffix.lower() != ".pdf"]
    pass2 = [s for s in todo if s.suffix.lower() == ".pdf"]

    def convert_batch(files, use_workers: bool = True):
        if not files:
            return
        if not use_workers:
            for src in files:
                src_key, res = convert_one(src)
                results[src_key] = res
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for src, res in pool.map(convert_one, files):
                    results[src] = res

    convert_batch(pass1, use_workers=False)

    good_texts = [r["md"] for r in results.values() if "md" in r]
    dictionary = hebrew_fix.build_dictionary(good_texts, dict_path)

    convert_batch(pass2, use_workers=True)

    def write_output(src: Path, res: dict, dst: Path | None = None,
                     rel_key: str | None = None,
                     original_name: str | None = None):
        dst = dst or _out_path(raw_root, out_root, src)
        rel = rel_key or src.relative_to(raw_root).as_posix()
        if "error" in res:
            report["files"][rel] = {"status": "failed", "error": res["error"]}
            return None
        md = res["md"]
        fixed, fix_report = hebrew_fix.fix_text(md, dictionary, margin=margin)
        meta_title, meta_created = res["meta"]
        shown = original_name or src.name
        title = resolve_title(meta_title, fixed, Path(shown))
        created = resolve_created(meta_created, src)
        fm = build_frontmatter(title, created, shown, Path(shown).suffix.lower(),
                               fix_report["hebrew_fixed"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(fm + "\n" + fixed, encoding="utf-8")
        report["files"][rel] = {
            "status": "converted", "converter": res["converter"],
            "hebrew_fixed": fix_report["hebrew_fixed"],
            "ambiguous": fix_report["ambiguous"]}
        return fixed

    for src in todo:
        res = results[src]
        fixed = write_output(src, res)
        if fixed is None:
            continue
        # Email attachments: convert into <stem>_attachments/ and link them.
        # Attachments are content-deduped against the full dataset (raw files + prior attachments).
        if res.get("attachments"):
            converted_links = []
            seen_att_dsts: set[str] = set()
            for att_name, att_bytes in res["attachments"]:
                att_rel_base = f"{src.relative_to(raw_root).as_posix()}#{att_name}"
                att_rel = att_rel_base
                # Ensure unique att_rel key if duplicate attachment names in same email
                counter_rel = 1
                while att_rel in report["files"]:
                    counter_rel += 1
                    att_rel = f"{att_rel_base}_{counter_rel}"

                # Content-hash dedup against raw files and prior attachments
                att_hash = hashlib.sha256(att_bytes).hexdigest()
                if att_hash in seen:
                    canonical = seen[att_hash]
                    report["files"][att_rel] = {
                        "status": "duplicate",
                        "duplicate_of": canonical,
                        "hash": att_hash,
                    }
                    # Link to canonical markdown
                    if att_hash in _att_md_by_hash:
                        link_target = _att_md_by_hash[att_hash]
                    elif "#" in canonical and canonical in _att_rel_by_hash.values():
                        # fallback lookup via canonical rel -> md
                        # reverse lookup
                        for h, rel in _att_rel_by_hash.items():
                            if rel == canonical and h in _att_md_by_hash:
                                link_target = _att_md_by_hash[h]
                                break
                        else:
                            link_target = _att_md_by_hash.get(att_hash, str(Path(canonical.split("#")[0]).with_suffix(".md").as_posix()))
                    else:
                        # raw file canonical: mirrored .md path
                        link_target = str(Path(canonical.split("#")[0]).with_suffix(".md").as_posix())
                    converted_links.append(f"- [{att_name}]({link_target}) (duplicate of {canonical})")
                    continue

                att_dst = (out_root / src.relative_to(raw_root).parent
                           / f"{src.stem}_attachments"
                           / Path(att_name).with_suffix(".md").name)
                # Handle name collisions for output path
                if att_dst.exists() or att_dst.as_posix() in seen_att_dsts:
                    stem = Path(att_name).stem or "attachment"
                    c = 1
                    candidate = att_dst
                    while candidate.exists() or candidate.as_posix() in seen_att_dsts:
                        candidate = att_dst.parent / f"{stem}_{c}.md"
                        c += 1
                    att_dst = candidate
                seen_att_dsts.add(att_dst.as_posix())
                # Use original extension for routing, not temp file suffix ambiguity
                routing_ext = Path(att_name).suffix.lower()
                with tempfile.NamedTemporaryFile(
                        suffix=Path(att_name).suffix, delete=False) as tmp:
                    tmp.write(att_bytes)
                    tmp_path = Path(tmp.name)
                try:
                    _, att_result = convert_one(tmp_path, routing_ext=routing_ext)
                    if "error" in att_result:
                        report["files"][att_rel] = {"status": "failed",
                                                     "error": att_result["error"]}
                    else:
                        write_output(tmp_path, att_result, dst=att_dst,
                                     rel_key=att_rel, original_name=att_name)
                        # Remember this attachment's hash so later attachments dedup against it
                        if att_hash not in seen:
                            seen[att_hash] = att_rel
                            _att_rel_by_hash[att_hash] = att_rel
                        rel_link = att_dst.relative_to(out_root).as_posix()
                        _att_md_by_hash[att_hash] = rel_link
                        # Also track via canonical rel mapping for raw-file-hash dedup
                        if att_hash not in _att_rel_by_hash:
                            _att_rel_by_hash[att_hash] = att_rel
                        converted_links.append(f"- [{att_name}]({rel_link})")
                finally:
                    tmp_path.unlink(missing_ok=True)
            if converted_links:
                parent_dst = _out_path(raw_root, out_root, src)
                with open(parent_dst, "a", encoding="utf-8") as fh:
                    fh.write("\n\n## Attachments\n" + "\n".join(converted_links) + "\n")

    report_path = out_root / "conversion_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    counts = {}
    for entry in report["files"].values():
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    print(f"converted: {counts.get('converted', 0)}  "
          f"skipped: {counts.get('skipped', 0)}  "
          f"failed: {counts.get('failed', 0)}  "
          f"duplicate: {counts.get('duplicate', 0)}  "
          f"-> {report_path}")
    # Detailed dedup log (1:1 output breaks for duplicates — see report duplicate_of)
    dups = [(rel, info["duplicate_of"], info.get("hash", "")[:8])
            for rel, info in report["files"].items() if info.get("status") == "duplicate"]
    if dups:
        print(f"dedup: {len(dups)} duplicate(s) suppressed (no raw_md output, see duplicate_of):")
        for rel, canonical, h in sorted(dups):
            print(f"  duplicate: {rel} -> {canonical}  hash:{h}")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("vault_root", type=Path)
    ap.add_argument("--force", action="store_true",
                    help="reconvert even up-to-date outputs")
    ap.add_argument("--config", type=Path, default=None,
                    help="config file (default: <vault>/convert_config.json)")
    args = ap.parse_args(argv)
    run(args.vault_root, force=args.force, config_path=args.config)


if __name__ == "__main__":
    main()
