# OpenRaven

**AI 驱动的知识资产平台，能自动从您的文档中提取、整理并激活专业知识。**

**阅读其他语言版本：**
[English](../README.md) | [繁體中文](README.zh-TW.md) | **简体中文** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Español](README.es.md) | [Nederlands](README.nl.md) | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven 将散落各处的文档——PDF、DOCX、演示文稿、会议记录、Notion 导出文件——转化为结构化、可查询的知识图谱。用自然语言提问、探索概念间的关联、自动生成百科文章，并从您的知识库建立课程。

## 为什么选择 OpenRaven？

当人才转换职位或离开组织时，机构知识便会随之流失。研究显示，42% 的机构知识仅存在于人们的脑海中（IDC）。OpenRaven 能捕捉并结构化这些知识，让它们随时可访问、可搜索、可共享。

## 功能特色

### 知识引擎
- **智能摄取** — 上传 PDF、DOCX、PPTX、XLSX、Markdown、图片（AI 视觉识别），或 Notion/Obsidian 导出文件。实体与关联将自动被提取。
- **知识图谱** — 交互式力导向图谱可视化，支持按实体类型、连接强度及搜索关键字筛选。可导出为 GraphML 或 PNG。
- **自然语言问答** — 使用 6 种查询模式（mix、local、global、hybrid、keyword、direct LLM）对知识库提问。回答包含来源引用。
- **自动生成百科** — 从提取的实体与关联自动生成文章。
- **课程生成** — 利用知识库建立结构化课程，包含课程规划、章节生成及交互式 HTML 导出。
- **发现洞察** — 自动分析知识主题、集群、缺口与趋势。

### 连接器
- **Google Drive** — 导入文档（PDF、Docs、Sheets、Slides）
- **Gmail** — 将电子邮件导入为知识库条目
- **Google Meet** — 通过 Drive API 导入会议记录
- **Otter.ai** — 通过 API 密钥导入会议记录

### 垂直领域 Schema
- **Base** — 通用实体提取（默认）
- **Engineering** — 技术架构、系统、API
- **Finance** — 公司、财务指标、法规
- **Legal (Taiwan)** — 法规条文、法院判决、法律原则（繁体中文）
- **Finance (Taiwan)** — 上市公司、财务指标（繁体中文）

### 多语言支持

OpenRaven 支持 12 种语言，并提供自动浏览器检测与手动切换：

| 语言 | 代码 | 语言 | 代码 |
|------|------|------|------|
| 英语 | `en` | 意大利语 | `it` |
| 繁体中文 | `zh-TW` | 越南语 | `vi` |
| 简体中文 | `zh-CN` | 泰语 | `th` |
| 日语 | `ja` | 俄语 | `ru` |
| 韩语 | `ko` | 法语 | `fr` |
| 西班牙语 | `es` | 荷兰语 | `nl` |

**运作方式：**
- 首次访问时自动检测浏览器／操作系统语言（备用语言：英语）
- 用户可通过导航栏中的语言选择器切换
- 偏好设置保存至 localStorage（即时生效）及用户个人资料（跨设备同步）
- LLM 回复会匹配用户选择的语言
- 百科文章与课程内容遵循来源文档语言
- 知识图谱标签保持英语

### 企业功能（托管 SaaS）
- **多租户隔离** — 每个租户拥有独立知识库与存储空间
- **身份验证** — 电子邮件／密码 + Google OAuth 2.0，含 Session 管理
- **审计日志** — 追踪所有用户操作，支持 CSV 导出
- **团队管理** — 邀请成员加入您的工作区
- **Neo4j 图形后端** — 生产级别的图形存储（可选，默认：NetworkX）
- **Docker Compose 部署** — 一键部署，包含 nginx、PostgreSQL、Neo4j

## 架构

```
openraven/                  # Python 后端（FastAPI + LightRAG + LangExtract）
  src/openraven/
    api/server.py           # FastAPI 应用程序工厂，所有 API 端点
    pipeline.py             # 核心管线：摄取、查询、图谱、百科、课程
    graph/rag.py            # LightRAG 封装，支持语言感知查询
    auth/                   # 身份验证系统（Sessions、OAuth、密码重置）
    audit/                  # 审计日志模块
  alembic/                  # 数据库迁移
  tests/                    # 159+ 个 Python 测试

openraven-ui/               # TypeScript 前端（React 19 + Vite 6 + Tailwind 4）
  src/
    i18n.ts                 # i18next 初始化（12 个语言，11 个命名空间）
    App.tsx                 # 根组件，包含路由 + 导航栏
    pages/                  # 14 个页面组件
    components/             # LanguageSelector、GraphViewer、ChatMessage 等
    hooks/useAuth.tsx       # 含语言同步的身份验证 Context
  public/locales/           # 132 个翻译 JSON 文件（12 个语言 x 11 个命名空间）
  server/index.ts           # Hono BFF（API 代理 + 静态文件服务）
  tests/                    # 46 个 Bun 测试

ecosystem.config.cjs        # PM2 部署配置
```

