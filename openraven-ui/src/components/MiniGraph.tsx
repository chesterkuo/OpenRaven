import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import GraphViewer, { type GraphNode } from "./GraphViewer";
import { TYPE_LABELS } from "../constants/graphTypes";

interface MiniGraphProps {
  sourceFiles: string[];
  height?: number;
}

export default function MiniGraph({ sourceFiles, height = 280 }: MiniGraphProps) {
  const { t, i18n } = useTranslation("graph");
  const { isDemo } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<{ nodes: GraphNode[]; edges: any[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [card, setCard] = useState<{ node: GraphNode } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (sourceFiles.length === 0) return;
    setLoading(true);
    const allPaths = sourceFiles.flatMap((f) => f.split("<SEP>"));
    const fileNames = allPaths.map((f) => f.trim().split("/").pop() || f.trim());
    const unique = [...new Set(fileNames)].filter(Boolean);
    fetch(`/api/graph/subgraph?files=${encodeURIComponent(unique.join(","))}&max_nodes=30`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [sourceFiles]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedId(node.id);
    setCard({ node });
  }, []);

  const handleNavigate = useCallback(
    (nodeId: string) => {
      const prefix = isDemo ? "/demo" : "";
      navigate(`${prefix}/graph?highlight=${encodeURIComponent(nodeId)}`);
    },
    [isDemo, navigate],
  );

  if (loading) return <div className="text-xs py-4" style={{ color: "var(--color-text-muted)" }}>{t("loadingGraph")}</div>;
  if (!data || data.nodes.length < 2) return null;

  const isChinese = i18n.language?.startsWith("zh");

  return (
    <div className="relative flex flex-col" style={{ height }}>
      <GraphViewer
        nodes={data.nodes}
        edges={data.edges}
        selectedNodeId={selectedId}
        onNodeClick={handleNodeClick}
        searchTerm=""
        mode="mini"
      />
      {card && (
        <div
          className="absolute bottom-2 left-2 right-2 p-3"
          style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)", zIndex: 10 }}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs uppercase tracking-wider px-1.5 py-0.5" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }}>
              {isChinese
                ? TYPE_LABELS[card.node.properties?.entity_type] || card.node.properties?.entity_type || "unknown"
                : card.node.properties?.entity_type || "unknown"}
            </span>
            <button onClick={() => setCard(null)} className="text-xs cursor-pointer" style={{ color: "var(--color-text-muted)" }}>✕</button>
          </div>
          <div className="text-sm font-medium mb-1" style={{ color: "var(--color-text)" }}>{card.node.id}</div>
          <div className="text-xs mb-2 line-clamp-2" style={{ color: "var(--color-text-secondary)" }}>
            {(card.node.properties?.description || "").split("<SEP>")[0].slice(0, 100)}
          </div>
          <button
            onClick={() => handleNavigate(card.node.id)}
            className="text-xs cursor-pointer hover:opacity-80"
            style={{ color: "var(--color-brand)" }}
          >
            {t("viewInGraph")} →
          </button>
        </div>
      )}
    </div>
  );
}
