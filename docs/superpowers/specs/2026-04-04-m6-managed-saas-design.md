# M6: Managed SaaS Platform — Design Spec

**Date:** 2026-04-04
**Goal:** Transform OpenRaven from a single-user local tool into a managed multi-tenant SaaS platform where users sign up, create knowledge bases, and use all features in isolated tenants.
**Timeline:** ~8 weeks (2 months)
**Billing:** Deferred to M7 (free tier only in M6)

## Overview

M6 adds the infrastructure layer to make OpenRaven a cloud-hosted, multi-tenant SaaS product. Users sign up with email/password or Google OAuth, get their own isolated workspace, and use all existing features (Ask, Ingest, Graph, Wiki, Connectors, Agents, Courses) scoped to their tenant.

**Key decisions:**
- PostgreSQL for user/tenant/session data
- Neo4j Community Edition (separate Docker container, GPL isolation) for knowledge graphs
- Self-hosted auth: Lucia v3 + email/password + Google OAuth
- Docker Compose for production deployment (no Kubernetes)
- Billing deferred to M7

## Tech Stack Additions

| Component | Technology | Purpose |
|-----------|-----------|---------|
| User/tenant DB | PostgreSQL 16 | Users, sessions, tenants, metadata |
| Graph DB | Neo4j Community 5.x | Knowledge graphs (replaces NetworkX for production) |
| Auth | Lucia v3 | Session management, password hashing |
| OAuth | Google OAuth 2.0 | "Sign in with Google" |
| Password hashing | bcrypt | Email/password auth |
| Neo4j driver | `neo4j` Python package | Bolt protocol connection |
| Reverse proxy | nginx | SSL termination, routing |
| Containerization | Docker Compose | Production deployment |

---

## 1. Auth System

### 1.1 Auth Library

Lucia v3 integrated with PostgreSQL session store. Handles session creation, validation, and expiration.

### 1.2 User Flow — Email/Password

1. **Sign up:** email + password → validate (min 8 chars) → bcrypt hash → insert `users` row → create tenant → create session → set cookie → redirect to `/`
2. **Login:** email + password → fetch user → verify bcrypt hash → create session → set cookie → redirect to `/`
3. **Password reset:** email input → generate time-limited token (SHA-256, 1 hour expiry) → store in `password_reset_tokens` table → send email with reset link → user submits new password → verify token → update hash → delete token

### 1.3 User Flow — Google OAuth

1. Click "Sign in with Google" → redirect to Google OAuth consent screen
2. Google redirects back with authorization code
3. Exchange code for tokens → fetch Google profile (email, name, avatar)
4. **Existing user (same email):** link `google_id` to user → create session
5. **New user:** create user + tenant → create session
6. Redirect to `/`

### 1.4 Database Schema (PostgreSQL)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    google_id VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT auth_method CHECK (google_id IS NOT NULL OR password_hash IS NOT NULL)
);

