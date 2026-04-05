# OpenRaven

**ドキュメントから専門知識を自動的に抽出・整理・活用する AI 駆動の知識資産プラットフォーム。**

**他の言語で読む：**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | **日本語** | [한국어](README.ko.md) | [Français](README.fr.md) | [Español](README.es.md) | [Nederlands](README.nl.md) | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven は、散在するドキュメント——PDF、DOCX、プレゼンテーション、会議の文字起こし、Notion エクスポート——を構造化されたクエリ可能な知識グラフに変換します。自然言語で質問したり、概念間のつながりを探索したり、Wiki 記事を自動生成したり、知識ベースからコースを構築したりできます。

## なぜ OpenRaven なのか？

職種や組織が変わると、組織の知識は失われてしまいます。調査によると、組織知識の 42% は人々の頭の中にしか存在しません（IDC）。OpenRaven はその知識を収集・構造化し、常にアクセス可能・検索可能・共有可能な状態にします。

## 機能

### 知識エンジン
- **スマートインジェスト** — PDF、DOCX、PPTX、XLSX、Markdown、画像（AI ビジョン）、または Notion/Obsidian エクスポートをアップロード。エンティティと関係が自動的に抽出されます。
- **知識グラフ** — エンティティタイプ、接続強度、検索によるフィルタリングを備えたインタラクティブな力指向グラフの可視化。GraphML または PNG としてエクスポート可能。
- **自然言語 Q&A** — 6 つのクエリモード（mix、local、global、hybrid、keyword、direct LLM）を使用して知識ベースに質問。回答にはソースの引用が含まれます。
- **自動生成 Wiki** — 抽出されたエンティティと関係から記事が自動生成されます。
- **コース生成** — カリキュラム計画、章の生成、インタラクティブ HTML エクスポートを備えた構造化コースを知識ベースから作成。
- **発見インサイト** — 知識のテーマ、クラスター、ギャップ、トレンドを自動分析。

### コネクター
- **Google Drive** — ドキュメントのインポート（PDF、Docs、Sheets、Slides）
- **Gmail** — メールを知識ベースのエントリとしてインポート
- **Google Meet** — Drive API 経由で会議の文字起こしをインポート
- **Otter.ai** — API キー経由で会議の文字起こしをインポート

### 垂直 Schema
- **Base** — 汎用エンティティ抽出（デフォルト）
- **Engineering** — 技術アーキテクチャ、システム、API
- **Finance** — 企業、財務指標、規制
- **Legal (Taiwan)** — 法令、裁判所の判決、法的原則（繁体字中国語）
- **Finance (Taiwan)** — TWSE 上場企業、財務指標（繁体字中国語）

### 多言語サポート

OpenRaven はブラウザの自動検出と手動切り替えにより 12 言語をサポートします：

| 言語 | コード | 言語 | コード |
|------|--------|------|--------|
| 英語 | `en` | イタリア語 | `it` |
| 繁体字中国語 | `zh-TW` | ベトナム語 | `vi` |
| 簡体字中国語 | `zh-CN` | タイ語 | `th` |
| 日本語 | `ja` | ロシア語 | `ru` |
| 韓国語 | `ko` | フランス語 | `fr` |
| スペイン語 | `es` | オランダ語 | `nl` |

**仕組み：**
- 初回訪問時にブラウザ／OS のロケールを自動検出（フォールバック：英語）
- ナビバーの言語セレクターで切り替え可能
- 設定は localStorage（即時）とユーザープロフィール（クロスデバイス同期）に保存
- LLM の回答はユーザーが選択した言語に合わせる
- Wiki 記事とコースコンテンツはソースドキュメントの言語に従う
- 知識グラフのラベルは英語のまま

### エンタープライズ機能（マネージド SaaS）
- **マルチテナント分離** — テナントごとに独立した知識ベースとストレージ
- **認証** — メール/パスワード + Google OAuth 2.0（セッション管理付き）
- **監査ログ** — すべてのユーザーアクションを追跡し、CSV エクスポートに対応
- **チーム管理** — ワークスペースにメンバーを招待
- **Neo4j グラフバックエンド** — 本番グレードのグラフストレージ（オプション、デフォルト：NetworkX）
- **Docker Compose デプロイ** — nginx、PostgreSQL、Neo4j を含むワンコマンドデプロイ

## アーキテクチャ

```
openraven/                  # Python バックエンド（FastAPI + LightRAG + LangExtract）
  src/openraven/
    api/server.py           # FastAPI アプリファクトリ、すべての API エンドポイント
    pipeline.py             # コアパイプライン：インジェスト、クエリ、グラフ、Wiki、コース
    graph/rag.py            # LightRAG ラッパー（ロケール対応クエリ）
    auth/                   # 認証システム（セッション、OAuth、パスワードリセット）
    audit/                  # 監査ログモジュール
  alembic/                  # データベースマイグレーション
  tests/                    # 159+ 個の Python テスト

openraven-ui/               # TypeScript フロントエンド（React 19 + Vite 6 + Tailwind 4）
  src/
    i18n.ts                 # i18next 初期化（12 ロケール、11 名前空間）
    App.tsx                 # ルートコンポーネント（ルート + ナビバー）
    pages/                  # 14 個のページコンポーネント
    components/             # LanguageSelector、GraphViewer、ChatMessage など
    hooks/useAuth.tsx       # ロケール同期付き認証 Context
  public/locales/           # 132 個の翻訳 JSON ファイル（12 ロケール × 11 名前空間）
  server/index.ts           # Hono BFF（API プロキシ + 静的ファイル配信）
  tests/                    # 46 個の Bun テスト

ecosystem.config.cjs        # PM2 デプロイ設定
```

