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
