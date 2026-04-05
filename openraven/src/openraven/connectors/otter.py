from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def transcript_to_markdown(title: str, date: str, speakers: list[dict]) -> str:
    """Convert an Otter.ai transcript to markdown format."""
    lines = [f"# {title}", f"\n**Date:** {date}\n"]
    for entry in speakers:
        ts = entry.get("timestamp", "")
        label = f"**{entry['name']} ({ts}):**" if ts else f"**{entry['name']}:**"
        lines.append(f"{label} {entry['text']}\n")
    return "\n".join(lines)


def save_api_key(api_key: str, key_path: Path) -> None:
    """Save Otter.ai API key to disk with restrictive permissions."""
    fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(api_key.strip())
    logger.info(f"Saved Otter.ai API key to {key_path}")


def load_api_key(key_path: Path) -> str:
    """Load Otter.ai API key from disk. Returns empty string if not found."""
    if not key_path.exists():
        return ""
    return key_path.read_text(encoding="utf-8").strip()


async def sync_otter(
    api_key: str,
    output_dir: Path,
    max_transcripts: int = 50,
) -> list[Path]:
    """Sync recent transcripts from Otter.ai API."""
    if not api_key:
        return []

    import asyncio

    def _fetch_and_save():
        import httpx

        downloaded = []
        output_dir.mkdir(parents=True, exist_ok=True)

        # NOTE: Otter.ai API endpoints are based on their documented API.
        # If the API structure changes, update the base_url and endpoint paths.
        try:
            with httpx.Client(
                base_url="https://otter.ai/forward/api/v1",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            ) as client:
                response = client.get("/speeches", params={"page_size": max_transcripts})
                response.raise_for_status()
                data = response.json()

                speeches = data.get("speeches", data.get("results", []))

                for speech in speeches:
                    try:
                        speech_id = speech.get("otid", speech.get("id", ""))
                        title = speech.get("title", "Untitled Meeting")
                        created = speech.get("created_at", speech.get("start_time", ""))

                        detail_resp = client.get(f"/speeches/{speech_id}")
                        detail_resp.raise_for_status()
                        detail = detail_resp.json()

                        transcripts = detail.get("transcripts", detail.get("segments", []))
                        speakers = []
                        for segment in transcripts:
                            speakers.append({
                                "name": segment.get(
                                    "speaker", segment.get("speaker_name", "Speaker")
                                ),
                                "text": segment.get("text", segment.get("transcript", "")),
                                "timestamp": segment.get(
                                    "timestamp", segment.get("start_time", "")
                                ),
                            })

                        if not speakers:
                            continue

                        md = transcript_to_markdown(title=title, date=created, speakers=speakers)
                        safe_name = title.replace("/", "_").replace("\\", "_")[:80].strip()
                        dest = output_dir / f"{safe_name}_{speech_id[:8]}.md"
                        dest.write_text(md, encoding="utf-8")
                        downloaded.append(dest)
                        logger.info(f"Downloaded Otter transcript: {title} ({speech_id})")
                    except Exception as e:
                        logger.warning(
                            f"Failed to process Otter transcript {speech.get('title', '?')}: {e}"
                        )
        except Exception as e:
            logger.warning(f"Otter.ai API error: {e}")

        return downloaded

    return await asyncio.to_thread(_fetch_and_save)
