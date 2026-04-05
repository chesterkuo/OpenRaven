# OpenRaven

**AI 驅動的知識資產平台，能自動從您的文件中擷取、整理並激活專業知識。**

**閱讀其他語言版本：**
[English](../README.md) | **繁體中文** | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Español](README.es.md) | [Nederlands](README.nl.md) | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven 將散落各處的文件——PDF、DOCX、簡報、會議逐字稿、Notion 匯出檔——轉化為結構化、可查詢的知識圖譜。用自然語言提問、探索概念間的關聯、自動生成維基文章，並從您的知識庫建立課程。

## 為什麼選擇 OpenRaven？

當人才轉換職位或離開組織時，機構知識便會隨之流失。研究顯示，42% 的機構知識僅存在於人們的腦海中（IDC）。OpenRaven 能捕捉並結構化這些知識，讓它們隨時可存取、可搜尋、可分享。

## 功能特色

### 知識引擎
- **智慧擷取** — 上傳 PDF、DOCX、PPTX、XLSX、Markdown、圖片（AI 視覺辨識），或 Notion/Obsidian 匯出檔。實體與關聯將自動被擷取。
- **知識圖譜** — 互動式力導向圖譜視覺化，支援依實體類型、連結強度及搜尋關鍵字篩選。可匯出為 GraphML 或 PNG。
- **自然語言問答** — 使用 6 種查詢模式（mix、local、global、hybrid、keyword、direct LLM）對知識庫提問。回答包含來源引用。
- **自動生成維基** — 從擷取的實體與關聯自動生成文章。
- **課程生成** — 利用知識庫建立結構化課程，包含課程規劃、章節生成及互動式 HTML 匯出。
- **發現洞察** — 自動分析知識主題、群集、缺口與趨勢。

### 連接器
- **Google Drive** — 匯入文件（PDF、Docs、Sheets、Slides）
- **Gmail** — 將電子郵件匯入為知識庫條目
- **Google Meet** — 透過 Drive API 匯入會議逐字稿
- **Otter.ai** — 透過 API 金鑰匯入會議逐字稿

### 垂直領域 Schema
- **Base** — 通用實體擷取（預設）
- **Engineering** — 技術架構、系統、API
- **Finance** — 公司、財務指標、法規
- **Legal (Taiwan)** — 法規條文、法院判決、法律原則（繁體中文）
- **Finance (Taiwan)** — 上市公司、財務指標（繁體中文）

### 多語言支援

OpenRaven 支援 12 種語言，並提供自動瀏覽器偵測與手動切換：

| 語言 | 代碼 | 語言 | 代碼 |
|------|------|------|------|
| 英語 | `en` | 義大利語 | `it` |
| 繁體中文 | `zh-TW` | 越南語 | `vi` |
| 簡體中文 | `zh-CN` | 泰語 | `th` |
| 日語 | `ja` | 俄語 | `ru` |
| 韓語 | `ko` | 法語 | `fr` |
| 西班牙語 | `es` | 荷蘭語 | `nl` |

**運作方式：**
- 首次訪問時自動偵測瀏覽器／作業系統語言（備用語言：英語）
- 使用者可透過導覽列中的語言選擇器切換
- 偏好設定儲存至 localStorage（即時生效）及使用者個人檔案（跨裝置同步）
- LLM 回應會配合使用者選擇的語言
- 維基文章與課程內容遵循來源文件語言
- 知識圖譜標籤保持英語

### 企業功能（託管 SaaS）
- **多租戶隔離** — 每個租戶擁有獨立知識庫與儲存空間
- **身份驗證** — 電子郵件／密碼 + Google OAuth 2.0，含 Session 管理
- **稽核日誌** — 追蹤所有使用者操作，支援 CSV 匯出
- **團隊管理** — 邀請成員加入您的工作區
- **Neo4j 圖形後端** — 生產等級的圖形儲存（選用，預設：NetworkX）
- **Docker Compose 部署** — 一鍵部署，包含 nginx、PostgreSQL、Neo4j

## 架構

```
openraven/                  # Python 後端（FastAPI + LightRAG + LangExtract）
  src/openraven/
    api/server.py           # FastAPI 應用程式工廠，所有 API 端點
    pipeline.py             # 核心管線：擷取、查詢、圖譜、維基、課程
    graph/rag.py            # LightRAG 封裝，支援語言感知查詢
    auth/                   # 身份驗證系統（Sessions、OAuth、密碼重設）
    audit/                  # 稽核日誌模組
  alembic/                  # 資料庫遷移
  tests/                    # 159+ 個 Python 測試

openraven-ui/               # TypeScript 前端（React 19 + Vite 6 + Tailwind 4）
  src/
    i18n.ts                 # i18next 初始化（12 個語言，11 個命名空間）
    App.tsx                 # 根元件，包含路由 + 導覽列
    pages/                  # 14 個頁面元件
    components/             # LanguageSelector、GraphViewer、ChatMessage 等
    hooks/useAuth.tsx       # 含語言同步的身份驗證 Context
  public/locales/           # 132 個翻譯 JSON 檔案（12 個語言 x 11 個命名空間）
  server/index.ts           # Hono BFF（API 代理 + 靜態檔案服務）
  tests/                    # 46 個 Bun 測試

ecosystem.config.cjs        # PM2 部署設定
```

