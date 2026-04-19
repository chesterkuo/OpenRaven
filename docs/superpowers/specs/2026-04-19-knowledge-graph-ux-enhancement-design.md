# 知識圖譜 UX 增強設計規格
## Knowledge Graph UX Enhancement — Embedded MiniGraph + Full Graph Upgrade

**日期**：2026-04-19
**狀態**：已確認
**目標用戶**：律師、法務人員、合規專員
**方案**：方案 C — 嵌入式 MiniGraph + 完整圖譜升級

---

## 一、問題陳述

### 1.1 現況

知識圖譜頁面目前提供：
- d3-force 力導向互動式圖譜（GraphViewer.tsx, 437 行）
- 6 種硬編碼的英文 entity type 篩選器（technology、concept、person、organization、event、location）
- 搜尋欄、最小連結數滑桿
- 點擊節點顯示 detail panel（描述、來源檔案、相鄰節點列表）
- 匯出 GraphML / PNG

### 1.2 痛點

| 痛點 | 說明 | 影響 |
|------|------|------|
| 看不懂節點是什麼 | Entity type 篩選器不對應法律領域實際類型 | 高 |
| 沒有原文可查 | 律師不信任 AI 摘要，需要法條/判決原始文字 | 高 |
| 不知道從哪開始 | 500 個節點一次全顯示，沒有引導 | 高 |
| 圖譜與問答斷裂 | Ask 回答引用了法條，無法跳到圖譜看關聯 | 高 |
| 跨文件引用不完整 | 同一實體出現在多份文件中，只顯示一個來源 | 中 |
| 關係類型模糊 | 邊的關係只有自由文字描述，沒有結構化標籤 | 中 |

---

## 二、律師使用場景

### 場景 A：案件研究

律師問「個資法要求企業在資料外洩時必須做哪些事？」，回答引用了個資法第 12 條、第 27 條、臺灣高等法院判決。律師想看這些法條和判決之間的關聯網路，不離開問答頁面就能看到 MiniGraph，點擊後跳到完整圖譜深入探索。

### 場景 B：合約審查

律師審查顧問合約中的 IP 歸屬條款，問答提到著作權法第 11 條和第 12 條。MiniGraph 顯示這兩條法條分別連結到哪些概念和案例，幫助律師發現遺漏的風險。

### 場景 C：法規合規盤點

法務主管打開完整圖譜頁面，用動態篩選器篩選「法條」類型，看到知識庫中所有法條及其關聯的合規要求，匯出圖譜作為報告素材。

---

## 三、整體架構

