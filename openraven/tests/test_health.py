from __future__ import annotations

from openraven.health.reporter import (
    HealthReport,
    format_health_report,
    generate_health_report,
)


def test_health_report_structure() -> None:
    report = HealthReport(
        total_files=10, total_entities=127, total_connections=340,
        topic_count=8, top_topics=["Architecture", "Testing", "Deployment"],
        languages_detected=["en", "zh-TW"], confidence_avg=0.82,
    )
    assert report.total_files == 10
    assert report.topic_count == 8


def test_generate_health_report_from_stats() -> None:
    file_records = [
        {"path": "/a.md", "status": "compiled", "char_count": 1000},
        {"path": "/b.pdf", "status": "compiled", "char_count": 5000},
    ]
    graph_stats = {"nodes": 45, "edges": 120, "topics": ["A", "B", "C"]}
    report = generate_health_report(file_records, graph_stats)
    assert report.total_files == 2
    assert report.total_entities == 45
    assert report.total_connections == 120
    assert report.topic_count == 3


def test_format_health_report() -> None:
    report = HealthReport(
        total_files=5, total_entities=50, total_connections=100,
        topic_count=3, top_topics=["A", "B", "C"],
    )
    text = format_health_report(report)
    assert "Files processed:" in text
    assert "50" in text
    assert "Knowledge Base Health Report" in text


# --- HealthMaintainer tests ---

from openraven.health.maintainer import HealthMaintainer, HealthInsight


def test_detect_stale_files(tmp_path) -> None:
    from openraven.storage import MetadataStore, FileRecord
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/old.md", hash="a", format="markdown", char_count=50, status="graphed"))
    store._conn.execute("UPDATE files SET updated_at = datetime('now', '-60 days') WHERE path = '/old.md'")
    store._conn.commit()

    maintainer = HealthMaintainer(store=store, graph=None, config=None)
    insights = maintainer.detect_staleness(days=30)
    assert len(insights) == 1
    assert insights[0].insight_type == "stale"
    assert "old.md" in insights[0].description
    store.close()


def test_no_stale_files(tmp_path) -> None:
    from openraven.storage import MetadataStore, FileRecord
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/new.md", hash="a", format="markdown", char_count=50, status="graphed"))

    maintainer = HealthMaintainer(store=store, graph=None, config=None)
    insights = maintainer.detect_staleness(days=30)
    assert len(insights) == 0
    store.close()


def test_detect_new_connections(tmp_path) -> None:
    import networkx as nx
    from openraven.graph.rag import RavenGraph

    graph = RavenGraph.create_lazy(working_dir=tmp_path / "lightrag_data")
    g = nx.Graph()
    # Create two clusters connected by a single bridge node
    g.add_node("A", entity_type="concept", description="Concept A")
    g.add_node("B", entity_type="concept", description="Concept B")
    g.add_node("BRIDGE", entity_type="concept", description="Bridge concept")
    g.add_node("C", entity_type="concept", description="Concept C")
    g.add_node("D", entity_type="concept", description="Concept D")
    g.add_edge("A", "B", weight="1.0")
    g.add_edge("A", "BRIDGE", weight="1.0")
    g.add_edge("BRIDGE", "C", weight="1.0")
    g.add_edge("C", "D", weight="1.0")
    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    nx.write_graphml(g, str(graph_file))

    maintainer = HealthMaintainer(store=None, graph=graph, config=None)
    insights = maintainer.detect_bridge_connections()
    assert len(insights) >= 1
    assert any("BRIDGE" in i.description for i in insights)


def test_health_insight_structure() -> None:
    insight = HealthInsight(
        insight_type="stale", title="Stale files", description="2 files not updated in 30+ days",
        related_entities=["/old.md"], severity="warning",
    )
    assert insight.insight_type == "stale"
    assert insight.severity == "warning"