CREATE TABLE sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_user_id UUID NOT NULL REFERENCES users(id),
    storage_quota_mb INTEGER DEFAULT 500,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tenant_members (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'owner',
    PRIMARY KEY (tenant_id, user_id)
);
```

### 1.5 Auth Middleware

FastAPI dependency injected on all `/api/*` routes:

```python
async def require_auth(request: Request) -> AuthContext:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    session = await get_session(session_id)
    if not session or session.expires_at < now():
        raise HTTPException(401, "Session expired")
    tenant = await get_tenant_for_user(session.user_id)
    return AuthContext(user_id=session.user_id, tenant_id=tenant.id)
```

All service layer functions receive `tenant_id` as a parameter for data scoping.

Public agent endpoints (`/agents/{agent_id}/query`, `/agents/{agent_id}/chat`) remain unauthenticated — they use their own token-based auth from M4.

---

## 2. Tenant Isolation

### 2.1 Isolation Strategy

| Layer | Strategy |
|-------|----------|
| PostgreSQL | All queries include `tenant_id` filter. Auth middleware injects tenant_id. |
| Neo4j | Label-based isolation: every node gets a `t_{tenant_id}` label. All Cypher queries filter by tenant label. |
| File storage | Per-tenant directory tree: `/data/tenants/{tenant_id}/` |
| LightRAG | Per-tenant working directory: `/data/tenants/{tenant_id}/lightrag/` |
| API layer | Auth middleware extracts tenant_id from session, passes to all service functions |

### 2.2 File Storage Layout

```
/data/tenants/{tenant_id}/
├── ingestion/           # Uploaded files (PDF, DOCX, etc.)
├── lightrag/            # LightRAG working directory
├── courses/             # Generated courses
├── agents/              # Agent configurations
└── google_token.json    # Google OAuth token for connectors
```

### 2.3 Tenant Lifecycle

1. **Auto-create on signup:** First login creates a tenant named "{User's name}'s workspace"
2. **Rename:** Owner can rename tenant via settings
3. **Soft limits:** Storage quota 500MB default, entity count warning at 10,000
4. **Team members:** Deferred to M7 (single-user tenants only in M6)
5. **Deletion:** Owner can delete tenant → removes all data (files, Neo4j nodes, LightRAG dir)

### 2.4 Migration from Single-Tenant

For existing local installations upgrading to SaaS mode:

1. Run migration script
2. Creates a "default" tenant owned by the first admin user
3. Moves files from `working_dir/` to `/data/tenants/{default_tenant_id}/`
4. Imports existing GraphML into Neo4j with tenant label
5. Original files preserved as backup

---

## 3. Neo4j Migration

### 3.1 Dual Backend Architecture

```
RavenGraph (interface)
  ├── networkx_backend.py  — existing, kept for local/dev mode
  └── neo4j_backend.py     — new, for production SaaS mode
```

Selected by config: `GRAPH_BACKEND=neo4j` (production) or `GRAPH_BACKEND=networkx` (local dev).

### 3.2 Neo4j Backend Implementation

Same `RavenGraph` interface methods:
- `insert(entities, relations, tenant_id)` — create nodes with `Entity` + `t_{tenant_id}` labels
- `query(query_text, tenant_id)` — full-text search scoped to tenant
- `get_entities(tenant_id)` — all entities for tenant
- `get_edges(tenant_id)` — all relationships for tenant
- `export_graphml(tenant_id)` — export tenant's subgraph as GraphML

### 3.3 Neo4j Schema

```cypher
-- Node labels: Entity, t_{tenant_id}
-- Node properties:
-- Note: entity IDs are unique within a tenant (enforced at application level)
-- No global uniqueness constraint since different tenants may have same entity names

-- Relationship type: RELATES_TO
-- Relationship properties: description, keywords, weight

-- Indexes
CREATE FULLTEXT INDEX entity_description IF NOT EXISTS
FOR (e:Entity) ON EACH [e.description];

CREATE INDEX entity_type IF NOT EXISTS
FOR (e:Entity) ON (e.entity_type);
```

### 3.4 LightRAG Neo4j Integration

LightRAG has native Neo4j support (`lightrag.kg.neo4j_impl`). Configure per-tenant:
- Each tenant gets its own namespace via node label prefix
- Connection shared (single Neo4j instance), isolation via labels

### 3.5 Migration Script

```bash
python -m openraven.migrate.to_neo4j --working-dir ./data --tenant-id <uuid>
```

- Reads existing GraphML file
- Creates nodes/edges in Neo4j with tenant label
- Verifies node/edge counts match
- Preserves original GraphML as backup

---

## 4. Login/Signup UI + Auth Guard

### 4.1 New Pages

All styled with Mistral Premium warm aesthetic (ivory bg, orange accents, golden shadows, sharp corners).

**`/login`:**
- Email + password fields
- "Sign in" button (dark solid)
- "Sign in with Google" button (cream secondary with Google icon)
- "Forgot password?" link → `/reset-password`
- "Don't have an account? Sign up" link → `/signup`

**`/signup`:**
- Name + email + password + confirm password fields
- "Create account" button (dark solid)
- "Sign up with Google" button (cream secondary)
- "Already have an account? Sign in" link → `/login`

**`/reset-password`:**
- Email input + "Send reset link" button
- Success message: "Check your email for reset instructions"

**`/reset-password/:token`:**
- New password + confirm password fields
- "Reset password" button

### 4.2 Auth Guard

React component wrapping all authenticated routes:

```tsx
function AuthGuard({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" />;
  return children;
}
```

`useAuth()` hook:
- Calls `GET /api/auth/me` on mount → returns user + tenant or 401
- Stores user/tenant in React context
- Provides `login()`, `signup()`, `logout()`, `loginWithGoogle()` methods

### 4.3 Auth API Endpoints

```
POST /api/auth/signup          → {name, email, password} → {user, session}
POST /api/auth/login           → {email, password} → {user, session}
POST /api/auth/logout          → clear session
GET  /api/auth/me              → current user + tenant (or 401)
GET  /api/auth/google          → redirect to Google OAuth
GET  /api/auth/google/callback → exchange code, create session, redirect to /
POST /api/auth/reset-password  → {email} → send reset email
POST /api/auth/reset-password/:token → {password} → reset password
```

### 4.4 Navigation Update

After login, the nav shows user avatar/email in the top-right corner with a dropdown:
- Workspace name
- Settings (future)
- Sign out

---

## 5. Docker Compose Deployment

### 5.1 Service Architecture

```yaml
services:
  nginx:        # Reverse proxy, SSL termination
  postgres:     # PostgreSQL 16
  neo4j:        # Neo4j Community 5.x
  openraven-api: # FastAPI backend (Python)
  openraven-ui:  # Hono BFF + Vite build (Bun)
```

### 5.2 Service Configuration

**nginx:**
- Ports: 80 (redirect to 443), 443 (SSL)
- Routes: `/api/*` → `openraven-api:8741`, `/*` → `openraven-ui:3002`
- SSL: Let's Encrypt via certbot or user-provided certs

**postgres:**
- Image: `postgres:16-alpine`
- Volume: `pg_data:/var/lib/postgresql/data`
- Port: 5432 (internal only)
- Init script: creates database + runs migrations

**neo4j:**
- Image: `neo4j:5-community`
- Volume: `neo4j_data:/data`
- Ports: 7687 (Bolt, internal only), 7474 (browser, optional)
- Config: `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}`
- Memory: `NEO4J_server_memory_heap_max__size=512m`

**openraven-api:**
- Dockerfile: `Dockerfile.api`
- Build: Python 3.12, pip install, uvicorn
- Env: `DATABASE_URL`, `NEO4J_URI`, `GEMINI_API_KEY`, `SESSION_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- Volume: `tenant_data:/data/tenants`
- Health check: `GET /health`

**openraven-ui:**
- Dockerfile: `Dockerfile.ui`
- Build: Bun install, vite build, bun run server
- Env: `API_URL=http://openraven-api:8741`
- Health check: `GET /`

### 5.3 Deployment Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Production stack |
| `docker-compose.dev.yml` | Dev override (hot reload, no SSL, exposed ports) |
| `nginx/nginx.conf` | Reverse proxy + SSL config |
| `nginx/certbot.conf` | Let's Encrypt config |
| `Dockerfile.api` | Python FastAPI image |
| `Dockerfile.ui` | Bun + Vite image |
| `.env.example` | Template for all required env vars |
| `scripts/deploy.sh` | One-command deploy: `./scripts/deploy.sh` |
| `scripts/migrate.sh` | Run database migrations |

### 5.4 Deploy Command

```bash
# First time
cp .env.example .env
# Edit .env with your secrets
./scripts/deploy.sh

# Under the hood:
docker compose up -d
docker compose exec openraven-api python -m openraven.migrate.postgres
```

---

## 6. Sub-Project Decomposition

M6 is built as 5 sequential sub-projects:

| # | Sub-project | Scope | Dependencies | Estimate |
|---|------------|-------|-------------|----------|
| M6.1 | PostgreSQL + Auth system | Lucia, user/session/tenant tables, signup/login API, Google OAuth | None | 2 weeks |
| M6.2 | Tenant isolation layer | Per-tenant file paths, service layer scoping, tenant middleware | M6.1 | 1.5 weeks |
| M6.3 | Neo4j graph backend | Neo4j adapter for RavenGraph, LightRAG Neo4j config, migration script | M6.2 | 2 weeks |
| M6.4 | Login/Signup UI + auth guard | Login, signup, reset-password pages, AuthGuard, useAuth hook, nav user menu | M6.1 | 1 week |
| M6.5 | Docker Compose deployment | Dockerfiles, docker-compose.yml, nginx, SSL, deploy script | M6.1-M6.4 | 1.5 weeks |

**Build order:** M6.1 → M6.2 → M6.3 (parallel with M6.4) → M6.5

**Note:** M6.3 and M6.4 can be built in parallel since M6.3 is backend (Python/Neo4j) and M6.4 is frontend (React/UI).

---

## 7. What Does NOT Change

- All existing features (Ask, Ingest, Graph, Wiki, Connectors, Agents, Courses)
- API contracts (same request/response shapes, just tenant-scoped)
- Mistral Premium design system
- LLM provider config (Gemini/Ollama)
- Chrome extension (local mode only — not SaaS-connected)
- NetworkX backend (kept for local/dev mode)

## 8. What's Deferred to M7

- Billing (Stripe subscriptions, usage tracking, plans)
- Team members (invite users to tenant, role management)
- SSO/SAML for enterprise (Okta, Azure AD)
- Audit logs
- Kubernetes deployment
- Custom domains per tenant
- Admin dashboard (usage analytics, tenant management)
