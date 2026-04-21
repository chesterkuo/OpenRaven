from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import openai

logger = logging.getLogger(__name__)


@dataclass
class WikiArticle:
    title: str
    summary: str
    sections: list[dict]  # [{"heading": str, "content": str}]
    sources: list[dict]   # [{"document": str, "excerpt": str, "char_start": int, "char_end": int}]
    related_topics: list[str]
    confidence_score: float  # 0.0 - 1.0


COMPILE_PROMPT = """\
You are a knowledge compiler. Given a topic and retrieved context from a personal knowledge graph,
write a structured wiki article.

Rules:
1. Every factual claim MUST cite a source using [Source: document_name] format
2. If information is inferred rather than directly stated, mark it as [Inferred]
3. Include a confidence score (0.0-1.0) based on how well-sourced the article is
4. Write in the same language as the majority of the source material
5. Be concise but thorough

Topic: {topic}

Retrieved Context:
{context}

Source Documents:
{sources}

Respond in this exact JSON format:
{{
  "summary": "2-3 sentence summary",
  "sections": [
    {{"heading": "section name", "content": "section content with [Source: doc] citations"}}
  ],
  "related_topics": ["topic1", "topic2"],
  "confidence_score": 0.85
}}
"""


async def compile_article(
    topic: str, context: str, sources: list[dict],
    api_key: str, model: str = "claude-sonnet-4-6",
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> WikiArticle:
    source_text = "\n".join(
        f"- {s['document']} (chars {s.get('char_start', '?')}-{s.get('char_end', '?')}): "
        f"{s.get('excerpt', '')}"
        for s in sources
    )
    prompt = COMPILE_PROMPT.format(topic=topic, context=context, sources=source_text)

    client = openai.AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)
    response = await client.chat.completions.create(
        model=model, max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    data = json.loads(content.strip())

    return WikiArticle(
        title=topic, summary=data["summary"], sections=data["sections"],
        sources=sources, related_topics=data.get("related_topics", []),
        confidence_score=data.get("confidence_score", 0.5),
    )


def render_article_markdown(article: WikiArticle) -> str:
    lines = [
        f"# {article.title}", "",
        f"**Confidence:** {article.confidence_score:.0%}", "",
        article.summary, "",
    ]

    for section in article.sections:
        lines.append(f"## {section['heading']}")
        lines.append("")
        lines.append(section["content"])
        lines.append("")

    if article.related_topics:
        lines.append("## Related Topics")
        lines.append("")
        for topic in article.related_topics:
            lines.append(f"- [[{topic}]]")
        lines.append("")

    if article.sources:
        lines.append("## Sources")
        lines.append("")
        for src in article.sources:
            excerpt = src.get("excerpt", "")[:80]
            char_s = src.get('char_start', '?')
            char_e = src.get('char_end', '?')
            lines.append(f"- **{src['document']}** (chars {char_s}-{char_e}): _{excerpt}_")
        lines.append("")

    return "\n".join(lines)


def _render_entity_from_graph(
    name: str,
    graph,
    sources_map: dict,
) -> WikiArticle:
    """Build a WikiArticle from graph data alone — no LLM calls.

    Pulls the entity's node + 1-hop neighbors via RavenGraph.get_subgraph,
    synthesizes a summary from the node's description attribute, and uses
    pre-collected source excerpts from sources_map.
    """
    subgraph = graph.get_subgraph(entities=[name], max_nodes=30)
    nodes = subgraph.get("nodes", [])

    seed = next((n for n in nodes if n.get("is_seed") or n.get("id") == name), None)
    description = ""
    entity_type = "Concept"
    if seed:
        props = seed.get("properties", {}) or {}
        description = props.get("description", "") or ""
        entity_type = props.get("entity_type") or (seed.get("labels", ["Concept"]) or ["Concept"])[0]

    related = [n["id"] for n in nodes if n.get("id") != name]

    sources = sources_map.get(name, [])

    summary = description if description else name
    sections = [
        {"heading": "Type", "content": entity_type},
    ]
    if sources:
        excerpts = "\n\n".join(f"> {s.get('excerpt', '').strip()}" for s in sources if s.get("excerpt"))
        if excerpts:
            sections.append({"heading": "Source Excerpts", "content": excerpts})

    return WikiArticle(
        title=name,
        summary=summary,
        sections=sections,
        sources=sources,
        related_topics=related,
        confidence_score=1.0,
    )


async def compile_wiki_for_graph(
    graph, entities: list[str], sources_map: dict, api_key: str,
    output_dir: Path, model: str = "claude-sonnet-4-6", max_concurrent: int = 5,
    on_progress: callable | None = None,
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> list[WikiArticle]:
    import asyncio

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(max_concurrent)
    completed_count = 0

    async def compile_one(entity_name: str) -> WikiArticle | None:
        nonlocal completed_count
        async with semaphore:
            try:
                context = await graph.query(
                    f"Tell me everything about: {entity_name}", mode="local"
                )
                sources = sources_map.get(entity_name, [])
                article = await compile_article(
                    topic=entity_name, context=context, sources=sources,
                    api_key=api_key, model=model, base_url=base_url,
                )
                safe_name = entity_name.replace("/", "_").replace(" ", "_").lower()
                md_path = output_dir / f"{safe_name}.md"
                md_path.write_text(render_article_markdown(article), encoding="utf-8")
                completed_count += 1
                if on_progress:
                    on_progress(completed_count, len(entities))
                return article
            except Exception as e:
                logger.warning(f"Failed to compile wiki for '{entity_name}': {e}")
                completed_count += 1
                return None

    results = await asyncio.gather(*[compile_one(name) for name in entities])
    return [a for a in results if a is not None]
