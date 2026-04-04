# M4: Expert Agent Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users deploy their knowledge base as a publicly queryable Expert Agent with a hosted chat page, rate-limited API, and token-gated access via Cloudflare Tunnel.

**Architecture:** An agent registry stores agent configs as JSON files. The existing FastAPI server gains management endpoints (`/api/agents/*`) and public-facing endpoints (`/agents/*`). A tunnel module wraps `cloudflared` to expose the server to the internet. An in-memory rate limiter controls anonymous and token-gated access. A self-contained HTML chat page is served at the agent's public URL.

**Tech Stack:** Python (FastAPI, click), cloudflared (external binary), TypeScript/React (AgentsPage UI). No new Python/JS dependencies.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/agents/__init__.py` | Create | Package init |
| `openraven/src/openraven/agents/registry.py` | Create | AgentConfig dataclass, CRUD, token management |
| `openraven/src/openraven/agents/ratelimit.py` | Create | In-memory sliding window rate limiter |
| `openraven/src/openraven/agents/tunnel.py` | Create | Cloudflare Tunnel wrapper (start/stop/URL) |
| `openraven/src/openraven/agents/chat_page.py` | Create | HTML template for agent chat page |
| `openraven/src/openraven/api/server.py` | Modify | Add agent management + public endpoints |
| `openraven/cli/main.py` | Modify | Add deploy/undeploy/agents commands |
| `openraven/tests/test_agents.py` | Create | Registry, rate limiter, API endpoint tests |
| `openraven-ui/src/pages/AgentsPage.tsx` | Create | Agent management UI |
| `openraven-ui/src/App.tsx` | Modify | Add /agents route + nav link |
| `openraven-ui/server/index.ts` | Modify | Add agents proxy route |

---

## Task 1: Agent Registry -- config, CRUD, tokens

**Files:**
- Create: `openraven/src/openraven/agents/__init__.py`
- Create: `openraven/src/openraven/agents/registry.py`
- Create: `openraven/tests/test_agents.py`

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_agents.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_create_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent
    agent = create_agent(
        agents_dir=tmp_path,
        name="Legal Expert",
        description="Answers legal questions",
        kb_path="/home/user/my-knowledge",
    )
    assert agent.name == "Legal Expert"
    assert agent.description == "Answers legal questions"
    assert agent.id
    assert agent.is_public is True
    assert agent.rate_limit_anonymous == 10
    assert (tmp_path / f"{agent.id}.json").exists()


def test_get_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent, get_agent
    agent = create_agent(agents_dir=tmp_path, name="Test", description="test", kb_path="/tmp")
    loaded = get_agent(agents_dir=tmp_path, agent_id=agent.id)
    assert loaded is not None
    assert loaded.name == "Test"
    assert loaded.id == agent.id


def test_get_agent_not_found(tmp_path) -> None:
    from openraven.agents.registry import get_agent
    assert get_agent(agents_dir=tmp_path, agent_id="nonexistent") is None


def test_list_agents(tmp_path) -> None:
    from openraven.agents.registry import create_agent, list_agents
    create_agent(agents_dir=tmp_path, name="Agent 1", description="first", kb_path="/tmp")
    create_agent(agents_dir=tmp_path, name="Agent 2", description="second", kb_path="/tmp")
    agents = list_agents(agents_dir=tmp_path)
    assert len(agents) == 2
    names = {a.name for a in agents}
    assert names == {"Agent 1", "Agent 2"}


def test_delete_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent, delete_agent, list_agents
    agent = create_agent(agents_dir=tmp_path, name="Doomed", description="bye", kb_path="/tmp")
    assert delete_agent(agents_dir=tmp_path, agent_id=agent.id) is True
    assert list_agents(agents_dir=tmp_path) == []


def test_delete_agent_not_found(tmp_path) -> None:
    from openraven.agents.registry import delete_agent
    assert delete_agent(agents_dir=tmp_path, agent_id="nope") is False


def test_update_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent, update_agent, get_agent
    agent = create_agent(agents_dir=tmp_path, name="Old Name", description="old", kb_path="/tmp")
    updated = update_agent(agents_dir=tmp_path, agent_id=agent.id, name="New Name", is_public=False)
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.is_public is False
    reloaded = get_agent(agents_dir=tmp_path, agent_id=agent.id)
    assert reloaded.name == "New Name"


def test_generate_token(tmp_path) -> None:
    from openraven.agents.registry import create_agent, generate_token, get_agent
    agent = create_agent(agents_dir=tmp_path, name="Secured", description="tokens", kb_path="/tmp")
    raw_token = generate_token(agents_dir=tmp_path, agent_id=agent.id)
    assert len(raw_token) >= 32
    reloaded = get_agent(agents_dir=tmp_path, agent_id=agent.id)
    assert len(reloaded.access_tokens) == 1


def test_verify_token(tmp_path) -> None:
    from openraven.agents.registry import create_agent, generate_token, verify_token
    agent = create_agent(agents_dir=tmp_path, name="Auth", description="check", kb_path="/tmp")
    raw_token = generate_token(agents_dir=tmp_path, agent_id=agent.id)
    assert verify_token(agents_dir=tmp_path, agent_id=agent.id, token=raw_token) is True
    assert verify_token(agents_dir=tmp_path, agent_id=agent.id, token="wrong-token") is False
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v`

