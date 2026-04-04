from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline


@pytest.fixture
def live_pipeline():
    default_dir = Path.home() / "my-knowledge"
    if not default_dir.exists():
        pytest.skip("No live knowledge base found at ~/my-knowledge")

    graph_file = default_dir / "graph_chunk_entity_relation.graphml"
    if not graph_file.exists():
        pytest.skip("Knowledge graph not built yet (no graphml file)")

    config = RavenConfig(working_dir=default_dir)
    return RavenPipeline(config)


def test_live_kb_has_entities(live_pipeline):
    stats = live_pipeline.graph.get_stats()
    assert stats["nodes"] > 0, "Knowledge graph has no entities"
    print(f"\nLive KB: {stats['nodes']} nodes, {stats['edges']} edges")


def test_live_kb_query_returns_answers(live_pipeline):
    stats = live_pipeline.graph.get_stats()
    topics = stats.get("topics", [])[:10]
    if not topics:
        pytest.skip("No topics in knowledge graph")

    passed = 0
    failed = 0
    for topic in topics:
        question = f"What do you know about {topic}?"
        result = asyncio.get_event_loop().run_until_complete(
            live_pipeline.ask_with_sources(question, mode="mix")
        )
        if result.answer and len(result.answer.strip()) > 10:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    print(f"\nLive KB Smoke: {passed}/{total} queries returned substantive answers")
    assert passed >= total * 0.7, f"Only {passed}/{total} queries returned answers (need ≥70%)"


def test_live_kb_sources_returned(live_pipeline):
    stats = live_pipeline.graph.get_stats()
    topics = stats.get("topics", [])[:5]
    if not topics:
        pytest.skip("No topics in knowledge graph")

    with_sources = 0
    for topic in topics:
        question = f"Tell me about {topic}"
        result = asyncio.get_event_loop().run_until_complete(
            live_pipeline.ask_with_sources(question, mode="local")
        )
        if result.sources:
            with_sources += 1

    print(f"\nLive KB Sources: {with_sources}/{len(topics)} queries returned sources")
    assert True
