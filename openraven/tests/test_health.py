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
