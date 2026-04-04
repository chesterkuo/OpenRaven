import { useEffect, useState, useMemo, useCallback } from "react";
import GraphViewer, { type GraphNode, type GraphEdge } from "../components/GraphViewer";
import GraphNodeDetail from "../components/GraphNodeDetail";

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_truncated: boolean;
}

const ENTITY_TYPES = ["technology", "concept", "person", "organization", "event", "location"];

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set(ENTITY_TYPES));
  const [minDegree, setMinDegree] = useState(0);

  useEffect(() => {
    fetch("/api/graph?max_nodes=500")
      .then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  const filteredNodes = useMemo(() => {
    if (!data) return [];

    // Step 1: Get type-filtered node IDs
    const typeFilteredNodeIds = new Set(
      data.nodes
        .filter((n) => {
          const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
          return activeTypes.has(type);
        })
        .map((n) => n.id)
    );

    // Step 2: Get edges where both endpoints pass the type filter
    const typeFilteredEdges = data.edges.filter(
      (e) => typeFilteredNodeIds.has(e.source) && typeFilteredNodeIds.has(e.target)
    );

    // Step 3: Build degree map from type-filtered edges
    const degrees = new Map<string, number>();
    for (const e of typeFilteredEdges) {
      degrees.set(e.source, (degrees.get(e.source) ?? 0) + 1);
      degrees.set(e.target, (degrees.get(e.target) ?? 0) + 1);
    }

    // Step 4: Filter nodes by type AND minDegree
    return data.nodes.filter((n) => {
      const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
      if (!activeTypes.has(type)) return false;
      if (minDegree > 0 && (degrees.get(n.id) ?? 0) < minDegree) return false;
      return true;
    });
  }, [data, activeTypes, minDegree]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    if (!data) return [];
    return data.edges.filter((e) => {
      return filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target);
    });
  }, [data, filteredNodeIds]);

  // Clear selectedNode when it becomes invisible due to type filter
  useEffect(() => {
    if (selectedNode && !filteredNodeIds.has(selectedNode.id)) {
      setSelectedNode(null);
    }
  }, [filteredNodeIds, selectedNode]);

  const neighbors = useMemo(() => {
    if (!selectedNode || !data) return [];
    const id = selectedNode.id;
    const neighborIds = new Set<string>();
    for (const e of data.edges) {
      if (e.source === id) neighborIds.add(e.target);
      if (e.target === id) neighborIds.add(e.source);
    }
    return data.nodes
      .filter((n) => neighborIds.has(n.id))
      .map((n) => ({ id: n.id, labels: n.labels }));
  }, [selectedNode, data]);

  const selectedEdges = useMemo(() => {
    if (!selectedNode || !data) return [];
    const id = selectedNode.id;
    return data.edges
      .filter(e => e.source === id || e.target === id)
      .map(e => ({
        target: e.source === id ? e.target : e.source,
        description: e.properties?.description ?? "",
        keywords: e.properties?.keywords ?? "",
      }));
  }, [selectedNode, data]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, []);

  const handleNavigate = useCallback((nodeId: string) => {
    const node = data?.nodes.find((n) => n.id === nodeId);
    if (node) setSelectedNode(node);
  }, [data]);

  function exportPNG() {
    const canvas = document.querySelector('[data-testid="graph-viewer"] canvas') as HTMLCanvasElement;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = "openraven-knowledge-graph.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  const toggleType = (type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  if (loading) return <div className="p-8" style={{ color: "var(--color-text-muted)" }} data-testid="graph-loading">Loading graph...</div>;
  if (error) return <div className="p-8" style={{ color: "var(--color-error)" }} data-testid="graph-error">Error: {error}</div>;
  if (!data || data.nodes.length === 0) {
    return (
      <div className="p-8" style={{ color: "var(--color-text-muted)" }} data-testid="graph-empty">
        <h1 className="text-3xl mb-2" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Knowledge Graph</h1>
        <p>No graph data yet. Add files to start building your knowledge graph.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", borderBottom: "1px solid var(--color-border)" }}>
        <input
          type="text"
          placeholder="Search nodes..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="px-3 py-1 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]" style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
        />
        <div className="flex gap-1">
          {ENTITY_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className="text-xs px-2 py-1" style={activeTypes.has(type) ? { background: "var(--color-brand)", color: "var(--color-text-on-brand)" } : { background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }}
            >
              {type}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs" style={{ color: "var(--color-text-muted)" }}>Min connections:</label>
          <input
            type="range"
            min={0}
            max={10}
            value={minDegree}
            onChange={(e) => setMinDegree(Number(e.target.value))}
            className="w-20 h-1" style={{ accentColor: "var(--color-brand)" }}
          />
          <span className="text-xs w-4" style={{ color: "var(--color-text-secondary)" }}>{minDegree}</span>
        </div>
        <a
          href="/api/graph/export"
          download
          className="text-xs px-2 py-1 uppercase" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          Export GraphML
        </a>
        <button
          onClick={exportPNG}
          className="text-xs px-2 py-1 uppercase" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          Export PNG
        </button>
        <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>
          {filteredNodes.length} nodes / {filteredEdges.length} edges
          {data.is_truncated && " (truncated)"}
        </span>
      </div>
      {/* Graph + Detail panel */}
      <div className="flex flex-1 min-h-0">
        <GraphViewer
          nodes={filteredNodes}
          edges={filteredEdges}
          selectedNodeId={selectedNode?.id ?? null}
          onNodeClick={handleNodeClick}
          searchTerm={searchTerm}
        />
        {selectedNode && (
          <GraphNodeDetail
            node={selectedNode}
            neighbors={neighbors}
            edges={selectedEdges}
            onClose={() => setSelectedNode(null)}
            onNavigate={handleNavigate}
          />
        )}
      </div>
    </div>
  );
}
