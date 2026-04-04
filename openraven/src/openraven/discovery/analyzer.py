from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import anthropic

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
    insights = []
    topics = graph_stats.get("topics", [])
    node_count = graph_stats.get("nodes", 0)
    edge_count = graph_stats.get("edges", 0)

    if node_count > 0:
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

    if len(topics) >= 3:
        insights.append(DiscoveryInsight(
            insight_type="cluster",
            title="Top Knowledge Areas",
            description=f"Found {len(topics)} distinct topics in your knowledge base.",
            related_entities=topics[:10],
            document_count=len(topics),
        ))

    return insights


async def discover_insights_with_llm(
    graph, api_key: str, model: str = "claude-sonnet-4-6",
) -> list[DiscoveryInsight]:
    overview = await graph.query(
        "What are the main themes, recurring patterns, and frameworks in this knowledge base? "
        "Identify clusters of related topics and any notable connections between different areas.",
        mode="global",
    )

    prompt = _DISCOVER_PROMPT_TMPL.format(overview=overview)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text
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
