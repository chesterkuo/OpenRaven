# PRD Gap Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 4 PRD gap features — query mode selector, image/vision ingestion, Notion/Obsidian import, and onboarding "first surprise".

**Architecture:** All 4 features extend existing patterns. Query mode is a pure UI change. Image ingestion adds a new parser path using the existing OpenAI-compat Gemini client. Zip import adds a new ingestion module that feeds into the existing pipeline. Onboarding enhances the existing discovery analyzer and adds a UI banner.

**Tech Stack:** React 19 + TypeScript (Bun), Python 3.12 + FastAPI, Gemini multimodal API (OpenAI-compat), zipfile (stdlib)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven-ui/src/pages/AskPage.tsx` | Modify | Add mode selector dropdown + OnboardingBanner |
| `openraven-ui/src/components/FileUploader.tsx` | Modify | Add image + zip formats |
| `openraven-ui/src/pages/IngestPage.tsx` | Modify | Add import help text |
| `openraven-ui/src/components/OnboardingBanner.tsx` | Create | Onboarding notification banner |
| `openraven/src/openraven/ingestion/parser.py` | Modify | Add `parse_image()` |
| `openraven/src/openraven/ingestion/importers.py` | Create | Zip import (Notion/Obsidian) |
| `openraven/src/openraven/pipeline.py` | Modify | Add image + zip extensions, route accordingly |
| `openraven/src/openraven/discovery/analyzer.py` | Modify | Richer insights with entity types + clusters |
| `openraven/src/openraven/graph/rag.py` | Modify | Add `get_detailed_stats()` |
| `openraven/tests/test_ingestion.py` | Modify | Add image parser + zip importer tests |
| `openraven/tests/test_discovery.py` | Modify | Add enhanced analyzer tests |

---

## Task 1: Query Mode Selector in Ask UI

**Files:**
- Modify: `openraven-ui/src/pages/AskPage.tsx`

- [ ] **Step 1: Add mode state and dropdown to AskPage**

Replace the hardcoded mode in `AskPage.tsx`. Add a `mode` state and a `<select>` element in the form area:

Make the following surgical edits to `AskPage.tsx` (do NOT replace the full file):

**Edit 1:** After the existing imports (line 3), add the mode constant:
```tsx
const QUERY_MODES = [
  { value: "mix", label: "Mix", desc: "Specific + broad reasoning (recommended)" },
  { value: "local", label: "Local", desc: "Search specific entities" },
  { value: "global", label: "Global", desc: "Cross-document reasoning" },
  { value: "hybrid", label: "Hybrid", desc: "Local + global combined" },
  { value: "naive", label: "Keyword", desc: "Traditional vector search" },
  { value: "bypass", label: "Direct LLM", desc: "Skip knowledge base" },
] as const;
```

**Edit 2:** After `const [insights, setInsights] = useState<Insight[]>([]);` (line 13), add:
```tsx
  const [mode, setMode] = useState("mix");
