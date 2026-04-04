# M5: Course/Material Auto-Generation — Design Spec

**Goal:** Let users generate structured training courses from their knowledge base by providing a title, target audience, and learning objectives. Outputs both markdown files and an interactive HTML course.

**Strategy:** Prompt-guided generation — the user describes what course they want, the LLM plans a curriculum from KB content, then renders it as both markdown and self-contained HTML. Async job model (like file ingestion).

---

## 1. Course Planner

New module `openraven/src/openraven/courses/planner.py`.

Takes user input (title, audience, objectives) + the KB entity graph. Uses the LLM to generate a structured curriculum outline:

```python
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
```

The planner queries the KB graph for entities related to the user's prompt, then asks the LLM to organize them into a logical learning sequence.

---

## 2. Course Renderer

New module `openraven/src/openraven/courses/renderer.py`.

Takes a `CurriculumOutline` + KB access (via `pipeline.ask_with_sources`) and generates content for each chapter by querying the KB for each section's key concepts.

### Markdown Output

Directory structure per course:
```
courses/{course_id}/
├── README.md           # Course overview: title, audience, objectives, TOC
├── 01-chapter-title.md # Chapter with sections, KB-sourced content, citations
├── 02-chapter-title.md
├── ...
└── course.html         # Interactive HTML version
```

Each chapter markdown includes:
- Chapter title and learning objectives
- Sections with content sourced from KB (with `[Source: document]` citations)
- Key takeaways summary
- Review questions (LLM-generated based on content)

### Interactive HTML Output

New module `openraven/src/openraven/courses/html_template.py`.

Single self-contained HTML file (`course.html`) with:
- Navigation sidebar (chapter list with progress indicators)
- Chapter content area with sections
- Progress tracking via localStorage (chapters marked as read)
- Review questions at end of each chapter (show/hide answers)
- Light/dark theme toggle
- "Powered by OpenRaven" footer
- Vanilla HTML/JS/CSS — no build step, no dependencies
- All user-provided strings HTML-escaped (XSS-safe)

---

## 3. Generation Flow

```
User: POST /api/courses/generate {title, audience, objectives}
  → Create async job (like ingest)
  → Planner: query KB graph for relevant entities
  → Planner: LLM generates CurriculumOutline
  → Renderer: for each chapter, query KB for section content
  → Renderer: LLM generates chapter text with citations
  → Renderer: generate markdown files
  → Renderer: generate HTML course
  → Save to working_dir/courses/{course_id}/
  → Job complete
```

---

## 4. API Endpoints

```
POST   /api/courses/generate          → {title, audience, objectives} → {job_id}
GET    /api/courses/generate/{job_id} → {status, progress, course_id}
GET    /api/courses                   → list all generated courses
GET    /api/courses/{id}              → course metadata (title, chapters, created_at)
GET    /api/courses/{id}/download     → zip download (markdown + HTML)
DELETE /api/courses/{id}              → delete course
```

---

## 5. UI — CoursesPage

New `openraven-ui/src/pages/CoursesPage.tsx`:

- Generation form: title input, audience input, objectives textarea
- "Generate Course" button → async job with progress indicator
- Course list: title, chapter count, created date
- Per-course: download zip, delete
- Nav link between "Agents" and "Status"

---

## 6. File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/courses/__init__.py` | Create | Package init |
| `openraven/src/openraven/courses/planner.py` | Create | CurriculumOutline, plan_curriculum() |
| `openraven/src/openraven/courses/renderer.py` | Create | render_markdown(), render_html() |
| `openraven/src/openraven/courses/html_template.py` | Create | Interactive HTML course template |
| `openraven/src/openraven/api/server.py` | Modify | Course generation + management endpoints |
| `openraven/tests/test_courses.py` | Create | Planner, renderer, API tests |
| `openraven-ui/src/pages/CoursesPage.tsx` | Create | Course generation UI |
| `openraven-ui/src/App.tsx` | Modify | Route + nav link |
| `openraven-ui/server/index.ts` | Modify | Proxy route |

---

## 7. Tests

- Planner: curriculum outline has chapters, key_concepts reference real entities
- Renderer: markdown output has README + chapter files, HTML output is valid
- HTML template: XSS-safe, contains navigation structure
- API: generate returns job_id, status endpoint works, list/download/delete
- ~15 new tests

---

## 8. Dependencies

- No new Python packages (uses existing OpenAI-compat client for LLM)
- No new JS packages
- Courses stored as files in `working_dir/courses/`
