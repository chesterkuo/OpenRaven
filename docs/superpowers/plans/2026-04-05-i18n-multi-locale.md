# i18n Multi-Locale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-locale support (12 languages) to the OpenRaven Web UI with auto-detection, manual selector, profile persistence, and locale-aware LLM responses.

**Architecture:** react-i18next with lazy-loaded JSON translation files served from `public/locales/`. Browser language detection via `i18next-browser-languagedetector`, manual override via LanguageSelector component. Locale persisted in localStorage (immediate) + user DB profile (cross-device). Backend `/api/ask` injects locale into LLM system prompt.

**Tech Stack:** i18next, react-i18next, i18next-browser-languagedetector, i18next-http-backend, FastAPI, SQLAlchemy, Alembic

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `openraven-ui/src/i18n.ts` | i18next initialization, language detection config, `<html lang>` sync |
| `openraven-ui/src/components/LanguageSelector.tsx` | Language picker dropdown, syncs to profile |
| `openraven-ui/public/locales/en/common.json` | English shared strings (nav, buttons, errors) |
| `openraven-ui/public/locales/en/ask.json` | English AskPage strings |
| `openraven-ui/public/locales/en/auth.json` | English auth strings (login/signup/reset) |
| `openraven-ui/public/locales/en/ingest.json` | English IngestPage strings |
| `openraven-ui/public/locales/en/graph.json` | English GraphPage strings |
| `openraven-ui/public/locales/en/wiki.json` | English WikiPage strings |
| `openraven-ui/public/locales/en/connectors.json` | English ConnectorsPage strings |
| `openraven-ui/public/locales/en/agents.json` | English AgentsPage strings |
| `openraven-ui/public/locales/en/courses.json` | English CoursesPage strings |
| `openraven-ui/public/locales/en/status.json` | English StatusPage strings |
| `openraven-ui/public/locales/{zh-TW,zh-CN,ja,ko,fr,es,nl,it,vi,th,ru}/*.json` | Translated copies (11 locales × 10 namespaces) |
| `openraven-ui/tests/components/LanguageSelector.test.tsx` | LanguageSelector tests |
| `openraven-ui/tests/i18n-setup.ts` | i18next test mock helper |
| `openraven/alembic/versions/002_add_user_locale.py` | Migration: add locale column |
| `openraven/tests/test_auth_locale.py` | Tests for locale endpoint + /me response |

### Modified Files

| File | Change |
|------|--------|
| `openraven-ui/package.json` | Add i18next dependencies |
| `openraven-ui/src/main.tsx` | Import i18n, add Suspense wrapper |
| `openraven-ui/src/design-tokens.css` | Update font stack for CJK/Thai |
| `openraven-ui/src/App.tsx` | Use `useTranslation('common')` for nav, add LanguageSelector |
| `openraven-ui/src/hooks/useAuth.tsx` | Sync locale from profile on login |
| `openraven-ui/src/pages/AskPage.tsx` | Extract strings, pass locale to /api/ask |
| `openraven-ui/src/pages/LoginPage.tsx` | Extract strings, add LanguageSelector |
| `openraven-ui/src/pages/SignupPage.tsx` | Extract strings, add LanguageSelector |
| `openraven-ui/src/pages/ResetPasswordPage.tsx` | Extract strings, add LanguageSelector |
| `openraven-ui/src/pages/IngestPage.tsx` | Extract strings |
| `openraven-ui/src/pages/GraphPage.tsx` | Extract strings |
| `openraven-ui/src/pages/WikiPage.tsx` | Extract strings |
| `openraven-ui/src/pages/ConnectorsPage.tsx` | Extract strings |
| `openraven-ui/src/pages/AgentsPage.tsx` | Extract strings |
| `openraven-ui/src/pages/CoursesPage.tsx` | Extract strings |
| `openraven-ui/src/pages/StatusPage.tsx` | Extract strings |
| `openraven-ui/src/components/FileUploader.tsx` | Extract strings |
| `openraven-ui/src/components/GraphNodeDetail.tsx` | Extract strings |
| `openraven/src/openraven/auth/db.py` | Add locale column to users table |
| `openraven/src/openraven/auth/models.py` | Add locale field to UserResponse |
| `openraven/src/openraven/auth/routes.py` | Add PATCH /locale endpoint, include locale in /me |
| `openraven/src/openraven/api/server.py` | Add locale to AskRequest, inject into LLM prompt |
| `openraven/src/openraven/pipeline.py` | Pass locale through ask_with_sources |
| `openraven/src/openraven/graph/rag.py` | Pass locale to LightRAG query |

---

## Task 1: Install i18next dependencies

**Files:**
- Modify: `openraven-ui/package.json`

- [ ] **Step 1: Install packages**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun add i18next react-i18next i18next-browser-languagedetector i18next-http-backend
```

- [ ] **Step 2: Verify installation**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun pm ls | grep i18next
```

Expected: all four packages listed.

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && git add package.json bun.lock* && git commit -m "feat(i18n): install i18next dependencies"
```

---

## Task 2: Create i18n initialization and update entry point

**Files:**
- Create: `openraven-ui/src/i18n.ts`
- Modify: `openraven-ui/src/main.tsx`
- Modify: `openraven-ui/src/design-tokens.css:36`

- [ ] **Step 1: Create `src/i18n.ts`**

```ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

export const SUPPORTED_LNGS = [
  'en', 'zh-TW', 'zh-CN', 'ja', 'ko', 'fr', 'es', 'nl', 'it', 'vi', 'th', 'ru',
] as const;

export type SupportedLocale = (typeof SUPPORTED_LNGS)[number];

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: [...SUPPORTED_LNGS],
    ns: ['common', 'ask', 'ingest', 'graph', 'wiki', 'connectors', 'agents', 'courses', 'status', 'auth'],
    defaultNS: 'common',
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    interpolation: {
      escapeValue: false,
    },
  });

i18n.on('languageChanged', (lng) => {
  document.documentElement.setAttribute('lang', lng);
});

export default i18n;
```

- [ ] **Step 2: Update `src/main.tsx`**

Replace the full contents of `openraven-ui/src/main.tsx` with:

```tsx
import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./i18n";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Suspense fallback={<div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>Loading...</div>}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Suspense>
  </StrictMode>
);
```

- [ ] **Step 3: Update font stack in `src/design-tokens.css`**

Change line 36 from:
```css
  --font-family: Arial, ui-sans-serif, system-ui, -apple-system, sans-serif;
```
to:
```css
  --font-family: system-ui, -apple-system, "Segoe UI", Arial, sans-serif;
```

- [ ] **Step 4: Verify dev server starts without errors**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && timeout 10 bun run dev:client 2>&1 || true
```

