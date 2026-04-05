from pathlib import Path

from openraven.ingestion.hasher import compute_file_hash
from openraven.ingestion.parser import ParsedDocument, parse_document


def test_compute_file_hash_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    h1 = compute_file_hash(f)
    h2 = compute_file_hash(f)
    assert h1 == h2
    assert len(h1) == 64


def test_compute_file_hash_changes_on_content_change(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("version 1")
    h1 = compute_file_hash(f)
    f.write_text("version 2")
    h2 = compute_file_hash(f)
    assert h1 != h2


def test_parse_markdown_file(tmp_path: Path) -> None:
    md = tmp_path / "test.md"
    md.write_text("# Title\n\nSome content here.")
    result = parse_document(md)
    assert isinstance(result, ParsedDocument)
    assert "Title" in result.text
    assert "Some content here" in result.text
    assert result.source_path == md
    assert result.format == "md"


def test_parse_document_returns_metadata(tmp_path: Path) -> None:
    md = tmp_path / "report.md"
    md.write_text("# Report\n\nAnalysis of market trends.")
    result = parse_document(md)
    assert result.char_count > 0
    assert result.source_path.name == "report.md"


from unittest.mock import AsyncMock, patch
import pytest


def test_parse_image_supported_extensions():
    """Image extensions should be recognized by the parser."""
    from openraven.ingestion.parser import IMAGE_EXTENSIONS
    assert ".png" in IMAGE_EXTENSIONS
    assert ".jpg" in IMAGE_EXTENSIONS
    assert ".jpeg" in IMAGE_EXTENSIONS
    assert ".webp" in IMAGE_EXTENSIONS
    assert ".heic" in IMAGE_EXTENSIONS


@pytest.mark.asyncio
async def test_parse_image_returns_parsed_document(tmp_path: Path) -> None:
    """parse_image should call Gemini vision API and return ParsedDocument."""
    img = tmp_path / "diagram.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

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
    img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)

    with patch("openraven.ingestion.parser.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        mock_client_cls.return_value = mock_client

        from openraven.ingestion.parser import parse_image
        result = await parse_image(img, api_key="test-key")

    assert isinstance(result, ParsedDocument)
    assert result.text == ""
    assert result.char_count == 0
