# M5: Course/Material Auto-Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users generate structured training courses from their knowledge base by providing a title, target audience, and learning objectives. Outputs both markdown files and an interactive HTML course. Async job model (like file ingestion).

**Architecture:** A `courses` package contains a planner (LLM-driven curriculum outlining), a renderer (markdown + HTML generation), and an HTML template module. The existing FastAPI server gains course generation/management endpoints (`/api/courses/*`). An async job tracks generation progress. Course files are stored under `working_dir/courses/{course_id}/`. The UI adds a CoursesPage with a generation form and course list.

**Tech Stack:** Python (FastAPI, openai, dataclasses), TypeScript/React (CoursesPage UI). No new Python/JS dependencies. Uses existing OpenAI-compat client pattern for LLM calls. Gemini default, Ollama supported.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/courses/__init__.py` | Create | Package init |
| `openraven/src/openraven/courses/planner.py` | Create | ChapterOutline, CurriculumOutline dataclasses, plan_curriculum() |
| `openraven/src/openraven/courses/renderer.py` | Create | render_markdown(), CourseRenderer orchestrator |
| `openraven/src/openraven/courses/html_template.py` | Create | render_course_html() — interactive self-contained HTML |
| `openraven/src/openraven/api/server.py` | Modify | Course generation + management endpoints (6 routes) |
| `openraven/src/openraven/config.py` | Modify | Add courses_dir property |
| `openraven/tests/test_courses.py` | Create | Planner, renderer, HTML template, API tests (~15 tests) |
| `openraven-ui/src/pages/CoursesPage.tsx` | Create | Course generation form + course list UI |
| `openraven-ui/src/App.tsx` | Modify | Add /courses route + nav link between "Agents" and "Status" |
| `openraven-ui/server/index.ts` | Modify | Add /api/courses proxy route |

---

## Task 1: Course Planner — CurriculumOutline + plan_curriculum

**Files:**
- Create: `openraven/src/openraven/courses/__init__.py`
- Create: `openraven/src/openraven/courses/planner.py`
- Create: `openraven/tests/test_courses.py` (planner tests only — extended in later tasks)

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_courses.py`:

```python
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
```

- [ ] **Step 2: Verify tests fail**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py -x --tb=short 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'openraven.courses'`

- [ ] **Step 3: Implement planner**

Create `openraven/src/openraven/courses/__init__.py`:

```python
```

Create `openraven/src/openraven/courses/planner.py`:

```python
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
```

- [ ] **Step 4: Verify tests pass**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py -x --tb=short 2>&1 | tail -10
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/courses/__init__.py openraven/src/openraven/courses/planner.py openraven/tests/test_courses.py && git commit -m "feat(courses): add curriculum planner with CurriculumOutline dataclass and plan_curriculum"
```

---

## Task 2: Markdown Renderer — render_markdown

**Files:**
- Create: `openraven/src/openraven/courses/renderer.py`
- Modify: `openraven/tests/test_courses.py`

- [ ] **Step 1: Write failing tests**

Append to `openraven/tests/test_courses.py`:

```python
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
```

- [ ] **Step 2: Verify tests fail**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py::test_render_readme -x --tb=short 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'render_readme' from 'openraven.courses.renderer'`

- [ ] **Step 3: Implement renderer**

Create `openraven/src/openraven/courses/renderer.py`:

```python
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
```

- [ ] **Step 4: Verify tests pass**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py -k "render" -x --tb=short 2>&1 | tail -10
```

Expected: all 3 renderer tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/courses/renderer.py openraven/tests/test_courses.py && git commit -m "feat(courses): add markdown renderer with render_readme and render_chapter_markdown"
```

---

## Task 3: Interactive HTML Template — XSS-safe, self-contained

**Files:**
- Create: `openraven/src/openraven/courses/html_template.py`
- Modify: `openraven/tests/test_courses.py`

- [ ] **Step 1: Write failing tests**

Append to `openraven/tests/test_courses.py`:

```python
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
    assert "<script>" not in html_out
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
```

- [ ] **Step 2: Verify tests fail**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py::test_render_course_html_basic -x --tb=short 2>&1 | tail -10
```

Expected: `ModuleNotFoundError: No module named 'openraven.courses.html_template'`

- [ ] **Step 3: Implement HTML template**

Create `openraven/src/openraven/courses/html_template.py`:

```python
from __future__ import annotations

import html
import json


def render_course_html(
    title: str,
    audience: str,
    chapters: list[dict],
) -> str:
    """Render an interactive self-contained HTML course.

    All user-provided strings are HTML-escaped to prevent XSS.
    The JS uses textContent (not innerHTML) for dynamic content rendering.

    Args:
        title: Course title.
        audience: Target audience description.
        chapters: List of dicts with keys: title, sections (list of {heading, content}),
                  review_questions (list of {question, answer}).
    """
    safe_title = html.escape(title)
    safe_audience = html.escape(audience)

    # Build sidebar nav items and chapter content sections
    nav_items = []
    content_sections = []

    for i, ch in enumerate(chapters):
        ch_id = f"ch-{i}"
        safe_ch_title = html.escape(ch["title"])

        nav_items.append(
            f'<li class="nav-item" data-chapter="{ch_id}">'
            f'<span class="nav-check" id="check-{ch_id}"></span>'
            f'<button class="nav-btn" onclick="showChapter(\'{ch_id}\')">'
            f'{safe_ch_title}</button></li>'
        )

        sections_html = []
        for sec in ch.get("sections", []):
            safe_heading = html.escape(sec["heading"])
            safe_content = html.escape(sec["content"])
            sections_html.append(
                f'<div class="section"><h3>{safe_heading}</h3>'
                f'<p>{safe_content}</p></div>'
            )

        questions_html = []
        for qi, qa in enumerate(ch.get("review_questions", [])):
            safe_q = html.escape(qa.get("question", ""))
            safe_a = html.escape(qa.get("answer", ""))
            questions_html.append(
                f'<div class="qa">'
                f'<p class="question">{qi + 1}. {safe_q}</p>'
                f'<button class="reveal-btn" onclick="toggleAnswer(\'ans-{ch_id}-{qi}\')">Show Answer</button>'
                f'<p class="answer" id="ans-{ch_id}-{qi}" style="display:none">{safe_a}</p>'
                f'</div>'
            )

        review_block = ""
        if questions_html:
            review_block = '<div class="review"><h3>Review Questions</h3>' + "\n".join(questions_html) + '</div>'

        content_sections.append(
            f'<div class="chapter" id="{ch_id}" style="display:none">'
            f'<h2>{safe_ch_title}</h2>'
            + "\n".join(sections_html)
            + review_block
            + f'<button class="mark-read-btn" onclick="markRead(\'{ch_id}\')">Mark as Read</button>'
            f'</div>'
        )

    nav_html = "\n".join(nav_items)
    content_html = "\n".join(content_sections)
    chapter_count = len(chapters)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  :root {{
    --bg: #fef9ef; --bg-surface: #ffffff; --bg-sidebar: #fff8e8;
    --text: #1f1f1f; --text-muted: #666; --brand: #fa520f;
    --border: #e5e5e5; --shadow: rgba(127,99,21,0.08) -4px 8px 20px;
  }}
  .dark {{
    --bg: #0a0a0a; --bg-surface: #1a1a1a; --bg-sidebar: #111;
    --text: #e5e5e5; --text-muted: #999; --brand: #fb6424;
    --border: #333; --shadow: rgba(0,0,0,0.3) -4px 8px 20px;
  }}

  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); display: flex; min-height: 100vh; }}

  .sidebar {{ width: 280px; background: var(--bg-sidebar); border-right: 1px solid var(--border);
              padding: 24px 16px; overflow-y: auto; flex-shrink: 0; }}
  .sidebar h1 {{ font-size: 1.15rem; margin-bottom: 4px; }}
  .sidebar .audience {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px; }}
  .sidebar .progress-bar {{ height: 4px; background: var(--border); margin-bottom: 16px; border-radius: 2px; }}
  .sidebar .progress-fill {{ height: 100%; background: var(--brand); border-radius: 2px; transition: width 0.3s; }}
  .sidebar ul {{ list-style: none; }}
  .nav-item {{ margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }}
  .nav-check {{ width: 16px; font-size: 0.75rem; }}
  .nav-btn {{ background: none; border: none; color: var(--text); font-size: 0.9rem;
              cursor: pointer; text-align: left; padding: 6px 8px; width: 100%; border-radius: 4px; }}
  .nav-btn:hover {{ background: var(--bg-surface); }}
  .nav-item.active .nav-btn {{ color: var(--brand); font-weight: 600; }}

  .main {{ flex: 1; padding: 32px 48px; max-width: 800px; overflow-y: auto; }}
  .chapter h2 {{ font-size: 1.5rem; margin-bottom: 16px; }}
  .section {{ margin-bottom: 24px; }}
  .section h3 {{ font-size: 1.1rem; margin-bottom: 8px; color: var(--brand); }}
  .section p {{ line-height: 1.7; }}
  .review {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--border); }}
  .review h3 {{ margin-bottom: 12px; }}
  .qa {{ margin-bottom: 12px; }}
  .question {{ font-weight: 600; margin-bottom: 4px; }}
  .answer {{ color: var(--text-muted); padding: 8px; background: var(--bg-sidebar); margin-top: 4px; border-radius: 4px; }}
  .reveal-btn {{ background: none; border: 1px solid var(--border); color: var(--text-muted);
                 padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }}
  .reveal-btn:hover {{ border-color: var(--brand); color: var(--brand); }}
  .mark-read-btn {{ margin-top: 24px; background: var(--brand); color: white; border: none;
                    padding: 10px 24px; border-radius: 6px; cursor: pointer; font-weight: 600; }}
  .mark-read-btn:hover {{ opacity: 0.9; }}
  .mark-read-btn.done {{ background: var(--border); color: var(--text-muted); cursor: default; }}

  .toolbar {{ position: fixed; top: 12px; right: 16px; z-index: 10; }}
  .theme-btn {{ background: var(--bg-surface); border: 1px solid var(--border); padding: 6px 12px;
                border-radius: 6px; cursor: pointer; color: var(--text); font-size: 0.85rem; }}

  .footer {{ position: fixed; bottom: 0; left: 0; right: 0; text-align: center;
             padding: 8px; font-size: 0.7rem; color: var(--text-muted); background: var(--bg); }}
  .footer a {{ color: var(--brand); text-decoration: none; }}

  .welcome {{ text-align: center; margin-top: 120px; }}
  .welcome h2 {{ font-size: 1.5rem; margin-bottom: 8px; }}
  .welcome p {{ color: var(--text-muted); }}
</style>
</head>
<body>
<div class="sidebar">
  <h1>{safe_title}</h1>
  <div class="audience">For: {safe_audience}</div>
  <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div>
  <nav><ul>{nav_html}</ul></nav>
</div>
<div class="main" id="main-content">
  <div class="welcome" id="welcome">
    <h2>Welcome</h2>
    <p>Select a chapter from the sidebar to begin.</p>
  </div>
  {content_html}
</div>
<div class="toolbar">
  <button class="theme-btn" onclick="toggleTheme()">Toggle Theme</button>
</div>
<div class="footer">Powered by <a href="https://github.com/chesterkuo/OpenRaven" target="_blank">OpenRaven</a></div>
<script>
var totalChapters = {chapter_count};
var readSet = JSON.parse(localStorage.getItem("course-progress-" + document.title) || "[]");

function showChapter(id) {{
  document.getElementById("welcome").style.display = "none";
  document.querySelectorAll(".chapter").forEach(function(el) {{ el.style.display = "none"; }});
  var target = document.getElementById(id);
  if (target) target.style.display = "block";
  document.querySelectorAll(".nav-item").forEach(function(el) {{
    el.classList.toggle("active", el.getAttribute("data-chapter") === id);
  }});
}}

function markRead(id) {{
  if (readSet.indexOf(id) === -1) {{
    readSet.push(id);
    localStorage.setItem("course-progress-" + document.title, JSON.stringify(readSet));
  }}
  updateProgress();
  var btn = document.querySelector("#" + id + " .mark-read-btn");
  if (btn) {{ btn.textContent = "Read"; btn.classList.add("done"); }}
}}

function updateProgress() {{
  readSet.forEach(function(id) {{
    var check = document.getElementById("check-" + id);
    if (check) check.textContent = "\\u2713";
    var btn = document.querySelector("#" + id + " .mark-read-btn");
    if (btn) {{ btn.textContent = "Read"; btn.classList.add("done"); }}
  }});
  var pct = totalChapters > 0 ? Math.round((readSet.length / totalChapters) * 100) : 0;
  document.getElementById("progress-fill").style.width = pct + "%";
}}

function toggleAnswer(id) {{
  var el = document.getElementById(id);
  if (el) el.style.display = el.style.display === "none" ? "block" : "none";
}}

function toggleTheme() {{
  document.documentElement.classList.toggle("dark");
  localStorage.setItem("course-theme", document.documentElement.classList.contains("dark") ? "dark" : "light");
}}

if (localStorage.getItem("course-theme") === "dark") document.documentElement.classList.add("dark");
updateProgress();
</script>
</body>
</html>"""
```