- [ ] **Step 3: Create package and implement registry**

Create `openraven/src/openraven/agents/__init__.py` (empty file).

Create `openraven/src/openraven/agents/registry.py`:

```python
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    id: str
    name: str
    description: str
    kb_path: str
    is_public: bool = True
    rate_limit_anonymous: int = 10
    rate_limit_token: int = 100
    access_tokens: list[dict] = field(default_factory=list)  # [{"hash": str, "last4": str}]
    tunnel_url: str = ""
    created_at: str = ""


def _agents_dir(agents_dir: Path) -> Path:
    agents_dir.mkdir(parents=True, exist_ok=True)
    return agents_dir


def _save_agent(agents_dir: Path, agent: AgentConfig) -> None:
    path = _agents_dir(agents_dir) / f"{agent.id}.json"
    path.write_text(json.dumps(asdict(agent), indent=2), encoding="utf-8")


def _load_agent(path: Path) -> AgentConfig | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentConfig(**data)


def create_agent(
    agents_dir: Path,
    name: str,
    description: str,
    kb_path: str,
    is_public: bool = True,
    rate_limit_anonymous: int = 10,
    rate_limit_token: int = 100,
) -> AgentConfig:
    agent = AgentConfig(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        kb_path=kb_path,
        is_public=is_public,
        rate_limit_anonymous=rate_limit_anonymous,
        rate_limit_token=rate_limit_token,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _save_agent(agents_dir, agent)
    logger.info(f"Created agent '{name}' ({agent.id})")
    return agent


def get_agent(agents_dir: Path, agent_id: str) -> AgentConfig | None:
    return _load_agent(_agents_dir(agents_dir) / f"{agent_id}.json")


def list_agents(agents_dir: Path) -> list[AgentConfig]:
    d = _agents_dir(agents_dir)
    agents = []
    for f in d.glob("*.json"):
        agent = _load_agent(f)
        if agent:
            agents.append(agent)
    return agents


_UPDATABLE_FIELDS = {"name", "description", "is_public", "rate_limit_anonymous", "rate_limit_token", "tunnel_url"}


def update_agent(agents_dir: Path, agent_id: str, **kwargs) -> AgentConfig | None:
    agent = get_agent(agents_dir, agent_id)
    if not agent:
        return None
    for key, value in kwargs.items():
        if key in _UPDATABLE_FIELDS:
            setattr(agent, key, value)
    _save_agent(agents_dir, agent)
    return agent


def delete_agent(agents_dir: Path, agent_id: str) -> bool:
    path = _agents_dir(agents_dir) / f"{agent_id}.json"
    if path.exists():
        path.unlink()
        logger.info(f"Deleted agent {agent_id}")
        return True
    return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(agents_dir: Path, agent_id: str) -> str:
    agent = get_agent(agents_dir, agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    raw_token = secrets.token_urlsafe(32)
    agent.access_tokens.append({"hash": _hash_token(raw_token), "last4": raw_token[-4:]})
    _save_agent(agents_dir, agent)
    return raw_token


def verify_token(agents_dir: Path, agent_id: str, token: str) -> bool:
    agent = get_agent(agents_dir, agent_id)
    if not agent:
        return False
    token_hash = _hash_token(token)
    return any(t["hash"] == token_hash for t in agent.access_tokens)
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/agents/ openraven/tests/test_agents.py
git commit -m "feat(agents): add agent registry with CRUD and token management"
```

