# OpenRaven PRD v1.0
## 個人專業知識資產化平台

**產品名稱**：OpenRaven
**版本**：v1.0 | **日期**：2026 Q2 | **狀態**：定稿

---

## 命名緣起

北歐神話中，智慧之神奧丁擁有兩隻渡鴉：**Huginn**（思想）與 **Muninn**（記憶）。牠們每天飛遍世界，收集知識帶回給奧丁。這幾乎就是 OpenRaven 的產品描述——

> **Huginn** = AI 思考代理，在你的文件中飛翔、萃取、連結知識
> **Muninn** = 永久記憶庫，讓你的職涯知識不再隨時間和人員流失而消散

渡鴉也是現實世界中最聰明的鳥類之一：使用工具、能解決問題、擁有長期記憶，並且會主動收集有價值的事物。**Open** 前綴代表核心引擎完全開源——隱私可被驗證，代碼可被審計。

---

## 目錄

1. [產品願景與定位](#1-產品願景與定位)
2. [目標用戶與核心痛點](#2-目標用戶與核心痛點)
3. [開源策略與商業模式](#3-開源策略與商業模式)
4. [設計原則：零學習成本](#4-設計原則零學習成本)
5. [資料隱私架構](#5-資料隱私架構)
6. [核心功能規格](#6-核心功能規格)
7. [技術架構](#7-技術架構)
8. [定價策略](#8-定價策略)
9. [Go-to-Market 路徑](#9-go-to-market-路徑)
10. [成功指標](#10-成功指標)
11. [風險與緩解](#11-風險與緩解)
12. [開放決策事項](#12-開放決策事項)

---

## 1. 產品願景與定位

### 1.1 產品使命

> **「讓專業知識從人的腦袋和文件碎片中，被系統性萃取、永久留存、並持續活化。」**

OpenRaven 是一個 AI 驅動的個人專業知識資產化平台。它讓律師、金融分析師、顧問、工程師等專業人士，在**零額外工作量**的前提下，將日常工作中產生的知識碎片——Email、報告、會議記錄、閱讀筆記、案件分析——自動編譯成持續成長、可查詢的結構化知識庫，最終可部署為代理作業的 Expert AI Agent。

**核心引擎完全開源（Apache 2.0），雲端協作和企業功能商業化。**

### 1.2 產品定位

| 維度 | 現有工具（Notion / Obsidian）| OpenRaven |
|---|---|---|
| 知識捕捉方式 | 主動手動記錄 | 被動自動萃取 |
| 知識組織方式 | 用戶自己建立結構 | LLM 自動編譯、分類、連結 |
| 知識主體 | 文件和筆記 | 隱性知識與判斷邏輯 |
| 資料所有權 | 視平台而定 | 用戶完全擁有，可本地/自託管 |
| 可審計性 | 閉源 | **完全開源，可自行審計** |
| 最終用途 | 個人閱讀查詢 | 可部署為 Expert AI Agent |

### 1.3 市場規模

| 市場 | 2025 規模 | CAGR | 2030 預測 |
|---|---|---|---|
| 知識管理軟體 | $232 億 | 13.8% | $742 億 |
| 企業 LMS | $96 億 | 19.4% | $274 億 |
| 繼任規劃軟體 | $38 億 | 12%+ | $67 億 |
| **可參照 TAM** | **~$370 億** | — | **~$1,000 億** |

**市場驗證**：
- 42% 的機構知識只存在於個人腦中（IDC）
- Fortune 500 每年因知識分享失敗損失 $315 億
- 一名資深員工離職的隱性成本高達 $43 萬（不含招募費）
- Delphi AI 2025 年獲 Sequoia、Anthropic 投資 Series A $1,600 萬，驗證「知識代理人」商業模式

---

## 2. 目標用戶與核心痛點

### 2.1 主要 Persona（個人版 MVP）

| Persona | 職業背景 | 核心痛點 | 使用動機 |
|---|---|---|---|
| **律師 Alex** | 執業 8 年公司法律師 | 案件研究分散、換案重複搜尋、離職帶不走知識 | 建立個人「法律智庫」，過去研究快速重用 |
| **分析師 Mei** | 投信股票研究員 | 產業研究隨時間失散，換工作積累歸零 | 個人投資知識資產，長期職涯競爭力 |
| **顧問 Ryan** | 管理顧問 10 年 | 每個 engagement 重建行業知識，方法論未系統化 | 個人顧問品牌知識庫，可對外商業化 |
| **工程師 Sam** | 資深後端工程師 | 系統決策的「為什麼」沒記錄，技術積累難帶走 | 技術成長的系統化記錄，未來寫書或教學的素材 |

### 2.2 設計紅線（用戶絕對不會做的事）

- ❌ 每天花時間整理和分類筆記
- ❌ 學習新的文件格式或 Wiki 語法
- ❌ 把重要資料上傳到不信任的雲端
- ❌ 接受 AI 公司將自己的資料用於模型訓練
- ❌ 為了使用工具而改變工作習慣

### 2.3 理想體驗

- ✅ 我照常工作，工具在背景自動捕捉整理
- ✅ 我想查什麼，直接問，像問一個了解我的助手
- ✅ 我的資料只在我控制的地方，沒人能拿去訓練 AI
- ✅ 我的知識庫是我的資產，換工作或退休都帶得走
- ✅ 未來我可以讓 AI 代替我回答專業問題

---

## 3. 開源策略與商業模式

### 3.1 Open-Core 架構

OpenRaven 採用 **Open-Core** 模式：核心引擎完全開源，雲端服務和企業功能商業化。

```
OpenRaven Core（開源 Apache 2.0）
├── 知識編譯引擎（LangExtract + LightRAG 整合）
├── 本地 Wiki 生成管道
├── CLI 工具
├── 本地儲存層（NetworkX + NanoVectorDB + SQLite）
├── 基本 Web UI（單用戶本地版）
└── 資料匯入匯出（Markdown / JSON / GraphML）

OpenRaven Cloud（商業閉源）
├── 雲端同步與跨裝置存取
├── 端對端加密雲端儲存（E2EE）
├── 雲端連接器（Google Drive / Gmail / Outlook）
├── Expert Agent 對外部署
├── 進階知識圖譜視覺化
├── 課程 / 教材自動生成
├── 企業多租戶（Neo4j + Qdrant 後端）
├── 繼任規劃功能
└── SOC 2 合規審計日誌
```

### 3.2 為什麼個人版要開源

**隱私可被驗證**
用戶可以自己審計代碼，確認沒有資料外洩或後門。這是解決「我不信任 AI 平台」的最強答案——不需要相信我們說的，看代碼就知道。對律師、金融分析師等高隱私需求的目標用戶，這比任何行銷說詞都更有力。

**社群驅動增長**
技術社群天然信任開源工具。GitHub Stars 是最便宜的行銷，也是進入 Hacker News 的門票。Karpathy 的 LLM 知識庫受眾（工程師、研究者）正是最早期的用戶群，他們習慣從開源工具開始。

**垂直行業 Schema 由社群貢獻**
LangExtract 的每個垂直行業萃取 schema（法律引用格式、財報實體、醫療術語）需要領域專家撰寫。開源讓社群可以貢獻台灣法院判決書格式、台灣金融申報格式等在地化 schema，這些積累本身就是商業版的核心 IP 護城河。

**對抗大廠功能複製**
開源的核心引擎讓 Notion / Google 難以輕易複製——他們可以抄功能，但無法建立同樣的開源社群信任和垂直 schema 生態。

### 3.3 版本區分

| 版本 | 授權 | 目標用戶 | 定位 |
|---|---|---|---|
| **OpenRaven Core** | Apache 2.0（開源）| 開發者、技術用戶、自託管偏好者 | 完整本地運行，代碼可審計 |
| **OpenRaven Personal** | 商業訂閱 | 一般個人專業人士 | 雲端便利 + 隱私保證 |
| **OpenRaven Cloud** | 商業訂閱 | 團隊、企業 | 協作、合規、企業功能 |

### 3.4 開源社群策略

**GitHub 倉庫結構**

```
github.com/openraven/
├── openraven          ← 核心引擎（Apache 2.0）
├── openraven-ui       ← 本地 Web UI（Apache 2.0）
├── openraven-chrome   ← Chrome 擴充功能（Apache 2.0）
└── openraven-schemas  ← 垂直行業 LangExtract Schema（社群貢獻）
    ├── legal-taiwan/
    ├── finance-tw/
    ├── medical/
    └── engineering/
```

**社群貢獻鼓勵機制**
- 垂直行業 Schema 貢獻者：在官網列名「社群貢獻者」
- 優秀 PR 合併後：提供一年免費 Personal 訂閱
- Schema Marketplace：未來允許高品質 schema 作者收取小額授權費（平台抽成 20%）

**開源與商業版的界線原則**
> 「任何讓個人用戶的知識庫在本地運行得更好的功能，都應該開源。任何需要我們的基礎設施才能運行的功能，才進入商業版。」

### 3.5 商業雲端整合架構

```
                        OpenRaven Cloud
                        ┌─────────────────────────────────┐
用戶裝置                │                                 │
┌──────────────┐        │  ┌─────────────┐               │
│ Core Engine  │◄──────►│  │  Sync API   │               │
│ (本地運行)   │  E2EE  │  │  (加密同步) │               │
└──────────────┘        │  └──────┬──────┘               │
                        │         │                       │
                        │  ┌──────▼──────┐               │
                        │  │ Knowledge   │               │
                        │  │ Store(E2EE) │               │
                        │  │ Neo4j+Qdrant│               │
                        │  └──────┬──────┘               │
                        │         │                       │
                        │  ┌──────▼──────────────────┐   │
                        │  │    Cloud Services        │   │
                        │  │  ┌─────┐ ┌────────────┐ │   │
                        │  │  │Drive│ │Agent Deploy│ │   │
                        │  │  │Gmail│ │Course Gen  │ │   │
                        │  │  │Meet │ │Enterprise  │ │   │
                        │  │  └─────┘ └────────────┘ │   │
                        │  └─────────────────────────┘   │
                        └─────────────────────────────────┘
```

**雲端連接器（僅商業版）**

| 連接器 | 功能 | 資料流向 |
|---|---|---|
| Google Drive | OAuth 授權，選擇性資料夾掃描 | 文件 → 加密後存本地/雲端 |
| Gmail / Outlook | 分析寄出信件，萃取專業判斷 | 信件元資料 → 本地處理 |
| Google Meet / Granola | 會議記錄自動攝取 | 轉錄 → 本地 LLM 處理 |
| Notion 匯入 | 批量導入現有筆記 | 開源版也支援（手動匯出 + 匯入）|

---

## 4. 設計原則：零學習成本

### 4.1 設計哲學：「沉默工作，清晰呈現」

AI 在背景默默工作，用戶從不需要「管理」知識庫。知識庫結構由系統自動生成，用戶只需要「閱讀」和「查詢」。

### 4.2 Onboarding 流程：5 分鐘上手

**步驟 1：連接資料來源（2 分鐘）**

用戶首次登入，只看到一個畫面：「選擇你工作在哪裡」

| 來源 | 開源版 | 商業版 |
|---|---|---|
| 📄 拖放文件（PDF / Word / PPT / Excel）| ✅ | ✅ |
| 📝 Notion / Obsidian 匯出匯入 | ✅ | ✅ |
| 🌐 Chrome 擴充功能（收藏網頁）| ✅ | ✅ |
| 📁 Google Drive | — | ✅ |
| 📧 Gmail / Outlook | — | ✅ |
| 🎙️ 會議記錄（Granola / Otter.ai）| — | ✅ |

> **設計原則**：用戶不需要一次連接所有來源。即使第一天只拖放三個 PDF，系統也能立即開始工作。每個資料來源的連接都有「這會做什麼 / 不會做什麼」的透明說明。

**步驟 2：AI 在背景編譯（完全自動）**

用戶關掉 App 去工作。系統在背景：
1. 文件攝取：解析所有來源，轉換為純文字
2. 實體萃取（LangExtract）：識別概念、判斷、方法論、案例，精確定位來源段落
3. 知識圖譜建立（LightRAG）：建立實體關係圖和向量索引
4. Wiki 文章生成：合成結構化文章，每個聲明附精確來源引用
5. 首次健康報告：「您的知識庫包含 127 個概念文章，橫跨 8 個主題領域」

**步驟 3：第一次的驚喜感**

用戶回來後發現：
- 「找到 3 個您過去處理過的類似案件」
- 「發現了 23 個您常用的分析框架」

> **第一次的驚喜感是最重要的留存觸發點。**

### 4.3 日常使用：對話即一切

| 用戶問的問題 | 查詢模式 | 系統行為 |
|---|---|---|
| 「上次我怎麼處理跨境收購的稅務問題？」 | `local` | 搜尋特定實體，呈現過去分析摘要，附來源段落 |
| 「我有哪些關於 SaaS 估值的研究？」 | `local` | 彙整相關研究，顯示知識演化時間軸 |
| 「我的知識庫的主要主題是什麼？」 | `global` | 跨文件廣域推理，生成主題概覽 |
| 「幫我分析這個法律問題」 | `mix` | 具體引用 + 廣義推理，最完整的回答 |
| 「有哪些我還不熟悉的領域需要補強？」 | `global` | 知識覆蓋率分析，生成建議閱讀清單 |

### 4.4 CLI 介面（開源版核心體驗）

```bash
# 安裝
brew install openraven
# 或
pip install openraven

# 初始化知識庫
raven init ~/my-knowledge

# 攝取文件
raven add ./docs/          # 整個目錄
raven add report.pdf       # 單一文件
raven add https://...      # 網頁 URL

# 查詢
raven ask "上次我怎麼處理這個問題？"
raven ask --mode global "我的主要研究方向有哪些？"

# 狀態
raven status               # 知識庫健康報告
raven graph                # 輸出知識圖譜（GraphML）

# 匯出
raven export --format markdown ./export/
```

---

## 5. 資料隱私架構

### 5.1 隱私是核心功能，不是附加功能

對專業人士而言，知識庫包含最敏感的職業資產。**隱私的顧慮是採用的最大障礙，必須正面解決。**

**最大的用戶顧慮**
> 「我的資料會被 OpenAI / Anthropic 拿去訓練模型嗎？」
> 「平台公司能看到我的知識庫內容嗎？」
> 「我的客戶機密資料會外洩嗎？」

**OpenRaven 的答案**：
- 代碼開源，隱私保證可被驗證
- API 企業版合約保證不訓練（詳見 5.2）
- 本地 LLM 選項（Ollama）實現零資料外洩
- E2EE 讓雲端版也無法讀取你的資料

### 5.2 LLM API 企業合約隱私保證

OpenRaven 使用 **API 企業版合約**，而非消費者版：

| 供應商 | 資料訓練政策 | DPA | 資料留存 | 零留存（ZDR）|
|---|---|---|---|---|
| **Anthropic Claude API** | 固定政策，絕對不訓練 | 自動納入商業條款 | **7 天** | ✅ 需申請 |
| **OpenAI API** | 商業 API 不用於訓練 | Services Agreement | 可協商 | ❌ |
| **Google Vertex AI** | 未授權不訓練（服務條款）| CDPA 自動納入 GCP | 可設 0 天 | ✅ |

> ⚠️ **重要區分**：2025 年 9 月 Anthropic 的消費者條款變更（要求選擇是否同意訓練）**完全不影響 API 用戶**。API 商業合約受獨立保護。

### 5.3 四種儲存模式

| 模式 | 適合用戶 | 資料位置 | 隱私等級 |
|---|---|---|---|
| **本地模式（Local-first）** | 個人，最高隱私需求 | 完全在用戶裝置 | ⭐⭐⭐⭐⭐ |
| **自託管雲端** | 技術型用戶，需跨裝置 | 用戶自己的 AWS/GCP | ⭐⭐⭐⭐⭐ |
| **OpenRaven Cloud（E2EE）** | 一般用戶，方便優先 | 加密後存於平台 | ⭐⭐⭐⭐ |
| **企業私有部署** | 企業客戶，合規需求 | 企業自有機房/雲 | ⭐⭐⭐⭐⭐ |

### 5.4 端對端加密（E2EE）設計

對使用 OpenRaven Cloud 的用戶：
- 知識庫在上傳前在用戶端加密（Client-side encryption，AES-256）
- OpenRaven 伺服器只存儲密文，無法讀取內容
- 加密金鑰由用戶掌控，不存在伺服器端
- 即使 OpenRaven 被駭或倒閉，攻擊者無法讀取用戶資料

### 5.5 本地 LLM 支援（零資料外洩模式）

透過 Ollama 整合，全部功能支援本地 LLM：

| 模型 | 硬體需求 | 效能 | 適用場景 |
|---|---|---|---|
| Llama 3.3 70B | GPU 24GB+ | 接近雲端 API | 高品質知識編譯 |
| Gemma 3 12B | 8GB RAM | 良好 | 日常問答 |
| Llama 3.1 8B | 8GB RAM | 基本 | 低資源裝置 |
| Phi-4 | 4GB RAM | 有限 | 最低硬體需求 |

> ⚠️ LightRAG 建議使用 32B+ 模型以獲最佳實體萃取品質。4B 模型在複雜文件上可能萃取不到足夠實體。建議本地模式最低 12B 模型。

### 5.6 資料主權設計

**Portability First**：用戶隨時可匯出完整知識庫
- 標準 Markdown 文件（可直接在 Obsidian 開啟）
- JSON（知識圖譜的所有關係和元資料）
- GraphML（LightRAG 的知識圖譜，可視覺化）

**Delete-first**：
- 刪除帳號後 7 天內所有資料永久刪除
- 向量資料庫中的嵌入向量同步刪除
- 提供刪除確認憑證

---

## 6. 核心功能規格

### 6.1 功能優先級

| 功能 | 優先級 | 開源 | 商業 |
|---|---|---|---|
| 知識編譯引擎（LangExtract + LightRAG）| P0 | ✅ | ✅ |
| 自然語言問答介面 | P0 | ✅ | ✅ |
| CLI 工具（raven add / ask）| P0 | ✅ | — |
| 文件攝取（拖放）| P0 | ✅ | ✅ |
| 本地 LLM 支援（Ollama）| P0 | ✅ | ✅ |
| 基本 Web UI | P0 | ✅ | ✅ |
| Google Drive 連接 | P1 | — | ✅ |
| Gmail / Outlook 連接 | P1 | — | ✅ |
| Chrome 擴充功能 | P1 | ✅ | ✅ |
| 知識圖譜視覺化（基本）| P1 | ✅ | ✅ |
| 知識圖譜視覺化（互動進階）| P2 | — | ✅ |
| 雲端同步（E2EE）| P1 | — | ✅ |
| 知識健康報告 | P2 | ✅ | ✅ |
| Expert Agent 對外部署 | P2 | — | ✅ |
| 課程 / 教材自動生成 | P3 | — | ✅ |
| 企業多租戶 | P3 | — | ✅ |

### 6.2 知識攝取引擎

**支援格式**：

| 類型 | 格式 | 處理方式 | 開源/商業 |
|---|---|---|---|
| 文件 | PDF、DOCX、PPTX、XLSX、TXT | Docling 解析 | 兩者 |
| 網頁 | URL、HTML | Jina Reader 轉 Markdown | 兩者 |
| Email | Gmail / Outlook（OAuth）| 分析寄出信件 | 商業 |
| 會議記錄 | Granola、Otter.ai、Meet 字幕 | 轉錄後萃取決策點 | 商業 |
| 雲端硬碟 | Google Drive / OneDrive | OAuth 選擇性掃描 | 商業 |
| 圖片 | PNG、JPEG、HEIC | Vision LLM 萃取 | 兩者 |

**增量更新機制**（開源版核心特性）：
1. 計算文件 hash，跳過未變更文件
2. 只重新處理有變動的文件
3. 透過依賴圖追蹤，只更新受影響的 Wiki 文章
4. 不觸發全庫重新編譯（成本控制關鍵）

### 6.3 知識編譯管道（4 階段）

```
原始文件
    │
    ▼
[Stage 1] LangExtract 實體萃取
    輸入：任意格式文件
    輸出：帶精確來源位置的結構化實體清單（JSONL）
    特性：source grounding——每個實體對應原始文字的精確段落
    LLM ：Gemini 3.1 Flash 或 Ollama（低成本，高吞吐）
    │
    ▼
[Stage 2] LightRAG 知識圖譜建立
    輸入：實體清單 + 原始文字片段
    處理：建立實體—關係圖
           ├─ 本地：NetworkX 圖 + NanoVectorDB 向量
           └─ 生產：Neo4j 圖 + Qdrant 向量
          雙層索引（低層：具體實體 | 高層：廣域主題）
    輸出：可查詢的知識圖譜
    │
    ▼
[Stage 3] Wiki 文章生成
    輸入：LightRAG 圖譜 + LangExtract 來源位置
    處理：為每個主題概念生成結構化 Markdown 文章
           每個聲明附精確來源引用（段落級別）
           建立文章間反向連結
    LLM ：Claude Sonnet 4.6（最高品質）
    輸出：完整 Wiki 文章庫
    │
    ▼
[Stage 4] 健康維護（定期背景執行）
    矛盾偵測、陳舊標記、知識缺口分析、新連結發現
```

**防幻覺機制**：
- LangExtract source grounding 保證每個聲明的原始段落可追溯
- 多輪核實：生成 → 提取聲明 → 對照來源驗證 → 標記不確定內容
- 信心度評分：每篇 Wiki 文章顯示「資料完整度」
- 無可信來源時，明確標記為「推斷」而非呈現為事實

### 6.4 LightRAG 查詢系統

六種查詢模式對應不同使用場景：

| 模式 | 適用場景 | 範例問句 |
|---|---|---|
| `local` | 特定實體查詢 | 「上次這個案件怎麼處理？」 |
| `global` | 跨文件廣域推理 | 「我的知識庫主要主題有哪些？」 |
| `mix`（推薦預設）| 綜合查詢 | 「幫我分析這個法律問題」 |
| `hybrid` | local + global 組合 | 兩個層面同時查詢 |
| `naive` | 傳統向量搜尋 | 簡單關鍵字查詢 |
| `bypass` | 直連 LLM | 不查知識庫的一般對話 |

---

## 7. 技術架構

### 7.1 技術選型總覽

| 層次 | 技術 | 授權 | 開源/商業 | 理由 |
|---|---|---|---|---|
| **實體萃取** | LangExtract（Google）| Apache 2.0 | 兩者 | Source grounding、Ollama 支援、長文件優化 |
| **知識圖譜框架** | LightRAG（HKU EMNLP 2025）| MIT | 兩者 | 增量更新、6 種查詢模式、成本比 GraphRAG 低 99% |
| **圖儲存（本地）** | NetworkX | BSD | 開源版 | 零依賴、純 Python、可匯出 GraphML |
| **圖儲存（生產）** | Neo4j Community | GPL v3 | 商業版 | LightRAG 測試最佳效能 |
| **向量儲存（本地）** | NanoVectorDB | — | 開源版 | LightRAG 預設，零配置 |
| **向量儲存（生產）** | Qdrant | Apache 2.0 | 商業版 | 開源、自託管友好 |
| **文件解析** | Docling + Jina Reader | Apache 2.0 | 兩者 | 開源，可本地運行 |
| **前端** | React + Vite + Capacitor | MIT | 兩者 | 跨平台（Web / iOS / Android）|
| **後端 API** | Bun + TypeScript + Hono | MIT | 兩者 | 高效能，TypeScript 原生 |
| **LLM（雲端）** | Claude API / Gemini Vertex | 商業 | 兩者 | 企業 API 有 DPA，不訓練 |
| **LLM（本地）** | Ollama + Llama / Gemma | MIT | 兩者 | 零資料外洩 |
| **主要資料庫** | SQLite + Litestream | MIT | 開源版 | 輕量、易備份 |
| **雲端資料庫** | PostgreSQL | PostgreSQL | 商業版 | KV + pgvector 一站式 |

> ⛔ **已排除**：KuzuDB（2025 年 10 月被 Apple 收購並封存）
> ⛔ **已排除**：Microsoft GraphRAG（增量更新需全量重建，成本不可接受）
> ⚠️ **謹慎**：FalkorDB（SSPL 非真正開源，商業使用需確認授權限制）

### 7.2 兩種部署模式

**開源本地模式（零配置）**

```python
# pip install openraven

from openraven import Raven

raven = Raven(
    working_dir="~/my-knowledge",
    llm="ollama/llama3.3:70b",        # 本地 LLM
    embedding="ollama/nomic-embed-text",
    # graph_storage  = NetworkX（預設）
    # vector_storage = NanoVectorDB（預設）
    # kv_storage     = JSON（預設）
)

await raven.add("./docs/")            # 攝取文件
result = await raven.ask("上次我怎麼處理這個問題？")
```

所有資料存在 `~/my-knowledge/`，備份只需複製資料夾。

**商業雲端模式（生產環境）**

```python
from openraven import Raven

raven = Raven(
    workspace="my-team",
    api_key="raven_...",              # OpenRaven Cloud
    graph_storage="neo4j",            # 雲端 Neo4j
    vector_storage="qdrant",          # 雲端 Qdrant
    llm="claude-sonnet-4-6",          # Claude API（DPA 保護）
    encryption="e2ee",                # 端對端加密
)
```

### 7.3 LangExtract + LightRAG 整合

```python
import langextract as lx
from openraven.pipeline import compile_wiki

# Stage 1：LangExtract 萃取實體（帶精確來源位置）
result = lx.extract(
    text_or_documents=document_path,
    prompt_description=domain_prompt,    # 法律/金融/技術 各有專屬 prompt
    examples=domain_examples,
    model_id="gemini-3.1-flash",         # 低成本批量萃取
    # 本地模式：
    # model_id="llama3.3:70b",
    # model_url="http://localhost:11434"
)

# Stage 2：LangExtract 結果 + 原文送入 LightRAG
enriched_text = attach_source_grounding(document_text, result)
await rag.ainsert(enriched_text)

# Stage 3：Wiki 文章生成，來源位置轉為精確引用
wiki = await compile_wiki(
    topic=entity.name,
    rag=rag,
    source_positions=result.source_positions,  # 段落級別引用
    llm="claude-sonnet-4-6",
)
```

### 7.4 成本路由策略

```
文件攝取（大量、低成本）
    → Gemini 3.1 Flash（$0.10/MTok input）
    → 或 Ollama Llama 3.1 8B（本地，$0）

Wiki 文章生成（精品、低量）
    → Claude Sonnet 4.6（$3.00/MTok input）
    → 或 Ollama Llama 3.3 70B（本地，$0）

日常問答（中量、平衡）
    → Claude Haiku 4.5（$0.80/MTok input）
    → 或 Ollama Gemma 3 12B（本地，$0）
```

**成本估算（雲端模式）**：

| 規模 | 初始編譯成本 | 問答（1K 次/天）| 月度更新 |
|---|---|---|---|
| 100 個文件 | $2–5 | ~$60/月 | ~$0.5/月 |
| 1,000 個文件 | $15–30 | ~$60/月 | ~$2/月 |
| 10,000 個文件 | $150–300 | ~$60/月 | ~$15/月 |
| **本地模式任何規模** | **$0** | **$0** | **$0** |

---

## 8. 定價策略

### 8.1 定價架構

採用**混合訂閱 + AI 積分**模式，開源版永久免費。

### 8.2 完整方案

| 方案 | 月費 | 年費 | 定位 |
|---|---|---|---|
| **OpenRaven Core** | 免費（開源）| — | 完整本地運行，Apache 2.0 |
| **Personal** | $19 | $190（年省 $38）| 雲端同步 + 連接器，個人用戶 |
| **Expert** | $49 | $490（年省 $98）| 含 Agent 部署 + 課程生成 |
| **Local Pro** | $299 一次性買斷 | — | 完整功能本地版，無訂閱費 |
| **Team** | $35/人/月 | $350/人/年 | 共享知識庫，最低 3 人 |
| **Enterprise** | $100–200/人/月 | 客製 | 私有部署，合規，繼任規劃 |

**垂直行業加購（Enterprise）**：

| 垂直版 | 加購費 | 包含 |
|---|---|---|
| Legal（法律）| +$100/人/月 | iManage 整合、台灣法院引用格式、特權文件管理 |
| Finance（金融）| +$100/人/月 | Bloomberg/路孚特整合、合規審計軌跡、申報格式 |

### 8.3 開源版和付費版的差異

| 功能 | Core（開源）| Personal | Expert | Team |
|---|---|---|---|---|
| 知識編譯引擎 | ✅ | ✅ | ✅ | ✅ |
| 本地儲存 | ✅ | ✅ | ✅ | ✅ |
| 本地 LLM（Ollama）| ✅ | ✅ | ✅ | ✅ |
| CLI 工具 | ✅ | ✅ | ✅ | ✅ |
| 基本 Web UI | ✅ | ✅ | ✅ | ✅ |
| Chrome 擴充功能 | ✅ | ✅ | ✅ | ✅ |
| 檔案數量限制 | 無限 | 無限 | 無限 | 無限 |
| 雲端同步（E2EE）| ❌ | ✅ | ✅ | ✅ |
| Google Drive 連接 | ❌ | ✅ | ✅ | ✅ |
| Gmail / Outlook | ❌ | ✅ | ✅ | ✅ |
| 會議記錄連接 | ❌ | ✅ | ✅ | ✅ |
| 知識圖譜互動視覺化 | 基本 | 基本 | 進階 | 進階 |
| Expert Agent 部署 | ❌ | ❌ | ✅ | ✅ |
| 課程 / 教材生成 | ❌ | ❌ | ✅ | ✅ |
| API 存取 | ❌ | ❌ | ✅ | ✅ |
| 共享知識庫 | ❌ | ❌ | ❌ | ✅ |
| SSO / 審計日誌 | ❌ | ❌ | ❌ | 企業版 |

### 8.4 單位經濟

**Personal 版（$19/月）**：
- LLM 推理成本：~$3–5/月
- 毛利率：~**75–85%**

**Enterprise 版**：
- 預期 LTV：$5,000–50,000/帳戶
- 月流失率目標：< 1%（知識庫本身是轉換成本）
- 目標 NRR：> 110%（使用量自然擴張）

---

## 9. Go-to-Market 路徑

### 9.1 戰略邏輯

```
開源社群信任 → 個人用戶採用 → 個人帶進企業 → 企業採購
```

### 9.2 Phase 1（0–6 個月）：開源社群 + 早期用戶

**目標**：GitHub 1,000 Stars，500 付費用戶，$10K MRR

**核心動作**：
- 在 Hacker News 發「Show HN: OpenRaven」
- 針對 Karpathy 受眾（LLM + 個人知識庫的早期採用者）
- 打造 10 個「magic demo」影片：「讓 AI 幫你的 10 年法律工作建知識庫」
- 開源社群建立：Discord、GitHub Discussions

**Hook**：
> 「`pip install openraven && raven add ./docs/ && raven ask "..."` — 你的私人 AI 研究員，完全本地，代碼可審計」

**KPI**：
- 首次編譯後 7 天留存率 > 60%
- 問答次數/週/用戶 > 5
- 免費→付費轉換率 > 5%

### 9.3 Phase 2（6–12 個月）：台灣垂直市場

**目標**：三個垂直各 100 個付費用戶，$50K MRR

- **法律**：律師公會、法律科技社群，從 5–10 名律師試點
- **金融**：CFA 協會台灣分會，從個人研究員帶動法人採購
- **顧問**：MBA 校友網路，管理顧問群體

**社群 Schema 策略**：
- 發布台灣法院判決書 LangExtract Schema
- 發布台灣上市公司財報萃取 Schema
- 邀請各垂直行業的 KOL 共同貢獻，官網列名

### 9.4 Phase 3（12–24 個月）：企業採購

**目標**：10 家企業帳戶，平均 ACV $10,000+，$200K MRR

- 個人用戶帶著知識庫進入公司，HR 看到繼任規劃價值
- 推出「知識留存 ROI 計算器」：量化展示節省的知識流失成本
- 發布 Case Study：「律師事務所用 OpenRaven 將資深律師知識留存率提升至 X%」

---

## 10. 成功指標

### 10.1 產品健康指標

| 指標 | M3 | M6 | M12 |
|---|---|---|---|
| GitHub Stars | 500 | 2,000 | 8,000 |
| MRR | $3K | $10K | $100K |
| 付費用戶 | 150 | 500 | 5,000 |
| 7 天留存率 | >50% | >60% | >70% |
| 問答次數/週/用戶 | >3 | >5 | >10 |
| NPS | >30 | >40 | >55 |

### 10.2 開源社群指標

| 指標 | M3 | M6 | M12 |
|---|---|---|---|
| GitHub Stars | 500 | 2,000 | 8,000 |
| 外部 Contributors | 5 | 20 | 80 |
| 社群貢獻 Schema 數量 | 2 | 8 | 25 |
| Discord 活躍成員 | 100 | 500 | 2,000 |

### 10.3 技術里程碑

| 里程碑 | 時間 | 驗收標準 |
|---|---|---|
| MVP（CLI + 本地問答）| M1 | 5 個 Alpha 用戶完整使用 |
| LangExtract + LightRAG 整合 | M1 | 問答準確率 > 80%，來源引用正確率 > 95% |
| 基本 Web UI | M2 | 可在瀏覽器使用完整功能 |
| Chrome 擴充功能 | M2 | Chrome Web Store 上線 |
| 本地 Ollama 全功能 | M2 | 所有功能在 Ollama 上 100% 可用 |
| OpenRaven Cloud Beta | M3 | E2EE 雲端同步，Google Drive 連接 |
| 知識圖譜視覺化 | M3 | > 50 個節點，連結準確率 > 85% |
| SOC 2 Type I | M6 | 企業採購門檻 |
| Expert Agent 部署 | M6 | 可對外部署可查詢的 URL |

---

## 11. 風險與緩解

| 風險 | 嚴重性 | 緩解策略 |
|---|---|---|
| LLM 幻覺影響專業信任 | 🔴 高 | LangExtract source grounding；信心度評分；審查介面 |
| 大廠複製功能 | 🟡 中 | 垂直行業 schema 護城河；開源社群信任；先發優勢 |
| LLM API 資料安全疑慮 | 🔴 高 | 代碼開源可審計；本地 Ollama 模式；DPA 企業合約 |
| 本地模型品質不足 | 🟡 中 | 建議 12B+ 模型；明確說明限制；雲端 fallback |
| 開源被大廠 Fork 商業化 | 🟡 中 | Apache 2.0 允許此行為；核心護城河是社群和 schema 生態 |
| 台灣個資法合規 | 🔴 高 | 法律顧問；資料可選台灣/新加坡節點；清楚隱私政策 |
| Neo4j GPL 授權限制 | 🟡 中 | 評估企業版授權；PostgreSQL + AGE 替代方案 |

---

## 12. 開放決策事項

**技術**

1. **本地模型最低需求**：LightRAG 建議 32B+ 模型，多數個人用戶無此硬體。是否推出「輕量模式」（品質降低但可用）？
2. **PostgreSQL + AGE vs Neo4j**：兩者都是 LightRAG 支援的後端。PostgreSQL 一站式（KV + Vector + Graph），Neo4j 效能更好。商業版優先評估哪個？
3. **Email 分析邊界**：全量掃描 vs 用戶手動標記。建議後者，但會影響功能完整性。

**商業**

4. **台灣先行 vs 直接英語全球**：台灣是法律/金融試點理想場所，但市場規模有限。建議 M6 後用台灣案例作為英語市場社會證明。
5. **Expert Agent 商業化**：平台收分潤（20%）vs 純訂閱。建議 Expert 版訂閱含 1 個 Agent，多個 Agent 按量計費。
6. **Local Pro 買斷定價**：$299 是否過低或過高，需要用戶調研驗證。

**法律**

7. **個人 vs 企業知識庫所有權**：在職期間建立的知識庫，屬於個人還是公司？需要法律顧問設計清楚的服務條款。

---

## 附錄 A：核心技術決策記錄

### 為什麼選 LightRAG 而非 Microsoft GraphRAG

| 維度 | Microsoft GraphRAG | LightRAG |
|---|---|---|
| 增量更新 | 需全量重建（致命缺點）| Union 操作，O(新文件) |
| 查詢成本 | 610,000 tokens / 次 | < 100 tokens / 次（6,000x 差）|
| 查詢速度 | 基準 | 快 30% |
| Ollama 支援 | 有限 | 完整 |
| 學術認可 | Microsoft Research | EMNLP 2025 |

### 為什麼 KuzuDB 不能使用

KuzuDB 在 2025 年 10 月被 Apple 收購後，GitHub repository 已封存，主動開發完全停止。社群 fork（LadybugDB）缺乏企業支撐，不適合作為產品基礎設施。

### LangExtract Source Grounding 的關鍵性

LangExtract 的核心差異在於每個萃取結果都帶有原始文字的精確段落位置：

```json
{
  "entity": "公司法第 185 條",
  "context": "重大資產處分需股東大會決議",
  "source_location": {
    "document": "客戶備忘錄_2025Q1.pdf",
    "page": 3,
    "char_start": 1247,
    "char_end": 1312
  }
}
```

這個位置資訊直接成為 Wiki 文章引用的依據，讓用戶可以點擊任何知識聲明，跳轉到原始文件的精確段落，從根本上解決了「LLM 幻覺」對專業知識庫的信任問題。

---

## 附錄 B：開源倉庫結構

```
github.com/openraven/
│
├── openraven/                     # 核心引擎（Apache 2.0）
│   ├── core/
│   │   ├── ingestion/             # 文件解析（Docling 整合）
│   │   ├── extraction/            # LangExtract 整合
│   │   ├── graph/                 # LightRAG 整合
│   │   ├── wiki/                  # Wiki 文章生成
│   │   └── health/                # 知識健康報告
│   ├── storage/
│   │   ├── local/                 # NetworkX + NanoVectorDB + SQLite
│   │   └── adapters/              # Neo4j / Qdrant / PostgreSQL 介面
│   ├── llm/
│   │   ├── ollama/                # 本地 LLM 支援
│   │   └── cloud/                 # Claude / Gemini API 介面
│   └── cli/                       # raven CLI 工具
│
├── openraven-ui/                  # 本地 Web UI（Apache 2.0）
│   ├── src/
│   │   ├── ask/                   # 問答介面
│   │   ├── graph/                 # 知識圖譜視覺化（基本版）
│   │   └── health/                # 健康報告 UI
│   └── ...
│
├── openraven-chrome/              # Chrome 擴充功能（Apache 2.0）
│
└── openraven-schemas/             # 垂直行業 Schema（社群貢獻）
    ├── legal/
    │   ├── taiwan-court/          # 台灣法院判決書格式
    │   ├── contract-review/       # 合約審查
    │   └── regulatory/            # 法規文件
    ├── finance/
    │   ├── taiwan-financial/      # 台灣金融申報
    │   ├── earnings-call/         # 法說會記錄
    │   └── research-report/       # 研究報告
    ├── medical/
    │   └── clinical-notes/        # 臨床記錄
    └── engineering/
        ├── architecture-decision/ # ADR 文件
        └── technical-spec/        # 技術規格書
```

---

*OpenRaven PRD v1.0 | 2026 Q2 | Plusblocks Technology Limited*
*「Like Huginn and Muninn, two ravens who fly across the world every day to gather knowledge for Odin.」*