Expected: Vite starts without TypeScript or import errors.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/i18n.ts openraven-ui/src/main.tsx openraven-ui/src/design-tokens.css && git commit -m "feat(i18n): add i18next init, Suspense wrapper, update font stack"
```

---

## Task 3: Create English translation files (all 10 namespaces)

**Files:**
- Create: `openraven-ui/public/locales/en/common.json`
- Create: `openraven-ui/public/locales/en/ask.json`
- Create: `openraven-ui/public/locales/en/auth.json`
- Create: `openraven-ui/public/locales/en/ingest.json`
- Create: `openraven-ui/public/locales/en/graph.json`
- Create: `openraven-ui/public/locales/en/wiki.json`
- Create: `openraven-ui/public/locales/en/connectors.json`
- Create: `openraven-ui/public/locales/en/agents.json`
- Create: `openraven-ui/public/locales/en/courses.json`
- Create: `openraven-ui/public/locales/en/status.json`

- [ ] **Step 1: Create `public/locales/en/common.json`**

```json
{
  "nav": {
    "ask": "Ask",
    "addFiles": "Add Files",
    "graph": "Graph",
    "wiki": "Wiki",
    "connectors": "Connectors",
    "agents": "Agents",
    "courses": "Courses",
    "status": "Status"
  },
  "signOut": "Sign out",
  "loading": "Loading...",
  "cancel": "Cancel",
  "save": "Save",
  "delete": "Delete",
  "error": "Something went wrong",
  "or": "or",
  "saving": "Saving...",
  "syncing": "Syncing...",
  "connected": "Connected",
  "notConnected": "Not connected",
  "connect": "Connect",
  "syncNow": "Sync Now",
  "download": "Download",
  "export": "Export",
  "create": "Create",
  "creating": "Creating...",
  "close": "Close",
  "copied": "Copied!",
  "nodesCount": "{{count}} nodes",
  "edgesCount": "{{count}} edges",
  "truncated": "(truncated)"
}
```

- [ ] **Step 2: Create `public/locales/en/ask.json`**

```json
{
  "heroTitle": "What would you like to know?",
  "discoveriesHeading": "Discoveries from your knowledge base",
  "sourcesCount": "Sources ({{count}})",
  "placeholder": "Ask your knowledge base...",
  "submit": "Ask",
  "thinking": "Thinking...",
  "errorReach": "Error: Could not reach the knowledge engine.",
  "modeLabel": "Mode",
  "modes": {
    "mix": "Mix",
    "local": "Local",
    "global": "Global",
    "hybrid": "Hybrid",
    "naive": "Keyword",
    "bypass": "Direct LLM"
  },
  "modeDesc": {
    "mix": "Specific + broad reasoning (recommended)",
    "local": "Search specific entities",
    "global": "Cross-document reasoning",
    "hybrid": "Local + global combined",
    "naive": "Traditional vector search",
    "bypass": "Skip knowledge base"
  }
}
```

- [ ] **Step 3: Create `public/locales/en/auth.json`**

```json
{
  "email": "Email",
  "password": "Password",
  "signIn": "Sign In",
  "signingIn": "Signing in...",
  "signInGoogle": "Sign in with Google",
  "forgotPassword": "Forgot password?",
  "createAccount": "Create account",
  "fullName": "Full name",
  "confirmPassword": "Confirm password",
  "passwordHint": "Password (min 8 chars)",
  "signUp": "Create Account",
  "creatingAccount": "Creating account...",
  "signUpGoogle": "Sign up with Google",
  "alreadyHaveAccount": "Already have an account?",
  "signInLink": "Sign in",
  "passwordsMismatch": "Passwords do not match",
  "passwordTooShort": "Password must be at least 8 characters",
  "loginFailed": "Login failed",
  "signupFailed": "Signup failed",
  "resetTitle": "Reset Password",
  "resetInstructions": "Enter your email and we'll send you a link to reset your password.",
  "sendResetLink": "Send Reset Link",
  "sending": "Sending...",
  "resetSent": "If an account with that email exists, we've sent reset instructions.",
  "backToSignIn": "Back to sign in"
}
```

- [ ] **Step 4: Create `public/locales/en/ingest.json`**

```json
{
  "title": "Add Documents",
  "schemaLabel": "Extraction Schema",
  "schemaAuto": "Auto-detect (default)",
  "importHint": "Import from Notion or Obsidian — upload your exported .zip file. Images (PNG, JPEG) are analyzed with AI vision.",
  "stages": {
    "uploading": "Uploading files...",
    "processing": "Processing documents...",
    "done": "Complete",
    "error": "Error occurred"
  },
  "stats": {
    "filesProcessed": "Files processed",
    "entitiesExtracted": "Entities extracted",
    "articlesGenerated": "Articles generated"
  },
  "uploadError": "Failed to connect to the knowledge engine.",
  "dropFiles": "Drop files here",
  "fileTypes": "PDF, DOCX, PPTX, XLSX, Markdown, TXT, Images (PNG/JPEG), or ZIP (Notion/Obsidian export)",
  "browseFiles": "BROWSE FILES"
}
```

- [ ] **Step 5: Create `public/locales/en/graph.json`**

```json
{
  "title": "Knowledge Graph",
  "loadingGraph": "Loading graph...",
  "searchPlaceholder": "Search nodes...",
  "minConnections": "Min connections:",
  "exportGraphML": "Export GraphML",
  "exportPNG": "Export PNG",
  "emptyMessage": "No graph data yet. Add files to start building your knowledge graph.",
  "source": "Source",
  "connectedCount": "Connected ({{count}})"
}
```

- [ ] **Step 6: Create `public/locales/en/wiki.json`**

```json
{
  "title": "Knowledge Wiki",
  "loadingWiki": "Loading wiki...",
  "articlesCount": "Articles ({{count}})",
  "selectArticle": "Select an article to read",
  "emptyMessage": "No articles yet. Add files to start generating wiki articles."
}
```

- [ ] **Step 7: Create `public/locales/en/connectors.json`**

```json
{
  "title": "Connectors",
  "oauthWarning": "Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env to enable connectors.",
  "gdrive": {
    "name": "Google Drive",
    "desc": "Import documents from your Google Drive (PDF, Docs, Sheets, Slides)."
  },
  "gmail": {
    "name": "Gmail",
    "desc": "Import emails from your Gmail account as knowledge base entries."
  },
  "meet": {
    "name": "Google Meet",
    "desc": "Import meeting transcripts from Google Meet.",
    "syncLabel": "Sync Transcripts"
  },
  "otter": {
    "name": "Otter.ai",
    "desc": "Import meeting transcripts from Otter.ai.",
    "apiKeyPlaceholder": "Otter.ai API key"
  },
  "syncFailed": "Sync failed",
  "stats": {
    "filesSynced": "Files synced",
    "entities": "Entities",
    "articles": "Articles"
  }
}
```

- [ ] **Step 8: Create `public/locales/en/agents.json`**

```json
{
  "title": "Expert Agents",
  "createAgent": "Create Agent",
  "namePlaceholder": "Agent name (e.g. Legal Expert)",
  "descriptionPlaceholder": "Description (what does this agent know?)",
  "emptyMessage": "No agents yet. Create one to deploy your knowledge base as a queryable expert.",
  "deployed": "Deployed",
  "localOnly": "Local only",
  "copyUrl": "Copy URL",
  "generateToken": "Generate Token",
  "tokenCopied": "Token copied!"
}
```

- [ ] **Step 9: Create `public/locales/en/courses.json`**

```json
{
  "title": "Courses",
  "generateCourse": "Generate a Course",
  "courseTitle": "Course Title *",
  "courseTitlePlaceholder": "e.g., Introduction to Event-Driven Architecture",
  "targetAudience": "Target Audience",
  "audiencePlaceholder": "e.g., Backend Engineers",
  "learningObjectives": "Learning Objectives (one per line)",
  "objectivesPlaceholder": "Understand EDA patterns\nImplement Kafka consumers\nDesign event schemas",
  "generate": "Generate Course",
  "generating": "Generating...",
  "generatedCourses": "Generated Courses",
  "chaptersCount": "{{count}} chapters",
  "emptyMessage": "No courses generated yet. Fill in the form above and generate your first course.",
  "progress": {
    "planning": "Planning curriculum...",
    "generating": "Generating chapters ({{done}}/{{total}})...",
    "done": "Complete!",
    "error": "Error"
  },
  "generationFailed": "Generation failed",
  "startFailed": "Failed to start generation"
}
```

- [ ] **Step 10: Create `public/locales/en/status.json`**

```json
{
  "title": "Knowledge Base Status",
  "files": "Files",
  "concepts": "Concepts",
  "connections": "Connections",
  "topics": "Topics",
  "llm": "LLM:",
  "topTopics": "Top Topics",
  "healthInsights": "Health Insights"
}
```

- [ ] **Step 11: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/public/locales/en/ && git commit -m "feat(i18n): add English translation files for all 10 namespaces"
```

