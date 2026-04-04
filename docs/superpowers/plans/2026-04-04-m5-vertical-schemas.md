# M5 Vertical Schemas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add domain-specific extraction schemas for Taiwan legal documents and Taiwan financial reports, with a schema registry and UI selector. Users can select a schema when ingesting documents, or rely on enhanced auto-detection.

**Architecture:** Each schema is a Python dict with `prompt_description` and `examples` (using `langextract.core.data.ExampleData`/`Extraction`). A central `SCHEMA_REGISTRY` in `schemas/__init__.py` maps string IDs to schema dicts. The pipeline's `_detect_schema()` accepts an optional `schema_name` override. `POST /api/ingest` accepts a `schema` form field. The UI fetches available schemas from `GET /api/schemas` and renders a dropdown on the ingest page.

**Tech Stack:** Python 3.11+, FastAPI, langextract, Hono, React 19, Tailwind v4 (all existing)

---

## File Structure

### Python backend (openraven/)

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/extraction/schemas/__init__.py` | Modify | Schema registry: `SCHEMA_REGISTRY`, `get_schema()`, `list_schemas()` |
| `openraven/src/openraven/extraction/schemas/legal_taiwan.py` | Create | Legal-Taiwan schema definition |
| `openraven/src/openraven/extraction/schemas/finance_taiwan.py` | Create | Finance-Taiwan schema definition |
| `openraven/src/openraven/pipeline.py` | Modify | Accept `schema_name` in `_detect_schema()` and `add_files()` |
| `openraven/src/openraven/api/server.py` | Modify | Add `GET /api/schemas`, update `POST /api/ingest` to accept `schema` form field |
| `openraven/tests/test_extraction.py` | Modify | Schema registry tests, new schema validation tests |
| `openraven/tests/test_pipeline.py` | Modify | Auto-detect tests for new schemas, schema override test |
| `openraven/tests/test_api.py` | Modify | Tests for `GET /api/schemas`, schema param in ingest |

### TypeScript frontend (openraven-ui/)

| File | Action | Responsibility |
|---|---|---|
| `openraven-ui/server/index.ts` | Modify | Add proxy for `/api/schemas` |
| `openraven-ui/server/routes/ingest.ts` | Modify | Forward `schema` form field to core API |
| `openraven-ui/src/pages/IngestPage.tsx` | Modify | Schema dropdown above file upload area |

---

## Task 1: Schema Registry (`__init__.py`)

**Files:**
- Modify: `openraven/src/openraven/extraction/schemas/__init__.py`
- Modify: `openraven/tests/test_extraction.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_extraction.py`:

```python
from openraven.extraction.schemas import SCHEMA_REGISTRY, get_schema, list_schemas
from openraven.extraction.schemas.base import BASE_SCHEMA
from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
from openraven.extraction.schemas.finance import FINANCE_SCHEMA


def test_schema_registry_contains_all_schemas() -> None:
    assert "base" in SCHEMA_REGISTRY
    assert "engineering" in SCHEMA_REGISTRY
    assert "finance" in SCHEMA_REGISTRY
    assert "legal-taiwan" in SCHEMA_REGISTRY
    assert "finance-taiwan" in SCHEMA_REGISTRY
    assert len(SCHEMA_REGISTRY) == 5


def test_get_schema_returns_correct_schema() -> None:
    assert get_schema("base") is BASE_SCHEMA
    assert get_schema("engineering") is ENGINEERING_SCHEMA
    assert get_schema("finance") is FINANCE_SCHEMA


def test_get_schema_unknown_returns_base() -> None:
    result = get_schema("nonexistent")
    assert result is BASE_SCHEMA


def test_list_schemas_returns_all_with_metadata() -> None:
    schemas = list_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) == 5
    ids = [s["id"] for s in schemas]
    assert "base" in ids
    assert "legal-taiwan" in ids
    assert "finance-taiwan" in ids
    for s in schemas:
        assert "id" in s
        assert "name" in s
        assert "description" in s
        assert isinstance(s["name"], str)
        assert len(s["name"]) > 0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_extraction.py -v -k "registry or list_schemas or get_schema_returns or get_schema_unknown"`
Expected: `ImportError` because `SCHEMA_REGISTRY`, `get_schema`, `list_schemas` do not exist yet.

- [ ] **Step 3: Implement schema registry**

Write `openraven/src/openraven/extraction/schemas/__init__.py`:

```python
"""Schema registry for all extraction schemas."""

from openraven.extraction.schemas.base import BASE_SCHEMA
from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
from openraven.extraction.schemas.finance import FINANCE_SCHEMA
from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA
from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA

