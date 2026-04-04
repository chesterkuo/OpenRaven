from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HealthReport:
    total_files: int
    total_entities: int
    total_connections: int
    topic_count: int
    top_topics: list[str] = field(default_factory=list)
    languages_detected: list[str] = field(default_factory=list)
    confidence_avg: float = 0.0


def generate_health_report(
    file_records: list[dict], graph_stats: dict, wiki_articles: list | None = None,
) -> HealthReport:
    total_files = len(file_records)
    total_entities = graph_stats.get("nodes", 0)
    total_connections = graph_stats.get("edges", 0)
    topics = graph_stats.get("topics", [])

    confidence_avg = 0.0
    if wiki_articles:
        scores = [a.confidence_score for a in wiki_articles if hasattr(a, "confidence_score")]
        if scores:
            confidence_avg = sum(scores) / len(scores)

    return HealthReport(
        total_files=total_files, total_entities=total_entities,
        total_connections=total_connections, topic_count=len(topics),
        top_topics=topics[:10], confidence_avg=confidence_avg,
    )


def format_health_report(report: HealthReport) -> str:
    lines = [
        "=== Knowledge Base Health Report ===", "",
        f"Files processed:    {report.total_files}",
        f"Concepts extracted: {report.total_entities}",
        f"Connections found:  {report.total_connections}",
        f"Topic areas:        {report.topic_count}", "",
    ]
    if report.top_topics:
        lines.append("Top topics:")
        for topic in report.top_topics[:10]:
            lines.append(f"  - {topic}")
        lines.append("")
    if report.confidence_avg > 0:
        lines.append(f"Average confidence: {report.confidence_avg:.0%}")
        lines.append("")
    lines.append("====================================")
    return "\n".join(lines)
