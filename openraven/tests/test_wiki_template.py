from unittest.mock import MagicMock

from openraven.wiki.compiler import _render_entity_from_graph, WikiArticle


def _fake_subgraph(seed: str, neighbors: list[tuple[str, str]]) -> dict:
    """Build a fake get_subgraph() payload: seed + 1-hop neighbors as a name/type list."""
    return {
        "nodes": [
            {"id": seed, "labels": ["Concept"], "properties": {"entity_type": "Concept", "description": f"About {seed}"}, "is_seed": True},
            *[
                {"id": n, "labels": [t], "properties": {"entity_type": t}, "is_seed": False}
                for n, t in neighbors
            ],
        ],
        "edges": [{"id": f"{seed}-{n}", "type": "DIRECTED", "source": seed, "target": n, "properties": {}} for n, _ in neighbors],
    }


def test_render_entity_from_graph_basic():
    graph = MagicMock()
    graph.get_subgraph.return_value = _fake_subgraph("Kafka", [("Streaming", "Concept"), ("Confluent", "Organization")])
    sources_map = {"Kafka": [{"document": "arch.md", "excerpt": "Kafka is a distributed log", "char_start": 100, "char_end": 130}]}

    article = _render_entity_from_graph("Kafka", graph, sources_map)

    assert isinstance(article, WikiArticle)
    assert article.title == "Kafka"
    assert "Kafka" in article.summary
    assert {"Streaming", "Confluent"} == set(article.related_topics)
    assert article.sources[0]["document"] == "arch.md"
    assert article.confidence_score == 1.0   # template render = full confidence


def test_render_entity_from_graph_missing_node():
    """Entity not in graph yet (e.g. LangExtract found it but LightRAG hasn't inserted) → empty-but-valid article."""
    graph = MagicMock()
    graph.get_subgraph.return_value = {"nodes": [], "edges": []}

    article = _render_entity_from_graph("Ghost Entity", graph, {})

    assert article.title == "Ghost Entity"
    assert article.related_topics == []
    assert article.sources == []
    assert article.summary == "Ghost Entity"


def test_render_entity_from_graph_uses_node_description():
    """If the LightRAG node has a description attribute, use it as the summary."""
    graph = MagicMock()
    graph.get_subgraph.return_value = {
        "nodes": [{"id": "X", "labels": ["Concept"], "properties": {"description": "A specific concept about data ingestion."}, "is_seed": True}],
        "edges": [],
    }
    article = _render_entity_from_graph("X", graph, {})
    assert article.summary == "A specific concept about data ingestion."