SCHEMA_REGISTRY: dict[str, dict] = {
    "base": BASE_SCHEMA,
    "engineering": ENGINEERING_SCHEMA,
    "finance": FINANCE_SCHEMA,
    "legal-taiwan": LEGAL_TAIWAN_SCHEMA,
    "finance-taiwan": FINANCE_TAIWAN_SCHEMA,
}


def get_schema(name: str) -> dict:
    """Return a schema by ID. Falls back to BASE_SCHEMA if not found."""
    return SCHEMA_REGISTRY.get(name, BASE_SCHEMA)


def list_schemas() -> list[dict]:
    """Return metadata for all registered schemas."""
    return [
        {
            "id": key,
            "name": schema.get("name", key),
            "description": schema.get("description", ""),
        }
        for key, schema in SCHEMA_REGISTRY.items()
    ]
```

Note: This will not pass yet because `legal_taiwan.py` and `finance_taiwan.py` do not exist. They are created in Tasks 2 and 3. After Task 3 completes, return here and verify all registry tests pass.

- [ ] **Step 4: Verify tests pass (after Tasks 2 and 3)**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_extraction.py -v -k "registry or list_schemas or get_schema_returns or get_schema_unknown"`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/extraction/schemas/__init__.py openraven/tests/test_extraction.py && git commit -m "feat(schemas): add schema registry with SCHEMA_REGISTRY, get_schema, list_schemas"
```

---

## Task 2: Legal-Taiwan Schema

**Files:**
- Create: `openraven/src/openraven/extraction/schemas/legal_taiwan.py`
- Modify: `openraven/tests/test_extraction.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_extraction.py`:

```python
def test_legal_taiwan_schema_structure() -> None:
    from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA

    assert "prompt_description" in LEGAL_TAIWAN_SCHEMA
    assert isinstance(LEGAL_TAIWAN_SCHEMA["prompt_description"], str)
    assert "examples" in LEGAL_TAIWAN_SCHEMA
    assert len(LEGAL_TAIWAN_SCHEMA["examples"]) >= 1
    assert "name" in LEGAL_TAIWAN_SCHEMA
    assert "description" in LEGAL_TAIWAN_SCHEMA


def test_legal_taiwan_schema_examples_use_langextract() -> None:
    from langextract.core.data import ExampleData

    from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA

    for example in LEGAL_TAIWAN_SCHEMA["examples"]:
        assert isinstance(example, ExampleData)
        assert len(example.extractions) >= 1


def test_legal_taiwan_schema_covers_required_entity_types() -> None:
    from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA

    prompt = LEGAL_TAIWAN_SCHEMA["prompt_description"]
    required_types = ["statute", "court_ruling", "legal_principle", "party", "judge", "court", "legal_document"]
    for entity_type in required_types:
        assert entity_type in prompt, f"Missing entity type '{entity_type}' in prompt_description"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_extraction.py -v -k "legal_taiwan"`
Expected: `ModuleNotFoundError` because `legal_taiwan.py` does not exist.

- [ ] **Step 3: Implement Legal-Taiwan schema**

Create `openraven/src/openraven/extraction/schemas/legal_taiwan.py`:

```python
"""Legal-Taiwan domain extraction schema for court rulings, statutes, and legal documents."""

from langextract.core.data import ExampleData, Extraction

LEGAL_TAIWAN_EXAMPLES = [
    ExampleData(
        text=(
            "最高法院 112 年度台上字第 1234 號民事判決，依民法第 184 條第 1 項前段，"
            "認定被告應負侵權行為損害賠償責任。原告主張其因被告之過失行為受有損害，"
            "法院審酌相關事證後，判決被告應賠償原告新台幣 500 萬元。"
        ),
        extractions=[
            Extraction(
                extraction_class="court_ruling",
                extraction_text="最高法院 112 年度台上字第 1234 號民事判決",
            ),
            Extraction(
                extraction_class="statute",
                extraction_text="民法第 184 條第 1 項前段",
            ),
            Extraction(
                extraction_class="legal_principle",
                extraction_text="侵權行為損害賠償責任",
            ),
            Extraction(
                extraction_class="party",
                extraction_text="原告",
            ),
            Extraction(
                extraction_class="party",
                extraction_text="被告",
            ),
            Extraction(
                extraction_class="court",
                extraction_text="最高法院",
            ),
        ],
    ),
    ExampleData(
        text=(
            "臺灣高等法院法官王大明審理本案，引用司法院大法官釋字第 748 號解釋，"
            "認為憲法保障人民之婚姻自由。本判決推翻地方法院之原判決。"
        ),
        extractions=[
            Extraction(
                extraction_class="judge",
                extraction_text="法官王大明",
            ),
            Extraction(
                extraction_class="court",
                extraction_text="臺灣高等法院",
            ),
            Extraction(
                extraction_class="legal_document",
                extraction_text="司法院大法官釋字第 748 號解釋",
            ),
            Extraction(
                extraction_class="legal_principle",
                extraction_text="憲法保障人民之婚姻自由",
            ),
        ],
    ),
]

