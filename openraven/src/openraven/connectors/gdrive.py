from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_MIMETYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/plain": ".txt",
    "text/html": ".html",
    "text/markdown": ".md",
}

EXPORT_MIMETYPES = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
}


def file_id_to_record_path(file_id: str) -> str:
    """Create a stable record path for a Drive file."""
    return f"gdrive://{file_id}"


async def sync_drive(
    credentials,
    output_dir: Path,
    max_files: int = 100,
) -> list[Path]:
    """Sync files from Google Drive to local temp directory."""
    if credentials is None:
        return []

    import asyncio
    from googleapiclient.discovery import build

    def _list_and_download():
        service = build("drive", "v3", credentials=credentials)
        downloaded = []

        query = " or ".join(
            f"mimeType='{mt}'" for mt in list(SUPPORTED_MIMETYPES) + list(EXPORT_MIMETYPES)
        )
        results = (
            service.files()
            .list(
                q=query,
                pageSize=max_files,
                orderBy="modifiedTime desc",
                fields="files(id, name, mimeType, md5Checksum, modifiedTime)",
            )
            .execute()
        )

        files = results.get("files", [])
        output_dir.mkdir(parents=True, exist_ok=True)

        for file_info in files:
            try:
                file_id = file_info["id"]
                name = file_info["name"]
                mime = file_info["mimeType"]

                if mime in EXPORT_MIMETYPES:
                    export_mime, ext = EXPORT_MIMETYPES[mime]
                    content = (
                        service.files()
                        .export(fileId=file_id, mimeType=export_mime)
                        .execute()
                    )
                elif mime in SUPPORTED_MIMETYPES:
                    ext = SUPPORTED_MIMETYPES[mime]
                    content = service.files().get_media(fileId=file_id).execute()
                else:
                    continue

                safe_name = name.replace("/", "_")
                if not safe_name.endswith(ext):
                    safe_name += ext
                dest = output_dir / safe_name
                dest.write_bytes(
                    content if isinstance(content, bytes) else content.encode("utf-8")
                )
                downloaded.append(dest)
                logger.info(f"Downloaded Drive file: {name} ({file_id})")
            except Exception as e:
                logger.warning(
                    f"Failed to download Drive file {file_info.get('name', '?')}: {e}"
                )

        return downloaded

    return await asyncio.to_thread(_list_and_download)