```
┌─────────────────────────────────────────────────┐
│                    後端 (Python)                  │
│                                                   │
│  ① GET /api/graph/node/:id/context                │
│     → 從原始 .md 檔搜尋實體所在段落               │
│     → 回傳：原文摘錄、所有出現的文件列表           │
│                                                   │
│  ② GET /api/graph/subgraph                        │
│     → 指定 files 或 entities                      │
│     → 回傳 seed 實體 + 1-hop 鄰居子圖             │
│                                                   │
├─────────────────────────────────────────────────┤
│                   前端 (React)                     │
│                                                   │
│  ③ GraphViewer 元件擴充                           │
│     → 新增 mode="mini"|"full" prop               │
│     → 新增 focusNodeId prop（平移+高亮動畫）      │
│                                                   │
│  ④ MiniGraph.tsx（新元件）                        │
│     → 封裝子圖 fetch + GraphViewer mini 模式       │
│     → 浮動卡片 + 跳轉完整圖譜                     │
│                                                   │
│  ⑤ AskPage 嵌入 MiniGraph                        │
│     → 回答的來源區下方，可展開/收合               │
│                                                   │
│  ⑥ GraphPage 完整升級                            │
│     → 動態 entity type 篩選器 + 中文標籤          │
│     → 引導摘要列                                  │
│     → URL ?highlight= 支援                       │
│     → GraphNodeDetail 升級                        │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## 四、新增 API 設計

### 4.1 GET /api/graph/node/:id/context

從原始 .md 檔中搜尋包含實體名稱的段落，回傳原文摘錄。

**實作方式**：掃描 `working_dir/ingested/` 或 demo 目錄下的 .md 原始檔，用實體 ID（名稱）做文字搜尋，取包含該名稱的前後段落。

**Request**：
```
GET /api/graph/node/個資法第27條/context
```

**Response**：
```json
{
  "node_id": "個資法第27條",
  "excerpts": [
    {
      "file": "pdpa-個資法.md",
      "text": "依個資法第 27 條及施行細則第 12 條，企業應建立：\n1. 個資盤點：清查持有之個人資料類別與數量\n2. 存取控制：實施最小權限原則...",
      "line_start": 45,
      "line_end": 52
    },
    {
      "file": "compliance-合規檢查.md",
      "text": "完成個人資料盤點（個資法第 27 條）...",
      "line_start": 12,
      "line_end": 15
    }
  ],
  "files": ["pdpa-個資法.md", "compliance-合規檢查.md"]
}
```

**搜尋規則**：
- 搜尋欄位：實體 ID（名稱）
- 摘錄範圍：匹配行的前後各 3 行
- 每份文件最多回傳 1 段摘錄
- 每段摘錄最多 500 字
- 搜尋範圍：`config.working_dir` 下的所有 .md 檔案（含 ingested/ 子目錄和原始放置位置）

### 4.2 GET /api/graph/subgraph

回傳以指定文件或實體為中心的子圖，供 MiniGraph 使用。

**Request**：
```
GET /api/graph/subgraph?files=pdpa-個資法.md,compliance-合規檢查.md&max_nodes=30
```

或：
```
GET /api/graph/subgraph?entities=個資法第27條,個資法第12條&max_nodes=30
```

**Response**：
```json
{
  "nodes": [
    {
      "id": "個資法第27條",
      "labels": ["content"],
      "properties": { "entity_type": "content", "description": "...", "file_path": "..." },
      "is_seed": true
    },
    {
      "id": "個人資料盤點",
      "labels": ["concept"],
      "properties": { "entity_type": "concept", "description": "..." },
      "is_seed": false
    }
  ],
  "edges": [
    {
      "source": "個資法第27條",
      "target": "個人資料盤點",
      "properties": { "description": "...", "keywords": "requirement" }
    }
  ]
}
```

**實作方式**：
- 在 `graph/rag.py` 的 GraphML 讀取邏輯基礎上新增 `get_subgraph()` 方法
- `files` 模式：找出 `file_path` 含指定檔名的所有節點作為 seed
- `entities` 模式：直接以指定 entity ID 作為 seed
- BFS 取 1-hop 鄰居
- `is_seed` 標記讓前端區分：seed 節點用強調色，鄰居節點用淡色
- `max_nodes` 預設 30，超過時優先保留 seed 節點及連結數最多的鄰居

---

## 五、MiniGraph 元件設計

### 5.1 元件介面

```typescript
interface MiniGraphProps {
  sourceFiles: string[];     // 從 Ask 回答的 sources 提取的檔名列表
  height?: number;           // 預設 280
  onNavigate?: (nodeId: string) => void;  // 點擊「在圖譜中查看」callback
}
```

### 5.2 內部流程

```
1. 接收 sourceFiles（從 Ask 回答的 sources 中提取 document 欄位）
2. fetch GET /api/graph/subgraph?files=A.md,B.md&max_nodes=30
3. 收到子圖資料（nodes + edges）
4. 如果子圖為空（< 2 nodes），不渲染
5. 渲染 GraphViewer mode="mini"
6. 點擊節點 → 顯示浮動卡片（名稱 + entity type 中文標籤 + 描述前 100 字）
7. 卡片內「在圖譜中查看」→ 觸發 onNavigate → 路由跳轉 /graph?highlight=<nodeId>
```

### 5.3 在 AskPage 中的位置

```
┌─ Ask 頁面 ────────────────────────────────┐
│                                            │
│  [AI 回答內容]                              │
│                                            │
│  來源 (16 筆):                              │
│  │ pdpa-個資法.md — 第 27 條規定...          │
│  │ compliance-合規檢查.md — 安全維護...      │
│                                            │
│  [▼ 關聯圖譜]  ← 展開/收合按鈕             │
│  ┌──────────────────────────────┐          │
│  │       MiniGraph (280px)      │          │
│  │                              │          │
│  │  ● seed節點（強調色）         │          │
│  │  ○ 鄰居節點（淡色）          │          │
│  │                              │          │
│  │  點擊節點 → 浮動卡片          │          │
│  │  [🔗 在完整圖譜中查看]        │          │
│  └──────────────────────────────┘          │
│                                            │
└────────────────────────────────────────────┘
```

**行為規則**：
- 回答包含 sources 且 sources ≥ 1 筆時，顯示「關聯圖譜」展開按鈕
- 預設收合（不自動展開，避免干擾閱讀）
- 展開時才觸發 subgraph API fetch
- 固定高度 280px
- 無工具列（不顯示搜尋、篩選、匯出）

---

## 六、GraphNodeDetail 升級

### 6.1 面板結構

```
┌─────────────────────────────────┐
│ [中文類型標籤]             [✕]  │
│                                 │
│ 實體名稱（大標題）              │
│                                 │
│ AI 生成描述（現有欄位）         │
│                                 │
│ ── 原文摘錄 ──                  │
│ 從 /api/graph/node/:id/context  │
│ 載入的原始文件段落              │
│             [📄 查看完整文件]   │
│                                 │
│ ── 出現在 N 份文件 ──           │
│ 📄 file-a.md                    │
│ 📄 file-b.md                    │
│                                 │
│ ── 關聯 (N) ──                  │
│ 關係標籤→ 鄰居名稱      [→]    │
│ 關係標籤← 鄰居名稱      [→]    │
│                                 │
│ [🔍 問 OpenRaven]  [📖 看Wiki]  │
└─────────────────────────────────┘
```

### 6.2 各區塊資料來源

| 區塊 | 來源 | 說明 |
|------|------|------|
| 中文類型標籤 | `properties.entity_type` + 對照表 | 如 concept→概念、statute→法條 |
| 描述 | `properties.description` | 取 `<SEP>` 前第一段 |
| 原文摘錄 | `GET /api/graph/node/:id/context` | 點擊節點時 async fetch，loading 時顯示 skeleton |
| 多文件出處 | `properties.file_path` | 解析 `<SEP>` 分隔的多路徑，顯示檔名部分 |
| 關聯列表 | 現有 edges 資料 | 從 edge keywords/description 提取簡短關係動詞 |
| 問 OpenRaven | 前端路由跳轉 | `/ask?q=請說明「{nodeId}」的相關規定`（demo 模式用 `/demo/ask`） |
| 看 Wiki | 前端路由跳轉 | 用 nodeId 模糊匹配 wiki slug，存在則顯示按鈕 |

### 6.3 關係動詞提取

從 edge 的 `keywords` 欄位提取簡短標籤：

```typescript
function extractRelationLabel(keywords: string, description: string): string {
  const LABEL_MAP: Record<string, string> = {
    "requirement": "要求",
    "legal basis": "依據",
    "governed by": "規範",
    "issued by": "作出",
    "covers": "承保",
    "component": "包含",
    "type of": "屬於",
    "party": "當事人",
    "court ruling": "判決",
  };
  for (const [key, label] of Object.entries(LABEL_MAP)) {
    if (keywords.includes(key)) return label;
  }
  return "關聯";  // fallback
}
```

---

## 七、GraphPage 升級

### 7.1 動態 Entity Type 篩選器

```typescript
const TYPE_LABELS: Record<string, string> = {
  concept: "概念",
  content: "內容",
  organization: "組織",
  person: "人物",
  method: "方法",
  data: "數據",
  event: "判決/事件",
  statute: "法條",
  artifact: "文件",
  location: "地點",
  technology: "技術",
};
```

- 從 API 回傳節點動態統計所有 entity_type
- 按數量降序排列
- 各按鈕顯示數量 badge
- 中文標籤跟隨使用者 locale（中文用對照表，其他語言用英文原名或各語言翻譯）
- 預設全部啟用

### 7.2 引導摘要列

圖譜上方新增一行統計文字：

```
📊 此知識庫包含 {nodes} 個實體、{edges} 條關聯。點擊節點查看詳情與原文，或使用篩選器聚焦特定類型。
```

- 走 i18n `graph.guideSummary` key
- 12 語言需翻譯

### 7.3 URL 參數高亮

支援 `?highlight=<nodeId>`：

1. GraphPage 讀取 URL searchParams `highlight`
2. 在載入完成的 nodes 中搜尋 `id === highlight`（完全匹配），找不到則模糊搜尋（`id.includes(highlight)`）
3. 找到後：
   - 呼叫 `setSelectedNode(matchedNode)` 打開 detail panel
   - 傳遞 `focusNodeId={matchedNode.id}` 給 GraphViewer
   - GraphViewer 接收 focusNodeId 後，平移視圖到該節點位置，該節點以脈動動畫高亮 2 秒
4. 找不到：console.warn，不顯示 UI 錯誤（因為實體名稱可能不完全匹配 graph node id）

---

## 八、GraphViewer 元件擴充

### 8.1 新增 Props

```typescript
interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onNodeClick: (node: GraphNode) => void;
  searchTerm: string;
  // 新增
  mode?: "full" | "mini";       // 預設 "full"
  focusNodeId?: string | null;  // 觸發平移+高亮動畫
}
```

### 8.2 mini 模式差異

| 行為 | full 模式 | mini 模式 |
|------|-----------|-----------|
| 畫布拖拉 | 可拖拉平移 | 禁用 |
| 縮放 | 滾輪縮放 | 禁用 |
| 節點大小 | 正常 | 縮小 70% |
| 字體大小 | 正常 | 縮小至 10px |
| 節點點擊 | 觸發 onNodeClick | 觸發 onNodeClick |
| 力模擬 | 正常 | 加大 center force，讓圖更緊湊 |
| 背景色 | var(--bg-surface) | transparent |

### 8.3 focusNode 動畫

收到新的 `focusNodeId` 時：
1. 計算該節點在 canvas 上的座標
2. 平移 transform 使節點置中
3. 該節點渲染一個 2 秒的放大縮小脈動動畫（用 canvas arc + alpha fade）
4. 動畫結束後恢復正常渲染

---

## 九、i18n 新增 Key

### graph.json 新增

```json
{
  "guideSummary": "此知識庫包含 {{nodes}} 個實體、{{edges}} 條關聯。點擊節點查看詳情與原文，或使用篩選器聚焦特定類型。",
  "expandMiniGraph": "關聯圖譜",
  "viewInGraph": "在圖譜中查看",
  "askAbout": "問 OpenRaven",
  "viewWiki": "查看 Wiki",
  "excerptHeading": "原文摘錄",
  "appearsIn": "出現在 {{count}} 份文件",
  "viewFullDocument": "查看完整文件",
  "relatedCount": "關聯 ({{count}})",
  "loadingContext": "載入原文中...",
  "entityNotFound": "找不到該實體"
}
```

12 語言皆需翻譯。

---

## 十、檔案變更清單

| 檔案 | 動作 | 說明 |
|------|------|------|
| `openraven/src/openraven/graph/rag.py` | 修改 | 新增 `get_subgraph()` 和 `get_node_context()` |
| `openraven/src/openraven/api/server.py` | 修改 | 新增 `GET /api/graph/subgraph` 和 `GET /api/graph/node/:id/context` |
| `openraven-ui/src/components/GraphViewer.tsx` | 修改 | 新增 `mode` 和 `focusNodeId` props |
| `openraven-ui/src/components/MiniGraph.tsx` | **新增** | Ask 頁面嵌入式迷你圖譜元件 |
| `openraven-ui/src/components/GraphNodeDetail.tsx` | 修改 | 原文摘錄、多來源、動作按鈕 |
| `openraven-ui/src/pages/GraphPage.tsx` | 修改 | 動態篩選器、引導列、URL highlight |
| `openraven-ui/src/pages/AskPage.tsx` | 修改 | 嵌入 MiniGraph 展開/收合區塊 |
| `openraven-ui/public/locales/*/graph.json` | 修改 | 新增 i18n key（12 語言） |

---

## 十一、Entity Type 中文對照表

| API entity_type | 中文標籤 | 節點顏色 |
|-----------------|---------|---------|
| concept | 概念 | #1f1f1f |
| content | 內容 | #6b7280 |
| organization | 組織 | #d94800 |
| person | 人物 | #ffa110 |
| method | 方法 | #8b6914 |
| data | 數據 | #a0a0a0 |
| event | 判決/事件 | #dc2626 |
| statute | 法條 | #2563eb |
| artifact | 文件 | #16a34a |
| location | 地點 | #7c7c7c |
| technology | 技術 | #fa520f |

---

## 十二、不在範圍內

- 圖譜渲染引擎本身（d3-force）不更換
- 不新增資料來源或連接器
- 不修改 extraction schema 定義
- 不涉及權限或多租戶邏輯
- 不做圖譜的 Top N 重要節點排行（留待未來迭代）
- 不做 edge 關係的 LLM 分類（用規則 + keyword 對照表）