LEGAL_TAIWAN_SCHEMA: dict = {
    "name": "Legal (Taiwan)",
    "description": "Optimized for Taiwan court rulings, statutes, and legal documents. Extracts statutes, court_ruling, legal_principle, party, judge, court, and legal_document entities.",
    "prompt_description": (
        "Extract knowledge entities from this Taiwan legal document. "
        "Focus on: statute references (法條, e.g. 民法第 X 條), "
        "court_ruling identifiers (判決, e.g. 案號), "
        "legal_principle concepts (法律原則, e.g. 侵權行為, 契約自由), "
        "party names (當事人 — 原告/被告), "
        "judge names (法官), "
        "court names (法院, e.g. 最高法院, 臺灣高等法院), "
        "and legal_document references (法律文件, e.g. 大法官解釋, 行政命令). "
        "Capture the relationships: cites (引用), interprets (解釋), "
        "overrules (推翻), applies_to (適用於), filed_by (提起). "
        "Preserve original Chinese terms alongside extracted entities."
    ),
    "examples": LEGAL_TAIWAN_EXAMPLES,
}
```

- [ ] **Step 4: Verify tests pass**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_extraction.py -v -k "legal_taiwan"`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/extraction/schemas/legal_taiwan.py openraven/tests/test_extraction.py && git commit -m "feat(schemas): add Legal-Taiwan extraction schema"
```

---

## Task 3: Finance-Taiwan Schema

**Files:**
- Create: `openraven/src/openraven/extraction/schemas/finance_taiwan.py`
- Modify: `openraven/tests/test_extraction.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_extraction.py`:

```python
def test_finance_taiwan_schema_structure() -> None:
    from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA

    assert "prompt_description" in FINANCE_TAIWAN_SCHEMA
    assert isinstance(FINANCE_TAIWAN_SCHEMA["prompt_description"], str)
    assert "examples" in FINANCE_TAIWAN_SCHEMA
    assert len(FINANCE_TAIWAN_SCHEMA["examples"]) >= 1
    assert "name" in FINANCE_TAIWAN_SCHEMA
    assert "description" in FINANCE_TAIWAN_SCHEMA


def test_finance_taiwan_schema_examples_use_langextract() -> None:
    from langextract.core.data import ExampleData

    from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA

    for example in FINANCE_TAIWAN_SCHEMA["examples"]:
        assert isinstance(example, ExampleData)
        assert len(example.extractions) >= 1


def test_finance_taiwan_schema_covers_required_entity_types() -> None:
    from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA

    prompt = FINANCE_TAIWAN_SCHEMA["prompt_description"]
    required_types = [
        "listed_company", "financial_metric", "regulatory_filing",
        "analyst_recommendation", "market_index", "industry_sector",
    ]
    for entity_type in required_types:
        assert entity_type in prompt, f"Missing entity type '{entity_type}' in prompt_description"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_extraction.py -v -k "finance_taiwan"`
Expected: `ModuleNotFoundError` because `finance_taiwan.py` does not exist.

- [ ] **Step 3: Implement Finance-Taiwan schema**

Create `openraven/src/openraven/extraction/schemas/finance_taiwan.py`:

```python
"""Finance-Taiwan domain extraction schema for TWSE filings and Taiwan financial reports."""

from langextract.core.data import ExampleData, Extraction

