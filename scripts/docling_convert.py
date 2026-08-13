#!/usr/bin/env python3
"""Docling conversion module: docling-serve HTTP client + large-PDF splitting.

DoclingClient talks to a docling-serve-compatible API:
  POST {url}/v1/convert/file   multipart upload; sync JSON or {"task_id": ...}
  GET  {url}/v1/status/poll/{task_id}
  GET  {url}/v1/result/{task_id}

PDFs larger than `split_threshold` pages are split into `chunk_pages`-page
PDFs in a temp dir, converted one by one, and the markdown is concatenated
in order.
"""
from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
import requests


@dataclass(frozen=True)
class _PollSettings:
    """Bundles the timeout/retry/poll Data Clump."""
    timeout: float = 300.0
    max_retries: int = 5
    retry_delay: float = 1.0
    poll_interval: float = 2.0


class DoclingClient:
    def __init__(self, base_url: str, timeout: float = 300.0,
                 max_retries: int = 5, retry_delay: float = 1.0,
                 poll_interval: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self._settings = _PollSettings(
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            poll_interval=poll_interval,
        )
        # Public attributes kept for API compatibility.
        self.timeout = self._settings.timeout
        self.max_retries = self._settings.max_retries
        self.retry_delay = self._settings.retry_delay
        self.poll_interval = self._settings.poll_interval

    def convert_file(self, path: Path) -> str:
        """Convert one file via the docling API; returns markdown."""
        path = Path(path)
        data = self._post_with_retries(path)
        if "task_id" in data:
            data = self._wait_for_result(data["task_id"])
        try:
            return data["document"]["md_content"]
        except KeyError:
            raise RuntimeError(f"docling response missing document.md_content: "
                               f"{list(data.keys())}")

    # -- internal HTTP helpers: hide url construction + timeout/raise duplication --

    def _get(self, path: str) -> dict:
        resp = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, files: dict) -> dict:
        resp = requests.post(f"{self.base_url}{path}", files=files,
                             timeout=self.timeout)
        if resp.status_code >= 500:
            raise RuntimeError(f"docling {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    def _post_with_retries(self, path: Path) -> dict:
        last_err = None
        for attempt in range(self.max_retries):
            try:
                with open(path, "rb") as fh:
                    return self._post("/v1/convert/file",
                                      files={"files": (path.name, fh)})
            except Exception as e:  # noqa: BLE001 - retry any transient failure
                last_err = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
        raise RuntimeError(f"docling convert failed after {self.max_retries} "
                           f"attempts for {path.name}: {last_err}")

    def _wait_for_result(self, task_id: str) -> dict:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            status = self._get(f"/v1/status/poll/{task_id}").get("task_status")
            if status == "success":
                return self._get(f"/v1/result/{task_id}")
            if status == "failure":
                raise RuntimeError(f"docling task {task_id} failed")
            time.sleep(self.poll_interval)
        raise RuntimeError(f"docling task {task_id} timed out")


def pdf_page_count(path: Path) -> int:
    with pdfium.PdfDocument(str(path)) as pdf:
        return len(pdf)


def split_pdf(path: Path, chunk_pages: int, out_dir: Path) -> list[Path]:
    """Split path into <=chunk_pages PDFs in out_dir; return chunks in order."""
    path, out_dir = Path(path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks = []
    with pdfium.PdfDocument(str(path)) as src:
        total = len(src)
        for start in range(0, total, chunk_pages):
            end = min(start + chunk_pages, total)
            chunk = pdfium.PdfDocument.new()
            chunk.import_pages(src, list(range(start, end)))
            out = out_dir / f"{path.stem}_p{start + 1}-{end}.pdf"
            chunk.save(str(out))
            chunk.close()
            chunks.append(out)
    return chunks


def convert(path: Path, client: DoclingClient, config: dict) -> str:
    """Convert a file through docling; large PDFs are split and recombined."""
    path = Path(path)
    threshold = config.get("split_threshold", 100)
    chunk_pages = config.get("chunk_pages", 50)
    if path.suffix.lower() == ".pdf" and pdf_page_count(path) > threshold:
        with tempfile.TemporaryDirectory(prefix="docling_chunks_") as td:
            chunks = split_pdf(path, chunk_pages, Path(td))
            return "\n\n".join(client.convert_file(c) for c in chunks)
    return client.convert_file(path)
