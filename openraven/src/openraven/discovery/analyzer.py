from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import openai

logger = logging.getLogger(__name__)

_DISCOVER_PROMPT_TMPL = (
    "Based on this knowledge base overview, generate 3-5 proactive discovery insights.\n\n"
    "Overview:\n{overview}\n\n"
    'Return JSON array:\n[\n  {{\n'
    '    "insight_type": "theme|cluster|gap|trend",\n'
    '    "title": "short title",\n'
    '    "description": "1-2 sentence description of what was found",\n'
    '    "related_entities": ["entity1", "entity2"]\n'
    "  }}\n]"
)


@dataclass
class DiscoveryInsight:
    insight_type: str  # "theme", "cluster", "gap", "trend"
    title: str
    description: str
    related_entities: list[str] = field(default_factory=list)
    document_count: int = 0


def analyze_themes(graph_stats: dict) -> list[DiscoveryInsight]:
    """Generate discovery insights from graph statistics."""
    insights: list[DiscoveryInsight] = []
    topics = graph_stats.get("topics", [])
    node_count = graph_stats.get("nodes", 0)
    edge_count = graph_stats.get("edges", 0)
    entity_types = graph_stats.get("entity_types", {})
    top_connected = graph_stats.get("top_connected", [])
    components = graph_stats.get("components", 0)

    if node_count == 0:
        return insights

    # 1. Knowledge coverage overview
    if entity_types:
        type_summary = ", ".join(
            f"{count} {etype}s" for etype, count in
            sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:4]
        )
        insights.append(DiscoveryInsight(
            insight_type="theme",
            title="Knowledge Coverage",
            description=(
                f"Your knowledge base contains {node_count} concepts with "
                f"{edge_count} connections: {type_summary}."
            ),
            related_entities=topics[:10],
            document_count=node_count,
        ))
    else:
        insights.append(DiscoveryInsight(
            insight_type="theme",
            title="Knowledge Base Overview",
            description=(
                f"Your knowledge base contains {node_count} concepts "
                f"with {edge_count} connections between them."
            ),
            related_entities=topics[:10],
            document_count=node_count,
        ))

    # 2. Top knowledge areas
    if len(topics) >= 3:
        insights.append(DiscoveryInsight(
            insight_type="cluster",
            title="Top Knowledge Areas",
            description=f"Found {len(topics)} distinct topics in your knowledge base.",
            related_entities=topics[:10],
            document_count=len(topics),
        ))

    # 3. Most connected concepts (hub nodes)
    if top_connected:
        hub_names = [name for name, deg in top_connected[:3]]
        hub_desc = ", ".join(hub_names)
        max_deg = top_connected[0][1] if top_connected else 0
        insights.append(DiscoveryInsight(
            insight_type="trend",
            title="Key Concepts Discovered",
            description=(
                f"Your most connected concepts are {hub_desc}. "
                f"The top concept links to {max_deg} other ideas."
            ),
            related_entities=[name for name, _ in top_connected[:5]],
            document_count=len(top_connected),
        ))

    # 4. Knowledge gaps (many disconnected components)
    if components > 3:
        insights.append(DiscoveryInsight(
            insight_type="gap",
            title="Knowledge Gaps Detected",
            description=(
                f"Found {components} separate topic clusters with no connections between them. "
                f"Adding more documents could help bridge these gaps."
            ),
            related_entities=topics[:5],
            document_count=components,
        ))

    return insights


async def discover_insights_with_llm(
    graph, api_key: str, model: str = "gemini-2.5-flash",
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> list[DiscoveryInsight]:
    """Generate discovery insights using LLM analysis of the knowledge graph."""
    overview = await graph.query(
        "What are the main themes, recurring patterns, and frameworks in this knowledge base? "
        "Identify clusters of related topics and any notable connections between different areas.",
        mode="global",
    )

    if not overview or not overview.strip():
        return []

    prompt = _DISCOVER_PROMPT_TMPL.format(overview=overview)

    client = openai.AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)
    response = await client.chat.completions.create(
        model=model, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    raw_insights = json.loads(content.strip())

    return [
        DiscoveryInsight(
            insight_type=item["insight_type"], title=item["title"],
            description=item["description"],
            related_entities=item.get("related_entities", []),
        )
        for item in raw_insights
    ]
