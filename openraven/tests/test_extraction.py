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