## クイックスタート

### 前提条件
- Python 3.12+
- Bun 1.0+
- Node.js 20+（PM2 用）

### 1. クローンとインストール

```bash
git clone https://github.com/nickhealthy/OpenRaven.git
cd OpenRaven

# バックエンド
cd openraven
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# フロントエンド
cd ../openraven-ui
bun install
```

### 2. 設定

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # 必須：LLM プロバイダー
WORKING_DIR=/path/to/knowledge-data     # 知識ベースデータの保存場所

# オプション：マネージド SaaS 機能を有効にする
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. PM2 で実行

```bash
# プロジェクトルートから実行
pm2 start ecosystem.config.cjs

# ステータス確認
pm2 status

# ログ確認
pm2 logs
```

サービス：
- **openraven-core**（ポート 8741）— Python API サーバー
- **openraven-ui**（ポート 3002）— BFF + フロントエンド

### 4. 本番用フロントエンドのビルド

```bash
cd openraven-ui
bun run build          # dist/ にビルド
pm2 restart openraven-ui
```

ブラウザで http://localhost:3002 を開いてください。

### 代替方法：Docker Compose

```bash
docker compose up -d
```

これにより nginx（ポート 80）、PostgreSQL、Neo4j、API サーバー、UI サーバーが起動します。

## 開発

### テストの実行

```bash
# バックエンド
cd openraven && python3 -m pytest tests/ -v

# フロントエンド
cd openraven-ui && bun test tests/

# ベンチマーク（GEMINI_API_KEY が必要）
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### 翻訳の追加

翻訳ファイルは `openraven-ui/public/locales/{locale}/{namespace}.json` にあります。

翻訳を追加または更新するには：
1. 対象ロケールの JSON ファイルを編集する
2. キーは英語のソースファイルと同一に保つ
3. `{{interpolation}}` プレースホルダーを保持する
4. `bun run build` を実行して PM2 を再起動する

新しいロケールを追加するには：
1. `public/locales/` 以下に新しいディレクトリを作成（例：`de/`）
2. `en/` からすべての JSON ファイルをコピーし、値を翻訳する
3. `src/i18n.ts` の `SUPPORTED_LNGS` にロケールコードを追加する
4. `src/components/LanguageSelector.tsx` の `LOCALES` 配列にロケールを追加する
5. `openraven/src/openraven/auth/routes.py` の `SUPPORTED_LOCALES` にロケールを追加する
6. `openraven/src/openraven/graph/rag.py` の `LOCALE_NAMES` にロケール名を追加する

## API 概要

| メソッド | エンドポイント | 説明 |
|----------|---------------|------|
| `POST` | `/api/ask` | 知識ベースへのクエリ（locale パラメータ対応） |
| `POST` | `/api/ingest` | ドキュメントのアップロードと処理 |
| `GET` | `/api/graph` | 知識グラフデータの取得 |
| `GET` | `/api/wiki` | Wiki 記事の一覧 |
| `GET` | `/api/status` | 知識ベースの統計情報 |
| `GET` | `/api/discovery` | 自動生成インサイト |
| `POST` | `/api/courses/generate` | コースの生成 |
| `GET` | `/api/connectors/status` | コネクターのステータス |
| `PATCH` | `/api/auth/locale` | ユーザーのロケール設定を更新 |
| `GET` | `/api/audit` | 監査ログ（ページネーション対応） |

完全な API ドキュメントは http://localhost:8741/docs を参照してください（FastAPI 自動生成）。

## 技術スタック

| レイヤー | テクノロジー |
|----------|-------------|
| LLM | Gemini（デフォルト）、Ollama（ローカル） |
| 知識グラフ | LightRAG + NetworkX（ローカル）/ Neo4j（本番） |
| エンティティ抽出 | LangExtract |
| バックエンド | FastAPI + Uvicorn（Python 3.12） |
| フロントエンド | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono（Bun ランタイム） |
| データベース | SQLite（ローカル）/ PostgreSQL（本番） |
| 認証 | セッションベース + Google OAuth 2.0 |
| デプロイ | PM2 / Docker Compose |
| デザインシステム | Mistral Premium（温かみのあるアイボリー、オレンジアクセント、ゴールデンシャドウ） |

## 検証結果

- **Q&A 精度**：96.7%（Tier 1 の 30 問中 29 問正解）
- **引用精度**：100%（30/30 のソース引用）
- **LLM ジャッジスコア**：平均 4.6/5.0（Tier 2）
- **テストカバレッジ**：Python と TypeScript で 260+ テスト

## ライセンス

Apache License 2.0 — 詳細は [LICENSE](LICENSE) を参照してください。

Copyright 2026 Plusblocks Technology Limited.

## について

[Plusblocks Technology Limited](https://plusblocks.com) が開発。OpenRaven のコアエンジンはオープンソースです。クラウドおよびエンタープライズ機能（マルチテナント、SSO、課金）はマネージドサービスとして提供されます。
