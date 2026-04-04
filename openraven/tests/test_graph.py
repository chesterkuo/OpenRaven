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


def test_get_graph_data_empty(graph: RavenGraph) -> None:
    data = graph.get_graph_data()
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["is_truncated"] is False


def test_get_graph_data_with_graphml(graph: RavenGraph) -> None:
    import networkx as nx

    # Create a small test graph — use "description" (not "entity_description")
    # because LightRAG's operate.py stores the attribute as "description"
    g = nx.Graph()
    g.add_node("KAFKA", entity_type="technology", description="Event streaming platform", file_path="adr.md")
    g.add_node("EDA", entity_type="concept", description="Event-driven architecture", file_path="adr.md")
    g.add_edge("KAFKA", "EDA", weight="1.0", description="Kafka implements EDA", keywords="streaming,events")

    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    nx.write_graphml(g, str(graph_file))

    data = graph.get_graph_data()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["is_truncated"] is False

    node_ids = {n["id"] for n in data["nodes"]}
    assert "KAFKA" in node_ids
    assert "EDA" in node_ids

    # Verify properties use LightRAG's actual attribute names
    kafka_node = next(n for n in data["nodes"] if n["id"] == "KAFKA")
    assert kafka_node["properties"]["description"] == "Event streaming platform"
    assert kafka_node["properties"]["entity_type"] == "technology"
    assert kafka_node["labels"] == ["technology"]

    edge = data["edges"][0]
    assert edge["source"] in ("KAFKA", "EDA")
    assert edge["target"] in ("KAFKA", "EDA")
    assert "description" in edge["properties"]


def test_get_graph_data_respects_max_nodes(graph: RavenGraph) -> None:
    import networkx as nx

    g = nx.Graph()
    for i in range(10):
        g.add_node(f"NODE_{i}", entity_type="concept", description=f"Node {i}")
    # Connect all to NODE_0 so it has highest degree
    for i in range(1, 10):
        g.add_edge("NODE_0", f"NODE_{i}", weight="1.0", description=f"Edge to {i}")

    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    nx.write_graphml(g, str(graph_file))

    data = graph.get_graph_data(max_nodes=3)
    assert len(data["nodes"]) == 3
    assert data["is_truncated"] is True
    # NODE_0 should be included (highest degree)
    node_ids = {n["id"] for n in data["nodes"]}
    assert "NODE_0" in node_ids


def test_get_graph_data_handles_corrupt_file(graph: RavenGraph) -> None:
    """Race condition: GraphML partially written during ingestion."""
    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    graph_file.write_text("<graphml><graph><broken")

    data = graph.get_graph_data()
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["is_truncated"] is False
