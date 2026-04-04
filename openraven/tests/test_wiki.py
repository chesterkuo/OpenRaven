from __future__ import annotations

from openraven.wiki.compiler import WikiArticle, render_article_markdown


def test_wiki_article_structure() -> None:
    article = WikiArticle(
        title="Event-Driven Architecture",
        summary="A software design pattern using events for communication.",
        sections=[
            {"heading": "Overview", "content": "Events decouple producers from consumers."},
            {"heading": "Trade-offs", "content": "Added complexity but better scalability."},
        ],
        sources=[
            {
                "document": "adr-001.md",
                "excerpt": "We chose event-driven...",
                "char_start": 100,
                "char_end": 140,
            },
        ],
        related_topics=["Apache Kafka", "CQRS", "Microservices"],
        confidence_score=0.85,
    )
    assert article.title == "Event-Driven Architecture"
    assert len(article.sections) == 2
    assert len(article.sources) == 1
    assert article.confidence_score == 0.85


def test_render_article_markdown() -> None:
    article = WikiArticle(
        title="Kafka",
        summary="Distributed streaming platform.",
        sections=[{"heading": "Usage", "content": "Used for real-time pipelines."}],
        sources=[{
            "document": "notes.md",
            "excerpt": "Kafka is used...",
            "char_start": 0,
            "char_end": 20,
        }],
        related_topics=["Event Streaming"],
        confidence_score=0.9,
    )
    md = render_article_markdown(article)
    assert "# Kafka" in md
    assert "Distributed streaming platform" in md
    assert "Usage" in md
    assert "notes.md" in md
    assert "Related" in md
    assert "[[Event Streaming]]" in md