FINANCE_TAIWAN_EXAMPLES = [
    ExampleData(
        text=(
            "台積電（2330.TW）2026 年第一季營收達 8,692 億元，年增 35%。"
            "先進製程（7nm 以下）佔營收 73%。目前本益比為 22 倍，"
            "金管會要求上市公司於每季結束後 45 日內申報財務報告。"
        ),
        extractions=[
            Extraction(
                extraction_class="listed_company",
                extraction_text="台積電（2330.TW）",
            ),
            Extraction(
                extraction_class="financial_metric",
                extraction_text="營收達 8,692 億元，年增 35%",
            ),
            Extraction(
                extraction_class="financial_metric",
                extraction_text="本益比為 22 倍",
            ),
            Extraction(
                extraction_class="industry_sector",
                extraction_text="先進製程（7nm 以下）",
            ),
            Extraction(
                extraction_class="regulatory_filing",
                extraction_text="每季結束後 45 日內申報財務報告",
            ),
        ],
    ),
    ExampleData(
        text=(
            "外資分析師建議買進聯發科（2454.TW），目標價上調至 1,500 元。"
            "加權指數（TAIEX）本週收在 22,350 點，電子類股表現優於大盤。"
            "鴻海為蘋果主要供應商，受惠於 AI 伺服器訂單成長。"
        ),
        extractions=[
            Extraction(
                extraction_class="analyst_recommendation",
                extraction_text="外資分析師建議買進聯發科，目標價上調至 1,500 元",
            ),
            Extraction(
                extraction_class="listed_company",
                extraction_text="聯發科（2454.TW）",
            ),
            Extraction(
                extraction_class="market_index",
                extraction_text="加權指數（TAIEX）本週收在 22,350 點",
            ),
            Extraction(
                extraction_class="industry_sector",
                extraction_text="電子類股",
            ),
            Extraction(
                extraction_class="listed_company",
                extraction_text="鴻海",
            ),
        ],
    ),
]

FINANCE_TAIWAN_SCHEMA: dict = {
    "name": "Finance (Taiwan)",
    "description": "Optimized for TWSE filings, Taiwan financial reports, and Chinese financial terminology. Extracts listed_company, financial_metric, regulatory_filing, analyst_recommendation, market_index, and industry_sector entities.",
    "prompt_description": (
        "Extract knowledge entities from this Taiwan financial document. "
        "Focus on: listed_company names and ticker symbols (上市公司, e.g. 台積電 2330.TW), "
        "financial_metric values (財務指標 — 營收, 毛利率, 本益比, EPS, 殖利率), "
        "regulatory_filing references (監管申報 — 金管會, 證交所公告), "
        "analyst_recommendation opinions and price targets (分析師建議), "
        "market_index values (市場指數 — 加權指數, 櫃買指數), "
        "and industry_sector classifications (產業別 — 半導體, 電子, 金融). "
        "Capture the relationships: reports, competes_with, supplies_to, regulated_by, recommends. "
        "Preserve original Chinese terms alongside extracted entities. "
        "Capture specific numbers, dates, ticker symbols, and sources of claims."
    ),
    "examples": FINANCE_TAIWAN_EXAMPLES,
}
```

- [ ] **Step 4: Verify tests pass**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_extraction.py -v -k "finance_taiwan"`
Expected: All 3 tests PASS.

- [ ] **Step 5: Verify Task 1 registry tests now pass**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_extraction.py -v -k "registry or list_schemas or get_schema_returns or get_schema_unknown"`
Expected: All 4 registry tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/extraction/schemas/finance_taiwan.py openraven/tests/test_extraction.py && git commit -m "feat(schemas): add Finance-Taiwan extraction schema"
```

---

## Task 4: Pipeline + API Updates

**Files:**
- Modify: `openraven/src/openraven/pipeline.py`
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_pipeline.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing pipeline tests**

Add to `openraven/tests/test_pipeline.py`:

```python
def test_detect_schema_legal_taiwan_by_content() -> None:
    from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA
    schema = _detect_schema(Path("document.md"), text="本案判決依據民法第 184 條，原告主張被告侵權")
    assert schema == LEGAL_TAIWAN_SCHEMA


def test_detect_schema_finance_taiwan_by_content() -> None:
    from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA
    schema = _detect_schema(Path("report.md"), text="台積電本季營收創新高，本益比回升至 25 倍")
    assert schema == FINANCE_TAIWAN_SCHEMA


def test_detect_schema_with_override() -> None:
    from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA
    schema = _detect_schema(Path("generic.md"), text="just some text", schema_name="legal-taiwan")
    assert schema == LEGAL_TAIWAN_SCHEMA


def test_detect_schema_override_unknown_falls_back_to_base() -> None:
    from openraven.extraction.schemas.base import BASE_SCHEMA
    schema = _detect_schema(Path("generic.md"), text="", schema_name="nonexistent")
    assert schema == BASE_SCHEMA
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_pipeline.py -v -k "legal_taiwan or finance_taiwan or override"`
Expected: FAIL because `_detect_schema` does not accept `schema_name` parameter and does not detect Taiwan-specific content.

- [ ] **Step 3: Write failing API tests**

Add to `openraven/tests/test_api.py`:

```python
def test_schemas_endpoint(client: TestClient) -> None:
    response = client.get("/api/schemas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    ids = [s["id"] for s in data]
    assert "base" in ids
    assert "legal-taiwan" in ids
    assert "finance-taiwan" in ids
    for s in data:
        assert "id" in s
        assert "name" in s
        assert "description" in s
```

