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
