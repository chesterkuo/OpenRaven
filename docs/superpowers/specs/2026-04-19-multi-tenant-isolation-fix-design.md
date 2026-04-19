# 多租戶隔離修復設計規格
## Multi-Tenant Isolation Fix — FastAPI Dependency Injection

**日期**：2026-04-19
**狀態**：已確認
**方案**：方案 D — FastAPI Depends 依賴注入

---

## 一、問題陳述

多租戶審計發現 6 個跨租戶資料洩漏風險：

| 問題 | 風險 | 位置 |
|------|------|------|
| Ingest 端點用全域 config/pipeline | HIGH | server.py:336 |
| 4 個 Connector sync 端點用全域 config | HIGH | server.py:560-661 |
| Graph export 缺少 request 參數 | HIGH | server.py:379 |
| Wiki export 缺少 request 參數 | HIGH | server.py:427 |
| `get_recent_messages()` 無 tenant_id 過濾 | MEDIUM | conversations/models.py:164 |
| Agent 端點用全域 agents_dir | MEDIUM | server.py:678-742 |

根本原因：部分端點直接存取全域 `config` 和 `pipeline` 變數，繞過了 tenant-scoping 機制。

---

## 二、設計方案

### 核心概念

用 FastAPI 的 `Depends()` 依賴注入取代手動呼叫 `resolve_config/resolve_pipeline`：

1. 定義兩個 dependency functions：`get_tenant_config()` 和 `get_tenant_pipeline()`
2. 所有需要 config/pipeline 的端點透過 `Depends()` 宣告依賴
3. 刪除舊的 `resolve_config()` 和 `resolve_pipeline()` 函數
4. 端點不再直接存取全域 `config` 和 `pipeline`

### 優勢

- **不可能忘記 tenant scoping** — 不宣告 Depends 就拿不到 config
- **Per-request 自動 cache** — FastAPI 自動 cache Depends 結果，同一 request 多次使用只執行一次 validate_session
- **延遲初始化** — 只需要 config 的端點不觸發 pipeline 初始化
- **測試可模擬** — `app.dependency_overrides` 可替換 dependency
- **型別安全** — IDE 自動完成

---

## 三、Dependency Functions 定義

在 `create_app()` 內定義，取代現有 `resolve_config` 和 `resolve_pipeline`：

```python
from openraven.auth.tenant import (
    get_tenant_config as _get_tenant_config,
    get_tenant_pipeline as _get_tenant_pipeline,
)

async def get_tenant_config(request: Request) -> RavenConfig:
    if config.auth_enabled and auth_engine:
        session_id = request.cookies.get("session_id")
        if session_id:
            ctx = validate_session(auth_engine, session_id)
            if ctx:
                return _get_tenant_config(
                    config, ctx.tenant_id,
                    tenants_root=Path(config.working_dir).parent,
                    demo_theme=ctx.demo_theme,
                )
    return config

async def get_tenant_pipeline(request: Request) -> RavenPipeline:
    if config.auth_enabled and auth_engine:
        session_id = request.cookies.get("session_id")
        if session_id:
            ctx = validate_session(auth_engine, session_id)
            if ctx:
                return _get_tenant_pipeline(
                    config, ctx.tenant_id,
                    tenants_root=Path(config.working_dir).parent,
                    demo_theme=ctx.demo_theme,
                )
    return pipeline
```

---

## 四、端點改動清單

### 4.1 需要 config + pipeline（類別 1）

| 端點 | 行號 | Depends |
|------|------|---------|
| `POST /api/ingest` | 336 | `cfg + pipe` |
| `POST /api/connectors/gdrive/sync` | 560 | `cfg + pipe` |
| `POST /api/connectors/gmail/sync` | 583 | `cfg + pipe` |
| `POST /api/connectors/meet/sync` | 606 | `cfg + pipe` |
| `POST /api/connectors/otter/sync` | 641 | `cfg + pipe` |

每個端點：
- 加 `cfg: RavenConfig = Depends(get_tenant_config)` 和 `pipe: RavenPipeline = Depends(get_tenant_pipeline)`
- `config.ingestion_dir` → `cfg.ingestion_dir`
- `pipeline.add_files()` → `pipe.add_files()`

### 4.2 只需要 pipeline（類別 2）

| 端點 | 行號 | Depends |
|------|------|---------|
| `POST /api/ask` | 246 | `pipe` |
| `GET /api/status` | 240 | `pipe` |
| `GET /api/graph` | 394 | `pipe` |
| `GET /api/graph/subgraph` | 402 | `pipe` |
| `GET /api/graph/node/{id}/context` | 417 | `pipe` |
| `GET /api/graph/export` | 379 | `pipe` |
| `GET /api/discovery` | 663 | `pipe` |

