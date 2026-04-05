# Multi-Locale Internationalization (i18n) Design

**Date:** 2026-04-05
**Status:** Approved
**Scope:** UI chrome + AskPage LLM responses

---

## Overview

Add multi-locale support to OpenRaven's Web UI. The browser auto-detects the user's locale from browser/OS settings, with English as the default fallback. Users can manually override via a language selector in the navbar. Locale preference is persisted in both localStorage (for immediate use) and the user profile (for cross-device sync).

## Supported Locales

| Language | Code | Direction |
|----------|------|-----------|
| English | `en` | LTR |
| Traditional Chinese | `zh-TW` | LTR |
| Simplified Chinese | `zh-CN` | LTR |
| Japanese | `ja` | LTR |
| Korean | `ko` | LTR |
| French | `fr` | LTR |
| Spanish | `es` | LTR |
| Dutch | `nl` | LTR |
| Italian | `it` | LTR |
| Vietnamese | `vi` | LTR |
| Thai | `th` | LTR |
| Russian | `ru` | LTR |

Default fallback: `en`. All locales are LTR — no RTL layout work required.

## Content Language Rules

| Area | Language Behavior |
|------|-------------------|
| **UI chrome** (nav, buttons, labels, errors) | User's selected locale (all 12 languages) |
| **AskPage LLM responses** | Match user's locale — prompt LLM to respond in that language |
| **Wiki articles** | Source language — follows uploaded content, no translation |
| **Knowledge graph labels** | Always English |
| **Course content** | Follows wiki/source content language |

## Library Stack

### Packages

- `i18next` — core i18n engine
- `react-i18next` — React bindings (`useTranslation` hook, `I18nextProvider`)
- `i18next-browser-languagedetector` — auto-detects from `navigator.language` + localStorage
- `i18next-http-backend` — lazy-loads JSON translation files on demand

### Initialization (`src/i18n.ts`)

```ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: ['en','zh-TW','zh-CN','ja','ko','fr','es','nl','it','vi','th','ru'],
    ns: ['common','ask','ingest','graph','wiki','connectors','agents','courses','status','auth'],
    defaultNS: 'common',
    backend: { loadPath: '/locales/{{lng}}/{{ns}}.json' },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    interpolation: { escapeValue: false },
  });

i18n.on('languageChanged', (lng) => {
  document.documentElement.setAttribute('lang', lng);
});

export default i18n;
```

### Entry Point (`src/main.tsx`)

```tsx
import './i18n';
import { Suspense } from 'react';

// Wrap App in Suspense for async locale loading
<Suspense fallback={<div>Loading...</div>}>
  <App />
</Suspense>
```

## Translation File Structure

```
openraven-ui/
  public/
    locales/
      en/
        common.json      # nav labels, shared buttons, errors, loading states
        ask.json          # AskPage strings
        ingest.json       # IngestPage strings
        graph.json        # GraphPage strings
        wiki.json         # WikiPage strings
        connectors.json   # ConnectorsPage strings
        agents.json       # AgentsPage strings
        courses.json      # CoursesPage strings
        status.json       # StatusPage strings
        auth.json         # Login, Signup, ResetPassword strings
      zh-TW/
        (same structure)
      zh-CN/
      ja/
      ko/
      fr/
      es/
      nl/
      it/
      vi/
      th/
      ru/
```

Files placed in `public/locales/` so `i18next-http-backend` fetches them as static assets — no build step needed.

### Namespaces

| Namespace | Contents |
|-----------|----------|
| `common` | Nav labels, "Sign out", "Loading...", "Cancel", "Save", "Delete", shared errors |
| `ask` | Hero title, placeholder, submit, thinking, mode labels/descriptions, sources |
| `ingest` | Upload UI, schema labels, stage labels, stats |
| `graph` | Search, filters, export buttons, node detail labels |
| `wiki` | Article list, export, empty states |
| `connectors` | Connector names stay English; status labels, "Connect"/"Sync Now" translated |
| `agents` | Create agent form, token generation, agent management |
| `courses` | Course generation form, audience, objectives |
| `status` | Stats labels, health insights heading, topic labels |
| `auth` | Login/signup/reset forms, validation errors, OAuth buttons |

