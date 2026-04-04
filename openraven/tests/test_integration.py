"""Integration tests — require GEMINI_API_KEY env var.

Run with: GEMINI_API_KEY=... pytest tests/test_integration.py -v
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — skipping integration tests",
)


@pytest.fixture
def integration_config(tmp_path: Path) -> RavenConfig:
    return RavenConfig(
        working_dir=tmp_path / "integration_kb",
        llm_model="gemini-2.5-flash",
        wiki_llm_model="gemini-2.5-flash",
    )


@pytest.fixture
def pipeline(integration_config: RavenConfig) -> RavenPipeline:
    return RavenPipeline(integration_config)


async def test_pipeline_ingests_and_extracts_english(
    pipeline: RavenPipeline, tmp_path: Path,
) -> None:
    """Test that pipeline ingests a file and extracts entities."""
    doc = tmp_path / "adr-001.md"
    doc.write_text("""\
# ADR-001: Use PostgreSQL for Primary Database

## Status: Accepted

## Context
We need a primary database for the user service. Evaluated PostgreSQL, MySQL, and MongoDB.

## Decision
Use PostgreSQL 16 with pgvector extension for future vector search needs.

## Consequences
- Positive: Strong typing, excellent query planner, JSONB flexibility
- Negative: Slightly higher memory usage than MySQL
""")

    result = await pipeline.add_files([doc])
    assert result.files_processed == 1
    assert result.entities_extracted > 0


async def test_pipeline_ingests_and_extracts_chinese(
    pipeline: RavenPipeline, tmp_path: Path,
) -> None:
    """Test that pipeline ingests a Chinese finance document."""
    doc = tmp_path / "research-tsmc.md"
    doc.write_text("""\
# 台積電（2330）投資研究筆記

## 基本面分析
台積電 2026 年第一季營收達 8,692 億元，年增 35%。
先進製程（7nm 以下）佔營收 73%。

## 風險評估
地緣政治風險仍是最大不確定因素。
""")

    result = await pipeline.add_files([doc])
    assert result.files_processed == 1
    assert result.entities_extracted > 0


async def test_pipeline_health_report_after_ingestion(
    pipeline: RavenPipeline, tmp_path: Path,
) -> None:
    """Test that health report shows processed files after ingestion."""
    doc = tmp_path / "test.md"
    doc.write_text("Apache Kafka is used for event-driven architecture. PostgreSQL for storage.")

    await pipeline.add_files([doc])
    report = pipeline.get_health_report()
    assert report.total_files >= 1
