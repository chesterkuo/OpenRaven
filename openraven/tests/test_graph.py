from __future__ import annotations

import os
from pathlib import Path

import pytest

from openraven.graph.rag import RavenGraph


@pytest.fixture
def graph(tmp_working_dir: Path) -> RavenGraph:
    return RavenGraph.create_lazy(working_dir=tmp_working_dir / "lightrag_data")


def test_raven_graph_initializes(graph: RavenGraph) -> None:
    assert graph is not None
    assert graph.working_dir.exists()


@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set",
)
async def test_insert_and_query(tmp_working_dir: Path) -> None:
    graph = await RavenGraph.create(working_dir=tmp_working_dir / "lightrag_int")
    text = "Apache Kafka is a distributed event streaming platform."
    await graph.insert(text, source="test.md")
    assert any(graph.working_dir.iterdir())


def test_export_graphml(graph: RavenGraph, tmp_path: Path) -> None:
    output = tmp_path / "graph.graphml"
    graph.export_graphml(output)
    assert output.exists()


def test_get_stats_empty(graph: RavenGraph) -> None:
    stats = graph.get_stats()
    assert stats["nodes"] == 0
    assert stats["edges"] == 0
    assert stats["topics"] == []