---

## Task 2: Rate Limiter

**Files:**
- Create: `openraven/src/openraven/agents/ratelimit.py`
- Modify: `openraven/tests/test_agents.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_agents.py`:

```python
import time


def test_rate_limiter_allows_under_limit() -> None:
    from openraven.agents.ratelimit import RateLimiter
    limiter = RateLimiter()
    allowed, remaining = limiter.check("user-1", limit=5, window_seconds=3600)
    assert allowed is True
    assert remaining == 4


def test_rate_limiter_blocks_over_limit() -> None:
    from openraven.agents.ratelimit import RateLimiter
    limiter = RateLimiter()
    for _ in range(5):
        limiter.check("user-2", limit=5, window_seconds=3600)
    allowed, remaining = limiter.check("user-2", limit=5, window_seconds=3600)
    assert allowed is False
    assert remaining == 0


def test_rate_limiter_separate_keys() -> None:
    from openraven.agents.ratelimit import RateLimiter
    limiter = RateLimiter()
    for _ in range(5):
        limiter.check("user-a", limit=5, window_seconds=3600)
    allowed, _ = limiter.check("user-b", limit=5, window_seconds=3600)
    assert allowed is True


def test_rate_limiter_resets_after_window() -> None:
    from openraven.agents.ratelimit import RateLimiter
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("user-3", limit=3, window_seconds=1)
    allowed, _ = limiter.check("user-3", limit=3, window_seconds=1)
    assert allowed is False
    time.sleep(1.1)
    allowed, remaining = limiter.check("user-3", limit=3, window_seconds=1)
    assert allowed is True
    assert remaining == 2


def test_rate_limiter_remaining_count() -> None:
    from openraven.agents.ratelimit import RateLimiter
    limiter = RateLimiter()
    _, r1 = limiter.check("user-4", limit=3, window_seconds=3600)
    _, r2 = limiter.check("user-4", limit=3, window_seconds=3600)
    _, r3 = limiter.check("user-4", limit=3, window_seconds=3600)
    assert r1 == 2
    assert r2 == 1
    assert r3 == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v -k "rate_limiter"`

- [ ] **Step 3: Implement rate limiter**

Create `openraven/src/openraven/agents/ratelimit.py`:

```python
from __future__ import annotations

import threading
import time


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int = 3600) -> tuple[bool, int]:
        """Check if a request is allowed. Returns (allowed, remaining_requests)."""
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            count = len(self._requests[key])
            if count >= limit:
                return False, 0
            self._requests[key].append(now)
            remaining = limit - count - 1
            return True, remaining
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/agents/ratelimit.py openraven/tests/test_agents.py
git commit -m "feat(agents): add in-memory sliding window rate limiter"
```

---

## Task 3: Tunnel Service

**Files:**
- Create: `openraven/src/openraven/agents/tunnel.py`
- Modify: `openraven/tests/test_agents.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_agents.py`:

```python
def test_tunnel_cloudflared_check() -> None:
    from openraven.agents.tunnel import is_cloudflared_available
    result = is_cloudflared_available()
    assert isinstance(result, bool)


def test_tunnel_pid_file_management(tmp_path) -> None:
    from openraven.agents.tunnel import get_tunnel_pid, save_tunnel_pid, clear_tunnel_pid
    pid_file = tmp_path / "tunnel.pid"
    assert get_tunnel_pid(pid_file) is None
    save_tunnel_pid(pid_file, 12345)
    assert get_tunnel_pid(pid_file) == 12345
    clear_tunnel_pid(pid_file)
    assert get_tunnel_pid(pid_file) is None


def test_tunnel_url_storage(tmp_path) -> None:
    from openraven.agents.tunnel import save_tunnel_url, get_tunnel_url
    url_file = tmp_path / "tunnel_url"
    save_tunnel_url(url_file, "https://abc-xyz.trycloudflare.com")
    assert get_tunnel_url(url_file) == "https://abc-xyz.trycloudflare.com"


def test_tunnel_url_missing(tmp_path) -> None:
    from openraven.agents.tunnel import get_tunnel_url
    assert get_tunnel_url(tmp_path / "nope") == ""
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v -k "tunnel"`

- [ ] **Step 3: Implement tunnel module**

Create `openraven/src/openraven/agents/tunnel.py`:

