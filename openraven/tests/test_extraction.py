from __future__ import annotations

from openraven.extraction.extractor import (
    Entity,
    ExtractionResult,
    enrich_text_for_rag,
)
from openraven.extraction.schemas.base import BASE_SCHEMA


def test_extraction_result_structure() -> None:
    entity = Entity(
        name="Event-Driven Architecture",
        entity_type="concept",
        context="We chose event-driven architecture using Apache Kafka",
        source_document="test.md",
        char_start=100,
        char_end=150,
    )
    result = ExtractionResult(entities=[entity], source_document="test.md")
    assert len(result.entities) == 1
    assert result.entities[0].name == "Event-Driven Architecture"
    assert result.entities[0].char_start == 100


def test_enrich_text_with_entities() -> None:
    entity = Entity(
        name="Kafka",
        entity_type="technology",
        context="using Apache Kafka for messaging",
        source_document="test.md",
        char_start=0,
        char_end=31,
    )
    result = ExtractionResult(entities=[entity], source_document="test.md")
    enriched = enrich_text_for_rag("using Apache Kafka for messaging", result)
    assert "Kafka" in enriched
    assert "[ENTITY:" in enriched


def test_enrich_empty_entities() -> None:
    result = ExtractionResult(entities=[], source_document="test.md")
    text = "some text"
    assert enrich_text_for_rag(text, result) == text


def test_base_schema_structure() -> None:
    assert "prompt_description" in BASE_SCHEMA
    assert isinstance(BASE_SCHEMA["prompt_description"], str)
    assert "examples" in BASE_SCHEMA


from openraven.extraction.schemas import SCHEMA_REGISTRY, get_schema, list_schemas
from openraven.extraction.schemas.base import BASE_SCHEMA as _BASE_SCHEMA
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
    assert get_schema("base") is _BASE_SCHEMA
    assert get_schema("engineering") is ENGINEERING_SCHEMA
    assert get_schema("finance") is FINANCE_SCHEMA


def test_get_schema_unknown_returns_base() -> None:
    result = get_schema("nonexistent")
    assert result is _BASE_SCHEMA


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