---

## Task 4: Create LanguageSelector component with test

**Files:**
- Create: `openraven-ui/src/components/LanguageSelector.tsx`
- Create: `openraven-ui/tests/i18n-setup.ts`
- Create: `openraven-ui/tests/components/LanguageSelector.test.tsx`

- [ ] **Step 1: Create test mock helper `tests/i18n-setup.ts`**

```ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

i18n.use(initReactI18next).init({
  lng: 'en',
  fallbackLng: 'en',
  ns: ['common'],
  defaultNS: 'common',
  resources: {
    en: { common: {} },
  },
  interpolation: { escapeValue: false },
});

export default i18n;
```

- [ ] **Step 2: Write the failing test `tests/components/LanguageSelector.test.tsx`**

```tsx
/** @jsxImportSource react */
// @bun-env happy-dom
import { describe, it, expect, mock } from "bun:test";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import "../../tests/i18n-setup";
import { LanguageSelector } from "../../src/components/LanguageSelector";

describe("LanguageSelector", () => {
  it("renders a select element with 12 locale options", () => {
    render(<LanguageSelector />);
    const select = screen.getByRole("combobox");
    expect(select).toBeDefined();
    const options = select.querySelectorAll("option");
    expect(options.length).toBe(12);
  });

  it("shows native language names", () => {
    render(<LanguageSelector />);
    expect(screen.getByText("繁體中文")).toBeDefined();
    expect(screen.getByText("日本語")).toBeDefined();
    expect(screen.getByText("Русский")).toBeDefined();
  });

  it("selects the current i18n language", () => {
    render(<LanguageSelector />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("en");
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun test tests/components/LanguageSelector.test.tsx
```

Expected: FAIL — `LanguageSelector` module not found.

- [ ] **Step 4: Create `src/components/LanguageSelector.tsx`**

```tsx
import { useTranslation } from 'react-i18next';

const LOCALES = [
  { code: 'en',    label: 'English' },
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'ja',    label: '日本語' },
  { code: 'ko',    label: '한국어' },
  { code: 'fr',    label: 'Français' },
  { code: 'es',    label: 'Español' },
  { code: 'nl',    label: 'Nederlands' },
  { code: 'it',    label: 'Italiano' },
  { code: 'vi',    label: 'Tiếng Việt' },
  { code: 'th',    label: 'ไทย' },
  { code: 'ru',    label: 'Русский' },
] as const;

export function LanguageSelector() {
  const { i18n } = useTranslation();

  const handleChange = async (lng: string) => {
    await i18n.changeLanguage(lng);
    fetch('/api/auth/locale', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ locale: lng }),
    }).catch(() => {});
  };

  return (
    <select
      value={i18n.language}
      onChange={e => handleChange(e.target.value)}
      aria-label="Language"
      className="text-sm px-2 py-1 cursor-pointer"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-text)',
      }}
    >
      {LOCALES.map(l => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun test tests/components/LanguageSelector.test.tsx
```

Expected: PASS — all 3 tests pass.

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/components/LanguageSelector.tsx openraven-ui/tests/i18n-setup.ts openraven-ui/tests/components/LanguageSelector.test.tsx && git commit -m "feat(i18n): add LanguageSelector component with tests"
```

---

## Task 5: Integrate i18n into App.tsx (navbar + LanguageSelector)

**Files:**
- Modify: `openraven-ui/src/App.tsx`

- [ ] **Step 1: Update `src/App.tsx`**

Replace the full contents with:

```tsx
import { Routes, Route, NavLink, useLocation, Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { LanguageSelector } from "./components/LanguageSelector";
import AskPage from "./pages/AskPage";
import StatusPage from "./pages/StatusPage";
import IngestPage from "./pages/IngestPage";
import GraphPage from "./pages/GraphPage";
import WikiPage from "./pages/WikiPage";
import ConnectorsPage from "./pages/ConnectorsPage";
import AgentsPage from "./pages/AgentsPage";
import CoursesPage from "./pages/CoursesPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";

function BlockLogo() {
  return (
    <div className="flex gap-0.5">
      <div className="w-1 h-5" style={{ background: "#ffd900" }} />
      <div className="w-1 h-5" style={{ background: "#ffa110" }} />
      <div className="w-1 h-5" style={{ background: "#fb6424" }} />
      <div className="w-1 h-5" style={{ background: "#fa520f" }} />
    </div>
  );
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? "text-[var(--color-brand)] border-b-2 border-[var(--color-brand)] pb-1 text-sm"
    : "text-[var(--color-text-secondary)] hover:text-[var(--color-brand)] text-sm pb-1";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const { t } = useTranslation('common');
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-page)" }}>
      <span style={{ color: "var(--color-text-muted)" }}>{t('loading')}</span>
    </div>
  );
  if (!user) return <Navigate to="/login" />;
  return <>{children}</>;
}