- [ ] **Step 4: Run to verify failure**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "schemas_endpoint"`
Expected: FAIL with 404 because `/api/schemas` endpoint does not exist.

- [ ] **Step 5: Update `_detect_schema()` in pipeline.py**

Modify `openraven/src/openraven/pipeline.py`. Replace the `_detect_schema` function:

```python
def _detect_schema(file_path: Path, text: str = "", schema_name: str | None = None) -> dict:
    if schema_name:
        from openraven.extraction.schemas import get_schema
        return get_schema(schema_name)

    name = file_path.name.lower()
    eng_keywords = ("adr", "architecture", "spec", "technical", "design", "system", "api", "infra")
    fin_keywords = (
        "research", "earnings", "financial", "valuation", "report", "investment", "analysis"
    )

    if any(kw in name for kw in eng_keywords):
        from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
        return ENGINEERING_SCHEMA
    elif any(kw in name for kw in fin_keywords):
        from openraven.extraction.schemas.finance import FINANCE_SCHEMA
        return FINANCE_SCHEMA

    sample = text[:2000].lower() if text else ""

    # Taiwan legal keywords — check before general finance to avoid misclassification
    legal_tw_content = ("判決", "法條", "原告", "被告", "法院", "民法", "刑法")
    if any(kw in sample for kw in legal_tw_content):
        from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA
        return LEGAL_TAIWAN_SCHEMA

    # Taiwan finance keywords — check before general finance for specificity
    fin_tw_content = ("上市", "營收", "毛利率", "本益比", "台積電", "金管會", "股價")
    if any(kw in sample for kw in fin_tw_content):
        from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA
        return FINANCE_TAIWAN_SCHEMA

    fin_content = (
        "revenue", "p/e", "earnings", "valuation", "market cap", "殖利率"
    )
    eng_content = (
        "architecture", "microservice", "api endpoint", "database", "deploy", "kubernetes", "docker"
    )

    if any(kw in sample for kw in fin_content):
        from openraven.extraction.schemas.finance import FINANCE_SCHEMA
        return FINANCE_SCHEMA
    elif any(kw in sample for kw in eng_content):
        from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
        return ENGINEERING_SCHEMA

    return BASE_SCHEMA
```

Note: Taiwan legal keywords are checked before Taiwan finance to avoid `法院` (court) matching in financial regulatory contexts. The `營收` and `本益比` keywords that were previously in the general finance content check are moved to `fin_tw_content` since they are Chinese-specific and should trigger the Taiwan finance schema.

- [ ] **Step 6: Update `add_files()` to accept `schema_name`**

Modify the `add_files` method signature in `openraven/src/openraven/pipeline.py`:

Change:
```python
async def add_files(self, paths: list[Path]) -> PipelineResult:
```
To:
```python
async def add_files(self, paths: list[Path], schema_name: str | None = None) -> PipelineResult:
```

And update the extraction stage where `_detect_schema` is called (inside the `for doc in parsed_docs` loop):

Change:
```python
schema = _detect_schema(doc.source_path, text=doc.text)
```
To:
```python
schema = _detect_schema(doc.source_path, text=doc.text, schema_name=schema_name)
```

- [ ] **Step 7: Add `GET /api/schemas` and update `POST /api/ingest` in server.py**

Add the schemas endpoint in `openraven/src/openraven/api/server.py`, after the `health` endpoint:

```python
@app.get("/api/schemas")
async def schemas():
    from openraven.extraction.schemas import list_schemas
    return list_schemas()
```

**IMPORTANT:** Add `Form` to the FastAPI imports at the top of `server.py`:
```python
from fastapi import BackgroundTasks, FastAPI, File, Form, Query, Request, UploadFile
```

Update the `ingest` endpoint to accept the `schema` form field. Replace:

```python
@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(...)):
    saved_paths: list[Path] = []
    config.ingestion_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        dest = config.ingestion_dir / upload.filename
        content = await upload.read()
        dest.write_bytes(content)
        saved_paths.append(dest)

    job_id = str(uuid.uuid4())[:8]
    job = IngestJob(job_id=job_id, files_total=len(saved_paths), stage="processing")
    ingest_jobs[job_id] = job

    result = await pipeline.add_files(saved_paths)
