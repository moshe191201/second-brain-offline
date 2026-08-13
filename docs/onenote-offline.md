# OneNote offline conversion

Headless local OneNote -> Markdown, no OneNote/COM/Graph, no human clicks.

## Requirement: .NET SDK 8.0+

**Why:** local `.one` / `.onepkg` / `.onetoc2` are parsed offline by `OfficeIMO.OneNote` 3.2.2
(pure managed parser for MS-ONESTORE + MS-FSSHTTPB + Cabinet `.onepkg`, see
`Docs/officeimo.onenote.current-state.md` in OfficeIMO). The helper
`scripts/OneNoteOffline` is a .NET 8 console app that projects pages to Markdown
via `OfficeIMO.OneNote.Markdown` and extracts embedded files/media as raw
payloads. The Python wrapper `scripts/onenote_conversion.py` then routes those
payloads through the existing vault converters.

**Install (Windows):**
```powershell
winget install Microsoft.DotNet.SDK.8
dotnet --version  # should show 8.x
```
Or download from https://aka.ms/dotnet-download (SDK 8.0.x).

**Build (once, auto-built on first run if missing):**
```powershell
dotnet build scripts/OneNoteOffline -c Release
# or let convert_to_md auto-build it
```

After first build the DLL at `scripts/OneNoteOffline/bin/Release/net8.0/OneNoteOffline.dll`
is runnable with `dotnet <dll>`; a self-contained publish (`dotnet publish -c Release --self-contained`)
removes the SDK requirement for deployment.

If .NET is missing, `convert_to_md.py` fails OneNote files with
`.NET SDK 8.0+ required` and still converts all other formats.

## What is converted

| Source | Handler |
|---|---|
| `.one` (single section) | `OneNoteSectionReader` -> one `*.md` per page |
| `.onetoc2` (notebook dir) | `OneNoteNotebookReader` -> hierarchy `SectionGroup/Section/Page.md` |
| `.onepkg` (Cabinet export) | `OneNotePackageReader` -> same hierarchy |
| Directory containing `.onetoc2` | treated as notebook |

Each page Markdown is via `OneNoteMarkdownProjection.ToMarkdown(page, AssetUriResolver)` with:
- frontmatter (`title`, `created`, `lastModified`)
- `assets/` folder per notebook (images, embedded files, recordings)

## Attachment routing (via `onenote_conversion.py`)

```
.docx/.doc/.pdf/.ppt/.pptx/.xlsx/.xls -> docling (docling-serve, same as .pdf in convert_to_md)
.html/.htm/.mht/.mhtml                 -> pandoc
.txt/.csv                             -> markitdown
.png/.jpg/.gif/.bmp/.tiff/.svg/.emf   -> kept as asset, linked inline
.zip/.bin/unknown                     -> kept as raw asset link
```

Docling for `.docx` is exactly what you asked for; every other attachment type
routes to the best available lib. If `docling-serve` is not running, attachments
are kept as raw links (no 300s timeout - quick probe with 1s).

## Usage

```powershell
# Single file / notebook (Python wrapper)
python scripts/onenote_conversion.py "C:\path\note.onepkg" "C:\out"

# Via vault pipeline (handles .one/.onepkg/.onetoc2 in raw/ automatically)
python scripts/convert_to_md.py "C:\path\to\vault" --force

# Direct .NET helper (no Python)
dotnet scripts\OneNoteOffline\bin\Release\net8.0\OneNoteOffline.dll "C:\path\note.onepkg" "C:\out"
```

Pipeline notes:
- Notebook dirs: if `raw/MyNotebook/` contains `Open Notebook.onetoc2`, its inner `.one` files are skipped individually and handled via the `.onetoc2`.
- Deduplication: content-hash dedup against `raw/` + prior attachments (same as email attachments in `convert_to_md.py`).
- Hebrew fix: OneNote pages feed the Hebrew dictionary and are fixed post-hoc (same as PDFs).
