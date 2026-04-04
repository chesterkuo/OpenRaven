from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# --- Task 1: Planner tests ---

def test_chapter_outline_fields() -> None:
    from openraven.courses.planner import ChapterOutline
    ch = ChapterOutline(
        title="Introduction",
        sections=["What is X", "Why X matters"],
        key_concepts=["Concept A", "Concept B"],
    )
    assert ch.title == "Introduction"
    assert len(ch.sections) == 2
    assert "Concept A" in ch.key_concepts


def test_curriculum_outline_fields() -> None:
    from openraven.courses.planner import ChapterOutline, CurriculumOutline
    outline = CurriculumOutline(
        title="Intro to AI",
        audience="Engineers",
        objectives=["Understand ML basics"],
        chapters=[
            ChapterOutline(title="Ch1", sections=["S1"], key_concepts=["ML"]),
        ],
    )
    assert outline.title == "Intro to AI"
    assert outline.audience == "Engineers"
    assert len(outline.chapters) == 1
    assert outline.chapters[0].title == "Ch1"


@pytest.mark.asyncio
async def test_plan_curriculum_returns_outline() -> None:
    from openraven.courses.planner import CurriculumOutline, plan_curriculum

    mock_llm_response = json.dumps({
        "chapters": [
            {
                "title": "Chapter 1: Foundations",
                "sections": ["What is Event-Driven Architecture", "Key Benefits"],
                "key_concepts": ["Apache Kafka", "Event Sourcing"],
            },
            {
                "title": "Chapter 2: Implementation",
                "sections": ["Setting Up Kafka", "Consumer Patterns"],
                "key_concepts": ["Kafka", "CQRS"],
            },
        ]
    })

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=mock_llm_response))]
    )

    with patch("openraven.courses.planner.openai.AsyncOpenAI", return_value=mock_client):
        outline = await plan_curriculum(
            title="Event-Driven Architecture",
            audience="Backend Engineers",
            objectives=["Understand EDA patterns", "Implement Kafka"],
            entity_names=["Apache Kafka", "CQRS", "Event Sourcing"],
            api_key="test-key",
            model="gemini-2.5-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    assert isinstance(outline, CurriculumOutline)
    assert outline.title == "Event-Driven Architecture"
    assert outline.audience == "Backend Engineers"
    assert len(outline.chapters) == 2
    assert outline.chapters[0].title == "Chapter 1: Foundations"
    assert "Apache Kafka" in outline.chapters[0].key_concepts


@pytest.mark.asyncio
async def test_plan_curriculum_handles_markdown_json() -> None:
    """LLM sometimes wraps JSON in markdown code fences."""
    from openraven.courses.planner import plan_curriculum

    wrapped = "```json\n" + json.dumps({
        "chapters": [
            {"title": "Ch1", "sections": ["S1"], "key_concepts": ["C1"]},
        ]
    }) + "\n```"

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=wrapped))]
    )

    with patch("openraven.courses.planner.openai.AsyncOpenAI", return_value=mock_client):
        outline = await plan_curriculum(
            title="Test", audience="Devs", objectives=["Learn"],
            entity_names=["C1"], api_key="k", model="m", base_url="http://x",
        )

    assert len(outline.chapters) == 1
    assert outline.chapters[0].title == "Ch1"


# --- Task 2: Markdown renderer tests ---

def test_render_readme() -> None:
    from openraven.courses.planner import ChapterOutline, CurriculumOutline
    from openraven.courses.renderer import render_readme

    outline = CurriculumOutline(
        title="Event-Driven Architecture",
        audience="Backend Engineers",
        objectives=["Understand EDA", "Implement Kafka"],
        chapters=[
            ChapterOutline(title="Chapter 1: Intro", sections=["What is EDA"], key_concepts=["EDA"]),
            ChapterOutline(title="Chapter 2: Kafka", sections=["Setup"], key_concepts=["Kafka"]),
        ],
    )
    md = render_readme(outline)
    assert "# Event-Driven Architecture" in md
    assert "Backend Engineers" in md
    assert "Understand EDA" in md
    assert "Chapter 1: Intro" in md
    assert "Chapter 2: Kafka" in md


