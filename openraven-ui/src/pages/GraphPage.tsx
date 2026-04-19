import { useEffect, useState, useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import GraphViewer, { type GraphNode, type GraphEdge } from "../components/GraphViewer";
import GraphNodeDetail from "../components/GraphNodeDetail";
import { TYPE_LABELS } from "../constants/graphTypes";

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_truncated: boolean;
}

export default function GraphPage() {
  const { t, i18n } = useTranslation("graph");
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight");

  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTypes, setActiveTypes] = useState<Set<string> | null>(null);
  const [minDegree, setMinDegree] = useState(0);
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/graph?max_nodes=500")
      .then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      })
      .then((d) => {
        setData(d);
        setLoading(false);
        const types = new Set(d.nodes.map((n: GraphNode) => n.properties?.entity_type ?? n.labels[0] ?? "unknown"));
        setActiveTypes(types);
      })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!highlightId || !data) return;
    const exact = data.nodes.find((n) => n.id === highlightId);
    const match = exact || data.nodes.find((n) => n.id.includes(highlightId));
    if (match) {
      setSelectedNode(match);
      setFocusNodeId(match.id);
    }
  }, [highlightId, data]);

  const typeCounts = useMemo(() => {
    if (!data) return new Map<string, number>();
    const counts = new Map<string, number>();
    for (const n of data.nodes) {
      const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
      counts.set(type, (counts.get(type) ?? 0) + 1);
    }
    return counts;
  }, [data]);

  const sortedTypes = useMemo(() => {
    return [...typeCounts.entries()].sort((a, b) => b[1] - a[1]).map(([type]) => type);
  }, [typeCounts]);

  const filteredNodes = useMemo(() => {
    if (!data || !activeTypes) return [];
    const typeFilteredNodeIds = new Set(
      data.nodes.filter((n) => {
        const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
        return activeTypes.has(type);
      }).map((n) => n.id),
    );
    const typeFilteredEdges = data.edges.filter(
      (e) => typeFilteredNodeIds.has(e.source) && typeFilteredNodeIds.has(e.target),
    );
    const degrees = new Map<string, number>();
    for (const e of typeFilteredEdges) {
      degrees.set(e.source, (degrees.get(e.source) ?? 0) + 1);
      degrees.set(e.target, (degrees.get(e.target) ?? 0) + 1);
    }
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
    return data.edges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [data, filteredNodeIds]);

  useEffect(() => {
    if (selectedNode && !filteredNodeIds.has(selectedNode.id)) setSelectedNode(null);
  }, [filteredNodeIds, selectedNode]);

  const neighbors = useMemo(() => {
    if (!selectedNode || !data) return [];
    const id = selectedNode.id;
    const neighborIds = new Set<string>();
    for (const e of data.edges) {
      if (e.source === id) neighborIds.add(e.target);
      if (e.target === id) neighborIds.add(e.source);
    }
    return data.nodes.filter((n) => neighborIds.has(n.id)).map((n) => ({ id: n.id, labels: n.labels }));
  }, [selectedNode, data]);

  const selectedEdges = useMemo(() => {
    if (!selectedNode || !data) return [];
    const id = selectedNode.id;
    return data.edges
      .filter((e) => e.source === id || e.target === id)
      .map((e) => ({
        target: e.source === id ? e.target : e.source,
        description: e.properties?.description ?? "",
        keywords: e.properties?.keywords ?? "",
      }));
  }, [selectedNode, data]);

  const handleNodeClick = useCallback((node: GraphNode) => { setSelectedNode(node); }, []);
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
      if (!prev) return prev;
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const isChinese = i18n.language?.startsWith("zh");

  if (loading) return <div className="p-8" style={{ color: "var(--color-text-muted)" }} data-testid="graph-loading">{t("loadingGraph")}</div>;
  if (error) return <div className="p-8" style={{ color: "var(--color-error)" }} data-testid="graph-error">Error: {error}</div>;
  if (!data || data.nodes.length === 0) {
    return (
      <div className="p-8" style={{ color: "var(--color-text-muted)" }} data-testid="graph-empty">
        <h1 className="text-3xl mb-2" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>{t("title")}</h1>
        <p>{t("emptyMessage")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Guide summary */}
      <div className="px-4 py-2 text-xs" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)", borderBottom: "1px solid var(--color-border)" }}>
        {t("guideSummary", { nodes: data.nodes.length, edges: data.edges.length })}
      </div>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 flex-wrap" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", borderBottom: "1px solid var(--color-border)" }}>
        <input
          type="text"
          placeholder={t("searchPlaceholder")}
          aria-label={t("searchPlaceholder")}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
        />
        <div className="flex gap-1 flex-wrap">
          {sortedTypes.map((type) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className="text-xs px-2.5 py-1.5 cursor-pointer"
              style={
                activeTypes?.has(type)
                  ? { background: "var(--color-brand)", color: "var(--color-text-on-brand)" }
                  : { background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }
              }
            >
              {isChinese ? TYPE_LABELS[type] || type : type} {typeCounts.get(type)}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs" style={{ color: "var(--color-text-muted)" }}>{t("minConnections")}</label>
          <input type="range" min={0} max={10} value={minDegree} onChange={(e) => setMinDegree(Number(e.target.value))} className="w-20 h-1" style={{ accentColor: "var(--color-brand)" }} />
          <span className="text-xs w-4" style={{ color: "var(--color-text-secondary)" }}>{minDegree}</span>
        </div>
        <a href="/api/graph/export" download className="text-xs px-2.5 py-1.5 uppercase cursor-pointer" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{t("exportGraphML")}</a>
        <button onClick={exportPNG} className="text-xs px-2.5 py-1.5 uppercase cursor-pointer" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{t("exportPNG")}</button>
        <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>
          {filteredNodes.length} nodes / {filteredEdges.length} edges
          {data.is_truncated && ` ${t("truncated", { ns: "common" })}`}
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
          focusNodeId={focusNodeId}
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
