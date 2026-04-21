from __future__ import annotations

import base64
import logging
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import opendataloader_pdf
import openai
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


def _parse_pdf(file_path: Path) -> str:
    """Extract plain text from a PDF via the OpenDataLoader Java CLI.

    NFKC-normalized to repair Kangxi-radical codepoints (U+2F00 block) that
    some CJK PDF authoring tools emit in place of CJK Unified (U+4E00 block) —
    e.g. U+2F64 ⽤ → U+7528 用. Matters for downstream exact-string entity match.
    """
    with tempfile.TemporaryDirectory() as out_dir:
        opendataloader_pdf.convert(
            input_path=str(file_path),
            output_dir=out_dir,
            format="text",
            quiet=True,
        )
        raw = (Path(out_dir) / f"{file_path.stem}.txt").read_text(encoding="utf-8")
    return unicodedata.normalize("NFKC", raw)


def parse_document(file_path: Path | str) -> ParsedDocument:
    """Parse a document file or URL into plain text.

    Supports:
    - PDF files via OpenDataLoader (Java CLI, fast + low-RAM)
    - DOCX, PPTX, XLSX, HTML via Docling
    - MD, TXT read directly
    - URLs via Jina Reader
    """
    path_str = str(file_path)

    if path_str.startswith("http://") or path_str.startswith("https://"):
        return parse_url(path_str)

    file_path = Path(file_path).resolve()
    suffix = file_path.suffix.lower().lstrip(".")

    if suffix in ("md", "txt"):
        text = file_path.read_text(encoding="utf-8")
    elif suffix == "pdf":
        text = _parse_pdf(file_path)
    else:
        converter = _get_converter()
        result = converter.convert(str(file_path))
        text = result.document.export_to_markdown()

    return ParsedDocument(
        text=text,
        source_path=file_path,
        format=suffix,
        char_count=len(text),
    )


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
    """Parse an image file using Gemini vision API."""
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
