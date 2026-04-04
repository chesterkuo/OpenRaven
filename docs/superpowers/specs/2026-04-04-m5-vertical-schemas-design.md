# M5: Vertical Schemas (Legal + Finance Taiwan) — Design Spec

**Goal:** Add domain-specific extraction schemas for Taiwan legal documents and Taiwan financial reports, with a schema selector in the UI. Designed for extensibility so a community schema marketplace can be added later.

**Strategy:** Bundled schemas shipped with the product. Each schema defines entity types, relation types, and extraction prompts optimized for a specific domain. Users select the schema when ingesting documents. Auto-detection enhanced with new domain keywords.

---

## 1. Schema Architecture

### Current State

Three schemas exist in `openraven/src/openraven/extraction/schemas/`:
- `base.py` — generic entities (concept, person, organization, etc.)
- `engineering.py` — ADR, API, microservice, deployment entities
- `finance.py` — company, financial_metric, analyst entities

Each schema is a Python dict with `entity_types`, `relation_types`, and `extraction_prompt`. The pipeline's `_detect_schema()` function selects a schema based on filename/content keywords.

### New Schemas

**Legal-Taiwan** (`legal_taiwan.py`):
- Entity types: `statute` (法條), `court_ruling` (判決), `legal_principle` (法律原則), `party` (當事人), `judge` (法官), `court` (法院), `legal_document` (法律文件)
- Relation types: `cites` (引用), `interprets` (解釋), `overrules` (推翻), `applies_to` (適用於), `filed_by` (提起)
- Extraction prompt: Optimized for Taiwan court ruling format (案號, 主文, 理由, etc.)
- Auto-detect keywords: 判決, 法條, 原告, 被告, 法院, 民法, 刑法

**Finance-Taiwan** (`finance_taiwan.py`):
- Entity types: `listed_company` (上市公司), `financial_metric` (財務指標), `regulatory_filing` (監管申報), `analyst_recommendation` (分析師建議), `market_index` (市場指數), `industry_sector` (產業別)
- Relation types: `reports`, `competes_with`, `supplies_to`, `regulated_by`, `recommends`
- Extraction prompt: Optimized for TWSE filings, Chinese financial terminology
- Auto-detect keywords: 上市, 營收, 毛利率, 本益比, 台積電, 金管會, 股價

---

## 2. Schema Registry

Modify `openraven/src/openraven/extraction/schemas/__init__.py` to maintain a registry of all available schemas:

```python
SCHEMA_REGISTRY = {
    "base": BASE_SCHEMA,
    "engineering": ENGINEERING_SCHEMA,
    "finance": FINANCE_SCHEMA,
    "legal-taiwan": LEGAL_TAIWAN_SCHEMA,
    "finance-taiwan": FINANCE_TAIWAN_SCHEMA,
}

def get_schema(name: str) -> dict:
    return SCHEMA_REGISTRY.get(name, BASE_SCHEMA)

def list_schemas() -> list[dict]:
    return [{"id": k, "name": v.get("name", k), "description": v.get("description", "")} for k, v in SCHEMA_REGISTRY.items()]
```

---

## 3. Schema Selection in Pipeline

Update `pipeline.py` `_detect_schema()` to:
1. Accept an optional `schema_name` parameter (user-selected)
2. If provided, use that schema directly via `get_schema(schema_name)`
3. If not provided, run existing auto-detection with enhanced keywords for new schemas

Update `add_files()` to accept optional `schema` parameter.

Update `POST /api/ingest` to accept optional `schema` field in the request.

---

## 4. Schema Selector UI

Update `IngestPage.tsx`:
- Add schema dropdown above the file upload area
- Fetch available schemas from `GET /api/schemas` endpoint
- Options: "Auto-detect (default)", "Engineering", "Finance", "Legal (Taiwan)", "Finance (Taiwan)", "Base"
- Selected schema passed to `/api/ingest` as form field

New endpoint: `GET /api/schemas` — returns list of available schemas with id, name, description.

---

## 5. Schema Documentation

Create documentation for community contributors:

```
openraven-schemas/
├── legal-taiwan/
│   └── README.md    # What it extracts, what docs it works with, examples
├── finance-taiwan/
│   └── README.md    # What it extracts, what docs it works with, examples
└── CONTRIBUTING.md  # How to create a new schema
```

---

## 6. File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/extraction/schemas/legal_taiwan.py` | Create | Legal-Taiwan schema definition |
| `openraven/src/openraven/extraction/schemas/finance_taiwan.py` | Create | Finance-Taiwan schema definition |
| `openraven/src/openraven/extraction/schemas/__init__.py` | Modify | Schema registry (SCHEMA_REGISTRY, get_schema, list_schemas) |
| `openraven/src/openraven/pipeline.py` | Modify | Accept schema parameter in add_files and _detect_schema |
| `openraven/src/openraven/api/server.py` | Modify | Add GET /api/schemas, update POST /api/ingest |
| `openraven/tests/test_extraction.py` | Modify | Schema registry tests, new schema validation |
| `openraven-ui/src/pages/IngestPage.tsx` | Modify | Schema dropdown |
| `openraven-ui/server/index.ts` | Modify | Proxy for /api/schemas |
| `openraven-schemas/legal-taiwan/README.md` | Create | Documentation |
| `openraven-schemas/finance-taiwan/README.md` | Create | Documentation |
| `openraven-schemas/CONTRIBUTING.md` | Create | Schema contribution guide |

---

## 7. Tests

- Schema registry: list_schemas returns all 5, get_schema returns correct schema
- Legal-Taiwan: schema has required entity_types and relation_types
- Finance-Taiwan: schema has required entity_types
- Auto-detect: Taiwan legal keywords trigger legal-taiwan schema
- Auto-detect: Taiwan finance keywords trigger finance-taiwan schema
- API: GET /api/schemas returns list, POST /api/ingest accepts schema field
- ~12 new tests

---

## 8. Extensibility for Future Marketplace

Schema format is designed to be portable:
- Each schema is a self-contained Python dict (could be serialized as JSON/YAML)
- `SCHEMA_REGISTRY` is the single point of registration
- Adding a new schema = create a .py file + register in __init__.py
- Future marketplace: schemas distributed as JSON files, loaded dynamically from a `~/.openraven/schemas/` directory