```

With:

```python
@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(...), schema: str | None = Form(default=None)):
    schema_name: str | None = schema if schema and schema != "auto" else None

    saved_paths: list[Path] = []
    config.ingestion_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        dest = config.ingestion_dir / upload.filename
        content = await upload.read()
        dest.write_bytes(content)
        saved_paths.append(dest)

    job_id = str(uuid.uuid4())[:8]
    job = IngestJob(job_id=job_id, files_total=len(saved_paths), stage="processing")
    ingest_jobs[job_id] = job

    result = await pipeline.add_files(saved_paths, schema_name=schema_name)
```

- [ ] **Step 8: Verify pipeline tests pass**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_pipeline.py -v`
Expected: All tests PASS including new auto-detect and override tests.

- [ ] **Step 9: Verify API tests pass**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "schemas_endpoint"`
Expected: PASS.

- [ ] **Step 10: Verify all existing tests still pass**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS (no regressions).

- [ ] **Step 11: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/pipeline.py openraven/src/openraven/api/server.py openraven/tests/test_pipeline.py openraven/tests/test_api.py && git commit -m "feat(api): add GET /api/schemas endpoint, accept schema param in pipeline and ingest"
```

---

## Task 5: IngestPage UI (Schema Dropdown)

**Files:**
- Modify: `openraven-ui/src/pages/IngestPage.tsx`
- Modify: `openraven-ui/server/index.ts`
- Modify: `openraven-ui/server/routes/ingest.ts`

- [ ] **Step 1: Add proxy for `/api/schemas` in Hono server**

In `openraven-ui/server/index.ts`, add after the existing config proxy block (before the static asset serving):

```typescript
// Proxy schemas endpoint to core API
app.get("/api/schemas", async (c) => {
  try {
    const res = await fetch(`${CORE_API_URL}/api/schemas`);
    return c.json(await res.json(), res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});
```

- [ ] **Step 2: Update ingest route to forward `schema` field**

In `openraven-ui/server/routes/ingest.ts`, update the handler to forward the `schema` form field:

Replace the entire file:

```typescript
import { Hono } from "hono";
import { ingestFiles } from "../services/core-client";

const ingestRouter = new Hono();

ingestRouter.post("/", async (c) => {
  const body = await c.req.formData();
  const coreForm = new FormData();
  for (const [key, value] of body.entries()) {
    if (value instanceof File) {
      coreForm.append("files", value);
    } else if (key === "schema") {
      coreForm.append("schema", value);
    }
  }
  try {
    const result = await ingestFiles(coreForm);
    return c.json(result);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return c.json({ error: `Core engine error: ${message}` }, 502);
  }
});

export default ingestRouter;
```

- [ ] **Step 3: Update IngestPage.tsx with schema dropdown**

Replace the entire `openraven-ui/src/pages/IngestPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import FileUploader from "../components/FileUploader";

interface IngestResult { files_processed: number; entities_extracted: number; articles_generated: number; errors: string[]; }
interface SchemaOption { id: string; name: string; description: string; }

const STAGE_LABELS: Record<string, string> = {
  uploading: "Uploading files...",
  processing: "Processing documents...",
  done: "Complete",
  error: "Error occurred",
};

export default function IngestPage() {
  const [result, setResult] = useState<IngestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [schemas, setSchemas] = useState<SchemaOption[]>([]);
  const [selectedSchema, setSelectedSchema] = useState("auto");

  useEffect(() => {
    fetch("/api/schemas")
      .then((res) => res.json())
      .then((data: SchemaOption[]) => setSchemas(data))
      .catch(() => setSchemas([]));
  }, []);

  async function handleUpload(files: File[]) {
    setLoading(true); setResult(null); setStage("uploading");
    const formData = new FormData();
    for (const file of files) formData.append("files", file);
    formData.append("schema", selectedSchema);
    try {
      setStage("processing");
      const res = await fetch("/api/ingest", { method: "POST", body: formData });
      const data = await res.json();
      setResult(data);
      setStage("done");
    } catch {
      setResult({ files_processed: 0, entities_extracted: 0, articles_generated: 0, errors: ["Failed to connect to the knowledge engine."] });
      setStage("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Add Documents</h1>

      <div className="mb-6">
        <label
          htmlFor="schema-select"
          className="block text-sm mb-2"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Extraction Schema
        </label>
        <select
          id="schema-select"
          value={selectedSchema}
          onChange={(e) => setSelectedSchema(e.target.value)}
          disabled={loading}
          className="w-full max-w-xs px-3 py-2 text-sm"
          style={{
            background: "var(--bg-surface)",
            color: "var(--color-text)",
            border: "1px solid var(--color-border)",
            borderRadius: "4px",
          }}
        >
          <option value="auto">Auto-detect (default)</option>
          {schemas.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {selectedSchema !== "auto" && (
          <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
            {schemas.find((s) => s.id === selectedSchema)?.description ?? ""}
          </p>
        )}
      </div>

      <FileUploader onUpload={handleUpload} disabled={loading} />
      {loading && stage && (
        <div className="mt-6">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--color-brand)", borderTopColor: "transparent" }} />
            <span style={{ color: "var(--color-text-secondary)" }}>{STAGE_LABELS[stage] ?? stage}</span>
          </div>
          <div className="mt-2 h-1 overflow-hidden" style={{ background: "var(--color-border)" }}>
            <div className="h-full animate-pulse" style={{ background: "var(--color-brand)", width: stage === "processing" ? "60%" : "20%" }} />
          </div>
        </div>
      )}
      {result && !loading && (
        <div className="mt-8 grid grid-cols-3 gap-6 text-center">
          {[
            { label: "Files processed", value: result.files_processed },
            { label: "Entities extracted", value: result.entities_extracted },
            { label: "Articles generated", value: result.articles_generated },
          ].map(stat => (
            <div key={stat.label} className="p-6" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
              <div className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>{stat.value}</div>
              <div className="text-sm mt-2" style={{ color: "var(--color-text-muted)" }}>{stat.label}</div>
            </div>
          ))}
          {result.errors.length > 0 && (
            <div className="col-span-3 text-sm" style={{ color: "var(--color-error)" }}>
              {result.errors.map((e, i) => <div key={i}>{e}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify UI builds**

Run: `cd /home/ubuntu/source/OpenRaven/openraven-ui && npx tsc --noEmit && npm run build`
Expected: No type errors, build succeeds.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/pages/IngestPage.tsx openraven-ui/server/index.ts openraven-ui/server/routes/ingest.ts && git commit -m "feat(ui): add schema dropdown to IngestPage with API proxy"
```