```python
from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def is_cloudflared_available() -> bool:
    return shutil.which("cloudflared") is not None


def save_tunnel_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(str(pid), encoding="utf-8")


def get_tunnel_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def clear_tunnel_pid(pid_file: Path) -> None:
    if pid_file.exists():
        pid_file.unlink()


def save_tunnel_url(url_file: Path, url: str) -> None:
    url_file.write_text(url, encoding="utf-8")


def get_tunnel_url(url_file: Path) -> str:
    if not url_file.exists():
        return ""
    return url_file.read_text(encoding="utf-8").strip()


def start_tunnel(port: int, working_dir: Path) -> str:
    """Start a Cloudflare Tunnel and return the public URL."""
    if not is_cloudflared_available():
        raise RuntimeError(
            "cloudflared is not installed. Install it:\n"
            "  macOS: brew install cloudflared\n"
            "  Linux: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        )

    pid_file = working_dir / "tunnel.pid"
    url_file = working_dir / "tunnel_url"
    stop_tunnel(working_dir)

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    save_tunnel_pid(pid_file, proc.pid)

    import re
    import time
    url = ""
    deadline = time.time() + 15
    while time.time() < deadline:
        line = proc.stderr.readline().decode("utf-8", errors="replace")
        match = re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", line)
        if match:
            url = match.group(1)
            break

    if not url:
        logger.warning("Could not detect tunnel URL within timeout")
        url = f"tunnel-starting (PID {proc.pid})"

    save_tunnel_url(url_file, url)
    logger.info(f"Tunnel started: {url} (PID {proc.pid})")
    return url


def stop_tunnel(working_dir: Path) -> bool:
    pid_file = working_dir / "tunnel.pid"
    url_file = working_dir / "tunnel_url"

    pid = get_tunnel_pid(pid_file)
    if pid is None:
        return False

    try:
        os.kill(pid, signal.SIGTERM)
        logger.info(f"Stopped tunnel (PID {pid})")
    except ProcessLookupError:
        logger.info(f"Tunnel process {pid} already stopped")
    except PermissionError:
        logger.warning(f"Cannot stop tunnel process {pid} (permission denied)")
        return False

    clear_tunnel_pid(pid_file)
    if url_file.exists():
        url_file.unlink()
    return True
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/agents/tunnel.py openraven/tests/test_agents.py
git commit -m "feat(agents): add Cloudflare Tunnel wrapper for agent deployment"
```

---

## Task 4: Agent Chat Page (HTML template)

**Files:**
- Create: `openraven/src/openraven/agents/chat_page.py`
- Modify: `openraven/tests/test_agents.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_agents.py`:

```python
def test_chat_page_renders_html() -> None:
    from openraven.agents.chat_page import render_chat_page
    html = render_chat_page(
        agent_id="test-123",
        agent_name="Legal Expert",
        agent_description="Answers legal questions",
    )
    assert "<!DOCTYPE html>" in html
    assert "Legal Expert" in html
    assert "Answers legal questions" in html
    assert "test-123" in html
    assert "/agents/test-123/ask" in html


def test_chat_page_escapes_html() -> None:
    from openraven.agents.chat_page import render_chat_page
    html = render_chat_page(
        agent_id="xss-test",
        agent_name='<script>alert("xss")</script>',
        agent_description="safe",
    )
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v -k "chat_page"`

- [ ] **Step 3: Implement chat page**

Create `openraven/src/openraven/agents/chat_page.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/agents/chat_page.py openraven/tests/test_agents.py
git commit -m "feat(agents): add self-contained HTML chat page template"
```

---

## Task 5: API Endpoints -- agent management + public query

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_agents.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_agents.py`:

```python
from fastapi.testclient import TestClient
from openraven.api.server import create_app
from openraven.config import RavenConfig


@pytest.fixture
def agent_client(tmp_path) -> TestClient:
    config = RavenConfig(working_dir=tmp_path / "kb", gemini_api_key="test-key")
    app = create_app(config)
    return TestClient(app)


