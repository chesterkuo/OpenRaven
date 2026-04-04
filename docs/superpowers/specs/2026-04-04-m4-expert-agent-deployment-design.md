# M4: Expert Agent Deployment — Design Spec

**Goal:** Let users deploy their knowledge base as a publicly queryable Expert Agent with a shareable URL, combining a hosted chat page for end-users and an API for developers.

**Strategy:** Local-first with self-hosted tunnel (Cloudflare Tunnel) for MVP. Cloud deployment deferred to post-M3 E2EE infrastructure. Public access with optional token gating and configurable rate limits.

---

## 1. Architecture Overview

Three layers:

1. **Agent Registry** — Manages agent configurations. Each agent is a named deployment of a knowledge base with settings (public/private, rate limits, description). Stored as JSON in `working_dir/agents/`.

2. **Agent API Server** — Extends the existing FastAPI server with public-facing agent endpoints. A tunnel service (Cloudflare Tunnel) exposes these endpoints to the internet. Runs as a separate PM2 process.

3. **Agent Chat Page** — Self-contained HTML page served at the agent's public URL. Minimal vanilla HTML/JS/CSS chat interface. No build step, no React dependency.

Flow:
```
User creates agent in UI → Config saved → Tunnel started → Public URL active
External visitor → Chat page loads → POST /agents/{id}/ask → Rate limited → KB queried → Answer + sources returned
```

---

## 2. Agent Registry

New module `openraven/src/openraven/agents/registry.py`.

### AgentConfig

```python
@dataclass
class AgentConfig:
    id: str                          # UUID
    name: str                        # Human-readable name
    description: str                 # What this agent knows about
    kb_path: str                     # Path to working_dir (same KB, no duplication)
    is_public: bool = True           # False = token-required only
    rate_limit_anonymous: int = 10   # Queries/hour for anonymous users
    rate_limit_token: int = 100      # Queries/hour for token holders
    access_tokens: list[str] = []    # List of hashed tokens (SHA-256)
    tunnel_url: str = ""             # Public URL when deployed (set by tunnel service)
    created_at: str = ""             # ISO timestamp
```

### Operations

- `create_agent(name, description, config) -> AgentConfig` — creates agent JSON in `working_dir/agents/{id}.json`
- `get_agent(agent_id) -> AgentConfig | None`
- `list_agents(working_dir) -> list[AgentConfig]`
- `update_agent(agent_id, **kwargs) -> AgentConfig`
- `delete_agent(agent_id) -> bool`
- `generate_token(agent_id) -> str` — returns raw token, stores SHA-256 hash
- `verify_token(agent_id, token) -> bool` — checks against stored hashes

---

## 3. Agent API Endpoints

### Management (local only, under `/api/`)

```
POST   /api/agents                    → create agent {name, description, is_public, rate_limits}
GET    /api/agents                    → list all agents
GET    /api/agents/{id}               → get agent details + stats
DELETE /api/agents/{id}               → delete agent
POST   /api/agents/{id}/tokens        → generate access token → {token: "raw-token"}
POST   /api/agents/{id}/deploy        → start tunnel → {tunnel_url: "https://..."}
POST   /api/agents/{id}/undeploy      → stop tunnel
```

### Public-facing (exposed via tunnel, under `/agents/`)

```
GET    /agents/{id}                   → serve chat page (HTML)
GET    /agents/{id}/info              → agent metadata {name, description} (JSON)
POST   /agents/{id}/ask               → query agent {question, mode} → {answer, sources} (rate limited)
```

Path split: `/api/agents/*` is management (never exposed through tunnel), `/agents/*` is the public interface.

### Rate Limiting on `/agents/{id}/ask`

- Anonymous requests: identified by IP, limited to `rate_limit_anonymous` queries/hour
- Token requests: `Authorization: Bearer <token>` header, limited to `rate_limit_token` queries/hour
- Private agents (`is_public=false`): anonymous requests get 403, token required
- Returns `429 Too Many Requests` with `Retry-After` header when exceeded

---

## 4. Rate Limiter

New module `openraven/src/openraven/agents/ratelimit.py`.

Simple in-memory sliding window rate limiter (no Redis needed):

```python
class RateLimiter:
    def check(self, key: str, limit: int, window_seconds: int = 3600) -> tuple[bool, int]:
        """Returns (allowed, remaining_requests)."""
```