## 快速开始

### 前置条件
- Python 3.12+
- Bun 1.0+
- Node.js 20+（用于 PM2）

### 1. 克隆并安装

```bash
git clone https://github.com/nickhealthy/OpenRaven.git
cd OpenRaven

# 后端
cd openraven
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 前端
cd ../openraven-ui
bun install
```

### 2. 配置环境

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # 必填：LLM 提供者
WORKING_DIR=/path/to/knowledge-data     # 知识库数据存储位置

# 可选：启用托管 SaaS 功能
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. 使用 PM2 运行

```bash
# 从项目根目录运行
pm2 start ecosystem.config.cjs

# 查看状态
pm2 status

# 查看日志
pm2 logs
```

服务：
- **openraven-core**（端口 8741）— Python API 服务器
- **openraven-ui**（端口 3002）— BFF + 前端

### 4. 构建前端生产版本

```bash
cd openraven-ui
bun run build          # 构建至 dist/
pm2 restart openraven-ui
```

在浏览器中打开 http://localhost:3002。

### 替代方案：Docker Compose

```bash
docker compose up -d
```

此命令将启动 nginx（端口 80）、PostgreSQL、Neo4j、API 服务器及 UI 服务器。

## 开发

### 运行测试

```bash
# 后端
cd openraven && python3 -m pytest tests/ -v

# 前端
cd openraven-ui && bun test tests/

# 性能基准测试（需要 GEMINI_API_KEY）
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### 添加翻译

翻译文件位于 `openraven-ui/public/locales/{locale}/{namespace}.json`。

添加或更新翻译：
1. 编辑目标语言的 JSON 文件
2. 保持键值与英语来源文件相同
3. 保留 `{{interpolation}}` 占位符
4. 运行 `bun run build` 并重启 PM2

添加新语言：
1. 在 `public/locales/` 下创建新目录（例如 `de/`）
2. 复制 `en/` 中的所有 JSON 文件并翻译值
3. 在 `src/i18n.ts` 的 `SUPPORTED_LNGS` 中添加语言代码
4. 在 `src/components/LanguageSelector.tsx` 的 `LOCALES` 数组中添加语言
5. 在 `openraven/src/openraven/auth/routes.py` 的 `SUPPORTED_LOCALES` 中添加语言
6. 在 `openraven/src/openraven/graph/rag.py` 的 `LOCALE_NAMES` 中添加语言名称

## API 概览

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/ask` | 查询知识库（支持 locale 参数） |
| `POST` | `/api/ingest` | 上传并处理文档 |
| `GET` | `/api/graph` | 获取知识图谱数据 |
| `GET` | `/api/wiki` | 列出百科文章 |
| `GET` | `/api/status` | 知识库统计信息 |
| `GET` | `/api/discovery` | 自动生成洞察 |
| `POST` | `/api/courses/generate` | 生成课程 |
| `GET` | `/api/connectors/status` | 连接器状态 |
| `PATCH` | `/api/auth/locale` | 更新用户语言偏好 |
| `GET` | `/api/audit` | 审计日志（分页） |

完整 API 文档请见 http://localhost:8741/docs（FastAPI 自动生成）。

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM | Gemini（默认）、Ollama（本地） |
| 知识图谱 | LightRAG + NetworkX（本地）/ Neo4j（生产） |
| 实体提取 | LangExtract |
| 后端 | FastAPI + Uvicorn（Python 3.12） |
| 前端 | React 19 + Vite 6 + Tailwind CSS 4 |
| 国际化 | react-i18next + i18next-browser-languagedetector |
| BFF | Hono（Bun 运行时） |
| 数据库 | SQLite（本地）/ PostgreSQL（生产） |
| 身份验证 | Session 型 + Google OAuth 2.0 |
| 部署 | PM2 / Docker Compose |
| 设计系统 | Mistral Premium（暖象牙色、橙色点缀、金色阴影） |

## 验证结果

- **问答准确率**：96.7%（30 题第一级中答对 29 题）
- **引用准确率**：100%（30/30 来源引用）
- **LLM 评审分数**：平均 4.6/5.0（第二级）
- **测试覆盖率**：Python 与 TypeScript 共 260+ 个测试

## 许可证

Apache License 2.0——详见 [LICENSE](LICENSE)。

Copyright 2026 Plusblocks Technology Limited.

## 关于

由 [Plusblocks Technology Limited](https://plusblocks.com) 开发。OpenRaven 的核心引擎为开源。云端与企业功能（多租户、SSO、计费）以托管服务形式提供。