function AppShell() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { t } = useTranslation('common');
  const isGraphPage = location.pathname === "/graph";

  return (
    <div className="h-screen flex flex-col" style={{ background: "var(--bg-page)", color: "var(--color-text)" }}>
      <nav className="px-6 py-3 flex items-center gap-6 shrink-0 sticky top-0 z-50"
        style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)" }}>
        <div className="flex items-center gap-2">
          <BlockLogo />
          <span className="text-lg tracking-tight" style={{ color: "var(--color-text)", letterSpacing: "-0.5px" }}>OpenRaven</span>
        </div>
        <NavLink to="/" end className={navLinkClass}>{t('nav.ask')}</NavLink>
        <NavLink to="/ingest" className={navLinkClass}>{t('nav.addFiles')}</NavLink>
        <NavLink to="/graph" className={navLinkClass}>{t('nav.graph')}</NavLink>
        <NavLink to="/wiki" className={navLinkClass}>{t('nav.wiki')}</NavLink>
        <NavLink to="/connectors" className={navLinkClass}>{t('nav.connectors')}</NavLink>
        <NavLink to="/agents" className={navLinkClass}>{t('nav.agents')}</NavLink>
        <NavLink to="/courses" className={navLinkClass}>{t('nav.courses')}</NavLink>
        <NavLink to="/status" className={navLinkClass}>{t('nav.status')}</NavLink>
        {user && (
          <div className="ml-auto flex items-center gap-3">
            <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>{user.email}</span>
            <LanguageSelector />
            <button onClick={logout} className="text-sm cursor-pointer hover:opacity-70" style={{ color: "var(--color-brand)" }}>
              {t('signOut')}
            </button>
          </div>
        )}
      </nav>
      <main className={isGraphPage ? "flex-1 flex flex-col min-h-0" : "max-w-4xl mx-auto px-6 py-8 w-full flex-1"}>
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/wiki" element={<WikiPage />} />
          <Route path="/connectors" element={<ConnectorsPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/courses" element={<CoursesPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/*" element={
          <AuthGuard>
            <AppShell />
          </AuthGuard>
        } />
      </Routes>
    </AuthProvider>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/App.tsx && git commit -m "feat(i18n): integrate useTranslation + LanguageSelector into App.tsx navbar"
```

---

## Task 6: Extract strings from auth pages (Login, Signup, ResetPassword)

**Files:**
- Modify: `openraven-ui/src/pages/LoginPage.tsx`
- Modify: `openraven-ui/src/pages/SignupPage.tsx`
- Modify: `openraven-ui/src/pages/ResetPasswordPage.tsx`

- [ ] **Step 1: Update `LoginPage.tsx`**

Replace full contents with:

```tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { useNavigate, Link } from "react-router-dom";
import { LanguageSelector } from "../components/LanguageSelector";

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err: any) {
      setError(err.message || t('loginFailed'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative" style={{ background: "var(--bg-page)" }}>
      <div className="absolute top-4 right-4">
        <LanguageSelector />
      </div>
      <div className="w-full max-w-sm p-8" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="flex gap-0.5">
            <div className="w-1.5 h-6" style={{ background: "#ffd900" }} />
            <div className="w-1.5 h-6" style={{ background: "#ffa110" }} />
            <div className="w-1.5 h-6" style={{ background: "#fb6424" }} />
            <div className="w-1.5 h-6" style={{ background: "#fa520f" }} />
          </div>
          <span className="text-2xl" style={{ color: "var(--color-text)", letterSpacing: "-0.5px" }}>OpenRaven</span>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email" value={email} onChange={e => setEmail(e.target.value)}
            placeholder={t('email')} aria-label={t('email')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
          <input
            type="password" value={password} onChange={e => setPassword(e.target.value)}
            placeholder={t('password')} aria-label={t('password')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
          {error && <p className="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>}
          <button
            type="submit" disabled={loading}
            className="py-2.5 text-base uppercase cursor-pointer disabled:opacity-50"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
          >
            {loading ? t('signingIn') : t('signIn')}
          </button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
          <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>{t('or', { ns: 'common' })}</span>
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
        </div>

        <button
          onClick={loginWithGoogle}
          className="w-full py-2.5 text-base cursor-pointer"
          style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}
        >
          {t('signInGoogle')}
        </button>

        <div className="mt-6 text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
          <Link to="/reset-password" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>
            {t('forgotPassword')}
          </Link>
          <span className="mx-2">·</span>
          <Link to="/signup" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>
            {t('createAccount')}
          </Link>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Update `SignupPage.tsx`**

Replace full contents with:

```tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { useNavigate, Link } from "react-router-dom";
import { LanguageSelector } from "../components/LanguageSelector";

export default function SignupPage() {
  const { signup, loginWithGoogle } = useAuth();
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) { setError(t('passwordsMismatch')); return; }
    if (password.length < 8) { setError(t('passwordTooShort')); return; }
    setLoading(true);
    try {
      await signup(name, email, password);
      navigate("/");
    } catch (err: any) {
      setError(err.message || t('signupFailed'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative" style={{ background: "var(--bg-page)" }}>
      <div className="absolute top-4 right-4">
        <LanguageSelector />
      </div>
      <div className="w-full max-w-sm p-8" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="flex gap-0.5">
            <div className="w-1.5 h-6" style={{ background: "#ffd900" }} />
            <div className="w-1.5 h-6" style={{ background: "#ffa110" }} />
            <div className="w-1.5 h-6" style={{ background: "#fb6424" }} />
            <div className="w-1.5 h-6" style={{ background: "#fa520f" }} />
          </div>
          <span className="text-2xl" style={{ color: "var(--color-text)", letterSpacing: "-0.5px" }}>OpenRaven</span>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder={t('fullName')} aria-label={t('fullName')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder={t('email')} aria-label={t('email')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder={t('passwordHint')} aria-label={t('password')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder={t('confirmPassword')} aria-label={t('confirmPassword')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          {error && <p className="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>}
          <button type="submit" disabled={loading}
            className="py-2.5 text-base uppercase cursor-pointer disabled:opacity-50"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
            {loading ? t('creatingAccount') : t('signUp')}
          </button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
          <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>{t('or', { ns: 'common' })}</span>
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
        </div>

        <button onClick={loginWithGoogle} className="w-full py-2.5 text-base cursor-pointer"
          style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
          {t('signUpGoogle')}
        </button>

        <div className="mt-6 text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
          {t('alreadyHaveAccount')}{" "}
          <Link to="/login" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>{t('signInLink')}</Link>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update `ResetPasswordPage.tsx`**

Replace full contents with:

```tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { LanguageSelector } from "../components/LanguageSelector";

export default function ResetPasswordPage() {
  const { t } = useTranslation('auth');
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setSent(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative" style={{ background: "var(--bg-page)" }}>
      <div className="absolute top-4 right-4">
        <LanguageSelector />
      </div>
      <div className="w-full max-w-sm p-8" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="flex gap-0.5">
            <div className="w-1.5 h-6" style={{ background: "#ffd900" }} />
            <div className="w-1.5 h-6" style={{ background: "#ffa110" }} />
            <div className="w-1.5 h-6" style={{ background: "#fb6424" }} />
            <div className="w-1.5 h-6" style={{ background: "#fa520f" }} />
          </div>
          <span className="text-2xl" style={{ color: "var(--color-text)", letterSpacing: "-0.5px" }}>OpenRaven</span>
        </div>

        {sent ? (
          <div className="text-center">
            <p className="text-base mb-4" style={{ color: "var(--color-text)" }}>
              {t('resetSent')}
            </p>
            <Link to="/login" style={{ color: "var(--color-brand)" }}>{t('backToSignIn')}</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              {t('resetInstructions')}
            </p>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder={t('email')} aria-label={t('email')} required
              className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <button type="submit" disabled={loading}
              className="py-2.5 text-base uppercase cursor-pointer disabled:opacity-50"
              style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
              {loading ? t('sending') : t('sendResetLink')}
            </button>
            <div className="text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
              <Link to="/login" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>{t('backToSignIn')}</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/pages/LoginPage.tsx openraven-ui/src/pages/SignupPage.tsx openraven-ui/src/pages/ResetPasswordPage.tsx && git commit -m "feat(i18n): extract strings from auth pages (login, signup, reset)"
```

---

## Task 7: Extract strings from AskPage + pass locale to /api/ask

**Files:**
- Modify: `openraven-ui/src/pages/AskPage.tsx`

- [ ] **Step 1: Update `AskPage.tsx`**

Replace full contents with:

```tsx
import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import ChatMessage from "../components/ChatMessage";
import DiscoveryCard from "../components/DiscoveryCard";

const QUERY_MODES = ['mix', 'local', 'global', 'hybrid', 'naive', 'bypass'] as const;

interface SourceRef { document: string; excerpt: string; char_start: number; char_end: number; }
interface Message { role: "user" | "assistant"; content: string; sources?: SourceRef[]; }
interface Insight { insight_type: string; title: string; description: string; related_entities: string[]; }

export default function AskPage() {
  const { t } = useTranslation('ask');
  const { i18n } = useTranslation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [mode, setMode] = useState("mix");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetch("/api/discovery").then(r => r.json()).then(setInsights).catch(() => {}); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, mode, locale: i18n.language }) });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.answer, sources: data.sources ?? [] }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: t('errorReach') }]);
    } finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {messages.length === 0 && insights.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <h2 className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>
            {t('heroTitle')}
          </h2>
        </div>
      )}
      {messages.length === 0 && insights.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>{t('discoveriesHeading')}</h2>
          <div className="grid grid-cols-2 gap-4">{insights.map((insight, i) => <DiscoveryCard key={i} insight={insight} />)}</div>
        </div>
      )}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((msg, i) => (
          <div key={i}>
            <ChatMessage role={msg.role} content={msg.content} />
            {msg.sources && msg.sources.length > 0 && (
              <div className="ml-4 mt-1 mb-2 pl-3" style={{ borderLeft: "2px solid var(--color-border)" }}>
                <div className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>{t('sourcesCount', { count: msg.sources.length })}</div>
                {msg.sources.map((s, j) => (
                  <div key={j} className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>
                    <span style={{ color: "var(--color-brand)" }}>{s.document}</span>
                    {s.excerpt && <span className="ml-2" style={{ color: "var(--color-text-muted)" }}>— {s.excerpt}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-sm animate-pulse" style={{ color: "var(--color-text-muted)" }}>{t('thinking')}</div>}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSubmit} className="flex gap-3 pt-4 items-end" style={{ borderTop: "1px solid var(--color-border)" }}>
        <div className="flex flex-col gap-1">
          <label htmlFor="mode-select" className="text-xs" style={{ color: "var(--color-text-muted)" }}>{t('modeLabel')}</label>
          <select
            id="mode-select"
            value={mode}
            onChange={e => setMode(e.target.value)}
            className="px-2 py-2.5 text-sm cursor-pointer"
            aria-label="Query mode"
            title={t(`modeDesc.${mode}`)}
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          >
            {QUERY_MODES.map(m => <option key={m} value={m}>{t(`modes.${m}`)}</option>)}
          </select>
        </div>
        <input type="text" value={input} onChange={e => setInput(e.target.value)} placeholder={t('placeholder')}
          aria-label={t('placeholder')}
          className="flex-1 px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
        <button type="submit" disabled={loading || !input.trim()}
          className="px-5 py-2.5 text-sm uppercase cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-default"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{t('submit')}</button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/pages/AskPage.tsx && git commit -m "feat(i18n): extract AskPage strings + pass locale to /api/ask"
```

---

## Task 8: Extract strings from remaining pages (Ingest, Graph, Wiki, Connectors, Agents, Courses, Status)

**Files:**
- Modify: `openraven-ui/src/pages/IngestPage.tsx`
- Modify: `openraven-ui/src/pages/GraphPage.tsx`
- Modify: `openraven-ui/src/pages/WikiPage.tsx`
- Modify: `openraven-ui/src/pages/ConnectorsPage.tsx`
- Modify: `openraven-ui/src/pages/AgentsPage.tsx`
- Modify: `openraven-ui/src/pages/CoursesPage.tsx`
- Modify: `openraven-ui/src/pages/StatusPage.tsx`
- Modify: `openraven-ui/src/components/FileUploader.tsx`
- Modify: `openraven-ui/src/components/GraphNodeDetail.tsx`

This task is large but mechanical — each page gets `useTranslation('<namespace>')` and replaces hard-coded strings with `t('key')` calls. The pattern is identical across all pages, matching keys from the English JSON files created in Task 3.

- [ ] **Step 1: Update `IngestPage.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('ingest');` at the top of the component.

Replace hard-coded strings:
- `"Add Documents"` → `{t('title')}`
- `"Extraction Schema"` → `{t('schemaLabel')}`
- `"Auto-detect (default)"` → `{t('schemaAuto')}`
- `"Import from Notion..."` → `{t('importHint')}`
- `STAGE_LABELS` object → use `t('stages.uploading')`, `t('stages.processing')`, `t('stages.done')`, `t('stages.error')`
- `"Files processed"` → `{t('stats.filesProcessed')}`
- `"Entities extracted"` → `{t('stats.entitiesExtracted')}`
- `"Articles generated"` → `{t('stats.articlesGenerated')}`
- Error message `"Failed to connect..."` → `t('uploadError')`

Remove the `STAGE_LABELS` const. Replace its usage at line 94 with:
```tsx
<span style={{ color: "var(--color-text-secondary)" }}>{t(`stages.${stage}`) ?? stage}</span>
```

- [ ] **Step 2: Update `FileUploader.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('ingest');` at the top of the component.

Replace:
- `"Drop files here"` → `{t('dropFiles')}`
- `"PDF, DOCX, PPTX..."` → `{t('fileTypes')}`
- `"BROWSE FILES"` → `{t('browseFiles')}`

- [ ] **Step 3: Update `GraphPage.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('graph');` at the top of the component.

Replace:
- `"Loading graph..."` → `{t('loadingGraph')}`
- `"Knowledge Graph"` → `{t('title')}`
- `"No graph data yet..."` → `{t('emptyMessage')}`
- `"Search nodes..."` → `{t('searchPlaceholder')}` (placeholder and aria-label)
- `"Min connections:"` → `{t('minConnections')}`
- `"Export GraphML"` → `{t('exportGraphML')}`
- `"Export PNG"` → `{t('exportPNG')}`
- `"{filteredNodes.length} nodes / {filteredEdges.length} edges"` → `` {`${filteredNodes.length} ${t('nodesCount', { ns: 'common', count: filteredNodes.length }).split(' ').pop()} / ${filteredEdges.length} ${t('edgesCount', { ns: 'common', count: filteredEdges.length }).split(' ').pop()}`} ``

Actually, simpler approach for the stats line:
```tsx
<span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>
  {filteredNodes.length} / {filteredEdges.length}
  {data.is_truncated && ` ${t('truncated', { ns: 'common' })}`}
</span>
```

- [ ] **Step 4: Update `GraphNodeDetail.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('graph');` at the top of the component.

Replace:
- `"Source"` → `{t('source')}`
- `"Connected ({neighbors.length})"` → `{t('connectedCount', { count: neighbors.length })}`

- [ ] **Step 5: Update `WikiPage.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('wiki');` at the top of the component.

Replace:
- `"Loading wiki..."` → `{t('loadingWiki')}`
- `"Knowledge Wiki"` → `{t('title')}`
- `"No articles yet..."` → `{t('emptyMessage')}`
- `"Articles ({articles.length})"` → `{t('articlesCount', { count: articles.length })}`
- `"Export"` → `{t('export', { ns: 'common' })}`
- `"Select an article to read"` → `{t('selectArticle')}`

- [ ] **Step 6: Update `ConnectorsPage.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('connectors');` at the top of the component.

Replace:
- `"Connectors"` → `{t('title')}`
- `"Google OAuth not configured..."` → `{t('oauthWarning')}`
- `"Connect"` → `{t('connect', { ns: 'common' })}`
- `"Connected"` / `"Not connected"` → `{t('connected', { ns: 'common' })}` / `{t('notConnected', { ns: 'common' })}`
- `"Syncing..."` → `{t('syncing', { ns: 'common' })}`
- `"Sync Now"` → `{t('syncNow', { ns: 'common' })}`
- Connector descriptions → `{t('gdrive.desc')}`, `{t('gmail.desc')}`, `{t('meet.desc')}`, `{t('otter.desc')}`
- Connector names → `{t('gdrive.name')}`, `{t('gmail.name')}`, `{t('meet.name')}`, `{t('otter.name')}`
- `"Sync Transcripts"` → `{t('meet.syncLabel')}`
- `"Otter.ai API key"` → `{t('otter.apiKeyPlaceholder')}`
- `"Saving..."` / `"Save"` → `{t('saving', { ns: 'common' })}` / `{t('save', { ns: 'common' })}`
- `"Sync failed"` → `t('syncFailed')`
- Stats labels → `{t('stats.filesSynced')}`, `{t('stats.entities')}`, `{t('stats.articles')}`

Refactor the `connectors` array to use translation keys instead of hard-coded strings:
```tsx
const connectors = [
  { key: "gdrive" as const, connected: status.gdrive.connected, syncLabel: t('syncNow', { ns: 'common' }) },
  { key: "gmail" as const, connected: status.gmail.connected, syncLabel: t('syncNow', { ns: 'common' }) },
  { key: "meet" as const, connected: status.meet.connected, syncLabel: t('meet.syncLabel') },
];
```
And in the JSX: `<h2>{t(`${c.key}.name`)}</h2>`, `<p>{t(`${c.key}.desc`)}</p>`.

- [ ] **Step 7: Update `AgentsPage.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('agents');` at the top of the component.

Replace:
- `"Expert Agents"` → `{t('title')}`
- `"Create Agent"` / `"Cancel"` → `{t('createAgent')}` / `{t('cancel', { ns: 'common' })}`
- `"Agent name..."` → placeholder `{t('namePlaceholder')}`
- `"Description..."` → placeholder `{t('descriptionPlaceholder')}`
- `"Creating..."` / `"Create"` → `{t('creating', { ns: 'common' })}` / `{t('create', { ns: 'common' })}`
- `"No agents yet..."` → `{t('emptyMessage')}`
- `"Deployed"` / `"Local only"` → `{t('deployed')}` / `{t('localOnly')}`
- `"Copy URL"` / `"Copied!"` → `{t('copyUrl')}` / `{t('copied', { ns: 'common' })}`
- `"Generate Token"` / `"Token copied!"` → `{t('generateToken')}` / `{t('tokenCopied')}`
- `"Delete"` → `{t('delete', { ns: 'common' })}`

- [ ] **Step 8: Update `CoursesPage.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('courses');` at the top of the component.

Replace:
- `"Courses"` → `{t('title')}`
- `"Generate a Course"` → `{t('generateCourse')}`
- `"Course Title *"` → `{t('courseTitle')}`
- Placeholder `"e.g., Introduction..."` → `{t('courseTitlePlaceholder')}`
- `"Target Audience"` → `{t('targetAudience')}`
- Placeholder `"e.g., Backend Engineers"` → `{t('audiencePlaceholder')}`
- `"Learning Objectives..."` → `{t('learningObjectives')}`
- Textarea placeholder → `{t('objectivesPlaceholder')}`
- `"Generating..."` / `"Generate Course"` → `{t('generating')}` / `{t('generate')}`
- `"Generated Courses"` → `{t('generatedCourses')}`
- `"{c.chapter_count} chapters"` → `{t('chaptersCount', { count: c.chapter_count })}`
- `"Download"` → `{t('download', { ns: 'common' })}`
- `"Delete"` → `{t('delete', { ns: 'common' })}`
- `"No courses generated yet..."` → `{t('emptyMessage')}`
- Progress text: `"Planning curriculum..."` → `t('progress.planning')`, etc.
- `"Generation failed"` → `t('generationFailed')`
- `"Failed to start generation"` → `t('startFailed')`

Refactor the `progressText` block:
```tsx
const progressText = job
  ? job.stage === "planning" ? t('progress.planning')
  : job.stage === "generating" ? t('progress.generating', { done: job.chapters_done, total: job.chapters_total })
  : job.stage === "done" ? t('progress.done')
  : job.stage === "error" ? t('progress.error')
  : job.stage
  : "";
```

- [ ] **Step 9: Update `StatusPage.tsx`**

Add `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation('status');` at the top of the component.

Replace:
- `"Loading..."` → `{t('loading', { ns: 'common' })}`
- `"Knowledge Base Status"` → `{t('title')}`
- `"Files"` → `{t('files')}`
- `"Concepts"` → `{t('concepts')}`
- `"Connections"` → `{t('connections')}`
- `"Topics"` → `{t('topics')}`
- `"LLM: "` → `{t('llm')}`
- `"Top Topics"` → `{t('topTopics')}`
- `"Health Insights"` → `{t('healthInsights')}`

- [ ] **Step 10: Run existing tests to verify nothing broke**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun test tests/
```

- [ ] **Step 11: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/pages/ openraven-ui/src/components/FileUploader.tsx openraven-ui/src/components/GraphNodeDetail.tsx && git commit -m "feat(i18n): extract strings from all remaining pages and components"
```

---

## Task 9: Backend — add locale column + PATCH endpoint + update /me

**Files:**
- Modify: `openraven/src/openraven/auth/db.py:12-27`
- Modify: `openraven/src/openraven/auth/models.py:17-22`
- Modify: `openraven/src/openraven/auth/routes.py:133-164`
- Create: `openraven/alembic/versions/002_add_user_locale.py`
- Create: `openraven/tests/test_auth_locale.py`

- [ ] **Step 1: Write failing test `tests/test_auth_locale.py`**

```python
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from openraven.auth.db import get_engine, create_tables
from openraven.auth.routes import create_auth_router

SUPPORTED_LOCALES = {"en", "zh-TW", "zh-CN", "ja", "ko", "fr", "es", "nl", "it", "vi", "th", "ru"}


@pytest.fixture
def client(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path}/test_locale.db")
    create_tables(engine)
    app = FastAPI()
    app.include_router(create_auth_router(engine))
    yield TestClient(app)


def _signup_and_login(client) -> TestClient:
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    return client


def test_me_returns_locale_null_by_default(client):
    _signup_and_login(client)
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["user"]["locale"] is None


def test_patch_locale_updates_user(client):
    _signup_and_login(client)
    res = client.patch("/api/auth/locale", json={"locale": "zh-TW"})
    assert res.status_code == 200
    assert res.json()["ok"] is True

    me = client.get("/api/auth/me")
    assert me.json()["user"]["locale"] == "zh-TW"


def test_patch_locale_rejects_unsupported(client):
    _signup_and_login(client)
    res = client.patch("/api/auth/locale", json={"locale": "xx-YY"})
    assert res.status_code == 400


def test_patch_locale_requires_auth(client):
    res = client.patch("/api/auth/locale", json={"locale": "en"})
    assert res.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_auth_locale.py -v
```

Expected: FAIL — locale column doesn't exist, endpoint doesn't exist.

- [ ] **Step 3: Add locale column to `auth/db.py`**

In `openraven/src/openraven/auth/db.py`, add after the `email_verified` column (line 20):

```python
    Column("locale", String(10)),
```

So the users table becomes:
```python
users = Table(
    "users", metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("name", String(255), nullable=False),
    Column("avatar_url", String(1024)),
    Column("google_id", String(255), unique=True),
    Column("password_hash", String(255)),
    Column("email_verified", Boolean, default=False),
    Column("locale", String(10)),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    CheckConstraint(
        "google_id IS NOT NULL OR password_hash IS NOT NULL",
        name="auth_method_check",
    ),
)
```

- [ ] **Step 4: Add locale to UserResponse in `auth/models.py`**

Add `locale: str | None = None` to the `UserResponse` model:

```python
class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    email_verified: bool = False
    locale: str | None = None
```

- [ ] **Step 5: Create `LocaleUpdate` model in `auth/models.py`**

Add at the end of the file:

```python
class LocaleUpdate(BaseModel):
    locale: str
```

- [ ] **Step 6: Update routes — add PATCH /locale endpoint and update /me**

In `openraven/src/openraven/auth/routes.py`:

Add to the imports at line 12:
```python
from openraven.auth.models import (
    UserCreate, UserLogin, UserResponse, TenantResponse, AuthMeResponse,
    PasswordResetRequest, PasswordResetConfirm, LocaleUpdate,
)
```

Add `SUPPORTED_LOCALES` constant after the rate limit constants (around line 23):
```python
SUPPORTED_LOCALES = {"en", "zh-TW", "zh-CN", "ja", "ko", "fr", "es", "nl", "it", "vi", "th", "ru"}
```

Update the `/me` endpoint to include `locale` — change the select query at line 143-145 to also select `users.c.locale`:
```python
            user_row = conn.execute(
                select(users.c.id, users.c.email, users.c.name, users.c.avatar_url, users.c.email_verified, users.c.locale)
                .where(users.c.id == ctx.user_id)
            ).first()
```

And update the UserResponse construction at lines 156-158:
```python
        return AuthMeResponse(
            user=UserResponse(
                id=user_row.id, email=user_row.email, name=user_row.name,
                avatar_url=user_row.avatar_url, email_verified=user_row.email_verified or False,
                locale=user_row.locale,
            ),
            tenant=TenantResponse(
                id=tenant_row.id, name=tenant_row.name,
                storage_quota_mb=tenant_row.storage_quota_mb,
            ),
        ).model_dump()
```

Add the PATCH endpoint after the `/me` endpoint (before the Google OAuth section):
```python
    @router.patch("/locale")
    async def update_locale(data: LocaleUpdate, request: Request):
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(401, "Not authenticated")
        ctx = validate_session(engine, session_id)
        if not ctx:
            raise HTTPException(401, "Session expired")
        if data.locale not in SUPPORTED_LOCALES:
            raise HTTPException(400, f"Unsupported locale: {data.locale}")
        with engine.connect() as conn:
            conn.execute(
                update(users).where(users.c.id == ctx.user_id).values(locale=data.locale)
            )
            conn.commit()
        return {"ok": True}
```

- [ ] **Step 7: Create Alembic migration `002_add_user_locale.py`**

```python
"""Add locale column to users table.

Revision ID: 002
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locale", sa.String(10)))


def downgrade() -> None:
    op.drop_column("users", "locale")
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_auth_locale.py -v
```

Expected: PASS — all 4 tests pass.

- [ ] **Step 9: Run existing auth tests to verify nothing broke**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_auth_api.py -v
```

Expected: PASS — all existing tests still pass.

- [ ] **Step 10: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/auth/db.py openraven/src/openraven/auth/models.py openraven/src/openraven/auth/routes.py openraven/alembic/versions/002_add_user_locale.py openraven/tests/test_auth_locale.py && git commit -m "feat(i18n): add locale column, PATCH /locale endpoint, include locale in /me"
```

---

## Task 10: Backend — inject locale into LLM prompt for /api/ask

**Files:**
- Modify: `openraven/src/openraven/api/server.py:22-24,187-194`
- Modify: `openraven/src/openraven/pipeline.py:219-220`
- Modify: `openraven/src/openraven/graph/rag.py:250-258`

- [ ] **Step 1: Add `locale` field to `AskRequest` model**

In `openraven/src/openraven/api/server.py`, update `AskRequest` (lines 22-24):

```python
class AskRequest(BaseModel):
    question: str
    mode: str = "mix"
    locale: str = "en"
```

- [ ] **Step 2: Update the `/api/ask` handler to pass locale**

In `openraven/src/openraven/api/server.py`, update the ask endpoint (lines 187-194):

```python
    @app.post("/api/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        result = await pipeline.ask_with_sources(req.question, mode=req.mode, locale=req.locale)
        return AskResponse(
            answer=result.answer,
            mode=req.mode,
            sources=[SourceRef(**s) for s in result.sources],
        )
```

- [ ] **Step 3: Update `pipeline.ask_with_sources` to accept locale**

In `openraven/src/openraven/pipeline.py`, update the method (line 219):

```python
    async def ask_with_sources(self, question: str, mode: str = "mix", locale: str = "en") -> QueryResult:
        return await self.graph.query_with_sources(question, mode=mode, locale=locale)
```

- [ ] **Step 4: Update `graph/rag.py` to inject locale into LLM query**

In `openraven/src/openraven/graph/rag.py`, add the `LOCALE_NAMES` constant near the top of the file (after imports):

```python
LOCALE_NAMES = {
    "en": "English",
    "zh-TW": "Traditional Chinese (繁體中文)",
    "zh-CN": "Simplified Chinese (简体中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
    "nl": "Dutch (Nederlands)",
    "it": "Italian (Italiano)",
    "vi": "Vietnamese (Tiếng Việt)",
    "th": "Thai (ภาษาไทย)",
    "ru": "Russian (Русский)",
}
```

Update `query_with_sources` (line 250):

```python
    async def query_with_sources(self, question: str, mode: QueryMode = "mix", locale: str = "en") -> QueryResult:
        await self.ensure_initialized()
        if not self._rag:
            return QueryResult(answer="", sources=[])
        locale_name = LOCALE_NAMES.get(locale, "English")
        localized_question = question
        if locale != "en":
            localized_question = f"{question}\n\n[IMPORTANT: Respond in {locale_name}. The user's interface language is {locale}.]"
        answer = await self._rag.aquery(localized_question, param=QueryParam(mode=mode))
        if not answer:
            return QueryResult(answer="", sources=[])
        sources = self._extract_sources_from_answer(answer)
        return QueryResult(answer=answer, sources=sources)
```

- [ ] **Step 5: Run backend tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/test_api.py -v
```

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/api/server.py openraven/src/openraven/pipeline.py openraven/src/openraven/graph/rag.py && git commit -m "feat(i18n): inject locale into LLM prompt for /api/ask responses"
```

---

## Task 11: Sync locale from user profile on login

**Files:**
- Modify: `openraven-ui/src/hooks/useAuth.tsx`

- [ ] **Step 1: Update `useAuth.tsx` to sync locale on login**

In `openraven-ui/src/hooks/useAuth.tsx`, add the i18n import at line 1:

```tsx
import { createContext, useContext, useState, useEffect, useCallback } from "react";
import i18n from "../i18n";
```

Update the `User` interface to include locale:

```tsx
interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  locale?: string;
}
```

In the `fetchMe` callback, after `setUser(data.user)` (around line 38), add locale sync:

```tsx
      const res = await fetch("/api/auth/me");
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
        setTenant(data.tenant);
        if (data.user.locale) {
          i18n.changeLanguage(data.user.locale);
        }
      } else {
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/hooks/useAuth.tsx && git commit -m "feat(i18n): sync locale from user profile on login"
```

---

## Task 12: Generate translation files for all 11 non-English locales

**Files:**
- Create: `openraven-ui/public/locales/{zh-TW,zh-CN,ja,ko,fr,es,nl,it,vi,th,ru}/*.json` (110 files)

This is a bulk-generation task. For each of the 11 locales, create the same 10 namespace JSON files with translated values. The keys remain identical to the English files.

- [ ] **Step 1: Create a script to generate all locale directories and files**

Write a Node/Bun script `openraven-ui/scripts/generate-locales.ts` that:
1. Reads all JSON files from `public/locales/en/`
2. For each non-English locale, creates the directory and copies the English JSON files as a starting point
3. The script is a one-time bootstrap — translations will be manually edited after

```ts
import { readdir, readFile, writeFile, mkdir } from "fs/promises";
import { join } from "path";

const LOCALES = ['zh-TW', 'zh-CN', 'ja', 'ko', 'fr', 'es', 'nl', 'it', 'vi', 'th', 'ru'];
const BASE = join(import.meta.dir, '../public/locales');

async function main() {
  const enDir = join(BASE, 'en');
  const files = await readdir(enDir);

  for (const locale of LOCALES) {
    const dir = join(BASE, locale);
    await mkdir(dir, { recursive: true });
    for (const file of files) {
      const content = await readFile(join(enDir, file), 'utf-8');
      await writeFile(join(dir, file), content);
    }
    console.log(`Created ${locale}/ with ${files.length} files`);
  }
}

main();
```

- [ ] **Step 2: Run the script**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run scripts/generate-locales.ts
```

- [ ] **Step 3: Translate the generated files**

For each locale, update the JSON values with proper translations. The keys stay the same — only the string values change. This can be done manually or with LLM assistance.

Priority order for translation: `common.json` (nav/shared) → `auth.json` (login flow) → `ask.json` (main feature) → remaining namespaces.

- [ ] **Step 4: Remove the bootstrap script**

```bash
rm openraven-ui/scripts/generate-locales.ts
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/public/locales/ && git commit -m "feat(i18n): add translation files for all 12 locales"
```

---

## Task 13: Run all tests and verify

**Files:** None (verification only)

- [ ] **Step 1: Run frontend tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun test tests/
```

Expected: All existing tests pass + new LanguageSelector tests pass.

- [ ] **Step 2: Run backend tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python -m pytest tests/ -v
```

Expected: All existing tests pass + new locale tests pass.

- [ ] **Step 3: Type-check frontend**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bunx tsc --noEmit
```

Expected: No TypeScript errors.

- [ ] **Step 4: Verify dev server starts and locale detection works**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && timeout 10 bun run dev:client 2>&1 || true
```

Check that:
- Vite starts without errors
- `/locales/en/common.json` is fetchable
- Language selector appears in the navbar
- Switching locale changes all UI text

- [ ] **Step 5: Final commit if any adjustments were made**

```bash
cd /home/ubuntu/source/OpenRaven && git add -A && git status
```

Only commit if there are uncommitted changes from fixes.