---

## Task 6: Schema Documentation + E2E Verification

**Files:**
- Modify: `openraven/src/openraven/extraction/schemas/base.py`
- Modify: `openraven/src/openraven/extraction/schemas/engineering.py`
- Modify: `openraven/src/openraven/extraction/schemas/finance.py`

- [ ] **Step 1: Add `name` and `description` to existing schemas**

The `list_schemas()` function reads `name` and `description` from each schema dict. The new schemas have these fields, but the existing three (`base.py`, `engineering.py`, `finance.py`) do not. Add them.

In `openraven/src/openraven/extraction/schemas/base.py`, replace the `BASE_SCHEMA` dict:

```python
BASE_SCHEMA: dict = {
    "name": "Base",
    "description": "Generic knowledge extraction for any document type. Extracts concepts, decisions, methods, technologies, people, organizations, and claims.",
    "prompt_description": (
        "Extract key knowledge entities from this document. "
        "Identify: concepts, decisions, methods/frameworks, technologies, "
        "people, organizations, and specific claims or findings. "
        "For each entity, capture the type and the surrounding context."
    ),
    "examples": BASE_EXAMPLES,
}
```

In `openraven/src/openraven/extraction/schemas/engineering.py`, replace the `ENGINEERING_SCHEMA` dict:

```python
ENGINEERING_SCHEMA: dict = {
    "name": "Engineering",
    "description": "Optimized for ADRs, tech specs, and architecture docs. Extracts architecture decisions, technology choices, trade-offs, performance metrics, and design patterns.",
    "prompt_description": (
        "Extract knowledge entities from this technical/engineering document. "
        "Focus on: architecture decisions (and their rationale), technology choices, "
        "trade-offs evaluated, performance metrics, system components, APIs, "
        "design patterns used, risks identified, and lessons learned. "
        "Capture WHY decisions were made, not just WHAT was decided."
    ),
    "examples": ENGINEERING_EXAMPLES,
}
```

In `openraven/src/openraven/extraction/schemas/finance.py`, replace the `FINANCE_SCHEMA` dict:

```python
FINANCE_SCHEMA: dict = {
    "name": "Finance",
    "description": "Optimized for financial research reports and earnings calls. Extracts companies, financial metrics, industry trends, analyst opinions, and risk factors.",
    "prompt_description": (
        "Extract knowledge entities from this financial/investment document. "
        "Focus on: companies and tickers, financial metrics (P/E, revenue, margins), "
        "industry trends, analyst opinions and price targets, risk factors, "
        "competitive dynamics, regulatory impacts, and valuation methodologies. "
        "Capture specific numbers, dates, and sources of claims."
    ),
    "examples": FINANCE_EXAMPLES,
}
```

- [ ] **Step 2: Write tests for name/description on all schemas**

Add to `openraven/tests/test_extraction.py`:

```python
def test_all_schemas_have_name_and_description() -> None:
    for schema_id, schema in SCHEMA_REGISTRY.items():
        assert "name" in schema, f"Schema '{schema_id}' missing 'name'"
        assert "description" in schema, f"Schema '{schema_id}' missing 'description'"
        assert isinstance(schema["name"], str) and len(schema["name"]) > 0
        assert isinstance(schema["description"], str) and len(schema["description"]) > 0


def test_all_schemas_have_prompt_and_examples() -> None:
    for schema_id, schema in SCHEMA_REGISTRY.items():
        assert "prompt_description" in schema, f"Schema '{schema_id}' missing 'prompt_description'"
        assert "examples" in schema, f"Schema '{schema_id}' missing 'examples'"
        assert len(schema["examples"]) >= 1, f"Schema '{schema_id}' has no examples"
```

- [ ] **Step 3: Run full test suite**

Run: `cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 4: E2E verification checklist**

Run each command and verify output:

```bash
# 1. Verify schema registry returns 5 schemas
cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -c "
from openraven.extraction.schemas import list_schemas, SCHEMA_REGISTRY
schemas = list_schemas()
assert len(schemas) == 5, f'Expected 5, got {len(schemas)}'
for s in schemas:
    print(f'{s[\"id\"]:20s} {s[\"name\"]:20s} {s[\"description\"][:60]}')
print('PASS: Schema registry OK')
"

# 2. Verify auto-detect picks Legal-Taiwan for legal content
cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -c "
from pathlib import Path
from openraven.pipeline import _detect_schema
from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA
schema = _detect_schema(Path('doc.md'), text='本案判決依據民法第 184 條')
assert schema is LEGAL_TAIWAN_SCHEMA
print('PASS: Legal-Taiwan auto-detect OK')
"

# 3. Verify auto-detect picks Finance-Taiwan for finance content
cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -c "
from pathlib import Path
from openraven.pipeline import _detect_schema
from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA
schema = _detect_schema(Path('doc.md'), text='台積電營收達 8692 億元')
assert schema is FINANCE_TAIWAN_SCHEMA
print('PASS: Finance-Taiwan auto-detect OK')
"

# 4. Verify schema override works
cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -c "
from pathlib import Path
from openraven.pipeline import _detect_schema
from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA
schema = _detect_schema(Path('random.md'), text='nothing special', schema_name='legal-taiwan')
assert schema is LEGAL_TAIWAN_SCHEMA
print('PASS: Schema override OK')
"

# 5. Verify UI builds
cd /home/ubuntu/source/OpenRaven/openraven-ui && npx tsc --noEmit && echo "PASS: UI type-check OK"
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/extraction/schemas/base.py openraven/src/openraven/extraction/schemas/engineering.py openraven/src/openraven/extraction/schemas/finance.py openraven/tests/test_extraction.py && git commit -m "feat(schemas): add name/description to all schemas, E2E verification tests"
```

---

## Test Summary

| Test | File | Task |
|---|---|---|
| `test_schema_registry_contains_all_schemas` | `test_extraction.py` | 1 |
| `test_get_schema_returns_correct_schema` | `test_extraction.py` | 1 |
| `test_get_schema_unknown_returns_base` | `test_extraction.py` | 1 |
| `test_list_schemas_returns_all_with_metadata` | `test_extraction.py` | 1 |
| `test_legal_taiwan_schema_structure` | `test_extraction.py` | 2 |
| `test_legal_taiwan_schema_examples_use_langextract` | `test_extraction.py` | 2 |
| `test_legal_taiwan_schema_covers_required_entity_types` | `test_extraction.py` | 2 |
| `test_finance_taiwan_schema_structure` | `test_extraction.py` | 3 |
| `test_finance_taiwan_schema_examples_use_langextract` | `test_extraction.py` | 3 |
| `test_finance_taiwan_schema_covers_required_entity_types` | `test_extraction.py` | 3 |
| `test_detect_schema_legal_taiwan_by_content` | `test_pipeline.py` | 4 |
| `test_detect_schema_finance_taiwan_by_content` | `test_pipeline.py` | 4 |
| `test_detect_schema_with_override` | `test_pipeline.py` | 4 |
| `test_detect_schema_override_unknown_falls_back_to_base` | `test_pipeline.py` | 4 |
| `test_schemas_endpoint` | `test_api.py` | 4 |
| `test_all_schemas_have_name_and_description` | `test_extraction.py` | 6 |
| `test_all_schemas_have_prompt_and_examples` | `test_extraction.py` | 6 |

**Total new tests: 17**
