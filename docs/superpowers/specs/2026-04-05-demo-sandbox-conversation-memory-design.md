# Demo Sandbox & Multi-turn Conversation Memory

**Date**: 2026-04-05
**Status**: Approved

## Overview

Two features to improve user acquisition and chat quality:

1. **Demo Sandbox** — Unauthenticated users can explore the platform with pre-loaded themed knowledge bases (chat, graph, documents) before registering.
2. **Multi-turn Conversation Memory** — Persistent conversation history with a fixed context window (last 10 turns) sent to the LLM for follow-up awareness.

---

## Feature 1: Demo Sandbox

### Goal

Let prospective users experience OpenRaven's core value — querying a knowledge base, exploring the graph, browsing documents — without creating an account. Multiple themed demo KBs showcase different use cases.

### Data Model

#### Demo Tenant

A special tenant `demo` is seeded at startup (or via CLI). Themed KBs live as sub-directories:

```
/data/tenants/demo/
  ├── legal-docs/        # Theme 1
  ├── tech-wiki/         # Theme 2
  └── research-papers/   # Theme 3
```

Each theme has its own pre-built LightRAG knowledge graph, ingested offline.

#### Demo Sessions

New column on `sessions` table:

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| is_demo | BOOLEAN | FALSE | Distinguishes demo from auth sessions |
| demo_theme | VARCHAR(50) | NULL | Selected theme slug |

Demo sessions: `user_id=NULL`, TTL of 2 hours (vs. 7 days for regular sessions).

### Backend

#### New Routes

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/api/demo/themes` | GET | Public | List available themes (name, description, doc count) |
| `/api/auth/demo` | POST | Public | Create demo session, accepts `{ theme }`, sets cookie |

#### Auth Middleware Changes

When session has `is_demo=True`:

- Set `AuthContext` with `tenant_id="demo"`, `user_id=None`, `is_demo=True`
- **Allow**: `POST /api/ask`, `GET /api/graph/*`, `GET /api/documents/*`, conversation CRUD
- **Block**: All other POST/PUT/DELETE — upload, ingest, agents config, settings, team, sync, account
- Pipeline resolved using `demo` tenant + `demo_theme` sub-directory

#### Rate Limiting

- 30 queries/hour per IP for demo sessions
- Max 5 conversations per demo session

### Frontend

#### New Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/demo` | DemoLandingPage | Theme picker with cards |
| `/demo/ask` | AskPage (demo mode) | Chat with demo KB |
| `/demo/graph` | GraphPage (demo mode) | Graph visualization |
| `/demo/documents` | DocumentsPage (demo mode) | Document list (read-only) |

#### Demo Landing Page

- 2-3 themed demo cards with icon, title, description, document count
- "Try it" button per card → `POST /api/auth/demo` → redirect to `/demo/ask`

#### Demo Layout

- Reuses existing app shell in restricted mode
- Sidebar: only Ask, Graph, Documents visible
- Persistent banner: _"You're exploring a demo. [Sign up] to create your own knowledge base."_
- Theme name in header (e.g., "Demo: Legal Docs")
- "Switch theme" button to return to theme picker

#### Auth Context Extension

```typescript
interface AuthState {
  user: User | null
  tenant: Tenant | null
  isDemo: boolean        // NEW
  demoTheme: string | null  // NEW
}
```

#### Routing Guard Update

```
/demo/*                          → allow (demo session created on theme pick)
/login, /signup, /reset-password → allow
/*                               → require auth, redirect to /login
```

---

## Feature 2: Multi-turn Conversation Memory

### Goal

Enable follow-up questions in chat by persisting conversation history and sending the last 10 turns as context to the LLM.

### Data Model

#### New Tables

```sql
conversations
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
  tenant_id   VARCHAR NOT NULL
  user_id     UUID NULL                -- NULL for demo sessions
  session_id  VARCHAR NULL             -- set for demo sessions, used to scope demo conversations
  title       VARCHAR(200)             -- auto-generated from first message
  demo_theme  VARCHAR(50) NULL         -- set for demo conversations
  created_at  TIMESTAMP DEFAULT now()
  updated_at  TIMESTAMP DEFAULT now()

messages
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE
  role            VARCHAR(10) NOT NULL  -- 'user' | 'assistant'
  content         TEXT NOT NULL
  sources         JSONB NULL            -- source refs for assistant messages
  created_at      TIMESTAMP DEFAULT now()
```

Indexes: `conversations(tenant_id, user_id)`, `messages(conversation_id, created_at)`.

### Backend

#### New API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/api/conversations` | POST | Create new conversation |
| `/api/conversations` | GET | List conversations for current user/session |
| `/api/conversations/:id` | GET | Get conversation with all messages |
| `/api/conversations/:id` | DELETE | Delete conversation (cascade deletes messages) |

#### Modified Ask Endpoint

`POST /api/ask` extended with:

```python
class AskRequest(BaseModel):
    question: str
    mode: str = "mix"
    locale: str = "en"
    conversation_id: str | None = None   # NEW
    history: list[dict] | None = None    # NEW — last N messages from frontend
```

**Flow:**

1. Validate `conversation_id` belongs to current tenant/user
2. Persist user message to `messages` table
3. Build context prefix from history (last 10 turns = 20 messages):
   ```
   Previous conversation:
   User: {msg1}
   Assistant: {msg2}
   ...

   Current question: {question}
   ```
4. Pass combined prompt to `pipeline.ask_with_sources()`
5. Persist assistant response + sources to `messages` table
6. Return response with `conversation_id`

#### History Fallback

If `history` is not provided but `conversation_id` is, backend fetches last 10 turns from DB.

#### Auto-title

First message in a conversation: title = first 100 characters of the question (truncated at word boundary).

### Frontend

#### Conversation Sidebar

Added to AskPage — left panel:

- "New Chat" button at top
- List of past conversations (title + relative timestamp)
- Click to load conversation messages
- Delete button with confirmation
- Demo mode: shows only current session's conversations

#### New Hook: `useConversations`

```typescript
interface Conversation {
  id: string
  title: string
  updated_at: string
}

function useConversations() {
  conversations: Conversation[]
  activeId: string | null
  messages: Message[]          // local cache

  createConversation()         // POST /api/conversations
  loadConversation(id)         // GET /api/conversations/:id
  deleteConversation(id)       // DELETE /api/conversations/:id
  sendMessage(question)        // POST /api/ask with conversation_id + history
}
```

#### Updated Ask Flow

1. No active conversation → create one (`POST /api/conversations`)
2. Append user message to local cache
3. `POST /api/ask` with `{ question, conversation_id, history: messages.slice(-20) }`
4. Append assistant response to local cache
5. Sidebar updates title/timestamp

#### Page Refresh Resilience

- On mount: `GET /api/conversations` loads sidebar
- Click conversation: `GET /api/conversations/:id` loads messages into cache
- Active conversation ID in URL: `/ask?c=<id>` — survives refresh

---

## Security & Cleanup

### Demo Session Security

- Demo sessions scoped to `demo` tenant only — no cross-tenant access
- `user_id=NULL` — no user record to leak
- Middleware blocks all mutating operations except ask and conversation CRUD
- Rate limited: 30 queries/hour per IP

### Conversation Security

- All queries filter by `tenant_id` from session
- Authenticated users: additionally filter by `user_id`
- Demo users: filter by `session_id` stored on the conversation record (added as nullable column `session_id VARCHAR NULL` on `conversations` table, set when `is_demo=True`)
- `conversation_id` validated against tenant ownership on every request

### Cleanup

- **Hourly background task**: Delete expired demo sessions + cascade-delete their conversations
- **Startup cleanup**: Purge expired demo sessions on server start
- **Empty conversation cleanup**: Conversations with no messages older than 1 hour auto-deleted
- **Demo conversation limit**: Max 5 per demo session

### Edge Cases

- **Demo KB not found**: Return 404 with friendly message if theme has no pipeline
- **History mismatch**: Backend uses DB as source of truth if frontend cache diverges
- **Concurrent demo users**: Each gets their own session — no shared state beyond the read-only KB

---

## Out of Scope

- Guest-to-registered user conversion (migrating demo conversations to a real account)
- Token-budget or summarization-based context windows
- Demo file upload or document ingestion
- Demo agent configuration
