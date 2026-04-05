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
    from openraven.ingestion.importers import _detect_format
    zip_path = _make_zip(tmp_path, {
        "Meeting Notes abc123def456789012345678abcdef01.md": "# Meeting",
        "Tasks abc123def456789012345678abcdef02.csv": "Name,Status",
    })
    with zipfile.ZipFile(zip_path) as zf:
        assert _detect_format(zf) == "notion"


def test_detect_obsidian_format(tmp_path: Path) -> None:
    from openraven.ingestion.importers import _detect_format
    zip_path = _make_zip(tmp_path, {
        ".obsidian/app.json": "{}",
        "notes/daily.md": "# Daily\n\nSee [[weekly review]]",
    })
    with zipfile.ZipFile(zip_path) as zf:
        assert _detect_format(zf) == "obsidian"


def test_detect_generic_format(tmp_path: Path) -> None:
    from openraven.ingestion.importers import _detect_format
    zip_path = _make_zip(tmp_path, {
        "notes.md": "# Notes\n\nSome content",
        "report.md": "# Report",
    })
    with zipfile.ZipFile(zip_path) as zf:
        assert _detect_format(zf) == "generic"


def test_import_notion_strips_uuids(tmp_path: Path) -> None:
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
    for p in result:
        assert p.read_text(encoding="utf-8").startswith("#")


def test_import_notion_converts_csv_to_markdown(tmp_path: Path) -> None:
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "Tasks abc123def456789012345678abcdef01.csv": "Name,Status,Priority\nBuild API,Done,High\nWrite tests,In Progress,Medium",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    assert len(result) == 1
    content = result[0].read_text(encoding="utf-8")
    assert "Build API" in content
    assert "|" in content


def test_import_obsidian_converts_wikilinks(tmp_path: Path) -> None:
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
    from openraven.ingestion.importers import import_zip
    zip_path = _make_zip(tmp_path, {
        "folder1/Notes abc123def456789012345678abcdef01.md": "# Notes from folder 1",
        "folder2/Notes abc123def456789012345678abcdef02.md": "# Notes from folder 2",
    })
    output_dir = tmp_path / "output"
    result = import_zip(zip_path, output_dir)
    assert len(result) == 2
    contents = {p.read_text(encoding="utf-8") for p in result}
    assert "# Notes from folder 1" in contents
    assert "# Notes from folder 2" in contents
