# OpenRaven

**문서에서 전문 지식을 자동으로 추출, 정리, 활성화하는 AI 기반 지식 자산 플랫폼.**

**다른 언어로 읽기：**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | **한국어** | [Français](README.fr.md) | [Español](README.es.md) | [Nederlands](README.nl.md) | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven은 산재된 문서——PDF, DOCX, 프레젠테이션, 회의 녹취록, Notion 내보내기——를 구조화된 쿼리 가능한 지식 그래프로 변환합니다. 자연어로 질문하고, 개념 간의 연결을 탐색하고, Wiki 문서를 자동 생성하며, 지식 베이스로부터 코스를 구축하세요.

## 왜 OpenRaven인가?

사람들이 직무나 조직을 바꿀 때 기관 지식은 사라집니다. 연구에 따르면 기관 지식의 42%는 오직 사람들의 머릿속에만 존재합니다(IDC). OpenRaven은 그 지식을 캡처하고 구조화하여 언제나 접근 가능하고, 검색 가능하며, 공유 가능하게 합니다.

## 기능

### 지식 엔진
- **스마트 수집** — PDF, DOCX, PPTX, XLSX, Markdown, 이미지(AI 비전), 또는 Notion/Obsidian 내보내기를 업로드. 엔티티와 관계가 자동으로 추출됩니다.
- **지식 그래프** — 엔티티 유형, 연결 강도, 검색으로 필터링할 수 있는 인터랙티브 힘 지향 그래프 시각화. GraphML 또는 PNG로 내보내기 가능.
- **자연어 Q&A** — 6가지 쿼리 모드(mix, local, global, hybrid, keyword, direct LLM)를 사용하여 지식 베이스에 질문. 응답에는 출처 인용이 포함됩니다.
- **자동 생성 Wiki** — 추출된 엔티티와 관계로부터 문서가 자동 생성됩니다.
- **코스 생성** — 커리큘럼 계획, 챕터 생성, 인터랙티브 HTML 내보내기를 포함한 구조화된 코스를 지식 베이스로부터 생성.
- **발견 인사이트** — 지식 주제, 클러스터, 격차, 트렌드를 자동 분석.

### 커넥터
- **Google Drive** — 문서 가져오기(PDF, Docs, Sheets, Slides)
- **Gmail** — 이메일을 지식 베이스 항목으로 가져오기
- **Google Meet** — Drive API를 통해 회의 녹취록 가져오기
- **Otter.ai** — API 키를 통해 회의 녹취록 가져오기

### 수직 Schema
- **Base** — 범용 엔티티 추출(기본값)
- **Engineering** — 기술 아키텍처, 시스템, API
- **Finance** — 기업, 재무 지표, 규정
- **Legal (Taiwan)** — 법령, 법원 판결, 법적 원칙(번체 중국어)
- **Finance (Taiwan)** — TWSE 상장 기업, 재무 지표(번체 중국어)

### 다국어 지원

OpenRaven은 자동 브라우저 감지와 수동 전환으로 12개 언어를 지원합니다：

| 언어 | 코드 | 언어 | 코드 |
|------|------|------|------|
| 영어 | `en` | 이탈리아어 | `it` |
| 번체 중국어 | `zh-TW` | 베트남어 | `vi` |
| 간체 중국어 | `zh-CN` | 태국어 | `th` |
| 일본어 | `ja` | 러시아어 | `ru` |
| 한국어 | `ko` | 프랑스어 | `fr` |
| 스페인어 | `es` | 네덜란드어 | `nl` |

**작동 방식：**
- 첫 방문 시 브라우저/OS 로케일을 자동 감지(대체: 영어)
- 사용자는 내비게이션 바의 언어 선택기로 전환 가능
- 설정은 localStorage(즉시)와 사용자 프로필(기기 간 동기화)에 저장
- LLM 응답은 사용자가 선택한 언어와 일치
- Wiki 문서와 코스 콘텐츠는 원본 문서 언어를 따름
- 지식 그래프 레이블은 영어 유지

### 엔터프라이즈 기능(관리형 SaaS)
- **멀티 테넌트 격리** — 테넌트별 독립 지식 베이스와 별도 스토리지
- **인증** — 이메일/비밀번호 + Google OAuth 2.0(세션 관리 포함)
- **감사 로그** — 모든 사용자 작업 추적, CSV 내보내기 지원
- **팀 관리** — 워크스페이스에 멤버 초대
- **Neo4j 그래프 백엔드** — 프로덕션 등급 그래프 스토리지(선택 사항, 기본값: NetworkX)
- **Docker Compose 배포** — nginx, PostgreSQL, Neo4j를 포함한 원커맨드 배포

## 아키텍처

```
openraven/                  # Python 백엔드(FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # FastAPI 앱 팩토리, 모든 API 엔드포인트
    pipeline.py             # 핵심 파이프라인: 수집, 쿼리, 그래프, Wiki, 코스
    graph/rag.py            # LightRAG 래퍼(로케일 인식 쿼리)
    auth/                   # 인증 시스템(세션, OAuth, 비밀번호 재설정)
    audit/                  # 감사 로그 모듈
  alembic/                  # 데이터베이스 마이그레이션
  tests/                    # 159+ 개의 Python 테스트

openraven-ui/               # TypeScript 프론트엔드(React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # i18next 초기화(12개 로케일, 11개 네임스페이스)
    App.tsx                 # 루트 컴포넌트(라우트 + 내비게이션 바)
    pages/                  # 14개의 페이지 컴포넌트
    components/             # LanguageSelector, GraphViewer, ChatMessage 등
    hooks/useAuth.tsx       # 로케일 동기화가 포함된 인증 Context
  public/locales/           # 132개의 번역 JSON 파일(12개 로케일 × 11개 네임스페이스)
  server/index.ts           # Hono BFF(API 프록시 + 정적 파일 서빙)
  tests/                    # 46개의 Bun 테스트

ecosystem.config.cjs        # PM2 배포 설정
```

