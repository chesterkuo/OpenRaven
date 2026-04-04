from __future__ import annotations

import html


def render_chat_page(agent_id: str, agent_name: str, agent_description: str) -> str:
    """Render the agent chat page as self-contained HTML.

    All user-provided strings are HTML-escaped to prevent XSS.
    The chat JS uses textContent (not innerHTML) for message rendering.
    """
    safe_name = html.escape(agent_name)
    safe_desc = html.escape(agent_description)
    safe_id = html.escape(agent_id)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_name} — OpenRaven Agent</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #030712; color: #f3f4f6; height: 100vh; display: flex; flex-direction: column; }}
  .header {{ border-bottom: 1px solid #1f2937; padding: 16px 24px; }}
  .header h1 {{ font-size: 1.25rem; font-weight: 700; }}
  .header p {{ font-size: 0.875rem; color: #9ca3af; margin-top: 4px; }}
  .messages {{ flex: 1; overflow-y: auto; padding: 16px 24px; }}
  .msg {{ margin-bottom: 12px; max-width: 80%; }}
  .msg.user {{ margin-left: auto; background: #1e40af; padding: 8px 14px; border-radius: 12px 12px 0 12px; }}
  .msg.assistant {{ background: #1f2937; padding: 8px 14px; border-radius: 12px 12px 12px 0; }}
  .msg .sources {{ margin-top: 6px; padding-top: 6px; border-top: 1px solid #374151; font-size: 0.75rem; color: #6b7280; }}
  .msg .sources .src-item {{ color: #60a5fa; }}
  .form {{ border-top: 1px solid #1f2937; padding: 12px 24px; display: flex; gap: 12px; }}
  .form input {{ flex: 1; background: #111827; border: 1px solid #374151; border-radius: 8px;
                 padding: 10px 16px; color: #f3f4f6; font-size: 0.9rem; outline: none; }}
  .form input:focus {{ border-color: #3b82f6; }}
  .form button {{ background: #2563eb; color: white; border: none; border-radius: 8px;
                  padding: 10px 20px; font-weight: 600; cursor: pointer; }}
  .form button:hover {{ background: #1d4ed8; }}
  .form button:disabled {{ background: #374151; color: #6b7280; cursor: default; }}
  .footer {{ text-align: center; padding: 8px; font-size: 0.7rem; color: #4b5563; }}
  .footer a {{ color: #60a5fa; text-decoration: none; }}
  .typing {{ color: #6b7280; font-size: 0.875rem; padding: 0 24px 8px; }}
</style>
</head>
<body>
<div class="header">
  <h1>{safe_name}</h1>
  <p>{safe_desc}</p>
</div>
<div class="messages" id="messages"></div>
<div class="typing" id="typing" style="display:none">Thinking...</div>
<form class="form" id="form">
  <input type="text" id="input" placeholder="Ask a question..." autocomplete="off" />
  <button type="submit" id="btn">Ask</button>
</form>
<div class="footer">Powered by <a href="https://github.com/chesterkuo/OpenRaven" target="_blank">OpenRaven</a></div>
<script>
const agentId = "{safe_id}";
const msgs = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("input");
const btn = document.getElementById("btn");
const typing = document.getElementById("typing");

function addMsg(role, text, sources) {{
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  if (sources && sources.length > 0) {{
    const srcDiv = document.createElement("div");
    srcDiv.className = "sources";
    const label = document.createTextNode("Sources: ");
    srcDiv.appendChild(label);
    sources.forEach(function(s, i) {{
      if (i > 0) srcDiv.appendChild(document.createTextNode(", "));
      const span = document.createElement("span");
      span.className = "src-item";
      span.textContent = s.document;
      srcDiv.appendChild(span);
    }});
    div.appendChild(srcDiv);
  }}
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}}

form.addEventListener("submit", async function(e) {{
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  addMsg("user", q);
  btn.disabled = true;
  typing.style.display = "block";
  try {{
    const res = await fetch("/agents/" + agentId + "/ask", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{question: q}})
    }});
    const data = await res.json();
    if (res.ok) {{
      addMsg("assistant", data.answer, data.sources || []);
    }} else {{
      addMsg("assistant", data.error || "Error: " + res.status);
    }}
  }} catch (err) {{
    addMsg("assistant", "Error: Could not reach the agent.");
  }}
  typing.style.display = "none";
  btn.disabled = false;
  input.focus();
}});
input.focus();
</script>
</body>
</html>"""
