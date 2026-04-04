from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docling.document_converter import DocumentConverter


@dataclass
class ParsedDocument:
    """A document converted to plain text with metadata."""

    text: str
    source_path: Path
    format: str
    char_count: int


_converter: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter


def parse_url(url: str) -> ParsedDocument:
    """Parse a web URL into plain text using Jina Reader."""
    import httpx

    response = httpx.get(
        f"https://r.jina.ai/{url}",
        headers={"Accept": "text/markdown"},
        timeout=30.0,
    )
    response.raise_for_status()
    text = response.text

    return ParsedDocument(
        text=text,
        source_path=Path(url),
        format="url",
        char_count=len(text),
    )


def parse_document(file_path: Path | str) -> ParsedDocument:
    """Parse a document file or URL into plain text.

    Supports:
    - Files: PDF, DOCX, PPTX, XLSX, MD, TXT, HTML (via Docling)
    - URLs: any http/https URL (via Jina Reader)
    """
    path_str = str(file_path)

    if path_str.startswith("http://") or path_str.startswith("https://"):
        return parse_url(path_str)

    file_path = Path(file_path).resolve()
    suffix = file_path.suffix.lower().lstrip(".")

    if suffix in ("md", "txt"):
        text = file_path.read_text(encoding="utf-8")
        return ParsedDocument(
            text=text,
            source_path=file_path,
            format=suffix,
            char_count=len(text),
        )

    converter = _get_converter()
    result = converter.convert(str(file_path))
    text = result.document.export_to_markdown()

    return ParsedDocument(
        text=text,
        source_path=file_path,
        format=suffix,
        char_count=len(text),
    )