## 빠른 시작

### 사전 요구 사항
- Python 3.12+
- Bun 1.0+
- Node.js 20+(PM2용)

### 1. 클론 및 설치

```bash
git clone https://github.com/nickhealthy/OpenRaven.git
cd OpenRaven

# 백엔드
cd openraven
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 프론트엔드
cd ../openraven-ui
bun install
```

### 2. 설정

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # 필수: LLM 제공자
WORKING_DIR=/path/to/knowledge-data     # 지식 베이스 데이터 저장 위치

# 선택 사항: 관리형 SaaS 기능 활성화
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. PM2로 실행

```bash
# 프로젝트 루트에서 실행
pm2 start ecosystem.config.cjs

# 상태 확인
pm2 status

# 로그 확인
pm2 logs
```

서비스：
- **openraven-core**(포트 8741) — Python API 서버
- **openraven-ui**(포트 3002) — BFF + 프론트엔드

### 4. 프론트엔드 프로덕션 빌드

```bash
cd openraven-ui
bun run build          # dist/ 에 빌드
pm2 restart openraven-ui
```

브라우저에서 http://localhost:3002 을 여세요.

### 대안: Docker Compose

```bash
docker compose up -d
```

이 명령은 nginx(포트 80), PostgreSQL, Neo4j, API 서버, UI 서버를 시작합니다.

## 개발

### 테스트 실행

```bash
# 백엔드
cd openraven && python3 -m pytest tests/ -v

# 프론트엔드
cd openraven-ui && bun test tests/

# 벤치마크(GEMINI_API_KEY 필요)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### 번역 추가

번역 파일은 `openraven-ui/public/locales/{locale}/{namespace}.json` 에 있습니다.

번역을 추가하거나 업데이트하려면：
1. 대상 로케일의 JSON 파일을 편집하세요
2. 키는 영어 원본 파일과 동일하게 유지하세요
3. `{{interpolation}}` 플레이스홀더를 보존하세요
4. `bun run build` 를 실행하고 PM2를 재시작하세요

새 로케일을 추가하려면：
1. `public/locales/` 아래에 새 디렉토리를 생성하세요(예: `de/`)
2. `en/` 의 모든 JSON 파일을 복사하고 값을 번역하세요
3. `src/i18n.ts` 의 `SUPPORTED_LNGS` 에 로케일 코드를 추가하세요
4. `src/components/LanguageSelector.tsx` 의 `LOCALES` 배열에 로케일을 추가하세요
5. `openraven/src/openraven/auth/routes.py` 의 `SUPPORTED_LOCALES` 에 로케일을 추가하세요
6. `openraven/src/openraven/graph/rag.py` 의 `LOCALE_NAMES` 에 로케일 이름을 추가하세요

## API 개요

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/ask` | 지식 베이스 쿼리(locale 매개변수 지원) |
| `POST` | `/api/ingest` | 문서 업로드 및 처리 |
| `GET` | `/api/graph` | 지식 그래프 데이터 가져오기 |
| `GET` | `/api/wiki` | Wiki 문서 목록 |
| `GET` | `/api/status` | 지식 베이스 통계 |
| `GET` | `/api/discovery` | 자동 생성 인사이트 |
| `POST` | `/api/courses/generate` | 코스 생성 |
| `GET` | `/api/connectors/status` | 커넥터 상태 |
| `PATCH` | `/api/auth/locale` | 사용자 로케일 설정 업데이트 |
| `GET` | `/api/audit` | 감사 로그(페이지네이션) |

전체 API 문서는 http://localhost:8741/docs 를 참조하세요(FastAPI 자동 생성).

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| LLM | Gemini(기본값), Ollama(로컬) |
| 지식 그래프 | LightRAG + NetworkX(로컬) / Neo4j(프로덕션) |
| 엔티티 추출 | LangExtract |
| 백엔드 | FastAPI + Uvicorn(Python 3.12) |
| 프론트엔드 | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono(Bun 런타임) |
| 데이터베이스 | SQLite(로컬) / PostgreSQL(프로덕션) |
| 인증 | 세션 기반 + Google OAuth 2.0 |
| 배포 | PM2 / Docker Compose |
| 디자인 시스템 | Mistral Premium(따뜻한 아이보리, 오렌지 액센트, 골든 섀도우) |

## 검증 결과

- **Q&A 정확도**: 96.7%(Tier 1 30문제 중 29문제 정답)
- **인용 정확도**: 100%(30/30 출처 인용)
- **LLM 심사 점수**: 평균 4.6/5.0(Tier 2)
- **테스트 커버리지**: Python과 TypeScript에서 260+ 테스트

## 라이선스

Apache License 2.0 — 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

Copyright 2026 Plusblocks Technology Limited.

## 소개

[Plusblocks Technology Limited](https://plusblocks.com)가 개발. OpenRaven의 핵심 엔진은 오픈소스입니다. 클라우드 및 엔터프라이즈 기능(멀티 테넌트, SSO, 청구)은 관리형 서비스로 제공됩니다.
