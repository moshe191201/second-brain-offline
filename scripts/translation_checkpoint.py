"""Chunk-level checkpoint store for stage 5 translation.

A 100-200 page PDF becomes ~67 chunks at chunk_chars=6000, translated strictly
sequentially with one LLM call each. The document-level content-addressed store
(data/translations/<sha>/) only skips work at document granularity, so a failure
in chunk 43 threw away chunks 1-42. At 95% per-chunk reliability a 67-chunk
document survives ~3% of the time.

This module is the partial-credit layer: every chunk that translates cleanly is
written to data/translations/chunks/<key[:2]>/<key>.json, so a rerun resumes
instead of restarting.

The key covers every input that determines a chunk's translation, including
prev_tail -- chunk N is fed the tail of chunk N-1's translation, so retranslating
N-1 must invalidate N.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

# Bump when the payload shape or the set of key inputs changes, so old
# checkpoints are never replayed against new semantics.
CHECKPOINT_VERSION = 1


def chunk_checkpoint_key(chunk_text: str, section_path: str, prev_tail: str,
                         glossary_fingerprint: str, model: str,
                         mock: bool, no_mask: bool) -> str:
    """Content address for one chunk translation. Stable across runs."""
    h = hashlib.sha256()
    for part in (
        str(CHECKPOINT_VERSION),
        chunk_text,
        section_path,
        prev_tail,
        glossary_fingerprint,
        model,
        "mock" if mock else "live",
        "nomask" if no_mask else "mask",
    ):
        # Length-prefix each field so concatenation is unambiguous.
        h.update(str(len(part)).encode())
        h.update(b"\x00")
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def chunk_checkpoint_path(out_root: Path, key: str) -> Path:
    """Sharded path for one chunk checkpoint, mirroring the document store."""
    return Path(out_root) / "chunks" / key[:2] / f"{key}.json"


def load_chunk_checkpoint(out_root: Path, key: str) -> dict | None:
    """Return a stored chunk result, or None on miss.

    A corrupt or unreadable checkpoint is a miss, never an error: the whole
    point of this store is to make long runs more survivable, so a bad file
    must cost one retranslated chunk, not the document.
    """
    p = chunk_checkpoint_path(out_root, key)
    try:
        with open(p, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def save_chunk_checkpoint(out_root: Path, key: str, payload: dict) -> None:
    """Write a chunk result atomically (temp file + os.replace)."""
    p = chunk_checkpoint_path(out_root, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(p.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_name, p)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