```

**Edit 3:** On line 27, change the hardcoded mode:
```tsx
// FROM:
body: JSON.stringify({ question, mode: "mix" })
// TO:
body: JSON.stringify({ question, mode })
```

**Edit 4:** Replace the `<form>` tag (line 70) to add `items-end`:
```tsx
// FROM:
<form onSubmit={handleSubmit} className="flex gap-3 pt-4" style={{ borderTop: "1px solid var(--color-border)" }}>
// TO:
<form onSubmit={handleSubmit} className="flex gap-3 pt-4 items-end" style={{ borderTop: "1px solid var(--color-border)" }}>
```

**Edit 5:** Insert the mode selector dropdown before the `<input type="text"` (line 71):
```tsx
        <div className="flex flex-col gap-1">
          <label htmlFor="mode-select" className="text-xs" style={{ color: "var(--color-text-muted)" }}>Mode</label>
          <select
            id="mode-select"
            value={mode}
            onChange={e => setMode(e.target.value)}
            className="px-2 py-2.5 text-sm cursor-pointer"
            aria-label="Query mode"
            title={QUERY_MODES.find(m => m.value === mode)?.desc}
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          >
            {QUERY_MODES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
        </div>
```

- [ ] **Step 2: Verify the UI builds**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx bun run build 2>&1 | tail -5
```
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add openraven-ui/src/pages/AskPage.tsx
git commit -m "feat: add query mode selector to Ask page

Users can now choose from all 6 LightRAG query modes (mix, local,
global, hybrid, naive, bypass) via a dropdown in the Ask page.
Previously hardcoded to 'mix'."
```

---

## Task 2: Image/Vision Ingestion — Parser

**Files:**
- Modify: `openraven/src/openraven/ingestion/parser.py`
- Modify: `openraven/tests/test_ingestion.py`

- [ ] **Step 1: Write failing test for parse_image**

Add to the end of `openraven/tests/test_ingestion.py`:

```python
from unittest.mock import AsyncMock, patch


def test_parse_image_supported_extensions():
    """Image extensions should be recognized by the parser."""
    from openraven.ingestion.parser import IMAGE_EXTENSIONS
    assert ".png" in IMAGE_EXTENSIONS
    assert ".jpg" in IMAGE_EXTENSIONS
    assert ".jpeg" in IMAGE_EXTENSIONS
    assert ".webp" in IMAGE_EXTENSIONS
    assert ".heic" in IMAGE_EXTENSIONS


import pytest

@pytest.mark.asyncio
async def test_parse_image_returns_parsed_document(tmp_path: Path) -> None:
    """parse_image should call Gemini vision API and return ParsedDocument."""
    img = tmp_path / "diagram.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # minimal PNG header

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "A diagram showing system architecture with three microservices."

    with patch("openraven.ingestion.parser.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from openraven.ingestion.parser import parse_image
        result = await parse_image(img, api_key="test-key")

    assert isinstance(result, ParsedDocument)
    assert "microservices" in result.text
    assert result.format == "png"
    assert result.source_path == img


@pytest.mark.asyncio
async def test_parse_image_fallback_on_error(tmp_path: Path) -> None:
    """parse_image should return empty content on API failure, not crash."""
    img = tmp_path / "broken.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)  # minimal JPEG header

    with patch("openraven.ingestion.parser.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        mock_client_cls.return_value = mock_client

        from openraven.ingestion.parser import parse_image
        result = await parse_image(img, api_key="test-key")

    assert isinstance(result, ParsedDocument)
    assert result.text == ""
    assert result.char_count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_ingestion.py::test_parse_image_supported_extensions tests/test_ingestion.py::test_parse_image_returns_parsed_document tests/test_ingestion.py::test_parse_image_fallback_on_error -v 2>&1 | tail -10
```
Expected: FAIL — `IMAGE_EXTENSIONS` and `parse_image` not defined.

- [ ] **Step 3: Implement parse_image in parser.py**

Add to the end of `openraven/src/openraven/ingestion/parser.py`, and add `import openai` at the top (after existing imports):

```python
import base64
import logging

import openai

# ... (existing code stays unchanged) ...

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".heic", ".webp"}

_IMAGE_PROMPT = (
    "Describe this image comprehensively. Extract all visible text, labels, "
    "data points, diagrams, relationships, and key information. "
    "Format as structured text with sections if appropriate."
)


async def parse_image(
    file_path: Path,
    api_key: str = "",
    model: str = "gemini-2.5-flash",
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> ParsedDocument:
    """Parse an image file using Gemini vision API.

    Sends the image to a multimodal LLM and returns the extracted description
    as a ParsedDocument that can be fed into the normal pipeline.
    """
    logger = logging.getLogger(__name__)
    file_path = Path(file_path).resolve()
    suffix = file_path.suffix.lower().lstrip(".")

    try:
        image_data = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        mime_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "heic": "image/heic",
            "webp": "image/webp",
        }.get(suffix, "image/png")

        client = openai.AsyncOpenAI(api_key=api_key or "none", base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _IMAGE_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
                ],
            }],
        )
        text = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Vision API failed for {file_path}: {e}")
        text = ""

    return ParsedDocument(
        text=text,
        source_path=file_path,
        format=suffix,
        char_count=len(text),
    )
```

Note: The `import openai` should be added at the top of `parser.py` alongside the existing imports. The `import base64` and `import logging` can go at the top too.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_ingestion.py -v 2>&1 | tail -15
```
Expected: All tests PASS, including the 3 new image tests.

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/ingestion/parser.py openraven/tests/test_ingestion.py
git commit -m "feat: add image/vision ingestion via Gemini multimodal API

parse_image() sends images (PNG, JPEG, HEIC, WEBP) to Gemini vision
API and returns extracted text as a ParsedDocument. Gracefully falls
back to empty content on API failure."
```

---

## Task 3: Image/Vision — Pipeline Integration + UI

**Files:**
- Modify: `openraven/src/openraven/pipeline.py`
- Modify: `openraven-ui/src/components/FileUploader.tsx`

- [ ] **Step 1: Add image extensions to pipeline and route to parse_image**

In `openraven/src/openraven/pipeline.py`, make these changes:

Add import at the top (after existing parser imports):
```python
from openraven.ingestion.parser import IMAGE_EXTENSIONS, parse_image
```

Update `SUPPORTED_EXTENSIONS` (line 23):
```python
SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".html"} | IMAGE_EXTENSIONS
```

In the `add_files` method, Stage 1 loop (around line 117-128), replace the `parse_document` call with image-aware routing:

```python
        # Stage 1: Ingestion
        parsed_docs: list[ParsedDocument] = []
        for fp in files_to_process:
            try:
                fp_path = Path(fp) if not isinstance(fp, Path) else fp
                if fp_path.suffix.lower() in IMAGE_EXTENSIONS:
                    doc = await parse_image(
                        fp_path,
                        api_key=self.config.llm_api_key,
                        model=self.config.llm_model,
                        base_url=(
                            f"{self.config.ollama_base_url}/v1"
                            if self.config.llm_provider == "ollama"
                            else "https://generativelanguage.googleapis.com/v1beta/openai/"
                        ),
                    )
                else:
                    doc = parse_document(fp)
                parsed_docs.append(doc)
                self.store.upsert_file(FileRecord(
                    path=str(fp), hash=compute_file_hash(fp_path) if fp_path.exists() else "url",
                    format=doc.format, char_count=doc.char_count, status="ingested",
                ))
            except Exception as e:
                errors.append(f"Ingestion failed for {fp}: {e}")
                logger.error(f"Ingestion failed for {fp}", exc_info=True)
