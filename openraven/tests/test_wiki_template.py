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


import asyncio
from pathlib import Path


def test_compile_wiki_for_graph_writes_md_files_without_llm(tmp_path: Path):
    """compile_wiki_for_graph must write one .md per entity using only graph data (no LLM client)."""
    from openraven.wiki.compiler import compile_wiki_for_graph

    graph = MagicMock()
    graph.get_subgraph.side_effect = lambda entities, max_nodes: _fake_subgraph(
        entities[0],
        [("Related One", "Concept")] if entities[0] == "Alpha" else [],
    )
    sources_map = {"Alpha": [{"document": "doc.md", "excerpt": "Alpha excerpt", "char_start": 0, "char_end": 13}]}

    articles = asyncio.run(compile_wiki_for_graph(
        graph=graph,
        entities=["Alpha", "Beta"],
        sources_map=sources_map,
        api_key="unused",          # MUST be ignored by the new path
        output_dir=tmp_path,
    ))

    assert {a.title for a in articles} == {"Alpha", "Beta"}
    assert (tmp_path / "alpha.md").exists()
    assert (tmp_path / "beta.md").exists()
    alpha_md = (tmp_path / "alpha.md").read_text(encoding="utf-8")
    assert "Alpha" in alpha_md
    assert "Related One" in alpha_md


def test_compile_wiki_for_graph_handles_oversized_entity_name(tmp_path: Path):
    """Mis-extracted 'entity' names can be whole paragraphs that overflow the
    255-byte ext4 filename limit. The writer must truncate safely and still
    emit a unique file."""
    from openraven.wiki.compiler import compile_wiki_for_graph, _safe_filename

    graph = MagicMock()
    graph.get_subgraph.return_value = _fake_subgraph("X", [])

    # 120 CJK chars × 3 bytes = 360 bytes; over the 255-byte filename limit.
    huge_name = "部署選項雲端快速上線彈性擴充託管基礎設施按用量計費地端資料隱私法規合規" * 4

    articles = asyncio.run(compile_wiki_for_graph(
        graph=graph, entities=[huge_name], sources_map={},
        api_key="unused", output_dir=tmp_path,
    ))

    # One file written, name short enough to be valid
    written = list(tmp_path.glob("*.md"))
    assert len(written) == 1
    assert len(written[0].name.encode("utf-8")) <= 255
    # Article is returned with the original (untruncated) title
    assert articles[0].title == huge_name
    # And _safe_filename is deterministic for the same input
    assert _safe_filename(huge_name) == _safe_filename(huge_name)