- [ ] **Step 4: Verify tests pass**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py -k "html" -x --tb=short 2>&1 | tail -10
```

Expected: all 6 HTML template tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/courses/html_template.py openraven/tests/test_courses.py && git commit -m "feat(courses): add interactive HTML course template with XSS protection and progress tracking"
```

---

## Task 4: Course Renderer — orchestrates planner + renderers

**Files:**
- Modify: `openraven/src/openraven/courses/renderer.py`
- Modify: `openraven/tests/test_courses.py`

- [ ] **Step 1: Write failing tests**

Append to `openraven/tests/test_courses.py`:

```python
# --- Task 4: CourseRenderer orchestrator tests ---

@pytest.mark.asyncio
async def test_generate_course_creates_directory(tmp_path: Path) -> None:
    from openraven.courses.planner import ChapterOutline, CurriculumOutline
    from openraven.courses.renderer import generate_course

    outline = CurriculumOutline(
        title="Test Course",
        audience="Developers",
        objectives=["Learn X"],
        chapters=[
            ChapterOutline(title="Chapter 1: Basics", sections=["Intro to X"], key_concepts=["X"]),
        ],
    )

    mock_ask = AsyncMock(return_value=MagicMock(
        answer="X is a framework for building apps. [Source: docs.md]",
        sources=[{"document": "docs.md", "excerpt": "X is...", "char_start": 0, "char_end": 50}],
    ))

    mock_llm_response = json.dumps({
        "key_takeaways": ["X is foundational"],
        "review_questions": [
            {"question": "What is X?", "answer": "A framework."}
        ],
    })
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=mock_llm_response))]
    )

    with patch("openraven.courses.renderer.openai.AsyncOpenAI", return_value=mock_client):
        course_dir = await generate_course(
            outline=outline,
            ask_fn=mock_ask,
            output_dir=tmp_path / "courses",
            api_key="test-key",
            model="gemini-2.5-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    assert course_dir.exists()
    assert (course_dir / "README.md").exists()
    assert (course_dir / "01-basics.md").exists()
    assert (course_dir / "course.html").exists()

    readme = (course_dir / "README.md").read_text(encoding="utf-8")
    assert "Test Course" in readme

    chapter_md = (course_dir / "01-basics.md").read_text(encoding="utf-8")
    assert "Chapter 1: Basics" in chapter_md

    course_html = (course_dir / "course.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in course_html
    assert "Test Course" in course_html
```