```

- [ ] **Step 2: Update FileUploader to accept images and zips**

In `openraven-ui/src/components/FileUploader.tsx`, update line 30 (display text):
```tsx
        PDF, DOCX, PPTX, XLSX, Markdown, TXT, Images (PNG/JPEG), or ZIP (Notion/Obsidian export)
```

Update line 40 (accept attribute):
```tsx
        <input type="file" multiple onChange={handleChange} disabled={disabled} className="hidden" accept=".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.png,.jpg,.jpeg,.heic,.webp,.zip" />
```

- [ ] **Step 3: Verify UI builds**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx bun run build 2>&1 | tail -5
```
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add openraven/src/openraven/pipeline.py openraven-ui/src/components/FileUploader.tsx
git commit -m "feat: integrate image ingestion into pipeline and UI

Pipeline now routes image files to parse_image() and accepts zip files.
FileUploader updated to accept PNG, JPEG, HEIC, WEBP, and ZIP formats."
```

---

## Task 4: Notion/Obsidian Import — Module

**Files:**
- Create: `openraven/src/openraven/ingestion/importers.py`
- Modify: `openraven/tests/test_ingestion.py`

- [ ] **Step 1: Write failing tests for importers**

Add to `openraven/tests/test_ingestion.py`:

```python
import zipfile


def _make_zip(tmp_path: Path, files: dict[str, str | bytes], zip_name: str = "export.zip") -> Path:
    """Helper to create a zip file with given files."""
    zip_path = tmp_path / zip_name
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in files.items():
            if isinstance(content, str):
                zf.writestr(name, content)
            else:
                zf.writestr(name, content)
    return zip_path


def test_detect_notion_format(tmp_path: Path) -> None:
    """Notion exports have filenames with 32-char UUID suffixes."""
    from openraven.ingestion.importers import _detect_format
    zip_path = _make_zip(tmp_path, {
        "Meeting Notes abc123def456789012345678abcdef01.md": "# Meeting",
        "Tasks abc123def456789012345678abcdef02.csv": "Name,Status",
    })
    with zipfile.ZipFile(zip_path) as zf:
        assert _detect_format(zf) == "notion"


def test_detect_obsidian_format(tmp_path: Path) -> None:
    """Obsidian exports have .obsidian/ folder or [[wikilinks]]."""
    from openraven.ingestion.importers import _detect_format
    zip_path = _make_zip(tmp_path, {
        ".obsidian/app.json": "{}",
        "notes/daily.md": "# Daily\n\nSee [[weekly review]]",
    })
    with zipfile.ZipFile(zip_path) as zf:
        assert _detect_format(zf) == "obsidian"


def test_detect_generic_format(tmp_path: Path) -> None:
    """Plain markdown zips should be detected as generic."""
    from openraven.ingestion.importers import _detect_format
    zip_path = _make_zip(tmp_path, {
        "notes.md": "# Notes\n\nSome content",
        "report.md": "# Report",
    })
    with zipfile.ZipFile(zip_path) as zf:
        assert _detect_format(zf) == "generic"


def test_import_notion_strips_uuids(tmp_path: Path) -> None:
    """Notion import should strip UUID suffixes from filenames."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "Meeting Notes abc123def456789012345678abcdef01.md": "# Meeting Notes\n\nDiscussed roadmap.",
        "Project Plan abc123def456789012345678abcdef02.md": "# Project Plan\n\nQ2 goals.",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    assert len(result) == 2
    names = {p.name for p in result}
    assert "Meeting Notes.md" in names
    assert "Project Plan.md" in names
    # Verify content is preserved
    for p in result:
        assert p.read_text(encoding="utf-8").startswith("#")


def test_import_notion_converts_csv_to_markdown(tmp_path: Path) -> None:
    """Notion CSV database exports should be converted to markdown tables."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "Tasks abc123def456789012345678abcdef01.csv": "Name,Status,Priority\nBuild API,Done,High\nWrite tests,In Progress,Medium",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    assert len(result) == 1
    content = result[0].read_text(encoding="utf-8")
    assert "Build API" in content
    assert "|" in content  # markdown table format


