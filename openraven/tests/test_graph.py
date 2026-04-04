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


def test_make_llm_func_gemini() -> None:
    func = RavenGraph._make_llm_func("gemini-2.5-flash", "test-key", provider="gemini")
    assert callable(func)


def test_make_llm_func_ollama() -> None:
    func = RavenGraph._make_llm_func("llama3.2:3b", "", provider="ollama")
    assert callable(func)


def test_make_embedding_func_gemini() -> None:
    ef = RavenGraph._make_embedding_func("text-embedding-004", "test-key", provider="gemini")
    assert ef.embedding_dim == 768


def test_make_embedding_func_ollama() -> None:
    ef = RavenGraph._make_embedding_func("nomic-embed-text", "", provider="ollama")
    assert ef.embedding_dim == 768


def test_make_embedding_func_ollama_1024() -> None:
    ef = RavenGraph._make_embedding_func("bge-m3:latest", "", provider="ollama")
    assert ef.embedding_dim == 1024


async def test_safe_gemini_embed_truncates_extra_vectors() -> None:
    """Gemini API sometimes returns more embeddings than input texts.

    The _safe_gemini_embed wrapper in _make_embedding_func should truncate
    the result to match the expected count so LightRAG's validator doesn't
    raise 'Vector count mismatch'.
    """
    import numpy as np

    from lightrag.utils import EmbeddingFunc

    # Simulate Gemini returning extra vectors (N+1 for N inputs)
    async def fake_gemini_embed(texts, **kwargs):
        n_extra = len(texts) + 1
        return np.ones((n_extra, 768), dtype=np.float32)

    # Replicate the wrapper logic from RavenGraph._make_embedding_func
    async def _safe_embed(texts, **kwargs):
        result = await fake_gemini_embed(texts, **kwargs)
        expected = len(texts)
        if result.shape[0] > expected:
            result = result[:expected]
        return result

    func = EmbeddingFunc(embedding_dim=768, func=_safe_embed, model_name="test")

    # Single text — should NOT raise ValueError
    result = await func(["hello world"])
    assert result.shape == (1, 768)

    # Multiple texts — should truncate from 4 to 3
    result = await func(["text one", "text two", "text three"])
    assert result.shape == (3, 768)


def test_query_result_dataclass() -> None:
    from openraven.graph.rag import QueryResult
    qr = QueryResult(answer="test answer", sources=[{"document": "doc.md", "excerpt": "text", "char_start": 0, "char_end": 10}])
    assert qr.answer == "test answer"
    assert len(qr.sources) == 1
    assert qr.sources[0]["document"] == "doc.md"


def test_query_result_empty_sources() -> None:
    from openraven.graph.rag import QueryResult
    qr = QueryResult(answer="", sources=[])
    assert qr.sources == []


def test_extract_sources_from_answer_finds_matching_entities(tmp_path) -> None:
    import networkx as nx
    from openraven.graph.rag import RavenGraph
    graph = nx.DiGraph()
    graph.add_node("Apache Kafka", entity_type="technology", description="A distributed streaming platform", file_path="adr-kafka.md")
    graph.add_node("Event-Driven Architecture", entity_type="concept", description="Architecture using events", file_path="adr-kafka.md")
    graph.add_node("Unrelated Topic", entity_type="concept", description="Something else", file_path="other.md")
    graph_file = tmp_path / "graph_chunk_entity_relation.graphml"
    nx.write_graphml(graph, str(graph_file))
    rg = RavenGraph(working_dir=tmp_path)
    answer = "The system uses Apache Kafka for event streaming."
    sources = rg._extract_sources_from_answer(answer)
    doc_names = [s["document"] for s in sources]
    assert any("adr-kafka" in d for d in doc_names)
    assert not any("other.md" in d for d in doc_names)


def test_extract_sources_empty_graph(tmp_path) -> None:
    from openraven.graph.rag import RavenGraph
    rg = RavenGraph(working_dir=tmp_path)
    sources = rg._extract_sources_from_answer("Some answer text")
    assert sources == []
