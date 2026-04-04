from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import openai

from openraven.courses.html_template import render_course_html
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


CHAPTER_PROMPT = """\
You are a course content enhancer. Given raw section content sourced from a knowledge base,
generate key takeaways and review questions for a chapter.

Chapter: {chapter_title}
Section content:
{section_content}

Respond in this exact JSON format:
{{
  "key_takeaways": ["takeaway 1", "takeaway 2"],
  "review_questions": [
    {{"question": "Question text?", "answer": "Answer text."}}
  ]
}}
"""


async def generate_course(
    outline: CurriculumOutline,
    ask_fn: Callable,
    output_dir: Path,
    api_key: str,
    model: str = "gemini-2.5-flash",
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
    on_progress: Callable[[int, int], Any] | None = None,
) -> Path:
    """Generate a complete course: markdown chapters + README + HTML.

    Args:
        outline: CurriculumOutline from the planner.
        ask_fn: Async callable that queries the KB (pipeline.ask_with_sources signature).
        output_dir: Base directory for courses (e.g., working_dir/courses).
        api_key: LLM API key.
        model: LLM model name.
        base_url: OpenAI-compat base URL.
        on_progress: Optional callback(chapters_done, chapters_total).

    Returns:
        Path to the generated course directory.
    """
    course_id = str(uuid.uuid4())[:8]
    course_dir = Path(output_dir) / course_id
    course_dir.mkdir(parents=True, exist_ok=True)

    client = openai.AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)

    # Generate README
    readme_md = render_readme(outline)
    (course_dir / "README.md").write_text(readme_md, encoding="utf-8")

    html_chapters = []

    for i, chapter in enumerate(outline.chapters, 1):
        # Query KB for each section's content
        sections = []
        raw_content_parts = []
        for section_title in chapter.sections:
            query = f"{section_title} {' '.join(chapter.key_concepts)}"
            result = await ask_fn(query, mode="mix")
            content = result.answer
            # Add source citations if available
            if hasattr(result, "sources") and result.sources:
                source_names = []
                for s in result.sources:
                    name = s["document"] if isinstance(s, dict) else s.document
                    source_names.append(name)
                if source_names:
                    content += " [Source: " + ", ".join(source_names) + "]"
            sections.append({"heading": section_title, "content": content})
            raw_content_parts.append(content)

        # Ask LLM for takeaways and review questions
        section_content_text = "\n\n".join(
            f"### {s['heading']}\n{s['content']}" for s in sections
        )
        prompt = CHAPTER_PROMPT.format(
            chapter_title=chapter.title, section_content=section_content_text,
        )
        response = await client.chat.completions.create(
            model=model, max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        llm_content = response.choices[0].message.content
        if "```json" in llm_content:
            llm_content = llm_content.split("```json")[1].split("```")[0]
        elif "```" in llm_content:
            llm_content = llm_content.split("```")[1].split("```")[0]

        try:
            extras = json.loads(llm_content.strip())
        except json.JSONDecodeError:
            logger.warning(f"LLM returned invalid JSON for chapter {chapter.title}, using defaults")
            extras = {}
        key_takeaways = extras.get("key_takeaways", [])
        review_questions_raw = extras.get("review_questions", [])

        # Render chapter markdown
        chapter_md = render_chapter_markdown(
            chapter_title=chapter.title,
            chapter_num=i,
            sections=sections,
            key_takeaways=key_takeaways,
            review_questions=[
                q["question"] if isinstance(q, dict) else q for q in review_questions_raw
            ],
        )
        slug = _slugify(chapter.title)
        filename = f"{i:02d}-{slug}.md"
        (course_dir / filename).write_text(chapter_md, encoding="utf-8")

        # Collect for HTML
        html_chapters.append({
            "title": chapter.title,
            "sections": sections,
            "review_questions": review_questions_raw if review_questions_raw else [],
        })

        if on_progress:
            on_progress(i, len(outline.chapters))

    # Render HTML course
    html_content = render_course_html(
        title=outline.title,
        audience=outline.audience,
        chapters=html_chapters,
    )
    (course_dir / "course.html").write_text(html_content, encoding="utf-8")

    # Save metadata
    from datetime import datetime, timezone
    metadata = {
        "id": course_id,
        "title": outline.title,
        "audience": outline.audience,
        "objectives": outline.objectives,
        "chapters": [
            {"title": ch.title, "sections": ch.sections, "key_concepts": ch.key_concepts}
            for ch in outline.chapters
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (course_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return course_dir


def _slugify(text: str) -> str:
    """Convert a chapter title to a filename-safe slug."""
    # Remove "Chapter N: " prefix if present
    text = re.sub(r"^Chapter\s+\d+:\s*", "", text)
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug
