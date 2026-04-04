from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HealthInsight:
    insight_type: str  # "stale", "gap", "connection", "contradiction"
    title: str
    description: str
    related_entities: list[str] = field(default_factory=list)
    severity: str = "info"  # "info", "warning", "critical"


class HealthMaintainer:
    """Runs Stage 4 health analyses on the knowledge base."""

    def __init__(self, store, graph, config) -> None:
        self.store = store
        self.graph = graph
        self.config = config

    def detect_staleness(self, days: int = 30) -> list[HealthInsight]:
        """Find files not updated in the given number of days."""
        if not self.store:
            return []
        stale = self.store.list_stale_files(days=days)
        if not stale:
            return []
        paths = [f.path for f in stale]
        return [HealthInsight(
            insight_type="stale",
            title=f"{len(stale)} stale file{'s' if len(stale) != 1 else ''}",
            description=f"Files not updated in {days}+ days: {', '.join(Path(p).name for p in paths[:5])}",
            related_entities=paths[:10],
            severity="warning",
        )]

    def detect_bridge_connections(self) -> list[HealthInsight]:
        """Find nodes that bridge otherwise disconnected clusters (high betweenness centrality)."""
        if not self.graph:
            return []
        import networkx as nx

        graph_file = self.graph.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return []
        try:
            g = nx.read_graphml(str(graph_file))
        except Exception:
            return []

        if g.number_of_nodes() < 5:
            return []

        betweenness = nx.betweenness_centrality(g)
        avg_bc = sum(betweenness.values()) / len(betweenness)
        bridges = [(node, bc) for node, bc in betweenness.items() if bc > avg_bc * 1.5 and bc > 0.1]
        bridges.sort(key=lambda x: x[1], reverse=True)

        insights = []
        for node, bc in bridges[:5]:
            neighbors = list(g.neighbors(node))
            insights.append(HealthInsight(
                insight_type="connection",
                title=f"Bridge concept: {node}",
                description=f"{node} connects {len(neighbors)} topics (centrality: {bc:.2f}). "
                            f"Connected to: {', '.join(neighbors[:5])}",
                related_entities=[node] + neighbors[:5],
                severity="info",
            ))
        return insights

    def detect_knowledge_gaps(self) -> list[HealthInsight]:
        """Find isolated nodes or small disconnected components."""
        if not self.graph:
            return []
        import networkx as nx

        graph_file = self.graph.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return []
        try:
            g = nx.read_graphml(str(graph_file))
        except Exception:
            return []

        if g.number_of_nodes() < 3:
            return []

        isolated = [n for n, d in g.degree() if d <= 1]
        insights = []
        if isolated:
            insights.append(HealthInsight(
                insight_type="gap",
                title=f"{len(isolated)} weakly connected concept{'s' if len(isolated) != 1 else ''}",
                description=f"These concepts have few connections and may need more context: "
                            f"{', '.join(isolated[:5])}",
                related_entities=isolated[:10],
                severity="info" if len(isolated) < 5 else "warning",
            ))

        components = list(nx.connected_components(g))
        if len(components) > 1:
            small = [c for c in components if len(c) < 3]
            if small:
                names = [next(iter(c)) for c in small[:5]]
                insights.append(HealthInsight(
                    insight_type="gap",
                    title=f"{len(small)} disconnected knowledge cluster{'s' if len(small) != 1 else ''}",
                    description=f"Small isolated clusters found: {', '.join(names)}. "
                                f"Adding more related documents may help connect them.",
                    related_entities=names,
                    severity="warning",
                ))

        return insights

    def run_all(self, staleness_days: int = 30) -> list[HealthInsight]:
        """Run all health analyses and return combined insights."""
        insights = []
        insights.extend(self.detect_staleness(staleness_days))
        insights.extend(self.detect_bridge_connections())
        insights.extend(self.detect_knowledge_gaps())
        return insights