def test_import_obsidian_converts_wikilinks(tmp_path: Path) -> None:
    """Obsidian import should convert [[wikilinks]] to plain text."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "notes/daily.md": "# Daily\n\nReview [[weekly plan]] and check [[project status]].",
        ".obsidian/app.json": "{}",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    assert len(result) == 1
    content = result[0].read_text(encoding="utf-8")
    assert "weekly plan" in content
    assert "[[" not in content


def test_import_obsidian_preserves_frontmatter(tmp_path: Path) -> None:
    """Obsidian frontmatter should be preserved."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "note.md": "---\ntitle: My Note\ntags: [ai, ml]\n---\n\n# My Note\n\nContent here.",
        ".obsidian/app.json": "{}",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    content = result[0].read_text(encoding="utf-8")
    assert "title: My Note" in content


def test_import_zip_skips_non_content_files(tmp_path: Path) -> None:
    """Import should skip config files, hidden files, __MACOSX, etc."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "notes.md": "# Notes",
        "__MACOSX/._notes.md": "resource fork",
        ".DS_Store": "binary",
        ".obsidian/plugins/foo.json": "{}",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    assert len(result) == 1
    assert result[0].name == "notes.md"


def test_import_zip_extracts_images(tmp_path: Path) -> None:
    """Images embedded in the zip should be extracted for vision pipeline."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "notes.md": "# Notes\n\n![diagram](images/arch.png)",
        "images/arch.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 50,
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    names = {p.name for p in result}
    assert "notes.md" in names
    assert "arch.png" in names


def test_import_obsidian_wikilink_with_display_text(tmp_path: Path) -> None:
    """Obsidian [[link|display text]] should use display text."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "note.md": "See [[weekly plan|my weekly plan]] for details.",
        ".obsidian/app.json": "{}",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    content = result[0].read_text(encoding="utf-8")
    assert "my weekly plan" in content
    assert "[[" not in content


def test_import_notion_handles_duplicate_filenames(tmp_path: Path) -> None:
    """Duplicate filenames after UUID stripping should be deduplicated."""
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "folder1/Notes abc123def456789012345678abcdef01.md": "# Notes from folder 1",
        "folder2/Notes abc123def456789012345678abcdef02.md": "# Notes from folder 2",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    assert len(result) == 2
    # Both files should exist (one with _2 suffix)
    contents = {p.read_text(encoding="utf-8") for p in result}
    assert "# Notes from folder 1" in contents
    assert "# Notes from folder 2" in contents
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_ingestion.py -k "import" -v 2>&1 | tail -15
```
Expected: FAIL — `importers` module doesn't exist.

- [ ] **Step 3: Implement importers.py**

Create `openraven/src/openraven/ingestion/importers.py`:

```python
"""Import zip exports from Notion and Obsidian into OpenRaven."""
from __future__ import annotations

import csv
import io
import logging
import re
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

logger = logging.getLogger(__name__)

# Notion filenames end with a 32-char hex UUID (with or without extension)
_NOTION_UUID_RE = re.compile(r"\s+[0-9a-f]{32}(?=\.\w+$|\s*$)")

# Obsidian [[wikilink]] or [[wikilink|display text]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")

# File extensions to extract as content
_CONTENT_EXTENSIONS = {".md", ".txt"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".heic", ".webp"}
_CSV_EXTENSIONS = {".csv"}

# Paths to skip
_SKIP_PREFIXES = ("__MACOSX/", ".obsidian/", ".trash/")
_SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def import_zip(zip_path: Path, output_dir: Path) -> list[Path]:
    """Extract and normalize a Notion or Obsidian zip export.

    Returns list of extracted file paths ready for pipeline ingestion.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path) as zf:
        fmt = _detect_format(zf)
        if fmt == "notion":
            return _import_notion(zf, output_dir)
        elif fmt == "obsidian":
            return _import_obsidian(zf, output_dir)
        else:
            return _import_generic(zf, output_dir)


def _detect_format(zf: ZipFile) -> Literal["notion", "obsidian", "generic"]:
    """Auto-detect zip format from contents."""
    names = zf.namelist()

    # Obsidian: has .obsidian/ directory
    if any(n.startswith(".obsidian/") for n in names):
        return "obsidian"

    # Obsidian: check for [[wikilinks]] in markdown files
    for name in names:
        if name.endswith(".md") and not _should_skip(name):
            try:
                content = zf.read(name).decode("utf-8", errors="ignore")
                if _WIKILINK_RE.search(content):
                    return "obsidian"
            except Exception:
                pass
            break  # only check first md file

    # Notion: filenames with 32-char hex UUIDs
    for name in names:
        basename = Path(name).name
        if _NOTION_UUID_RE.search(basename):
            return "notion"

    return "generic"


def _should_skip(name: str) -> bool:
    """Check if a zip entry should be skipped."""
    if any(name.startswith(prefix) for prefix in _SKIP_PREFIXES):
        return True
    basename = Path(name).name
    if basename in _SKIP_NAMES or basename.startswith("."):
        return True
    return False


