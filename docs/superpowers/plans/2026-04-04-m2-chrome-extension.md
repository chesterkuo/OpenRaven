# Chrome Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Chrome extension that lets users save web pages to their OpenRaven knowledge base with one click — captures page content, sends to the local `/api/ingest` endpoint.

**Architecture:** Manifest V3 extension with a popup UI (save button + status) and a content script that extracts readable text from the current page. Sends to the Hono BFF at `http://localhost:3002/api/ingest` as a multipart form upload. The extension needs no external server — it talks to the user's locally-running OpenRaven instance.

**Tech Stack:**
- Chrome Manifest V3
- TypeScript (compiled with Bun)
- Vanilla DOM for popup (minimal bundle, no React)

**PRD Alignment:**
- Implements "Chrome 擴充功能" (P1, M2 acceptance: Chrome Web Store published)
- PRD repo: `openraven-chrome` (Apache 2.0)

**Scope note:** This plan creates the extension in a new directory `openraven-chrome/` within the monorepo. Per the PRD, it could be a separate repo, but keeping it in the monorepo simplifies development. It can be split out before Chrome Web Store publishing.

---

## File Structure

### Extension (openraven-chrome/)

| File | Action | Responsibility |
|---|---|---|
| `manifest.json` | Create | Extension manifest V3, permissions, popup, content script |
| `package.json` | Create | Build tooling (Bun + TypeScript) |
| `tsconfig.json` | Create | TypeScript config |
| `src/popup.html` | Create | Popup UI shell |
| `src/popup.ts` | Create | Popup logic — save button, status display (vanilla DOM, safe methods) |
| `src/content.ts` | Create | Content script — extract page text |
| `src/background.ts` | Create | Service worker — orchestrate capture + upload |
| `src/api.ts` | Create | API client — POST to localhost:3002/api/ingest |
| `icons/icon-16.png` | Create | Extension icon 16x16 |
| `icons/icon-48.png` | Create | Extension icon 48x48 |
| `icons/icon-128.png` | Create | Extension icon 128x128 |
| `tests/api.test.ts` | Create | Unit test for API client |

### Python backend (openraven/)

| File | Action | Responsibility |
|---|---|---|
| `src/openraven/api/server.py` | Modify | Add CORS for chrome-extension:// origins |

---

## Task 1: Extension scaffold — manifest, package.json, build

**Files:**
- Create: `openraven-chrome/manifest.json`
- Create: `openraven-chrome/package.json`
- Create: `openraven-chrome/tsconfig.json`

- [ ] **Step 1: Create manifest.json**

Create `openraven-chrome/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "OpenRaven",
  "version": "0.1.0",
  "description": "Save web pages to your personal knowledge base",
  "permissions": ["activeTab", "scripting"],
  "host_permissions": ["http://localhost:3002/*"],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon-16.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png"
    }
  },
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "icons": {
    "16": "icons/icon-16.png",
    "48": "icons/icon-48.png",
    "128": "icons/icon-128.png"
  }
}
```

- [ ] **Step 2: Create package.json**

Create `openraven-chrome/package.json`:

```json
{
  "name": "openraven-chrome",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "bun run build:popup && bun run build:background && bun run build:content",
    "build:popup": "bun build src/popup.ts --outdir dist --target browser",
    "build:background": "bun build src/background.ts --outdir dist --target browser",
    "build:content": "bun build src/content.ts --outdir dist --target browser",
    "package": "bun run build && cp manifest.json dist/ && cp -r icons dist/ && cp src/popup.html dist/",
    "test": "bun test tests/"
  },
  "devDependencies": {
    "@types/chrome": "latest",
    "typescript": "^5.7.0"
  }
}
```

- [ ] **Step 3: Create tsconfig.json**

Create `openraven-chrome/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "types": ["chrome"]
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 4: Create placeholder icons**

```bash
mkdir -p openraven-chrome/icons
python3 -c "
import struct, zlib
def png(w,h,r,g,b):
    raw=b''
    for _ in range(h): raw+=b'\x00'+bytes([r,g,b])*w
    return b'\x89PNG\r\n\x1a\n'+b''.join(chunk(t,d) for t,d in [
        (b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0)),
        (b'IDAT',zlib.compress(raw)),
        (b'IEND',b'')])
def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
for s in [16,48,128]:
    open(f'openraven-chrome/icons/icon-{s}.png','wb').write(png(s,s,30,64,175))
"
```

- [ ] **Step 5: Commit**

```bash
git add openraven-chrome/
git commit -m "feat(chrome): scaffold extension with manifest v3 and build config"
```

---

## Task 2: Content script — extract page text

**Files:**
- Create: `openraven-chrome/src/content.ts`

- [ ] **Step 1: Create content.ts**

Create `openraven-chrome/src/content.ts`:

```typescript
// Content script: extract readable text from the current page

