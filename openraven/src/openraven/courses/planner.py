from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import openai

logger = logging.getLogger(__name__)


@dataclass
class ChapterOutline:
    title: str
    sections: list[str]       # Section titles
    key_concepts: list[str]   # Entity names from KB to cover


@dataclass
class CurriculumOutline:
    title: str
    audience: str
    objectives: list[str]
    chapters: list[ChapterOutline]


PLAN_PROMPT = """\
You are a curriculum designer. Given a course title, target audience, learning objectives,
and a list of available knowledge base entities, design a structured course outline.

Rules:
1. Organize entities into a logical learning sequence (foundational → advanced)
2. Each chapter should cover 2-5 sections
3. key_concepts MUST reference entity names from the provided list
4. Create 3-8 chapters depending on the breadth of the topic
5. Section titles should be specific and descriptive

Course Title: {title}
Target Audience: {audience}
Learning Objectives:
{objectives}

Available KB Entities:
{entities}

Respond in this exact JSON format:
{{
  "chapters": [
    {{
      "title": "Chapter N: Title",
      "sections": ["Section title 1", "Section title 2"],
      "key_concepts": ["entity_name_1", "entity_name_2"]
    }}
  ]
}}
"""


async def plan_curriculum(
    title: str,
    audience: str,
    objectives: list[str],
    entity_names: list[str],
    api_key: str,
    model: str = "gemini-2.5-flash",
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> CurriculumOutline:
    """Use the LLM to generate a structured curriculum outline from KB entities."""
    objectives_text = "\n".join(f"- {o}" for o in objectives)
    entities_text = "\n".join(f"- {e}" for e in entity_names)

    prompt = PLAN_PROMPT.format(
        title=title, audience=audience,
        objectives=objectives_text, entities=entities_text,
    )

    client = openai.AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)
    response = await client.chat.completions.create(
        model=model, max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    data = json.loads(content.strip())

    chapters = [
        ChapterOutline(
            title=ch["title"],
            sections=ch["sections"],
            key_concepts=ch.get("key_concepts", []),
        )
        for ch in data["chapters"]
    ]

    return CurriculumOutline(
        title=title, audience=audience,
        objectives=objectives, chapters=chapters,
    )
