from __future__ import annotations

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def message_id_to_record_path(message_id: str) -> str:
    """Create a stable record path for a Gmail message."""
    return f"gmail://{message_id}"


def message_to_markdown(subject: str, sender: str, date: str, body: str) -> str:
    """Convert an email message to markdown format."""
    return f"# {subject}\n\n**From:** {sender}\n**Date:** {date}\n\n{body}"


async def sync_gmail(
    credentials,
    output_dir: Path,
    max_messages: int = 50,
) -> list[Path]:
    """Sync recent Gmail messages to local markdown files."""
    if credentials is None:
        return []

    import asyncio
    from googleapiclient.discovery import build

    def _list_and_download():
        service = build("gmail", "v1", credentials=credentials)
        downloaded = []

        output_dir.mkdir(parents=True, exist_ok=True)

        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                maxResults=max_messages,
            )
            .execute()
        )

        messages = results.get("messages", [])

        for msg_stub in messages:
            try:
                msg = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_stub["id"],
                        format="full",
                    )
                    .execute()
                )

                headers = {
                    h["name"].lower(): h["value"] for h in msg["payload"]["headers"]
                }
                subject = headers.get("subject", "(no subject)")
                sender = headers.get("from", "unknown")
                date = headers.get("date", "")

                body = _extract_body(msg["payload"])
                if not body or len(body.strip()) < 20:
                    continue

                msg_id = msg_stub["id"]
                md = message_to_markdown(
                    subject=subject, sender=sender, date=date, body=body
                )
                safe_name = (
                    subject.replace("/", "_").replace("\\", "_")[:80].strip()
                )
                dest = output_dir / f"{safe_name}_{msg_id[:8]}.md"
                dest.write_text(md, encoding="utf-8")
                downloaded.append(dest)
                logger.info(f"Downloaded Gmail: {subject} ({msg_stub['id']})")
            except Exception as e:
                logger.warning(
                    f"Failed to process Gmail message {msg_stub.get('id', '?')}: {e}"
                )

        return downloaded

    return await asyncio.to_thread(_list_and_download)


def _strip_html_tags(html: str) -> str:
    """Strip HTML tags using regex, returning plain text."""
    import re

    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _extract_body(payload: dict) -> str:
    """Extract plain text body from Gmail payload, handling multipart."""
    if (
        payload.get("mimeType") == "text/plain"
        and payload.get("body", {}).get("data")
    ):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
            "utf-8", errors="replace"
        )

    if (
        payload.get("mimeType") == "text/html"
        and payload.get("body", {}).get("data")
    ):
        html = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
            "utf-8", errors="replace"
        )
        return _strip_html_tags(html)

    html_fallback = None
    for part in payload.get("parts", []):
        if (
            part.get("mimeType") == "text/plain"
            and part.get("body", {}).get("data")
        ):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                "utf-8", errors="replace"
            )
        if (
            part.get("mimeType") == "text/html"
            and part.get("body", {}).get("data")
            and html_fallback is None
        ):
            html_fallback = base64.urlsafe_b64decode(
                part["body"]["data"]
            ).decode("utf-8", errors="replace")
        if part.get("parts"):
            result = _extract_body(part)
            if result:
                return result

    if html_fallback:
        return _strip_html_tags(html_fallback)

    return ""
