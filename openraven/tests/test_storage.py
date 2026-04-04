from pathlib import Path

from openraven.storage import FileRecord, MetadataStore


def test_store_and_retrieve_file_record(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    record = FileRecord(
        path="/docs/report.pdf",
        hash="abc123",
        format="pdf",
        char_count=5000,
        status="ingested",
    )
    store.upsert_file(record)
    retrieved = store.get_file("/docs/report.pdf")
    assert retrieved is not None
    assert retrieved.hash == "abc123"
    assert retrieved.status == "ingested"


def test_upsert_updates_existing_record(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(
        FileRecord(path="/a.md", hash="v1", format="md", char_count=100, status="ingested")
    )
    store.upsert_file(
        FileRecord(path="/a.md", hash="v2", format="md", char_count=200, status="extracted")
    )
    record = store.get_file("/a.md")
    assert record is not None
    assert record.hash == "v2"
    assert record.status == "extracted"


def test_get_nonexistent_file_returns_none(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    assert store.get_file("/nope.txt") is None


def test_list_files(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(
        FileRecord(path="/a.md", hash="h1", format="md", char_count=100, status="ingested")
    )
    store.upsert_file(
        FileRecord(path="/b.pdf", hash="h2", format="pdf", char_count=200, status="ingested")
    )
    files = store.list_files()
    assert len(files) == 2


def test_file_record_has_updated_at(tmp_path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/doc.md", hash="abc", format="markdown", char_count=100, status="ingested"))
    record = store.get_file("/doc.md")
    assert record is not None
    assert record.updated_at is not None
    assert isinstance(record.updated_at, str)
    store.close()


def test_list_stale_files(tmp_path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/old.md", hash="a", format="markdown", char_count=50, status="graphed"))
    # Force the timestamp to 60 days ago
    store._conn.execute("UPDATE files SET updated_at = datetime('now', '-60 days') WHERE path = '/old.md'")
    store._conn.commit()
    store.upsert_file(FileRecord(path="/new.md", hash="b", format="markdown", char_count=50, status="graphed"))

    stale = store.list_stale_files(days=30)
    assert len(stale) == 1
    assert stale[0].path == "/old.md"
    store.close()