def _import_notion(zf: ZipFile, output_dir: Path) -> list[Path]:
    """Handle Notion export: strip UUIDs, convert CSVs."""
    extracted: list[Path] = []

    for name in zf.namelist():
        if _should_skip(name):
            continue

        basename = Path(name).name
        suffix = Path(basename).suffix.lower()

        if suffix in _CSV_EXTENSIONS:
            # Convert CSV to markdown table
            content = zf.read(name).decode("utf-8", errors="ignore")
            md_content = _csv_to_markdown(content, basename)
            clean_name = _NOTION_UUID_RE.sub("", Path(basename).stem).strip() + ".md"
            dest = _deduplicate_path(output_dir / clean_name)
            dest.write_text(md_content, encoding="utf-8")
            extracted.append(dest)
        elif suffix in _CONTENT_EXTENSIONS:
            content = zf.read(name).decode("utf-8", errors="ignore")
            clean_name = _NOTION_UUID_RE.sub("", basename).strip()
            dest = _deduplicate_path(output_dir / clean_name)
            dest.write_text(content, encoding="utf-8")
            extracted.append(dest)
        elif suffix in _IMAGE_EXTENSIONS:
            dest = _deduplicate_path(output_dir / basename)
            dest.write_bytes(zf.read(name))
            extracted.append(dest)

    return extracted


def _import_obsidian(zf: ZipFile, output_dir: Path) -> list[Path]:
    """Handle Obsidian export: convert wikilinks, preserve frontmatter."""
    extracted: list[Path] = []

    for name in zf.namelist():
        if _should_skip(name):
            continue

        basename = Path(name).name
        suffix = Path(basename).suffix.lower()

        if suffix in _CONTENT_EXTENSIONS:
            content = zf.read(name).decode("utf-8", errors="ignore")
            content = _WIKILINK_RE.sub(lambda m: m.group(2) or m.group(1), content)
            dest = _deduplicate_path(output_dir / basename)
            dest.write_text(content, encoding="utf-8")
            extracted.append(dest)
        elif suffix in _IMAGE_EXTENSIONS:
            dest = _deduplicate_path(output_dir / basename)
            dest.write_bytes(zf.read(name))
            extracted.append(dest)

    return extracted


def _import_generic(zf: ZipFile, output_dir: Path) -> list[Path]:
    """Extract all content files from a generic zip."""
    extracted: list[Path] = []

    for name in zf.namelist():
        if _should_skip(name):
            continue

        basename = Path(name).name
        suffix = Path(basename).suffix.lower()

        if suffix in _CONTENT_EXTENSIONS:
            content = zf.read(name).decode("utf-8", errors="ignore")
            dest = _deduplicate_path(output_dir / basename)
            dest.write_text(content, encoding="utf-8")
            extracted.append(dest)
        elif suffix in _IMAGE_EXTENSIONS:
            dest = _deduplicate_path(output_dir / basename)
            dest.write_bytes(zf.read(name))
            extracted.append(dest)

    return extracted