def test_api_create_agent(agent_client: TestClient) -> None:
    response = agent_client.post("/api/agents", json={
        "name": "Test Agent", "description": "For testing"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Agent"
    assert "id" in data


def test_api_list_agents(agent_client: TestClient) -> None:
    agent_client.post("/api/agents", json={"name": "A1", "description": "first"})
    agent_client.post("/api/agents", json={"name": "A2", "description": "second"})
    response = agent_client.get("/api/agents")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_api_delete_agent(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={"name": "Del", "description": "bye"})
    agent_id = resp.json()["id"]
    del_resp = agent_client.delete(f"/api/agents/{agent_id}")
    assert del_resp.status_code == 200
    assert agent_client.get("/api/agents").json() == []


def test_api_generate_token(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={"name": "Tok", "description": "tokens"})
    agent_id = resp.json()["id"]
    tok_resp = agent_client.post(f"/api/agents/{agent_id}/tokens")
    assert tok_resp.status_code == 200
    assert "token" in tok_resp.json()


def test_api_agent_ask_public(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={"name": "Q", "description": "query"})
    agent_id = resp.json()["id"]
    ask_resp = agent_client.post(f"/agents/{agent_id}/ask", json={"question": "test"})
    assert ask_resp.status_code == 200
    data = ask_resp.json()
    assert "answer" in data
    assert "sources" in data


def test_api_agent_ask_rate_limited(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={
        "name": "Limited", "description": "rate test",
        "rate_limit_anonymous": 2,
    })
    agent_id = resp.json()["id"]
    for _ in range(2):
        agent_client.post(f"/agents/{agent_id}/ask", json={"question": "q"})
    blocked = agent_client.post(f"/agents/{agent_id}/ask", json={"question": "q"})
    assert blocked.status_code == 429


def test_api_agent_private_requires_token(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={
        "name": "Private", "description": "secret", "is_public": False
    })
    agent_id = resp.json()["id"]
    ask_resp = agent_client.post(f"/agents/{agent_id}/ask", json={"question": "test"})
    assert ask_resp.status_code == 403


def test_api_agent_info(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={"name": "Info", "description": "meta"})
    agent_id = resp.json()["id"]
    info = agent_client.get(f"/agents/{agent_id}/info")
    assert info.status_code == 200
    assert info.json()["name"] == "Info"
    assert info.json()["description"] == "meta"


def test_api_deploy_not_found(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents/nonexistent/deploy")
    assert resp.status_code == 404


def test_api_create_agent_requires_name(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={"description": "no name"})
    assert resp.status_code == 400


def test_api_agent_chat_page(agent_client: TestClient) -> None:
    resp = agent_client.post("/api/agents", json={"name": "Chat", "description": "page"})
    agent_id = resp.json()["id"]
    page_resp = agent_client.get(f"/agents/{agent_id}")
    assert page_resp.status_code == 200
    assert "text/html" in page_resp.headers["content-type"]
    assert "Chat" in page_resp.text
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v -k "api_"`

- [ ] **Step 3: Read server.py first**

Read `openraven/src/openraven/api/server.py` to understand the existing pattern.

- [ ] **Step 4: Add agent endpoints to server.py**

First, update the imports at the top of server.py — add `Request` to the FastAPI import:

```python
from fastapi import BackgroundTasks, FastAPI, File, Query, Request, UploadFile
```

Add `import hashlib` at the top:

```python
import hashlib
```

Then add inside `create_app()`, after the connector endpoints section (after the last `gmail_sync` or `otter_sync` endpoint):

```python
    # --- Agent Deployment ---

    agents_dir = config.working_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    from openraven.agents.ratelimit import RateLimiter
    agent_rate_limiter = RateLimiter()

    @app.post("/api/agents")
    async def create_agent_endpoint(body: dict):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import create_agent
        if not body.get("name", "").strip():
            return JSONResponse({"error": "name is required"}, status_code=400)
        agent = create_agent(
            agents_dir=agents_dir,
            name=body.get("name", ""),
            description=body.get("description", ""),
            kb_path=str(config.working_dir),
            is_public=body.get("is_public", True),
            rate_limit_anonymous=body.get("rate_limit_anonymous", 10),
            rate_limit_token=body.get("rate_limit_token", 100),
        )
        return {
            "id": agent.id, "name": agent.name, "description": agent.description,
            "is_public": agent.is_public, "tunnel_url": agent.tunnel_url,
            "rate_limit_anonymous": agent.rate_limit_anonymous,
            "rate_limit_token": agent.rate_limit_token,
            "created_at": agent.created_at,
        }

    @app.get("/api/agents")
    async def list_agents_endpoint():
        from openraven.agents.registry import list_agents
        agents = list_agents(agents_dir)
        return [
            {"id": a.id, "name": a.name, "description": a.description,
             "is_public": a.is_public, "tunnel_url": a.tunnel_url,
             "created_at": a.created_at}
            for a in agents
        ]

    @app.get("/api/agents/{agent_id}")
    async def get_agent_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        return {
            "id": agent.id, "name": agent.name, "description": agent.description,
            "is_public": agent.is_public, "tunnel_url": agent.tunnel_url,
            "rate_limit_anonymous": agent.rate_limit_anonymous,
            "rate_limit_token": agent.rate_limit_token,
            "token_count": len(agent.access_tokens),
            "tokens": [{"last4": t["last4"]} for t in agent.access_tokens],
            "created_at": agent.created_at,
        }

    @app.delete("/api/agents/{agent_id}")
    async def delete_agent_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import delete_agent
        if delete_agent(agents_dir, agent_id):
            return {"deleted": True}
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    @app.post("/api/agents/{agent_id}/tokens")
    async def generate_token_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import generate_token
        try:
            token = generate_token(agents_dir, agent_id)
            return {"token": token}
        except ValueError:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

    @app.post("/api/agents/{agent_id}/deploy")
    async def deploy_agent_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent, update_agent
        from openraven.agents.tunnel import start_tunnel
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        try:
            url = start_tunnel(port=config.api_port, working_dir=config.working_dir)
            update_agent(agents_dir, agent_id, tunnel_url=url)
            return {"tunnel_url": url}
        except RuntimeError as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/agents/{agent_id}/undeploy")
    async def undeploy_agent_endpoint(agent_id: str):
        from openraven.agents.registry import update_agent
        from openraven.agents.tunnel import stop_tunnel
        stop_tunnel(config.working_dir)
        update_agent(agents_dir, agent_id, tunnel_url="")
        return {"undeployed": True}

    # --- Public Agent Endpoints (exposed via tunnel) ---

    @app.get("/agents/{agent_id}")
    async def agent_chat_page(agent_id: str):
        from fastapi.responses import HTMLResponse, JSONResponse
        from openraven.agents.chat_page import render_chat_page
        from openraven.agents.registry import get_agent
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        page_html = render_chat_page(agent.id, agent.name, agent.description)
        return HTMLResponse(page_html)

    @app.get("/agents/{agent_id}/info")
    async def agent_info(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        return {"name": agent.name, "description": agent.description}

    @app.post("/agents/{agent_id}/ask")
    async def agent_ask(agent_id: str, body: dict, request: Request):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent, verify_token

        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        auth_header = request.headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        if not agent.is_public and not token:
            return JSONResponse({"error": "This agent requires an access token."}, status_code=403)
        if token and not verify_token(agents_dir, agent_id, token):
            return JSONResponse({"error": "Invalid access token."}, status_code=403)

        if token:
            rate_key = f"token:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
            limit = agent.rate_limit_token
        else:
            client_ip = request.client.host if request.client else "unknown"
            rate_key = f"ip:{client_ip}:{agent_id}"
            limit = agent.rate_limit_anonymous

        allowed, remaining = agent_rate_limiter.check(rate_key, limit=limit)
        if not allowed:
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={"Retry-After": "3600", "X-RateLimit-Remaining": "0"},
            )

        question = body.get("question", "")
        mode = body.get("mode", "mix")
        result = await pipeline.ask_with_sources(question, mode=mode)
        return {
            "answer": result.answer,
            "sources": [{"document": s["document"], "excerpt": s["excerpt"]} for s in result.sources],
        }
```

- [ ] **Step 5: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_agents.py -v`
Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v` (no regressions)

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_agents.py
git commit -m "feat(api): add agent management and public query endpoints"
```

---

## Task 6: CLI Commands -- deploy/undeploy/agents

**Files:**
- Modify: `openraven/cli/main.py`

- [ ] **Step 1: Read cli/main.py**

Read `openraven/cli/main.py` to understand the existing click command pattern.

- [ ] **Step 2: Add agent CLI commands**

Add after the `export_cmd` function in `openraven/cli/main.py`:

```python
@cli.command()
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
def agents(working_dir: str):
    """List all deployed agents."""
    from openraven.agents.registry import list_agents

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir))
    agent_list = list_agents(config.working_dir / "agents")

    if not agent_list:
        click.echo("No agents configured. Create one in the UI or use 'raven deploy'.")
        return

    for agent in agent_list:
        status = "ACTIVE" if agent.tunnel_url else "stopped"
        url = agent.tunnel_url or "(not deployed)"
        click.echo(f"  {agent.name} [{status}]")
        click.echo(f"    ID:  {agent.id}")
        click.echo(f"    URL: {url}")
        click.echo("")


@cli.command()
@click.argument("name")
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--description", "-d", default="", help="Agent description")
def deploy(name: str, working_dir: str, description: str):
    """Deploy a knowledge base as a public Expert Agent."""
    from openraven.agents.registry import create_agent, list_agents, update_agent
    from openraven.agents.tunnel import start_tunnel

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir))
    agents_dir = config.working_dir / "agents"

    existing = [a for a in list_agents(agents_dir) if a.name == name]
    if existing:
        agent = existing[0]
        click.echo(f"Found existing agent: {agent.name} ({agent.id})")
    else:
        desc = description or f"Expert Agent: {name}"
        agent = create_agent(
            agents_dir=agents_dir, name=name, description=desc,
            kb_path=str(config.working_dir),
        )
        click.echo(f"Created agent: {agent.name} ({agent.id})")

    click.echo(f"Starting tunnel on port {config.api_port}...")
    try:
        url = start_tunnel(port=config.api_port, working_dir=config.working_dir)
        update_agent(agents_dir, agent.id, tunnel_url=url)
        click.echo("")
        click.echo(f"Agent deployed!")
        click.echo(f"  Chat:  {url}/agents/{agent.id}")
        click.echo(f"  API:   POST {url}/agents/{agent.id}/ask")
        click.echo("")
        click.echo("Keep this terminal open. Press Ctrl+C to stop.")
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
def undeploy(working_dir: str):
    """Stop the deployed agent tunnel."""
    from openraven.agents.tunnel import stop_tunnel

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir))
    if stop_tunnel(config.working_dir):
        click.echo("Tunnel stopped.")
    else:
        click.echo("No active tunnel found.")
```

- [ ] **Step 3: Run full test suite**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/benchmark/`

- [ ] **Step 4: Commit**

```bash
git add openraven/cli/main.py
git commit -m "feat(cli): add raven deploy/undeploy/agents commands"
```

---

## Task 7: AgentsPage UI + routing

**Files:**
- Create: `openraven-ui/src/pages/AgentsPage.tsx`
- Modify: `openraven-ui/src/App.tsx`
- Modify: `openraven-ui/server/index.ts`

- [ ] **Step 1: Read App.tsx and server/index.ts**

Read both files to understand routing and proxy patterns.

- [ ] **Step 2: Create AgentsPage.tsx**

Create `openraven-ui/src/pages/AgentsPage.tsx`:

```tsx
import { useEffect, useState } from "react";

interface Agent {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  tunnel_url: string;
  created_at: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => { loadAgents(); }, []);

  async function loadAgents() {
    try {
      const res = await fetch("/api/agents");
      setAgents(await res.json());
    } catch { /* ignore */ }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await fetch("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), description: description.trim() }),
      });
      setName("");
      setDescription("");
      setShowCreate(false);
      await loadAgents();
    } catch { /* ignore */ }
    finally { setCreating(false); }
  }

  async function handleDelete(id: string) {
    await fetch(`/api/agents/${id}`, { method: "DELETE" });
    await loadAgents();
  }

  async function handleGenerateToken(id: string) {
    const res = await fetch(`/api/agents/${id}/tokens`, { method: "POST" });
    const data = await res.json();
    if (data.token) {
      await navigator.clipboard.writeText(data.token);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  }

  function copyUrl(agent: Agent) {
    const url = agent.tunnel_url
      ? `${agent.tunnel_url}/agents/${agent.id}`
      : `http://localhost:8741/agents/${agent.id}`;
    navigator.clipboard.writeText(url);
    setCopiedId(agent.id + "-url");
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Expert Agents</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500">
          {showCreate ? "Cancel" : "Create Agent"}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
          <div className="flex flex-col gap-3">
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Agent name (e.g. Legal Expert)"
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500" />
            <input value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (what does this agent know?)"
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500" />
            <button type="submit" disabled={creating || !name.trim()} className="self-start text-sm px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      )}

      {agents.length === 0 && !showCreate && (
        <div className="text-gray-500 text-sm">No agents yet. Create one to deploy your knowledge base as a queryable expert.</div>
      )}

      <div className="flex flex-col gap-4">
        {agents.map(agent => (
          <div key={agent.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="font-semibold">{agent.name}</h2>
                <p className="text-sm text-gray-400">{agent.description}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${agent.tunnel_url ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
                {agent.tunnel_url ? "Deployed" : "Local only"}
              </span>
            </div>
            <div className="text-xs text-gray-500 mb-3 font-mono">
              {agent.tunnel_url
                ? <span className="text-blue-400">{agent.tunnel_url}/agents/{agent.id}</span>
                : <span>http://localhost:8741/agents/{agent.id}</span>
              }
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => copyUrl(agent)} className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-800 text-gray-200 hover:bg-gray-700">
                {copiedId === agent.id + "-url" ? "Copied!" : "Copy URL"}
              </button>
              <button onClick={() => handleGenerateToken(agent.id)} className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-800 text-gray-200 hover:bg-gray-700">
                {copiedId === agent.id ? "Token copied!" : "Generate Token"}
              </button>
              <button onClick={() => handleDelete(agent.id)} className="text-xs px-2 py-1 rounded border border-red-800 bg-gray-800 text-red-400 hover:bg-red-900/30">
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add route to App.tsx**

Add import:
```tsx
import AgentsPage from "./pages/AgentsPage";
```

Add nav link (after Connectors, before Status):
```tsx
<NavLink to="/agents" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Agents</NavLink>
```

Add route:
```tsx
<Route path="/agents" element={<AgentsPage />} />
```

- [ ] **Step 4: Add agents proxy to server/index.ts**

Add after the connectors proxy section:

```typescript
// Proxy agent management endpoints to core API
app.all("/api/agents/*", async (c) => {
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
app.all("/api/agents", async (c) => {
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

- [ ] **Step 5: Build and test**

Run: `cd openraven-ui && bun test tests/ && bun run build`

- [ ] **Step 6: Commit**

```bash
git add openraven-ui/src/pages/AgentsPage.tsx openraven-ui/src/App.tsx openraven-ui/server/index.ts
git commit -m "feat(ui): add AgentsPage with create, deploy, token management"
```

---

## Task 8: E2E Verification

- [ ] **Step 1: Run full test suite**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/benchmark/
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 2: Restart PM2 and verify**

```bash
pm2 restart all && sleep 10
curl -sf http://localhost:8741/api/agents | python3 -m json.tool
```

Expected: `[]` (empty list).

- [ ] **Step 3: Create and test an agent via API**

```bash
# Create agent
curl -sf -X POST http://localhost:8741/api/agents -H "Content-Type: application/json" -d '{"name": "Test Expert", "description": "For validation"}' | python3 -m json.tool

# Get agent ID
AGENT_ID=$(curl -sf http://localhost:8741/api/agents | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Test chat page
curl -sf http://localhost:8741/agents/$AGENT_ID | head -5

# Test agent ask
curl -sf -X POST http://localhost:8741/agents/$AGENT_ID/ask -H "Content-Type: application/json" -d '{"question": "What is Kafka?"}' | python3 -m json.tool

# Delete test agent
curl -sf -X DELETE http://localhost:8741/api/agents/$AGENT_ID | python3 -m json.tool
```

---

## Summary

| Task | What | Tests Added |
|---|---|---|
| 1 | Agent Registry -- config, CRUD, tokens | 10 registry tests |
| 2 | Rate Limiter -- sliding window | 5 rate limiter tests |
| 3 | Tunnel Service -- cloudflared wrapper | 4 tunnel tests |
| 4 | Chat Page -- HTML template | 2 template tests |
| 5 | API Endpoints -- management + public | 8 API tests |
| 6 | CLI Commands -- deploy/undeploy/agents | Build check |
| 7 | AgentsPage UI + routing | Build check |
| 8 | E2E Verification | Full suite |

**Total new tests: 32**

**Architecture note:** The Cloudflare Tunnel is server-wide (one tunnel per OpenRaven instance), not per-agent. All agents share the same tunnel URL. Deploy/undeploy is managed via CLI (`raven deploy`/`raven undeploy`) or the `/api/agents/{id}/deploy` endpoint. The AgentsPage UI shows the tunnel URL per agent but deploy control is via CLI for MVP.

**Public agent access:** The chat page at `/agents/{id}` is served directly by the FastAPI server (port 8741) and through the Cloudflare Tunnel. It is NOT proxied through the Hono UI server (port 3002) — this is intentional since the tunnel points directly to FastAPI.
