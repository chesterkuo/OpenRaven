from __future__ import annotations

from pathlib import Path

from openraven.config import RavenConfig
from openraven.pipeline import PipelineResult, RavenPipeline, _detect_schema


def test_pipeline_initializes(config: RavenConfig) -> None:
    pipeline = RavenPipeline(config)
    assert pipeline.config == config


def test_pipeline_result_structure() -> None:
    result = PipelineResult(
        files_processed=5, entities_extracted=42, articles_generated=8, errors=[]
    )
    assert result.files_processed == 5
    assert result.has_errors is False


def test_pipeline_result_with_errors() -> None:
    result = PipelineResult(
        files_processed=5, entities_extracted=42, articles_generated=8,
        errors=["Failed to parse file.xlsx"],
    )
    assert result.has_errors is True


def test_detect_schema_engineering() -> None:
    from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
    schema = _detect_schema(Path("adr-001-database.md"))
    assert schema == ENGINEERING_SCHEMA


def test_detect_schema_finance_by_name() -> None:
    from openraven.extraction.schemas.finance import FINANCE_SCHEMA
    schema = _detect_schema(Path("research-report-q1.md"))
    assert schema == FINANCE_SCHEMA


def test_detect_schema_finance_by_content() -> None:
    from openraven.extraction.schemas.finance import FINANCE_SCHEMA
    schema = _detect_schema(Path("q1-2026.md"), text="The revenue grew 25% and P/E ratio is 22x")
    assert schema == FINANCE_SCHEMA


def test_detect_schema_default() -> None:
    from openraven.extraction.schemas.base import BASE_SCHEMA
    schema = _detect_schema(Path("notes.md"))
    assert schema == BASE_SCHEMA


def test_pipeline_passes_provider_to_graph(config: RavenConfig) -> None:
    config.llm_provider = "ollama"
    config.llm_model = "llama3.2:3b"
    config.embedding_model = "nomic-embed-text"
    pipeline = RavenPipeline(config)
    # Pipeline should construct without error even with ollama provider
    assert pipeline.graph is not None


def test_detect_schema_legal_taiwan_by_content() -> None:
    from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA
    schema = _detect_schema(Path("document.md"), text="本案判決依據民法第 184 條，原告主張被告侵權")
    assert schema == LEGAL_TAIWAN_SCHEMA


def test_detect_schema_finance_taiwan_by_content() -> None:
    from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA
    schema = _detect_schema(Path("quarterly.md"), text="台積電本季營收創新高，本益比回升至 25 倍")
    assert schema == FINANCE_TAIWAN_SCHEMA


def test_detect_schema_with_override() -> None:
    from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA
    schema = _detect_schema(Path("generic.md"), text="just some text", schema_name="legal-taiwan")
    assert schema == LEGAL_TAIWAN_SCHEMA


def test_detect_schema_override_unknown_falls_back_to_base() -> None:
    from openraven.extraction.schemas.base import BASE_SCHEMA
    schema = _detect_schema(Path("generic.md"), text="", schema_name="nonexistent")
    assert schema == BASE_SCHEMA


def test_pipeline_health_report(config: RavenConfig) -> None:
    pipeline = RavenPipeline(config)
    report = pipeline.get_health_report()
    assert report.total_files == 0
    assert report.total_entities == 0
