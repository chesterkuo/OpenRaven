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