def test_render_chapter_markdown() -> None:
    from openraven.courses.renderer import render_chapter_markdown

    md = render_chapter_markdown(
        chapter_title="Chapter 1: Foundations",
        chapter_num=1,
        sections=[
            {"heading": "What is EDA", "content": "EDA is a pattern [Source: arch-doc.md]"},
            {"heading": "Benefits", "content": "Scalability and decoupling."},
        ],
        key_takeaways=["EDA enables scalability", "Kafka is the standard tool"],
        review_questions=["What is event sourcing?", "Why use Kafka?"],
    )
    assert "# Chapter 1: Foundations" in md
    assert "## What is EDA" in md
    assert "[Source: arch-doc.md]" in md
    assert "Key Takeaways" in md
    assert "EDA enables scalability" in md
    assert "Review Questions" in md
    assert "What is event sourcing?" in md


def test_render_chapter_markdown_writes_file(tmp_path: Path) -> None:
    from openraven.courses.renderer import render_chapter_markdown

    md = render_chapter_markdown(
        chapter_title="Chapter 1: Intro",
        chapter_num=1,
        sections=[{"heading": "S1", "content": "Content here."}],
        key_takeaways=["Takeaway 1"],
        review_questions=["Q1?"],
    )
    out = tmp_path / "01-intro.md"
    out.write_text(md, encoding="utf-8")
    assert out.exists()
    assert "# Chapter 1: Intro" in out.read_text(encoding="utf-8")


# --- Task 3: HTML template tests ---

def test_render_course_html_basic() -> None:
    from openraven.courses.html_template import render_course_html

    html_out = render_course_html(
        title="Test Course",
        audience="Developers",
        chapters=[
            {
                "title": "Chapter 1: Intro",
                "sections": [
                    {"heading": "What is X", "content": "X is a thing."},
                ],
                "review_questions": [
                    {"question": "What is X?", "answer": "X is a thing."},
                ],
            },
        ],
    )
    assert "<!DOCTYPE html>" in html_out
    assert "Test Course" in html_out
    assert "Chapter 1: Intro" in html_out
    assert "What is X" in html_out
    assert "Powered by" in html_out
    assert "OpenRaven" in html_out


def test_render_course_html_xss_safe() -> None:
    from openraven.courses.html_template import render_course_html

    html_out = render_course_html(
        title='<script>alert("xss")</script>',
        audience='<img onerror="alert(1)">',
        chapters=[
            {
                "title": '<b onmouseover="hack()">Ch1</b>',
                "sections": [
                    {"heading": "S1", "content": "Safe content."},
                ],
                "review_questions": [],
            },
        ],
    )
    assert '<script>alert("xss")</script>' not in html_out
    assert "&lt;script&gt;" in html_out
    assert 'onerror="alert(1)"' not in html_out
    assert 'onmouseover="hack()"' not in html_out


def test_render_course_html_has_navigation() -> None:
    from openraven.courses.html_template import render_course_html

    html_out = render_course_html(
        title="Nav Test",
        audience="Testers",
        chapters=[
            {"title": "Ch1", "sections": [{"heading": "S1", "content": "C1"}], "review_questions": []},
            {"title": "Ch2", "sections": [{"heading": "S2", "content": "C2"}], "review_questions": []},
        ],
    )
    assert "nav" in html_out.lower() or "sidebar" in html_out.lower()
    assert "Ch1" in html_out
    assert "Ch2" in html_out


def test_render_course_html_has_theme_toggle() -> None:
    from openraven.courses.html_template import render_course_html

    html_out = render_course_html(
        title="Theme Test", audience="All",
        chapters=[{"title": "Ch1", "sections": [{"heading": "S", "content": "C"}], "review_questions": []}],
    )
    assert "theme" in html_out.lower()
    assert "localStorage" in html_out


def test_render_course_html_has_progress_tracking() -> None:
    from openraven.courses.html_template import render_course_html

    html_out = render_course_html(
        title="Progress Test", audience="All",
        chapters=[{"title": "Ch1", "sections": [{"heading": "S", "content": "C"}], "review_questions": []}],
    )
    assert "localStorage" in html_out
    assert "progress" in html_out.lower() or "read" in html_out.lower()


def test_render_course_html_uses_textcontent() -> None:
    """HTML template must use textContent not innerHTML for user-provided strings."""
    from openraven.courses.html_template import render_course_html

    html_out = render_course_html(
        title="Safe", audience="All",
        chapters=[{"title": "Ch1", "sections": [{"heading": "S", "content": "C"}], "review_questions": []}],
    )
    # The JS portion should not use innerHTML for dynamic content
    # (static template construction is fine since we HTML-escape all user data)
    assert "innerHTML" not in html_out
