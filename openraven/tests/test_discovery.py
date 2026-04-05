from __future__ import annotations

from openraven.discovery.analyzer import DiscoveryInsight, analyze_themes


def test_discovery_insight_structure() -> None:
    insight = DiscoveryInsight(
        insight_type="theme", title="Event-Driven Architecture",
        description="Found 5 documents discussing event-driven patterns",
        related_entities=["Kafka", "RabbitMQ", "CQRS"], document_count=5,
    )
    assert insight.insight_type == "theme"
    assert len(insight.related_entities) == 3


def test_analyze_themes_from_graph_stats() -> None:
    graph_stats = {
        "nodes": 45, "edges": 120,
        "topics": ["Event-Driven Architecture", "Apache Kafka", "Microservices",
                    "CQRS", "Database Sharding", "PostgreSQL", "Redis",
                    "REST API", "GraphQL", "gRPC"],
    }
    insights = analyze_themes(graph_stats)
    assert len(insights) > 0
    assert all(isinstance(i, DiscoveryInsight) for i in insights)


def test_analyze_themes_empty_graph() -> None:
    insights = analyze_themes({"nodes": 0, "edges": 0, "topics": []})
    assert len(insights) == 0


def test_analyzer_does_not_import_anthropic() -> None:
    """The old analyzer used anthropic client which was never configured. Verify it's gone."""
    import inspect
    import openraven.discovery.analyzer as mod
    source = inspect.getsource(mod)
    assert "import anthropic" not in source


def test_analyze_themes_produces_coverage_insight() -> None:
    graph_stats = {
        "nodes": 45, "edges": 120,
        "topics": ["Kafka", "Microservices", "CQRS", "PostgreSQL", "Redis"],
        "entity_types": {"technology": 20, "concept": 15, "person": 5, "organization": 5},
        "top_connected": [("Kafka", 12), ("Microservices", 10), ("PostgreSQL", 8)],
        "components": 3,
    }
    insights = analyze_themes(graph_stats)
    types = [i.insight_type for i in insights]
    assert "theme" in types
    assert len(insights) >= 3


def test_analyze_themes_produces_connections_insight() -> None:
    graph_stats = {
        "nodes": 30, "edges": 80,
        "topics": ["AI", "Machine Learning", "Neural Networks"],
        "entity_types": {"concept": 25, "technology": 5},
        "top_connected": [("AI", 15), ("Machine Learning", 12), ("Neural Networks", 8)],
        "components": 1,
    }
    insights = analyze_themes(graph_stats)
    descriptions = " ".join(i.description for i in insights)
    assert "AI" in descriptions or "Machine Learning" in descriptions


def test_analyze_themes_produces_gap_insight() -> None:
    graph_stats = {
        "nodes": 20, "edges": 15,
        "topics": ["Topic A", "Topic B"],
        "entity_types": {"concept": 20},
        "top_connected": [("Topic A", 5)],
        "components": 5,
    }
    insights = analyze_themes(graph_stats)
    types = [i.insight_type for i in insights]
    assert "gap" in types


def test_analyze_themes_backward_compatible() -> None:
    graph_stats = {"nodes": 10, "edges": 5, "topics": ["A", "B", "C"]}
    insights = analyze_themes(graph_stats)
    assert len(insights) >= 1


def test_get_detailed_stats_shape(tmp_path) -> None:
    import networkx as nx
    from openraven.graph.rag import RavenGraph

    graph_file = tmp_path / "lightrag_data" / "graph_chunk_entity_relation.graphml"
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    G = nx.Graph()
    G.add_node("Kafka", entity_type="technology")
    G.add_node("Microservices", entity_type="concept")
    G.add_node("Isolated", entity_type="concept")
    G.add_edge("Kafka", "Microservices")
    nx.write_graphml(G, str(graph_file))

    rg = RavenGraph(working_dir=tmp_path / "lightrag_data")
    stats = rg.get_detailed_stats()

    assert "entity_types" in stats
    assert "top_connected" in stats
    assert "components" in stats
    assert stats["entity_types"]["technology"] == 1
    assert stats["entity_types"]["concept"] == 2
    assert stats["components"] == 2
