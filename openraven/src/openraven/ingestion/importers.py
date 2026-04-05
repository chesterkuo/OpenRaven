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
    """Extract and normalize a Notion or Obsidian zip export."""
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

    if any(n.startswith(".obsidian/") for n in names):
        return "obsidian"

    for name in names:
        if name.endswith(".md") and not _should_skip(name):
            try:
                content = zf.read(name).decode("utf-8", errors="ignore")
                if _WIKILINK_RE.search(content):
                    return "obsidian"
            except Exception:
                pass
            break

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


def _import_notion(zf: ZipFile, output_dir: Path) -> list[Path]:
    """Handle Notion export: strip UUIDs, convert CSVs."""
    extracted: list[Path] = []

    for name in zf.namelist():
        if _should_skip(name):
            continue

        basename = Path(name).name
        suffix = Path(basename).suffix.lower()

        if suffix in _CSV_EXTENSIONS:
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


def _csv_to_markdown(csv_content: str, filename: str = "") -> str:
    """Convert CSV content to a markdown table."""
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    if not rows:
        return ""

    title = Path(filename).stem
    title = _NOTION_UUID_RE.sub("", title).strip()

    lines = [f"# {title}\n"]
    header = rows[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[:len(header)]) + " |")

    return "\n".join(lines) + "\n"
