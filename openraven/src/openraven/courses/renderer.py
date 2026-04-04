from __future__ import annotations

import logging
import re

from openraven.courses.planner import CurriculumOutline

logger = logging.getLogger(__name__)


def render_readme(outline: CurriculumOutline) -> str:
    """Render a README.md with course overview, audience, objectives, and TOC."""
    lines = [
        f"# {outline.title}",
        "",
        f"**Target Audience:** {outline.audience}",
        "",
        "## Learning Objectives",
        "",
    ]
    for obj in outline.objectives:
        lines.append(f"- {obj}")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")
    for i, ch in enumerate(outline.chapters, 1):
        slug = _slugify(ch.title)
        lines.append(f"{i}. [{ch.title}]({i:02d}-{slug}.md)")
    lines.append("")
    return "\n".join(lines)


def render_chapter_markdown(
    chapter_title: str,
    chapter_num: int,
    sections: list[dict],
    key_takeaways: list[str],
    review_questions: list[str],
) -> str:
    """Render a single chapter as markdown with sections, takeaways, and review questions."""
    lines = [
        f"# {chapter_title}",
        "",
    ]

    for section in sections:
        lines.append(f"## {section['heading']}")
        lines.append("")
        lines.append(section["content"])
        lines.append("")

    lines.append("## Key Takeaways")
    lines.append("")
    for takeaway in key_takeaways:
        lines.append(f"- {takeaway}")
    lines.append("")

    lines.append("## Review Questions")
    lines.append("")
    for i, q in enumerate(review_questions, 1):
        lines.append(f"{i}. {q}")
    lines.append("")

    return "\n".join(lines)


def _slugify(text: str) -> str:
    """Convert a chapter title to a filename-safe slug."""
    # Remove "Chapter N: " prefix if present
    text = re.sub(r"^Chapter\s+\d+:\s*", "", text)
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug
