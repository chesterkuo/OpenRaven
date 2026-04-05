# OpenRaven

**AI-powered knowledge asset platform that automatically extracts, organizes, and activates professional knowledge from your documents.**

OpenRaven transforms scattered documents — PDFs, DOCX, presentations, meeting transcripts, Notion exports — into a structured, queryable knowledge graph. Ask questions in natural language, explore connections between concepts, generate wiki articles, and build courses from your knowledge base.

## Why OpenRaven?

Professionals lose institutional knowledge when switching roles or organizations. Research shows 42% of institutional knowledge exists only in people's heads (IDC). OpenRaven captures and structures that knowledge so it's always accessible, searchable, and shareable.

## Features

### Knowledge Engine
- **Smart Ingestion** — Upload PDFs, DOCX, PPTX, XLSX, Markdown, images (AI vision), or Notion/Obsidian exports. Entities and relationships are automatically extracted.
- **Knowledge Graph** — Interactive force-directed graph visualization with filtering by entity type, connection strength, and search. Export as GraphML or PNG.
- **Natural Language Q&A** — Ask your knowledge base questions using 6 query modes (mix, local, global, hybrid, keyword, direct LLM). Responses include source citations.
- **Auto-Generated Wiki** — Articles are automatically generated from extracted entities and relationships.
- **Course Generation** — Create structured courses from your knowledge base with curriculum planning, chapter generation, and interactive HTML export.
- **Discovery Insights** — Automatic analysis of knowledge themes, clusters, gaps, and trends.

### Connectors
- **Google Drive** — Import documents (PDF, Docs, Sheets, Slides)
- **Gmail** — Import emails as knowledge base entries
- **Google Meet** — Import meeting transcripts via Drive API
- **Otter.ai** — Import meeting transcripts via API key

### Vertical Schemas
- **Base** — General-purpose entity extraction (default)
- **Engineering** — Technical architecture, systems, APIs
- **Finance** — Companies, financial metrics, regulations
- **Legal (Taiwan)** — Statutes, court rulings, legal principles (Traditional Chinese)
- **Finance (Taiwan)** — TWSE listed companies, financial metrics (Traditional Chinese)

### Multi-Locale Support

OpenRaven supports 12 languages with automatic browser detection and manual override:

| Language | Code | Language | Code |
|----------|------|----------|------|
| English | `en` | Italian | `it` |
| Traditional Chinese | `zh-TW` | Vietnamese | `vi` |
| Simplified Chinese | `zh-CN` | Thai | `th` |
| Japanese | `ja` | Russian | `ru` |
| Korean | `ko` | French | `fr` |
| Spanish | `es` | Dutch | `nl` |

**How it works:**
- Browser/OS locale is auto-detected on first visit (fallback: English)
- Users can switch via the language selector in the navbar
- Preference is saved to localStorage (immediate) and user profile (cross-device sync)
- LLM responses match the user's selected language
- Wiki articles and course content follow source document language
- Knowledge graph labels remain in English

### Enterprise Features (Managed SaaS)
- **Multi-Tenant Isolation** — Per-tenant knowledge bases with separate storage
- **Authentication** — Email/password + Google OAuth 2.0 with session management
- **Audit Logging** — Track all user actions with CSV export
- **Team Management** — Invite members to your workspace
- **Neo4j Graph Backend** — Production-grade graph storage (optional, default: NetworkX)
- **Docker Compose Deployment** — One-command deployment with nginx, PostgreSQL, Neo4j

## Architecture

```
openraven/                  # Python backend (FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # FastAPI app factory, all API endpoints
    pipeline.py             # Core pipeline: ingest, query, graph, wiki, courses
    graph/rag.py            # LightRAG wrapper with locale-aware queries
    auth/                   # Auth system (sessions, OAuth, password reset)
    audit/                  # Audit logging module
  alembic/                  # Database migrations
  tests/                    # 159+ Python tests

openraven-ui/               # TypeScript frontend (React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # i18next initialization (12 locales, 11 namespaces)
    App.tsx                 # Root component with routes + navbar
    pages/                  # 14 page components
    components/             # LanguageSelector, GraphViewer, ChatMessage, etc.
    hooks/useAuth.tsx       # Auth context with locale sync
  public/locales/           # 132 translation JSON files (12 locales x 11 namespaces)
  server/index.ts           # Hono BFF (API proxy + static file serving)
  tests/                    # 46 Bun tests

ecosystem.config.cjs        # PM2 deployment configuration
```

## Quick Start

### Prerequisites
- Python 3.12+
- Bun 1.0+
- Node.js 20+ (for PM2)

### 1. Clone and install

```bash
git clone https://github.com/nickhealthy/OpenRaven.git
cd OpenRaven

# Backend
cd openraven
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd ../openraven-ui
bun install
```

### 2. Configure

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # Required: LLM provider
WORKING_DIR=/path/to/knowledge-data     # Where knowledge base data is stored

# Optional: Enable managed SaaS features
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. Run with PM2

```bash
# From project root
pm2 start ecosystem.config.cjs

# Check status
pm2 status

# View logs
pm2 logs
```

Services:
- **openraven-core** (port 8741) — Python API server
- **openraven-ui** (port 3002) — BFF + frontend

### 4. Build frontend for production

```bash
cd openraven-ui
bun run build          # Builds to dist/
pm2 restart openraven-ui
```

Open http://localhost:3002 in your browser.

### Alternative: Docker Compose

```bash
docker compose up -d
```

This starts nginx (port 80), PostgreSQL, Neo4j, API server, and UI server.

## Development

### Run tests

```bash
# Backend
cd openraven && python3 -m pytest tests/ -v

# Frontend
cd openraven-ui && bun test tests/

# Benchmarks (requires GEMINI_API_KEY)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### Adding translations

Translation files are in `openraven-ui/public/locales/{locale}/{namespace}.json`.

To add or update a translation:
1. Edit the JSON file for the target locale
2. Keep keys identical to the English source file
3. Preserve `{{interpolation}}` placeholders
4. Run `bun run build` and restart PM2

To add a new locale:
1. Create a new directory under `public/locales/` (e.g., `de/`)
2. Copy all JSON files from `en/` and translate the values
3. Add the locale code to `SUPPORTED_LNGS` in `src/i18n.ts`
4. Add the locale to the `LOCALES` array in `src/components/LanguageSelector.tsx`
5. Add the locale to `SUPPORTED_LOCALES` in `openraven/src/openraven/auth/routes.py`
6. Add the locale name to `LOCALE_NAMES` in `openraven/src/openraven/graph/rag.py`

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ask` | Query knowledge base (supports locale param) |
| `POST` | `/api/ingest` | Upload and process documents |
| `GET` | `/api/graph` | Get knowledge graph data |
| `GET` | `/api/wiki` | List wiki articles |
| `GET` | `/api/status` | Knowledge base statistics |
| `GET` | `/api/discovery` | Auto-generated insights |
| `POST` | `/api/courses/generate` | Generate a course |
| `GET` | `/api/connectors/status` | Connector status |
| `PATCH` | `/api/auth/locale` | Update user locale preference |
| `GET` | `/api/audit` | Audit log (paginated) |

See the full API documentation at http://localhost:8741/docs (FastAPI auto-generated).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Gemini (default), Ollama (local) |
| Knowledge Graph | LightRAG + NetworkX (local) / Neo4j (production) |
| Entity Extraction | LangExtract |
| Backend | FastAPI + Uvicorn (Python 3.12) |
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono (Bun runtime) |
| Database | SQLite (local) / PostgreSQL (production) |
| Auth | Session-based + Google OAuth 2.0 |
| Deployment | PM2 / Docker Compose |
| Design System | Mistral Premium (warm ivory, orange accents, golden shadows) |

## Validation Results

- **QA Accuracy**: 96.7% (29/30 Tier 1 questions)
- **Citation Accuracy**: 100% (30/30 source references)
- **LLM Judge Score**: 4.6/5.0 average (Tier 2)
- **Test Coverage**: 260+ tests across Python and TypeScript

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

Copyright 2026 Plusblocks Technology Limited.

## About

Built by [Plusblocks Technology Limited](https://plusblocks.com). OpenRaven's core engine is open-source. Cloud and enterprise features (multi-tenant, SSO, billing) are available as a managed service.