### Example: `en/common.json`

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
  "error": "Something went wrong"
}
```

### Example: `en/ask.json`

```json
{
  "heroTitle": "What would you like to know?",
  "discoveriesHeading": "Discoveries from your knowledge base",
  "sources": "Sources",
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

### Example: `en/auth.json`

```json
{
  "email": "Email",
  "password": "Password",
  "signIn": "Sign In",
  "signInGoogle": "Sign in with Google",
  "forgotPassword": "Forgot password?",
  "createAccount": "Create account",
  "fullName": "Full name",
  "confirmPassword": "Confirm password",
  "signUp": "Create Account",
  "signUpGoogle": "Sign up with Google",
  "alreadyHaveAccount": "Already have an account?",
  "passwordMinLength": "Password (min 8 chars)",
  "passwordsMismatch": "Passwords do not match",
  "passwordTooShort": "Password must be at least 8 characters"
}
```

## Component Integration Pattern

### `useTranslation` hook in pages

```tsx
// AskPage.tsx
import { useTranslation } from 'react-i18next';

export default function AskPage() {
  const { t } = useTranslation('ask');
  return (
    <>
      <h2>{t('heroTitle')}</h2>
      <input placeholder={t('placeholder')} />
      <button>{t('submit')}</button>
      {loading && <div>{t('thinking')}</div>}
    </>
  );
}
```

### Multiple namespaces

```tsx
// App.tsx — AppShell nav
const { t } = useTranslation('common');
<NavLink to="/">{t('nav.ask')}</NavLink>
<NavLink to="/ingest">{t('nav.addFiles')}</NavLink>
<button onClick={logout}>{t('signOut')}</button>
```

### Interpolation

```tsx
<div>{t('sourcesCount', { count: msg.sources.length })}</div>
```

### QUERY_MODES refactored to use translation keys

```tsx
const QUERY_MODES = ['mix','local','global','hybrid','naive','bypass'] as const;
// In JSX:
<option value={m}>{t(`modes.${m}`)}</option>
// Tooltip:
title={t(`modeDesc.${m}`)}
```

## Language Selector Component

### `src/components/LanguageSelector.tsx`

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

Labels use native language names so users can always find their language.

### Placement

- **Authenticated pages:** Navbar, between user email and "Sign out"
- **Unauthenticated pages** (login/signup/reset): Top-right corner

## Locale Persistence (localStorage + Account Profile)

### Flow

1. **First visit:** `i18next-browser-languagedetector` reads `navigator.language` → sets locale → saves to `localStorage('i18nextLng')`
2. **Manual switch:** User picks from dropdown → `i18n.changeLanguage()` updates localStorage + fires `PATCH /api/auth/locale` to save to user profile (best-effort, non-blocking)
3. **Login:** After `fetchMe()` returns, if `user.locale` is set, call `i18n.changeLanguage(user.locale)` to override localStorage with server-side preference
4. **Unauthenticated pages:** localStorage + browser detection only

### Auth hook change (`useAuth.tsx`)

```tsx
// In fetchMe callback, after setting user:
if (data.user.locale) {
  i18n.changeLanguage(data.user.locale);
}
```

## Backend Changes

### Database

Add `locale` column to `users` table:

```sql
ALTER TABLE users ADD COLUMN locale VARCHAR(10) DEFAULT NULL;
```

`NULL` means "use browser detection" (no explicit preference set yet).

### New endpoint: `PATCH /api/auth/locale`

```ts
// Request: { locale: "zh-TW" }
// Validates locale is in supported list
// Updates users.locale for authenticated user
// Response: { ok: true }
```

### Update `GET /api/auth/me`

Include `locale` in the response:

```ts
{ user: { id, email, name, avatar_url, locale }, tenant: { ... } }
```

### AskPage LLM locale injection

In the `/api/ask` handler, inject locale into the LLM system prompt:

```python
locale = request.get("locale", "en")

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

system_suffix = f"\nIMPORTANT: Respond in {LOCALE_NAMES.get(locale, 'English')}. "
                f"The user's interface language is {locale}."
```

Frontend passes locale per-request:

```tsx
body: JSON.stringify({ question, mode, locale: i18n.language })
```

## HTML `lang` & Font Considerations

### `<html lang>` attribute

Set dynamically on locale change (handled in `src/i18n.ts` init):

```ts
i18n.on('languageChanged', (lng) => {
  document.documentElement.setAttribute('lang', lng);
});
```

### Font stack

Keep system-ui as the base — modern OS fonts handle CJK/Thai/Russian well:

- Windows: MS Gothic, Malgun Gothic, SimHei, Segoe UI
- macOS: Hiragino, PingFang, Apple SD Gothic, SF Pro
- Linux: Noto Sans variants

Update `design-tokens.css` font stack to prefer system-ui:

```css
--font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
```

Only add explicit CJK web fonts if visual testing reveals issues.

## Complete Change Summary

### Frontend (`openraven-ui/`)

| Change | Files |
|--------|-------|
| Install i18next packages (4) | `package.json` |
| Create i18n init config | `src/i18n.ts` (new) |
| Add `import './i18n'` + Suspense wrapper | `src/main.tsx` |
| Create LanguageSelector component | `src/components/LanguageSelector.tsx` (new) |
| Add selector to navbar + unauth pages | `src/App.tsx`, `LoginPage.tsx`, `SignupPage.tsx`, `ResetPasswordPage.tsx` |
| Sync server locale on login | `src/hooks/useAuth.tsx` |
| Set `<html lang>` on locale change | `src/i18n.ts` |
| Update font stack | `src/design-tokens.css` |
| Extract strings → `useTranslation()` | All 11 pages + `ChatMessage`, `DiscoveryCard`, `FileUploader` |
| Create translation JSON files | `public/locales/**/*.json` (108 files: 12 locales × 9 namespaces) |
| Pass locale to `/api/ask` | `src/pages/AskPage.tsx` |

### Backend

| Change | Files |
|--------|-------|
| Add `locale` column to users table | Migration file |
| Add `PATCH /api/auth/locale` endpoint | Auth routes |
| Include `locale` in `/api/auth/me` response | Auth routes |
| Inject locale into LLM system prompt | `/api/ask` handler |

### Out of Scope

- Wiki article translation (follows source language)
- Knowledge graph label translation (stays English)
- Course content translation (follows wiki/source)
- RTL layout support (no RTL locales in scope)
- Web font loading for CJK (use system fonts first)
