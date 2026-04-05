# M7.7 Package Publishing + M7.5 Audit Logs — Design Spec

**Date**: 2026-04-05
**Scope**: Two independent M7 features — PyPI package publishing and audit logging

---

## M7.7: Package Publishing (PyPI)

### Goal
Make `pip install openraven` work, exposing the `raven` CLI entry point with all core functionality.

### Scope
- `pyproject.toml` with metadata, dependencies, and `[project.scripts]` entry point
- Verify all CLI commands work from clean pip install: `raven init`, `raven add`, `raven ask`, `raven status`, `raven graph`, `raven export`
- Manual publish workflow (`python -m build && twine upload`)

### Package Configuration

**pyproject.toml:**
- Package name: `openraven`
- Version: `0.1.0`
- Entry point: `raven = "openraven.cli.main:main"`
- Python requires: `>=3.11`
- Package discovery: src layout (`packages = [{include = "openraven", from = "src"}]`)
- Dependencies: extracted from current imports — `lightrag-hku`, `langextract`, `docling`, `fastapi`, `uvicorn[standard]`, `openai`, `httpx`, `networkx`, `pydantic`, `python-multipart`, `alembic`, `psycopg2-binary`, `bcrypt`, `neo4j`
- Optional dependencies group `[project.optional-dependencies]`:
  - `ollama` = `["ollama"]`
  - `neo4j` = `["neo4j"]`
- Classifiers: Development Status 3 - Alpha, License OSI Approved Apache 2.0, Python 3.11/3.12

**Build system:**
- `build-system.requires = ["hatchling"]`
- `build-system.build-backend = "hatchling.build"`

### What's NOT Included
- No GitHub Actions CI/CD (manual publish for now)
- No Homebrew formula (future)
- No UI bundling (separate install)
- No Docker image publishing

### Testing Strategy
- Install in a clean venv: `pip install .`
- Verify `raven --help` shows all commands
- Verify `raven init ~/test-kb` creates directory structure
- Verify imports work: `python -c "from openraven.pipeline import RavenPipeline"`

---

## M7.5: Audit Logs

### Goal
Log all significant user actions in PostgreSQL for SOC 2 readiness. Only active when `DATABASE_URL` is set (SaaS mode).

### Database Schema

**Table: `audit_logs`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PRIMARY KEY | Auto-increment |
| `user_id` | INTEGER | FK to users, nullable for system events |
| `tenant_id` | INTEGER | FK to tenants |
| `action` | VARCHAR(50) | Action type (see below) |
| `details` | JSONB | Action-specific context |
| `ip_address` | VARCHAR(45) | IPv4 or IPv6 |
| `timestamp` | TIMESTAMPTZ | DEFAULT NOW() |

**Index:** `(tenant_id, timestamp DESC)` for efficient filtered queries.

**Action types:**
- `login`, `logout`, `signup`, `password_reset`
- `file_ingest`, `file_delete`
- `kb_query`
- `agent_deploy`, `agent_undeploy`
- `member_invite`, `member_remove`
- `settings_change`

### Module: `openraven/src/openraven/audit/`

**`logger.py`:**
```python
async def log_action(
    db_url: str,
    user_id: int | None,
    tenant_id: int | None,
    action: str,
    details: dict | None = None,
    ip_address: str = "",
) -> None:
```
- Inserts row into `audit_logs`
- No-op when `db_url` is empty (local mode — no audit logging)
- Never raises — wraps in try/except to avoid disrupting the main request
- Uses async connection pool (reuse existing psycopg pattern from auth module)

**`routes.py`:**
- `GET /api/audit` — list logs with query params: `action`, `user_id`, `from`, `to`, `limit` (default 100), `offset` (default 0)
- `GET /api/audit/export` — CSV download of filtered logs
- Both require authentication + tenant ownership (admin/owner role)
- Returns: `{ logs: [...], total: int, limit: int, offset: int }`

### Integration Points

Call `log_action()` in these existing endpoints:
- Auth routes (`auth/routes.py`): login, logout, signup, password_reset
- Ingest endpoint (`api/server.py`): file_ingest (with file names in details)
- Ask endpoint (`api/server.py`): kb_query (with question in details)
- Agent endpoints (`api/server.py`): agent_deploy, agent_undeploy

### Alembic Migration
New migration file creating `audit_logs` table with index.

### UI: AuditLogPage

- New page at `/audit` route
- Table columns: Timestamp, User (email), Action, Details, IP Address
- Filter controls: action type dropdown, date range picker (from/to inputs), user filter
- CSV export button
- Pagination (100 per page)
- Admin-only: show in nav only for tenant owner/admin
- Styled with Mistral Premium design tokens

### What's NOT Included
- No log retention/cleanup (store everything for now, add 90-day cleanup later)
- No real-time streaming/websocket for live log tailing
- No log forwarding to external SIEM
- No RBAC beyond owner/admin check

### Testing Strategy
- Unit test `log_action()` with mock DB connection
- Unit test `log_action()` no-op when db_url is empty
- API test for `GET /api/audit` with auth
- API test for `GET /api/audit/export` returns CSV
- Test that audit logging doesn't break main request on DB error
- Test filter parameters (action type, date range, pagination)

---

## Out of Scope
- GitHub Actions CI/CD pipeline
- Homebrew formula
- SOC 2 Type I audit (requires this + external auditor)
- Log retention automation
- RBAC roles beyond owner (admin, member roles deferred to M7.2)