function extractPageContent(): { title: string; url: string; text: string } {
  const article = document.querySelector("article") ?? document.querySelector("main") ?? document.body;

  const clone = article.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("script, style, nav, footer, header, aside, [role='navigation'], [role='banner']").forEach((el) => el.remove());

  const text = clone.innerText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n");

  return {
    title: document.title,
    url: window.location.href,
    text,
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "EXTRACT_CONTENT") {
    const content = extractPageContent();
    sendResponse(content);
  }
  return true;
});
```

- [ ] **Step 2: Commit**

```bash
git add openraven-chrome/src/content.ts
git commit -m "feat(chrome): add content script for page text extraction"
```

---

## Task 3: API client — send to OpenRaven

**Files:**
- Create: `openraven-chrome/src/api.ts`
- Create: `openraven-chrome/tests/api.test.ts`

- [ ] **Step 1: Create api.ts**

Create `openraven-chrome/src/api.ts`:

```typescript
const OPENRAVEN_URL = "http://localhost:3002";

export interface IngestResult {
  files_processed: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export async function sendToOpenRaven(
  title: string,
  url: string,
  text: string,
): Promise<IngestResult> {
  const markdown = `# ${title}\n\n> Source: ${url}\n\n${text}`;
  const filename = title.replace(/[^a-zA-Z0-9_\- ]/g, "").slice(0, 80).trim() + ".md";

  const formData = new FormData();
  formData.append("files", new Blob([markdown], { type: "text/markdown" }), filename);

  const response = await fetch(`${OPENRAVEN_URL}/api/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`OpenRaven API error: ${response.status}`);
  }

  return response.json();
}

export async function checkConnection(): Promise<boolean> {
  try {
    const response = await fetch(`${OPENRAVEN_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}
```

- [ ] **Step 2: Write test**

Create `openraven-chrome/tests/api.test.ts`:

```typescript
import { describe, it, expect, mock, beforeEach } from "bun:test";

describe("api", () => {
  beforeEach(() => {
    globalThis.fetch = mock(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ files_processed: 1, entities_extracted: 3, articles_generated: 1, errors: [] }),
      } as Response)
    );
  });

  it("checkConnection returns true when server is up", async () => {
    const { checkConnection } = await import("../src/api");
    const result = await checkConnection();
    expect(result).toBe(true);
  });

  it("checkConnection returns false when server is down", async () => {
    globalThis.fetch = mock(() => Promise.reject(new Error("ECONNREFUSED")));
    const { checkConnection } = await import("../src/api");
    const result = await checkConnection();
    expect(result).toBe(false);
  });
});
```

- [ ] **Step 3: Run test**

Run: `cd openraven-chrome && bun install && bun test tests/`

- [ ] **Step 4: Commit**

```bash
git add openraven-chrome/src/api.ts openraven-chrome/tests/api.test.ts
git commit -m "feat(chrome): add API client for OpenRaven ingestion"
```

---

## Task 4: Background service worker

**Files:**
- Create: `openraven-chrome/src/background.ts`

- [ ] **Step 1: Create background.ts**

Create `openraven-chrome/src/background.ts`:

```typescript
import { sendToOpenRaven } from "./api";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "SAVE_PAGE") {
    handleSavePage(message.tabId).then(sendResponse).catch((err) =>
      sendResponse({ success: false, error: err.message })
    );
    return true;
  }
});

