interface GraphNodeDetailProps {
  node: {
    id: string;
    labels: string[];
    properties: Record<string, any>;
  } | null;
  neighbors: { id: string; labels: string[] }[];
  onClose: () => void;
  onNavigate: (nodeId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "text-blue-400",
  concept: "text-green-400",
  person: "text-amber-400",
  organization: "text-purple-400",
  event: "text-red-400",
  location: "text-cyan-400",
};

export default function GraphNodeDetail({ node, neighbors, onClose, onNavigate }: GraphNodeDetailProps) {
  if (!node) return null;

  const entityType = node.properties.entity_type ?? node.labels[0] ?? "unknown";
  // LightRAG stores "description" (not "entity_description") in GraphML
  const description = node.properties.description ?? "";
  // file_path is human-readable; source_id is chunk hashes (fallback)
  const source = node.properties.file_path ?? node.properties.source_id ?? "";
  const colorClass = TYPE_COLORS[entityType] ?? "text-gray-400";

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <span className={`text-xs font-medium uppercase tracking-wider ${colorClass}`}>{entityType}</span>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-sm">✕</button>
      </div>
      <h2 className="text-lg font-bold text-white mb-3">{node.id}</h2>
      {description && (
        <p className="text-sm text-gray-400 mb-4 leading-relaxed">{description}</p>
      )}
      {source && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Source</h3>
          <p className="text-sm text-gray-400 break-all">{source}</p>
        </div>
      )}
      {neighbors.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Connected ({neighbors.length})
          </h3>
          <div className="flex flex-col gap-1">
            {neighbors.map((n) => (
              <button
                key={n.id}
                onClick={() => onNavigate(n.id)}
                className="text-left text-sm text-blue-400 hover:text-blue-300 truncate"
              >
                {n.id}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