- Tracks request timestamps per key (IP or token hash)
- Sliding window: counts requests in the last `window_seconds`
- Thread-safe (uses a lock)
- Auto-cleans expired entries to prevent memory growth

---

## 5. Tunnel Service

New module `openraven/src/openraven/agents/tunnel.py`.

Wrapper around `cloudflared` (Cloudflare Tunnel):

- `start_tunnel(port) -> str` — starts cloudflared, returns public URL
- `stop_tunnel()` — kills cloudflared process
- `get_tunnel_url() -> str | None` — returns current URL if tunnel is active
- Stores PID in `working_dir/tunnel.pid` for process management
- Falls back to instructions for manual ngrok setup if cloudflared not installed

### CLI Commands

- `raven deploy <agent_name>` — creates agent if needed, starts tunnel, prints URL
- `raven undeploy` — stops tunnel
- `raven agents list` — list all agents with status

### PM2 Integration

Optional PM2 process `openraven-tunnel` for persistent deployment.

---

## 6. Agent Chat Page

New module `openraven/src/openraven/agents/chat_page.py` — serves HTML template.

Self-contained HTML page (no build step):

- Agent name and description header
- Chat interface: text input, message history, auto-scroll
- Sends `POST /agents/{id}/ask` with question
- Displays answer with source citations
- Shows rate limit info ("X queries remaining")
- "Powered by OpenRaven" footer with link
- Dark theme matching existing UI aesthetic
- Vanilla HTML/JS/CSS — no React, no bundler
- Template rendered server-side with agent name/description injected

---

## 7. UI — Agents Management Page

New `openraven-ui/src/pages/AgentsPage.tsx`:

- List deployed agents: name, status (deployed/stopped), public URL, query count
- "Create Agent" button → form: name, description, public toggle, rate limit sliders
- Per-agent actions: Copy URL, Generate Token, Deploy/Undeploy, Delete
- Token management: generate new tokens, list existing (show last 4 chars only)
- Deploy button starts tunnel, shows URL with copy button

Nav link added between "Connectors" and "Status".

---

## 8. File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/agents/__init__.py` | Create | Package init |
| `openraven/src/openraven/agents/registry.py` | Create | AgentConfig, CRUD, token management |
| `openraven/src/openraven/agents/ratelimit.py` | Create | In-memory sliding window rate limiter |
| `openraven/src/openraven/agents/tunnel.py` | Create | Cloudflare Tunnel wrapper, start/stop/URL |
| `openraven/src/openraven/agents/chat_page.py` | Create | HTML template for agent chat page |
| `openraven/src/openraven/api/server.py` | Modify | Add agent management + public endpoints |
| `openraven/cli/main.py` | Modify | Add deploy/undeploy/agents commands |
| `openraven/tests/test_agents.py` | Create | Registry, rate limiter, API endpoint tests |
| `openraven-ui/src/pages/AgentsPage.tsx` | Create | Agent management UI |
| `openraven-ui/src/App.tsx` | Modify | Add /agents route + nav link |
| `openraven-ui/server/index.ts` | Modify | Add agents proxy route |

---

## 9. Tests

### Registry (~8 tests)
- Create agent returns valid config with UUID
- Get agent by ID
- List agents returns all
- Delete agent removes file
- Generate token returns raw token, stores hash
- Verify valid token returns True
- Verify invalid token returns False
- Update agent modifies fields

### Rate Limiter (~5 tests)
- Allows requests under limit
- Blocks requests over limit (returns False)
- Resets after window expires
- Separate tracking per key
- Returns correct remaining count

### API Endpoints (~7 tests)
- POST /api/agents creates agent
- GET /api/agents lists agents
- DELETE /api/agents/{id} removes agent
- POST /agents/{id}/ask returns answer (public)
- POST /agents/{id}/ask returns 429 when rate limited
- POST /agents/{id}/ask returns 403 on private agent without token
- GET /agents/{id} returns HTML chat page

**Total new tests: ~20**

---

## 10. Dependencies

- `cloudflared` — installed separately (`brew install cloudflared` or download binary). Not a Python dependency. Tunnel features gracefully degrade if not installed.
- No new Python packages needed.
- No new npm/bun packages needed.

---

## 11. Out of Scope (Future)

- Cloud-hosted deployment (requires E2EE + cloud backend from M3)
- Custom domains for agents
- Agent analytics dashboard (query logs, popular questions)
- Multi-KB agents (federation across knowledge bases)
- Agent-to-agent communication
- Billing/usage metering for API access