## 快速開始

### 前置需求
- Python 3.12+
- Bun 1.0+
- Node.js 20+（用於 PM2）

### 1. 複製並安裝

```bash
git clone https://github.com/nickhealthy/OpenRaven.git
cd OpenRaven

# 後端
cd openraven
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 前端
cd ../openraven-ui
bun install
```

### 2. 設定環境

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # 必填：LLM 提供者
WORKING_DIR=/path/to/knowledge-data     # 知識庫資料儲存位置

# 選用：啟用託管 SaaS 功能
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. 使用 PM2 執行

```bash
# 從專案根目錄執行
pm2 start ecosystem.config.cjs

# 查看狀態
pm2 status

# 查看日誌
pm2 logs
```

服務：
- **openraven-core**（連接埠 8741）— Python API 伺服器
- **openraven-ui**（連接埠 3002）— BFF + 前端

### 4. 建置前端生產版本

```bash
cd openraven-ui
bun run build          # 建置至 dist/
pm2 restart openraven-ui
```

在瀏覽器中開啟 http://localhost:3002。

### 替代方案：Docker Compose

```bash
docker compose up -d
```

此命令將啟動 nginx（連接埠 80）、PostgreSQL、Neo4j、API 伺服器及 UI 伺服器。

## 開發

### 執行測試

```bash
# 後端
cd openraven && python3 -m pytest tests/ -v

# 前端
cd openraven-ui && bun test tests/

# 效能基準測試（需要 GEMINI_API_KEY）
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### 新增翻譯

翻譯檔案位於 `openraven-ui/public/locales/{locale}/{namespace}.json`。

新增或更新翻譯：
1. 編輯目標語言的 JSON 檔案
2. 保持鍵值與英語來源檔案相同
3. 保留 `{{interpolation}}` 佔位符
4. 執行 `bun run build` 並重啟 PM2

新增語言：
1. 在 `public/locales/` 下建立新目錄（例如 `de/`）
2. 複製 `en/` 中的所有 JSON 檔案並翻譯值
3. 在 `src/i18n.ts` 的 `SUPPORTED_LNGS` 中新增語言代碼
4. 在 `src/components/LanguageSelector.tsx` 的 `LOCALES` 陣列中新增語言
5. 在 `openraven/src/openraven/auth/routes.py` 的 `SUPPORTED_LOCALES` 中新增語言
6. 在 `openraven/src/openraven/graph/rag.py` 的 `LOCALE_NAMES` 中新增語言名稱

## API 概覽

| 方法 | 端點 | 說明 |
|------|------|------|
| `POST` | `/api/ask` | 查詢知識庫（支援 locale 參數） |
| `POST` | `/api/ingest` | 上傳並處理文件 |
| `GET` | `/api/graph` | 取得知識圖譜資料 |
| `GET` | `/api/wiki` | 列出維基文章 |
| `GET` | `/api/status` | 知識庫統計資訊 |
| `GET` | `/api/discovery` | 自動生成洞察 |
| `POST` | `/api/courses/generate` | 生成課程 |
| `GET` | `/api/connectors/status` | 連接器狀態 |
| `PATCH` | `/api/auth/locale` | 更新使用者語言偏好 |
| `GET` | `/api/audit` | 稽核日誌（分頁） |

完整 API 文件請見 http://localhost:8741/docs（FastAPI 自動生成）。

## 技術堆疊

| 層級 | 技術 |
|------|------|
| LLM | Gemini（預設）、Ollama（本地） |
| 知識圖譜 | LightRAG + NetworkX（本地）/ Neo4j（生產） |
| 實體擷取 | LangExtract |
| 後端 | FastAPI + Uvicorn（Python 3.12） |
| 前端 | React 19 + Vite 6 + Tailwind CSS 4 |
| 國際化 | react-i18next + i18next-browser-languagedetector |
| BFF | Hono（Bun 執行環境） |
| 資料庫 | SQLite（本地）/ PostgreSQL（生產） |
| 身份驗證 | Session 型 + Google OAuth 2.0 |
| 部署 | PM2 / Docker Compose |
| 設計系統 | Mistral Premium（暖象牙色、橙色點綴、金色陰影） |

## 驗證結果

- **問答準確率**：96.7%（30 題第一級中答對 29 題）
- **引用準確率**：100%（30/30 來源引用）
- **LLM 評審分數**：平均 4.6/5.0（第二級）
- **測試覆蓋率**：Python 與 TypeScript 共 260+ 個測試

## 授權條款

Apache License 2.0——詳見 [LICENSE](LICENSE)。

Copyright 2026 Plusblocks Technology Limited.

## 關於

由 [Plusblocks Technology Limited](https://plusblocks.com) 開發。OpenRaven 的核心引擎為開源。雲端與企業功能（多租戶、SSO、計費）以託管服務形式提供。
