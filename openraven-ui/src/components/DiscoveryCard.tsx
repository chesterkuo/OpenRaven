interface Insight { insight_type: string; title: string; description: string; related_entities: string[]; }
interface Props { insight: Insight; }

const TYPE_COLORS: Record<string, string> = {
  theme: "border-blue-500/30 bg-blue-500/5", cluster: "border-green-500/30 bg-green-500/5",
  gap: "border-amber-500/30 bg-amber-500/5", trend: "border-purple-500/30 bg-purple-500/5",
};

export default function DiscoveryCard({ insight }: Props) {
  const colorClass = TYPE_COLORS[insight.insight_type] ?? TYPE_COLORS.theme;
  return (
    <div className={`border rounded-lg p-4 ${colorClass}`}>
      <span className="text-xs uppercase tracking-wider text-gray-500">{insight.insight_type}</span>
      <h3 className="font-medium text-gray-200">{insight.title}</h3>
      <p className="text-sm text-gray-400 mt-1">{insight.description}</p>
      {insight.related_entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {insight.related_entities.slice(0, 5).map(entity => <span key={entity} className="text-xs bg-gray-800 rounded px-2 py-0.5 text-gray-400">{entity}</span>)}
        </div>
      )}
    </div>
  );
}