async function handleSavePage(tabId: number): Promise<{ success: boolean; result?: any; error?: string }> {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"],
    });

    const [response] = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_CONTENT" }) as any[];
    if (!response?.text) {
      return { success: false, error: "Could not extract page content" };
    }

    const result = await sendToOpenRaven(response.title, response.url, response.text);
    return { success: true, result };
  } catch (err) {
    return { success: false, error: (err as Error).message };
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add openraven-chrome/src/background.ts
git commit -m "feat(chrome): add background service worker for page capture"
```

---

## Task 5: Popup UI (safe DOM methods, no innerHTML)

**Files:**
- Create: `openraven-chrome/src/popup.html`
- Create: `openraven-chrome/src/popup.ts`

- [ ] **Step 1: Create popup.html**

Create `openraven-chrome/src/popup.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { width: 320px; padding: 16px; margin: 0; background: #030712; color: #e5e7eb; font-family: system-ui, sans-serif; font-size: 14px; }
    .btn { width: 100%; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
    .btn-primary { background: #2563eb; color: white; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-primary:disabled { background: #374151; color: #6b7280; cursor: not-allowed; }
    .status { margin-top: 12px; padding: 8px; border-radius: 6px; font-size: 12px; }
    .status-success { background: #064e3b; color: #6ee7b7; }
    .status-error { background: #450a0a; color: #fca5a5; }
    .status-loading { background: #1e1b4b; color: #a5b4fc; }
    .title { font-size: 16px; font-weight: bold; margin-bottom: 4px; }
    .subtitle { color: #6b7280; font-size: 12px; margin-bottom: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 8px; text-align: center; }
    .stat-value { font-size: 18px; font-weight: bold; }
    .stat-label { font-size: 10px; color: #6b7280; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <div class="title">OpenRaven</div>
  <div class="subtitle" id="page-title">Save this page to your knowledge base</div>
  <button class="btn btn-primary" id="save-btn">Save to Knowledge Base</button>
  <div id="status-loading" class="status status-loading hidden">Saving page...</div>
  <div id="status-success" class="status status-success hidden">
    Saved successfully!
    <div class="stats">
      <div><div class="stat-value" id="stat-entities" style="color:#60a5fa">0</div><div class="stat-label">Entities</div></div>
      <div><div class="stat-value" id="stat-articles" style="color:#4ade80">0</div><div class="stat-label">Articles</div></div>
      <div><div class="stat-value" id="stat-files" style="color:#c084fc">0</div><div class="stat-label">Files</div></div>
    </div>
  </div>
  <div id="status-error" class="status status-error hidden"><span id="error-message"></span></div>
  <script src="popup.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create popup.ts (safe DOM methods only — no innerHTML)**

Create `openraven-chrome/src/popup.ts`:

```typescript
import { checkConnection } from "./api";

const saveBtn = document.getElementById("save-btn") as HTMLButtonElement;
const pageTitle = document.getElementById("page-title") as HTMLDivElement;
const statusLoading = document.getElementById("status-loading") as HTMLDivElement;
const statusSuccess = document.getElementById("status-success") as HTMLDivElement;
const statusError = document.getElementById("status-error") as HTMLDivElement;
const errorMessage = document.getElementById("error-message") as HTMLSpanElement;
const statEntities = document.getElementById("stat-entities") as HTMLDivElement;
const statArticles = document.getElementById("stat-articles") as HTMLDivElement;
const statFiles = document.getElementById("stat-files") as HTMLDivElement;

function hideAll() {
  statusLoading.classList.add("hidden");
  statusSuccess.classList.add("hidden");
  statusError.classList.add("hidden");
}

function showError(msg: string) {
  hideAll();
  errorMessage.textContent = msg;
  statusError.classList.remove("hidden");
}

function showSuccess(entities: number, articles: number, files: number) {
  hideAll();
  statEntities.textContent = String(entities);
  statArticles.textContent = String(articles);
  statFiles.textContent = String(files);
  statusSuccess.classList.remove("hidden");
}

function showLoading() {
  hideAll();
  statusLoading.classList.remove("hidden");
}

// Show current tab title
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0]?.title) {
    pageTitle.textContent = tabs[0].title;
  }
});

// Check connection on popup open
checkConnection().then((connected) => {
  if (!connected) {
    showError("OpenRaven is not running. Start it with: pm2 start");
    saveBtn.disabled = true;
  }
});

saveBtn.addEventListener("click", async () => {
  saveBtn.disabled = true;
  showLoading();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    showError("No active tab");
    saveBtn.disabled = false;
    return;
  }

  chrome.runtime.sendMessage({ type: "SAVE_PAGE", tabId: tab.id }, (response) => {
    if (response?.success) {
      const r = response.result;
      showSuccess(r.entities_extracted, r.articles_generated, r.files_processed);
    } else {
      showError(response?.error ?? "Unknown error");
      saveBtn.disabled = false;
    }
  });
});
```

- [ ] **Step 3: Build and verify**

```bash
cd openraven-chrome && bun install && bun run package
ls -la dist/
```

- [ ] **Step 4: Commit**

```bash
git add openraven-chrome/src/popup.html openraven-chrome/src/popup.ts
git commit -m "feat(chrome): add popup UI with safe DOM methods"
```

---

## Task 6: CORS for chrome-extension + E2E test

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Update CORS in server.py**

In `server.py`, update the CORS middleware to allow chrome-extension origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: Build extension and test load**

```bash
cd openraven-chrome && bun run package
# Load as unpacked extension in Chrome: chrome://extensions -> Load unpacked -> select dist/
```

- [ ] **Step 3: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven-chrome/
git commit -m "feat(chrome): complete extension with CORS support for chrome-extension origins"
```

---

## Summary

| Task | What | Tests |
|---|---|---|
| 1 | Extension scaffold (manifest, build) | — |
| 2 | Content script (page text extraction) | — |
| 3 | API client (send to OpenRaven) | 2 unit tests |
| 4 | Background service worker | — |
| 5 | Popup UI (safe DOM, no innerHTML) | Build verification |
| 6 | CORS + E2E test | Manual browser test |

**Total new tests: 2**

**Chrome Web Store publishing** is a separate step after the extension is tested. Requires: developer account ($5), privacy policy, screenshots, store listing description. This is not covered in this plan.