- [ ] **Step 2: Verify tests fail**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py::test_generate_course_creates_directory -x --tb=short 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'generate_course' from 'openraven.courses.renderer'`

- [ ] **Step 3: Implement generate_course**

Add to `openraven/src/openraven/courses/renderer.py` (after the existing functions):

```python
import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import openai

from openraven.courses.html_template import render_course_html
from openraven.courses.planner import CurriculumOutline


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

        extras = json.loads(llm_content.strip())
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
    metadata = {
        "id": course_id,
        "title": outline.title,
        "audience": outline.audience,
        "objectives": outline.objectives,
        "chapters": [
            {"title": ch.title, "sections": ch.sections, "key_concepts": ch.key_concepts}
            for ch in outline.chapters
        ],
    }
    (course_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return course_dir
```

- [ ] **Step 4: Verify tests pass**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py::test_generate_course_creates_directory -x --tb=short 2>&1 | tail -10
```

Expected: test passes.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/courses/renderer.py openraven/tests/test_courses.py && git commit -m "feat(courses): add generate_course orchestrator combining planner, markdown, and HTML renderers"
```

---

## Task 5: API Endpoints — generate, status, list, download, delete

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/src/openraven/config.py`
- Modify: `openraven/tests/test_courses.py`

- [ ] **Step 1: Write failing tests**

Append to `openraven/tests/test_courses.py`:

```python
# --- Task 5: API endpoint tests ---

from fastapi.testclient import TestClient


@pytest.fixture
def course_client(tmp_path: Path) -> TestClient:
    from openraven.api.server import create_app
    from openraven.config import RavenConfig
    config = RavenConfig(
        working_dir=tmp_path / "kb",
        gemini_api_key="test-key",
    )
    app = create_app(config)
    return TestClient(app)


def test_courses_list_empty(course_client: TestClient) -> None:
    res = course_client.get("/api/courses")
    assert res.status_code == 200
    assert res.json() == []


def test_courses_generate_missing_title(course_client: TestClient) -> None:
    res = course_client.post("/api/courses/generate", json={
        "audience": "Devs", "objectives": ["Learn X"]
    })
    assert res.status_code == 400


def test_courses_generate_returns_job_id(course_client: TestClient) -> None:
    res = course_client.post("/api/courses/generate", json={
        "title": "Test Course",
        "audience": "Developers",
        "objectives": ["Learn X"],
    })
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data


def test_courses_status_not_found(course_client: TestClient) -> None:
    res = course_client.get("/api/courses/generate/nonexistent")
    assert res.status_code == 404


def test_courses_get_not_found(course_client: TestClient) -> None:
    res = course_client.get("/api/courses/nonexistent")
    assert res.status_code == 404


def test_courses_delete_not_found(course_client: TestClient) -> None:
    res = course_client.delete("/api/courses/nonexistent")
    assert res.status_code == 404
```

- [ ] **Step 2: Verify tests fail**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py -k "courses_list or courses_generate or courses_status or courses_get or courses_delete" -x --tb=short 2>&1 | tail -15
```

Expected: 404 errors because `/api/courses` endpoints do not exist yet.

- [ ] **Step 3: Add courses_dir to config**

Add to `openraven/src/openraven/config.py` after the `ingestion_dir` property:

```python
    @property
    def courses_dir(self) -> Path:
        return self.working_dir / "courses"
```

- [ ] **Step 4: Add API endpoints to server.py**

Add to `openraven/src/openraven/api/server.py`, inside `create_app()` before `return app`, after the agent endpoints section:

```python
    # --- Course Generation ---

    @dataclass
    class CourseJob:
        job_id: str
        stage: str = "planning"
        chapters_total: int = 0
        chapters_done: int = 0
        course_id: str = ""
        error: str = ""

    course_jobs: dict[str, CourseJob] = {}

    @app.post("/api/courses/generate")
    async def courses_generate(body: dict, background_tasks: BackgroundTasks):
        from fastapi.responses import JSONResponse
        title = body.get("title", "").strip()
        audience = body.get("audience", "").strip()
        objectives = body.get("objectives", [])
        if not title:
            return JSONResponse({"error": "title is required"}, status_code=400)

        job_id = str(uuid.uuid4())[:8]
        job = CourseJob(job_id=job_id)
        course_jobs[job_id] = job

        async def run_generation() -> None:
            try:
                from openraven.courses.planner import plan_curriculum
                from openraven.courses.renderer import generate_course

                base_url = (
                    f"{config.ollama_base_url}/v1"
                    if config.llm_provider == "ollama"
                    else "https://generativelanguage.googleapis.com/v1beta/openai/"
                )

                # Get entity names from graph
                graph_stats = pipeline.graph.get_stats()
                entity_names = list(graph_stats.get("entities", {}).keys())[:100]

                job.stage = "planning"
                outline = await plan_curriculum(
                    title=title, audience=audience or "General",
                    objectives=objectives if objectives else [f"Learn about {title}"],
                    entity_names=entity_names,
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    base_url=base_url,
                )

                job.chapters_total = len(outline.chapters)
                job.stage = "generating"

                def on_progress(done: int, total: int) -> None:
                    job.chapters_done = done

                config.courses_dir.mkdir(parents=True, exist_ok=True)
                course_dir = await generate_course(
                    outline=outline,
                    ask_fn=pipeline.ask_with_sources,
                    output_dir=config.courses_dir,
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    base_url=base_url,
                    on_progress=on_progress,
                )

                job.course_id = course_dir.name
                job.stage = "done"
            except Exception as e:
                logger.error(f"Course generation failed: {e}", exc_info=True)
                job.stage = "error"
                job.error = str(e)

        background_tasks.add_task(run_generation)
        return {"job_id": job_id}

    @app.get("/api/courses/generate/{job_id}")
    async def courses_generate_status(job_id: str):
        from fastapi.responses import JSONResponse
        job = course_jobs.get(job_id)
        if not job:
            return JSONResponse({"error": "Job not found"}, status_code=404)
        return {
            "job_id": job.job_id,
            "stage": job.stage,
            "chapters_total": job.chapters_total,
            "chapters_done": job.chapters_done,
            "course_id": job.course_id,
            "error": job.error,
        }

    @app.get("/api/courses")
    async def courses_list():
        courses_dir = config.courses_dir
        if not courses_dir.exists():
            return []
        courses = []
        for d in sorted(courses_dir.iterdir()):
            meta_file = d / "metadata.json"
            if d.is_dir() and meta_file.exists():
                import json as _json
                meta = _json.loads(meta_file.read_text(encoding="utf-8"))
                # Get created_at from directory mtime
                import datetime
                created_at = datetime.datetime.fromtimestamp(
                    d.stat().st_mtime, tz=datetime.timezone.utc
                ).isoformat()
                courses.append({
                    "id": meta["id"],
                    "title": meta["title"],
                    "audience": meta.get("audience", ""),
                    "chapter_count": len(meta.get("chapters", [])),
                    "created_at": created_at,
                })
        return courses

    @app.get("/api/courses/{course_id}")
    async def courses_get(course_id: str):
        from fastapi.responses import JSONResponse
        course_dir = config.courses_dir / course_id
        meta_file = course_dir / "metadata.json"
        if not course_dir.exists() or not meta_file.exists():
            return JSONResponse({"error": "Course not found"}, status_code=404)
        import json as _json
        meta = _json.loads(meta_file.read_text(encoding="utf-8"))
        import datetime
        created_at = datetime.datetime.fromtimestamp(
            course_dir.stat().st_mtime, tz=datetime.timezone.utc
        ).isoformat()
        return {
            "id": meta["id"],
            "title": meta["title"],
            "audience": meta.get("audience", ""),
            "objectives": meta.get("objectives", []),
            "chapters": meta.get("chapters", []),
            "created_at": created_at,
        }

    @app.get("/api/courses/{course_id}/download")
    async def courses_download(course_id: str, background_tasks: BackgroundTasks):
        import os
        import zipfile
        from fastapi.responses import JSONResponse
        course_dir = config.courses_dir / course_id
        if not course_dir.exists():
            return JSONResponse({"error": "Course not found"}, status_code=404)
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(course_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(course_dir))
        background_tasks.add_task(os.unlink, tmp.name)
        import json as _json
        meta_file = course_dir / "metadata.json"
        safe_name = "course"
        if meta_file.exists():
            meta = _json.loads(meta_file.read_text(encoding="utf-8"))
            safe_name = meta.get("title", "course").replace(" ", "-").lower()[:40]
        return FileResponse(
            path=tmp.name, media_type="application/zip",
            filename=f"{safe_name}.zip",
        )

    @app.delete("/api/courses/{course_id}")
    async def courses_delete(course_id: str):
        import shutil
        from fastapi.responses import JSONResponse
        course_dir = config.courses_dir / course_id
        if not course_dir.exists():
            return JSONResponse({"error": "Course not found"}, status_code=404)
        shutil.rmtree(course_dir)
        return {"deleted": True}
```

- [ ] **Step 5: Verify tests pass**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py -k "courses_list or courses_generate or courses_status or courses_get or courses_delete" -x --tb=short 2>&1 | tail -15
```

Expected: all 6 API tests pass.

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/api/server.py openraven/src/openraven/config.py openraven/tests/test_courses.py && git commit -m "feat(api): add course generation, status, list, download, and delete endpoints"
```

---

## Task 6: CoursesPage UI + Routing + Proxy

**Files:**
- Create: `openraven-ui/src/pages/CoursesPage.tsx`
- Modify: `openraven-ui/src/App.tsx`
- Modify: `openraven-ui/server/index.ts`

- [ ] **Step 1: Create CoursesPage.tsx**

Create `openraven-ui/src/pages/CoursesPage.tsx`:

```tsx
import { useEffect, useState } from "react";

interface Course {
  id: string;
  title: string;
  audience: string;
  chapter_count: number;
  created_at: string;
}

interface GenerateJob {
  job_id: string;
  stage: string;
  chapters_total: number;
  chapters_done: number;
  course_id: string;
  error: string;
}

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [title, setTitle] = useState("");
  const [audience, setAudience] = useState("");
  const [objectives, setObjectives] = useState("");
  const [generating, setGenerating] = useState(false);
  const [job, setJob] = useState<GenerateJob | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadCourses();
  }, []);

  async function loadCourses() {
    try {
      const res = await fetch("/api/courses");
      setCourses(await res.json());
    } catch { /* ignore */ }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setGenerating(true);
    setError("");
    setJob(null);
    try {
      const res = await fetch("/api/courses/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          audience: audience.trim() || "General",
          objectives: objectives.trim()
            ? objectives.split("\n").map(o => o.trim()).filter(Boolean)
            : [],
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || "Generation failed"); setGenerating(false); return; }

      const jobId = data.job_id;
      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/courses/generate/${jobId}`);
          const statusData: GenerateJob = await statusRes.json();
          setJob(statusData);
          if (statusData.stage === "done" || statusData.stage === "error") {
            clearInterval(poll);
            setGenerating(false);
            if (statusData.stage === "error") setError(statusData.error || "Generation failed");
            else { setTitle(""); setAudience(""); setObjectives(""); loadCourses(); }
          }
        } catch { /* ignore polling errors */ }
      }, 2000);
      setTimeout(() => { clearInterval(poll); setGenerating(false); }, 600_000);
    } catch {
      setError("Failed to start generation");
      setGenerating(false);
    }
  }

  async function handleDelete(courseId: string) {
    try {
      await fetch(`/api/courses/${courseId}`, { method: "DELETE" });
      loadCourses();
    } catch { /* ignore */ }
  }

  function handleDownload(courseId: string) {
    window.open(`/api/courses/${courseId}/download`, "_blank");
  }

  const progressText = job
    ? job.stage === "planning" ? "Planning curriculum..."
    : job.stage === "generating" ? `Generating chapters (${job.chapters_done}/${job.chapters_total})...`
    : job.stage === "done" ? "Complete!"
    : job.stage === "error" ? "Error"
    : job.stage
    : "";

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>
        Courses
      </h1>

      <div className="p-6 mb-8" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
        <h2 className="text-lg mb-4" style={{ color: "var(--color-text)" }}>Generate a Course</h2>
        <form onSubmit={handleGenerate}>
          <div className="mb-4">
            <label className="block text-sm mb-1" style={{ color: "var(--color-text-muted)" }}>
              Course Title *
            </label>
            <input
              type="text" value={title} onChange={e => setTitle(e.target.value)}
              placeholder="e.g., Introduction to Event-Driven Architecture"
              required
              className="w-full px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm mb-1" style={{ color: "var(--color-text-muted)" }}>
              Target Audience
            </label>
            <input
              type="text" value={audience} onChange={e => setAudience(e.target.value)}
              placeholder="e.g., Backend Engineers"
              className="w-full px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm mb-1" style={{ color: "var(--color-text-muted)" }}>
              Learning Objectives (one per line)
            </label>
            <textarea
              value={objectives} onChange={e => setObjectives(e.target.value)}
              placeholder={"Understand EDA patterns\nImplement Kafka consumers\nDesign event schemas"}
              rows={3}
              className="w-full px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)", resize: "vertical" }}
            />
          </div>
          <button
            type="submit" disabled={generating || !title.trim()}
            className="text-sm px-4 py-2 uppercase cursor-pointer disabled:opacity-50 disabled:cursor-default"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
          >
            {generating ? "Generating..." : "Generate Course"}
          </button>
        </form>

        {generating && progressText && (
          <div className="mt-4 text-sm" style={{ color: "var(--color-text-muted)" }}>
            {progressText}
            {job && job.stage === "generating" && job.chapters_total > 0 && (
              <div className="mt-2" style={{ height: 4, background: "var(--color-border)", borderRadius: 2 }}>
                <div style={{
                  height: "100%", borderRadius: 2,
                  background: "var(--color-brand)",
                  width: `${Math.round((job.chapters_done / job.chapters_total) * 100)}%`,
                  transition: "width 0.3s",
                }} />
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-4 text-sm" style={{ color: "var(--color-error)" }}>{error}</div>
        )}
      </div>

      {courses.length > 0 && (
        <div>
          <h2 className="text-lg mb-4" style={{ color: "var(--color-text)" }}>Generated Courses</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {courses.map(c => (
              <div key={c.id} className="p-4" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
                <h3 className="text-base mb-1" style={{ color: "var(--color-text)" }}>{c.title}</h3>
                <div className="text-xs mb-3" style={{ color: "var(--color-text-muted)" }}>
                  {c.chapter_count} chapters &middot; {c.audience} &middot; {new Date(c.created_at).toLocaleDateString()}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDownload(c.id)}
                    className="text-sm px-3 py-1 cursor-pointer"
                    style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}
                  >
                    Download
                  </button>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="text-sm px-3 py-1 cursor-pointer"
                    style={{ background: "var(--bg-surface-hover)", color: "var(--color-error)" }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {courses.length === 0 && !generating && (
        <div className="text-center py-12" style={{ color: "var(--color-text-muted)" }}>
          No courses generated yet. Fill in the form above and generate your first course.
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add route and nav link to App.tsx**

In `openraven-ui/src/App.tsx`:

Add import at top:
```tsx
import CoursesPage from "./pages/CoursesPage";
```

Add nav link after `<NavLink to="/agents" ...>Agents</NavLink>`:
```tsx
        <NavLink to="/courses" className={navLinkClass}>Courses</NavLink>
```

Add route after the agents Route:
```tsx
          <Route path="/courses" element={<CoursesPage />} />
```

- [ ] **Step 3: Add proxy route to server/index.ts**

In `openraven-ui/server/index.ts`, add after the agents proxy blocks (before the config proxy):

```typescript
// Proxy course endpoints to core API
app.all("/api/courses/*", async (c) => {
  try {
    const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
    const headers: Record<string, string> = {};
    const ct = c.req.header("content-type");
    if (ct) headers["content-type"] = ct;
    const body = c.req.method === "GET" || c.req.method === "HEAD" ? undefined : await c.req.text();
    const res = await fetch(url, { method: c.req.method, headers, body });
    const data = await res.json();
    return c.json(data, res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});
app.all("/api/courses", async (c) => {
  try {
    const url = `${CORE_API_URL}${c.req.path}`;
    const headers: Record<string, string> = {};
    const ct = c.req.header("content-type");
    if (ct) headers["content-type"] = ct;
    const body = c.req.method === "GET" || c.req.method === "HEAD" ? undefined : await c.req.text();
    const res = await fetch(url, { method: c.req.method, headers, body });
    const data = await res.json();
    return c.json(data, res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});
```

- [ ] **Step 4: Verify UI builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx tsc --noEmit 2>&1 | tail -10
```

Expected: no type errors.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/pages/CoursesPage.tsx openraven-ui/src/App.tsx openraven-ui/server/index.ts && git commit -m "feat(ui): add CoursesPage with generation form, progress tracking, and course list"
```

---

## Task 7: E2E Verification

- [ ] **Step 1: Run full test suite**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_courses.py -v --tb=short 2>&1 | tail -30
```

Expected: all ~15 tests pass (4 planner + 3 renderer + 6 HTML + 1 orchestrator + 6 API = 20 tests).

- [ ] **Step 2: Run existing tests to verify no regressions**

```bash
cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all existing tests still pass, total count increases by ~20.

- [ ] **Step 3: Verify UI builds cleanly**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx tsc --noEmit && npm run build 2>&1 | tail -10
```

Expected: no errors.

- [ ] **Step 4: Manual smoke test checklist**

Start the server and UI:
```bash
cd /home/ubuntu/source/OpenRaven && pm2 restart all
```

Verify in browser at `http://localhost:3000/courses`:
- [ ] Courses page loads with generation form
- [ ] Title field is required (submit button disabled when empty)
- [ ] "Generate Course" starts an async job with progress indicator
- [ ] After generation completes, course appears in the list
- [ ] Download button triggers zip download containing README.md, chapter files, and course.html
- [ ] course.html opens standalone with sidebar navigation, theme toggle, and progress tracking
- [ ] Delete button removes course from the list
- [ ] Nav bar shows "Courses" link between "Agents" and "Status"

- [ ] **Step 5: Final commit (if any fixes needed)**

```bash
cd /home/ubuntu/source/OpenRaven && git add -A && git status
```

Only commit if there are meaningful fixes. Do not commit if working tree is clean.