def _deduplicate_path(dest: Path) -> Path:
    """If dest already exists, add _2, _3, etc. before the extension."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _csv_to_markdown(csv_content: str, filename: str = "") -> str:
    """Convert CSV content to a markdown table."""
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    if not rows:
        return ""

    title = Path(filename).stem
    # Strip Notion UUID from title
    title = _NOTION_UUID_RE.sub("", title).strip()

    lines = [f"# {title}\n"]
    header = rows[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows[1:]:
        # Pad row if shorter than header
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[:len(header)]) + " |")

    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_ingestion.py -k "import or detect" -v 2>&1 | tail -20
```
Expected: All 8 new import tests PASS.

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/ingestion/importers.py openraven/tests/test_ingestion.py
git commit -m "feat: add Notion/Obsidian zip import module

Supports auto-detection of Notion (UUID filenames, CSV databases) and
Obsidian (.obsidian/ dir, [[wikilinks]]) formats. Strips Notion UUIDs,
converts CSVs to markdown tables, resolves wikilinks to plain text.
Extracts embedded images for vision pipeline."
```

---

## Task 5: Zip Import — Pipeline Integration + UI

**Files:**
- Modify: `openraven/src/openraven/pipeline.py`
- Modify: `openraven-ui/src/pages/IngestPage.tsx`

- [ ] **Step 1: Add zip handling to pipeline**

In `openraven/src/openraven/pipeline.py`, add import at top:
```python
from openraven.ingestion.importers import import_zip
```

Also add `.zip` to `SUPPORTED_EXTENSIONS` (was not added in Task 3 to avoid a broken intermediate state):
```python
SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".zip"} | IMAGE_EXTENSIONS
```

In the `add_files` method, add zip expansion before Stage 1. Insert this block after `files_to_process = self._filter_unchanged(file_paths)` (around line 109) and before the `if not files_to_process:` check:

```python
        # Pre-stage: expand zip files
        expanded: list[Path | str] = []
        for fp in files_to_process:
            fp_path = Path(fp) if not isinstance(fp, Path) else fp
            if fp_path.suffix.lower() == ".zip":
                try:
                    zip_output = self.config.ingestion_dir / f"_import_{fp.stem}"
                    imported = import_zip(fp, zip_output)
                    expanded.extend(imported)
                    logger.info(f"Extracted {len(imported)} files from {fp.name}")
                except Exception as e:
                    errors.append(f"Zip import failed for {fp}: {e}")
                    logger.error(f"Zip import failed for {fp}", exc_info=True)
            else:
                expanded.append(fp)
        files_to_process = expanded
```

- [ ] **Step 2: Add import help text to IngestPage**

In `openraven-ui/src/pages/IngestPage.tsx`, add a help note after the FileUploader (after line 86, before the loading indicator):

```tsx
      <p className="mt-3 text-xs" style={{ color: "var(--color-text-muted)" }}>
        Import from Notion or Obsidian — upload your exported .zip file. Images (PNG, JPEG) are analyzed with AI vision.
      </p>
```

- [ ] **Step 3: Verify builds**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx bun run build 2>&1 | tail -5
```
Expected: Build succeeds.

- [ ] **Step 4: Run all existing tests to verify no regressions**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_ingestion.py tests/test_api.py -v 2>&1 | tail -20
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/pipeline.py openraven-ui/src/pages/IngestPage.tsx
git commit -m "feat: integrate zip import into pipeline and add UI help text

Pipeline expands .zip files via import_zip() before Stage 1 processing.
IngestPage shows help text about Notion/Obsidian import and image AI."
```

---

## Task 6: Enhanced Discovery Insights — Backend

**Files:**
- Modify: `openraven/src/openraven/graph/rag.py`
- Modify: `openraven/src/openraven/discovery/analyzer.py`
- Modify: `openraven/tests/test_discovery.py`

- [ ] **Step 1: Write failing tests for enhanced discovery**

Add to `openraven/tests/test_discovery.py`:

```python
def test_analyze_themes_produces_coverage_insight() -> None:
    """Enhanced analyzer should produce a knowledge coverage insight."""
    graph_stats = {
        "nodes": 45, "edges": 120,
        "topics": ["Kafka", "Microservices", "CQRS", "PostgreSQL", "Redis"],
        "entity_types": {"technology": 20, "concept": 15, "person": 5, "organization": 5},
        "top_connected": [("Kafka", 12), ("Microservices", 10), ("PostgreSQL", 8)],
        "components": 3,
    }
    insights = analyze_themes(graph_stats)
    types = [i.insight_type for i in insights]
    assert "theme" in types  # coverage insight
    # Should have more insights than before (was just 2)
    assert len(insights) >= 3


def test_analyze_themes_produces_connections_insight() -> None:
    """Should report cross-topic connections when top_connected is present."""
    graph_stats = {
        "nodes": 30, "edges": 80,
        "topics": ["AI", "Machine Learning", "Neural Networks"],
        "entity_types": {"concept": 25, "technology": 5},
        "top_connected": [("AI", 15), ("Machine Learning", 12), ("Neural Networks", 8)],
        "components": 1,
    }
    insights = analyze_themes(graph_stats)
    descriptions = " ".join(i.description for i in insights)
    # Should mention the most connected concepts
    assert "AI" in descriptions or "Machine Learning" in descriptions


def test_analyze_themes_produces_gap_insight() -> None:
    """Should produce a gap insight when there are disconnected components."""
    graph_stats = {
        "nodes": 20, "edges": 15,
        "topics": ["Topic A", "Topic B"],
        "entity_types": {"concept": 20},
        "top_connected": [("Topic A", 5)],
        "components": 5,  # many disconnected components = gaps
    }
    insights = analyze_themes(graph_stats)
    types = [i.insight_type for i in insights]
    assert "gap" in types


def test_analyze_themes_backward_compatible() -> None:
    """Existing stats format (without new fields) should still work."""
    graph_stats = {"nodes": 10, "edges": 5, "topics": ["A", "B", "C"]}
    insights = analyze_themes(graph_stats)
    assert len(insights) >= 1  # at least the overview


def test_get_detailed_stats_shape(tmp_path) -> None:
    """get_detailed_stats should return entity_types, top_connected, components."""
    import networkx as nx
    from openraven.graph.rag import RavenGraph

    # Create a minimal graphml file
    graph_file = tmp_path / "lightrag_data" / "graph_chunk_entity_relation.graphml"
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    G = nx.Graph()
    G.add_node("Kafka", entity_type="technology")
    G.add_node("Microservices", entity_type="concept")
    G.add_node("Isolated", entity_type="concept")
    G.add_edge("Kafka", "Microservices")
    nx.write_graphml(G, str(graph_file))

    rg = RavenGraph(working_dir=tmp_path / "lightrag_data")
    stats = rg.get_detailed_stats()

    assert "entity_types" in stats
    assert "top_connected" in stats
    assert "components" in stats
    assert stats["entity_types"]["technology"] == 1
    assert stats["entity_types"]["concept"] == 2
    assert stats["components"] == 2  # Kafka-Microservices cluster + Isolated
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_discovery.py -k "coverage or connections or gap_insight or backward" -v 2>&1 | tail -15
```
Expected: FAIL — current analyzer doesn't produce these insight types with this detail.

- [ ] **Step 3: Add get_detailed_stats to RavenGraph**

In `openraven/src/openraven/graph/rag.py`, add this method to the `RavenGraph` class (after `get_stats`):

```python
    def get_detailed_stats(self) -> dict:
        """Return detailed graph statistics including entity types and clusters.

        Extends get_stats() with entity_types distribution, top connected nodes,
        and connected component count for richer discovery insights.
        """
        base = self.get_stats()

        if self._graph_backend == "neo4j":
            return self._get_detailed_stats_neo4j(base)

        import networkx as nx

        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return {**base, "entity_types": {}, "top_connected": [], "components": 0}

        try:
            graph = nx.read_graphml(str(graph_file))
        except Exception:
            return {**base, "entity_types": {}, "top_connected": [], "components": 0}

        # Entity type distribution
        entity_types: dict[str, int] = {}
        for _, attrs in graph.nodes(data=True):
            etype = attrs.get("entity_type", "unknown")
            entity_types[etype] = entity_types.get(etype, 0) + 1

        # Top connected nodes by degree
        degrees = dict(graph.degree())
        top_connected = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10]

        # Connected components
        if graph.is_directed():
            components = nx.number_weakly_connected_components(graph)
        else:
            components = nx.number_connected_components(graph)

        return {
            **base,
            "entity_types": entity_types,
            "top_connected": top_connected,
            "components": components,
        }

    def _get_detailed_stats_neo4j(self, base: dict) -> dict:
        """Detailed stats from Neo4j."""
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(self._neo4j_uri, auth=(self._neo4j_user, self._neo4j_password))
            with driver.session() as session:
                # Entity types
                type_result = session.run(
                    "MATCH (n) RETURN n.entity_type AS etype, count(*) AS cnt"
                )
                entity_types = {r["etype"] or "unknown": r["cnt"] for r in type_result}

                # Top connected
                degree_result = session.run(
                    "MATCH (n)-[r]-() RETURN n.id AS id, count(r) AS deg ORDER BY deg DESC LIMIT 10"
                )
                top_connected = [(r["id"], r["deg"]) for r in degree_result]

            driver.close()
            return {**base, "entity_types": entity_types, "top_connected": top_connected, "components": 0}
        except Exception:
            return {**base, "entity_types": {}, "top_connected": [], "components": 0}
```

- [ ] **Step 4: Rewrite analyze_themes with richer insights**

Replace the `analyze_themes` function in `openraven/src/openraven/discovery/analyzer.py`:

```python
def analyze_themes(graph_stats: dict) -> list[DiscoveryInsight]:
    """Generate discovery insights from graph statistics.

    Accepts both basic stats (nodes, edges, topics) and detailed stats
    (entity_types, top_connected, components) for richer insights.
    """
    insights: list[DiscoveryInsight] = []
    topics = graph_stats.get("topics", [])
    node_count = graph_stats.get("nodes", 0)
    edge_count = graph_stats.get("edges", 0)
    entity_types = graph_stats.get("entity_types", {})
    top_connected = graph_stats.get("top_connected", [])
    components = graph_stats.get("components", 0)

    if node_count == 0:
        return insights

    # 1. Knowledge coverage overview
    if entity_types:
        type_summary = ", ".join(
            f"{count} {etype}s" for etype, count in
            sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:4]
        )
        insights.append(DiscoveryInsight(
            insight_type="theme",
            title="Knowledge Coverage",
            description=(
                f"Your knowledge base contains {node_count} concepts with "
                f"{edge_count} connections: {type_summary}."
            ),
            related_entities=topics[:10],
            document_count=node_count,
        ))
    else:
        insights.append(DiscoveryInsight(
            insight_type="theme",
            title="Knowledge Base Overview",
            description=(
                f"Your knowledge base contains {node_count} concepts "
                f"with {edge_count} connections between them."
            ),
            related_entities=topics[:10],
            document_count=node_count,
        ))

    # 2. Top knowledge areas
    if len(topics) >= 3:
        insights.append(DiscoveryInsight(
            insight_type="cluster",
            title="Top Knowledge Areas",
            description=f"Found {len(topics)} distinct topics in your knowledge base.",
            related_entities=topics[:10],
            document_count=len(topics),
        ))

    # 3. Most connected concepts (hub nodes)
    if top_connected:
        hub_names = [name for name, deg in top_connected[:3]]
        hub_desc = ", ".join(hub_names)
        max_deg = top_connected[0][1] if top_connected else 0
        insights.append(DiscoveryInsight(
            insight_type="trend",
            title="Key Concepts Discovered",
            description=(
                f"Your most connected concepts are {hub_desc}. "
                f"The top concept links to {max_deg} other ideas."
            ),
            related_entities=[name for name, _ in top_connected[:5]],
            document_count=len(top_connected),
        ))

    # 4. Knowledge gaps (many disconnected components)
    if components > 3:
        insights.append(DiscoveryInsight(
            insight_type="gap",
            title="Knowledge Gaps Detected",
            description=(
                f"Found {components} separate topic clusters with no connections between them. "
                f"Adding more documents could help bridge these gaps."
            ),
            related_entities=topics[:5],
            document_count=components,
        ))

    return insights
```

- [ ] **Step 5: Update the /api/discovery endpoint to use detailed stats**

In `openraven/src/openraven/api/server.py`, update the discovery endpoint (around line 510-521). Change:

```python
        graph_stats = pipeline.graph.get_stats()
```

to:

```python
        graph_stats = pipeline.graph.get_detailed_stats()
```

- [ ] **Step 6: Run tests to verify they pass**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_discovery.py -v 2>&1 | tail -15
```
Expected: All tests PASS, including the 4 new ones.

- [ ] **Step 7: Commit**

```bash
git add openraven/src/openraven/graph/rag.py openraven/src/openraven/discovery/analyzer.py openraven/src/openraven/api/server.py openraven/tests/test_discovery.py
git commit -m "feat: enhance discovery with entity types, hub nodes, and gap detection

get_detailed_stats() returns entity type distribution, top connected
nodes, and component count. analyze_themes() now produces 4 insight
types: coverage, clusters, key concepts, and knowledge gaps."
```

---

## Task 7: Onboarding Banner — UI

**Files:**
- Create: `openraven-ui/src/components/OnboardingBanner.tsx`
- Modify: `openraven-ui/src/pages/AskPage.tsx`

- [ ] **Step 1: Create OnboardingBanner component**

Create `openraven-ui/src/components/OnboardingBanner.tsx`:

```tsx
import { useState, useEffect } from "react";

const STORAGE_KEY = "openraven_onboarding_dismissed";

interface StatusData {
  total_files: number;
  total_entities: number;
  topics_count: number;
}

export default function OnboardingBanner() {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(STORAGE_KEY) === "true");

  useEffect(() => {
    if (dismissed) return;
    fetch("/api/status")
      .then(r => r.json())
      .then((data) => {
        const totalFiles = data.total_files ?? 0;
        const totalEntities = data.total_entities ?? 0;
        const topicsCount = data.topic_count ?? 0;
        if (totalFiles > 0) {
          setStatus({ total_files: totalFiles, total_entities: totalEntities, topics_count: topicsCount });
        }
      })
      .catch(() => {});
  }, [dismissed]);

  function handleDismiss() {
    localStorage.setItem(STORAGE_KEY, "true");
    setDismissed(true);
  }

  if (dismissed || !status) return null;

  return (
    <div
      className="mb-6 p-4 flex items-start justify-between gap-4"
      style={{
        background: "var(--color-surface-secondary, #fff8f0)",
        borderLeft: "3px solid var(--color-brand, #fa520f)",
        boxShadow: "var(--shadow-golden, 0 1px 3px rgba(250,82,15,0.1))",
      }}
    >
      <div>
        <p className="text-sm" style={{ color: "var(--color-text)" }}>
          <strong>Your knowledge base is ready!</strong>{" "}
          {status.total_entities > 0
            ? `We found ${status.total_entities} concepts${status.topics_count > 0 ? ` across ${status.topics_count} topics` : ""}. `
            : `${status.total_files} files processed. `}
          Ask a question to explore your knowledge.
        </p>
      </div>
      <button
        onClick={handleDismiss}
        className="text-xs cursor-pointer shrink-0 px-2 py-1"
        style={{ color: "var(--color-text-muted)", background: "transparent", border: "none" }}
        aria-label="Dismiss onboarding banner"
      >
        Dismiss
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Integrate OnboardingBanner into AskPage**

In `openraven-ui/src/pages/AskPage.tsx`, add the import at top:
```tsx
import OnboardingBanner from "../components/OnboardingBanner";
```

Add the banner inside the return, just after the opening `<div className="flex flex-col h-[calc(100vh-8rem)]">` and before the first `{messages.length === 0 && ...}` block:

```tsx
      {messages.length === 0 && <OnboardingBanner />}
```

- [ ] **Step 3: Verify UI builds**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx bun run build 2>&1 | tail -5
```
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add openraven-ui/src/components/OnboardingBanner.tsx openraven-ui/src/pages/AskPage.tsx
git commit -m "feat: add onboarding banner on Ask page after first ingestion

Shows 'Your knowledge base is ready!' with entity/topic counts when
the KB has content. Dismissible via localStorage flag. Uses Mistral
Premium design tokens."
```

---

## Task 8: Final Integration Test + All-Tests Run

**Files:** None (verification only)

- [ ] **Step 1: Run all Python tests**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/ -v --ignore=tests/benchmark --ignore=tests/fixtures 2>&1 | tail -30
```
Expected: All tests PASS (existing + new).

- [ ] **Step 2: Run UI build**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx bun run build 2>&1 | tail -5
```
Expected: Build succeeds with no errors.

- [ ] **Step 3: Run UI tests if available**

Run:
```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx bun test 2>&1 | tail -10
```
Expected: All tests PASS.

- [ ] **Step 4: Final commit with all quick wins summary**

Only if there are any uncommitted changes from integration fixes:
```bash
git add -A && git commit -m "fix: integration adjustments for quick win features"
```
