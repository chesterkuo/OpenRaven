from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileRecord:
    """Metadata record for an ingested file."""

    path: str
    hash: str
    format: str
    char_count: int
    status: str


class MetadataStore:
    """SQLite-backed metadata store for tracking file processing state."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                format TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def upsert_file(self, record: FileRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO files (path, hash, format, char_count, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                hash=excluded.hash,
                format=excluded.format,
                char_count=excluded.char_count,
                status=excluded.status,
                updated_at=CURRENT_TIMESTAMP
            """,
            (record.path, record.hash, record.format, record.char_count, record.status),
        )
        self._conn.commit()

    def get_file(self, path: str) -> FileRecord | None:
        row = self._conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
        if row is None:
            return None
        return FileRecord(
            path=row["path"],
            hash=row["hash"],
            format=row["format"],
            char_count=row["char_count"],
            status=row["status"],
        )

    def list_files(self, status: str | None = None) -> list[FileRecord]:
        if status:
            rows = self._conn.execute("SELECT * FROM files WHERE status = ?", (status,)).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM files").fetchall()
        return [
            FileRecord(path=r["path"], hash=r["hash"], format=r["format"],
                       char_count=r["char_count"], status=r["status"])
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
