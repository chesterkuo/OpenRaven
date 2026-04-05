import { useTranslation } from "react-i18next";

interface GraphNodeDetailProps {
  node: {
    id: string;
    labels: string[];
    properties: Record<string, any>;
  } | null;
  neighbors: { id: string; labels: string[] }[];
  edges?: { target: string; description: string; keywords: string }[];
  onClose: () => void;
  onNavigate: (nodeId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "#fa520f",
  concept: "#1f1f1f",
  person: "#ffa110",
  organization: "#d94800",
  event: "#b8860b",
  location: "#8b6914",
};

export default function GraphNodeDetail({ node, neighbors, edges, onClose, onNavigate }: GraphNodeDetailProps) {
  const { t } = useTranslation('graph');
  if (!node) return null;
  const edgeList = edges ?? [];

  const entityType = node.properties.entity_type ?? node.labels[0] ?? "unknown";
  const description = node.properties.description ?? "";
  const source = node.properties.file_path ?? node.properties.source_id ?? "";
  const typeColor = TYPE_COLORS[entityType] ?? "var(--color-text-muted)";

  return (
    <div className="w-80 p-4 overflow-y-auto" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs uppercase tracking-wider px-2 py-0.5" style={{ background: "var(--bg-surface-warm)", color: typeColor }}>
          {entityType}
        </span>
        <button onClick={onClose} aria-label="Close" className="text-sm cursor-pointer hover:opacity-70 p-1" style={{ color: "var(--color-text-muted)" }}>✕</button>
      </div>
      <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>{node.id}</h2>
      {description && (
        <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{description}</p>
      )}
      {source && (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--color-text-muted)" }}>{t('source')}</h3>
          <p className="text-sm break-all" style={{ color: "var(--color-text-secondary)" }}>{source}</p>
        </div>
      )}
      {neighbors.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>
            {t('connectedCount', { count: neighbors.length })}
          </h3>
          <div className="flex flex-col gap-2">
            {neighbors.map((n) => {
              const edge = edgeList.find(e => e.target === n.id);
              return (
                <div key={n.id} className="p-2" style={{ background: "var(--bg-surface-hover)", boxShadow: "var(--shadow-subtle)" }}>
                  <button
                    onClick={() => onNavigate(n.id)}
                    className="text-left text-sm truncate block cursor-pointer hover:opacity-70"
                    style={{ color: "var(--color-brand)" }}
                  >
                    {n.id}
                  </button>
                  {edge?.description && (
                    <p className="text-xs mt-0.5 ml-2" style={{ color: "var(--color-text-muted)" }}>{edge.description}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
