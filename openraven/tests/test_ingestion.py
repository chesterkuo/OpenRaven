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