每個端點：
- 加 `pipe: RavenPipeline = Depends(get_tenant_pipeline)`
- `pipeline.*` → `pipe.*`
- `resolve_pipeline(request)` → 刪除（改用 Depends）

### 4.3 只需要 config（類別 3）

| 端點 | 行號 | Depends |
|------|------|---------|
| `GET /api/wiki` | 445 | `cfg` |
| `GET /api/wiki/{slug}` | 464 | `cfg` |
| `GET /api/wiki/export` | 427 | `cfg` |
| `GET /api/connectors/status` | 512 | `cfg` |
| `GET /api/connectors/google/auth-url` | 524 | `cfg` |
| `GET /api/connectors/google/callback` | 536 | `cfg` |
| `POST /api/connectors/otter/save-key` | 631 | `cfg` |

每個端點：
- 加 `cfg: RavenConfig = Depends(get_tenant_config)`
- `config.wiki_dir` → `cfg.wiki_dir`
- `config.google_token_path` → `cfg.google_token_path`
- `resolve_config(request)` → 刪除（改用 Depends）

### 4.4 Agent 端點（類別 4）

| 端點 | 行號 | Depends |
|------|------|---------|
| `POST /api/agents` | 684 | `cfg` |
| `GET /api/agents` | 707 | `cfg` |
| `GET /api/agents/{id}` | 718 | `cfg` |
| `DELETE /api/agents/{id}` | 735 | `cfg` |
| `POST /api/agents/{id}/tokens` | 743 | `cfg` |
| `DELETE /api/agents/{id}/tokens/{last4}` | 756+ | `cfg` |
| `POST /api/agents/{id}/toggle` | 770+ | `cfg` |

每個端點：
- 加 `cfg: RavenConfig = Depends(get_tenant_config)`
- `agents_dir` → `cfg.working_dir / "agents"`
- `config.working_dir` → `cfg.working_dir`
- 刪除全域 `agents_dir = config.working_dir / "agents"` (line 678)

---

## 五、Conversation 函數修改

### 5.1 `get_recent_messages()` 加 tenant_id 過濾

檔案：`openraven/src/openraven/conversations/models.py:164`

```python
# 現在
def get_recent_messages(engine, conversation_id, limit=20):
    rows = conn.execute(
        select(messages)
        .where(messages.c.conversation_id == conversation_id)
        ...
    )

# 改為
def get_recent_messages(engine, conversation_id, tenant_id, limit=20):
    rows = conn.execute(
        select(messages)
        .join(conversations, messages.c.conversation_id == conversations.c.id)
        .where(messages.c.conversation_id == conversation_id)
        .where(conversations.c.tenant_id == tenant_id)
        ...
    )
```

### 5.2 呼叫端修改

`server.py` 中呼叫 `get_recent_messages()` 的地方需要傳入 `tenant_id`（從 auth context 取得）。

---

## 六、刪除項目

改完後刪除：
- `resolve_config()` 函數定義 (server.py:198-208)
- `resolve_pipeline()` 函數定義 (server.py:210-220)
- `agents_dir = config.working_dir / "agents"` (server.py:678)
- `agents_dir.mkdir(...)` (server.py:679)

---

## 七、不在範圍內

- 前端 UI 改動（不涉及）
- 資料庫 schema 改動（不涉及）
- BFF 改動（不涉及，BFF 只轉發 cookie）
- 新增端點（不涉及）
- test_api.py 的 401 問題（pre-existing，不在本次修復範圍）

---

## 八、檔案改動清單

| 檔案 | 動作 |
|------|------|
| `openraven/src/openraven/api/server.py` | 修改：定義 dependency functions，改所有端點簽名，刪除 resolve_* |
| `openraven/src/openraven/conversations/models.py` | 修改：`get_recent_messages` 加 tenant_id |
| `openraven/src/openraven/conversations/routes.py` | 修改：`get_recent_messages` 呼叫加 tenant_id |
| `openraven/tests/test_graph.py` | 修改：如有需要調整 |
| `openraven/tests/test_conversations.py` | 修改：更新 `get_recent_messages` 呼叫 |

---

## 九、測試策略

- 現有 24 graph tests 應全部通過（dependency functions fallback 到全域 config/pipeline）
- 現有 conversation tests 需要更新 `get_recent_messages` 呼叫簽名
- 新增測試：驗證 tenant_id 過濾在 `get_recent_messages` 中正確工作
- E2E 驗證：demo sandbox 功能不受影響（dependency functions 正確處理 demo sessions）
