interface Insight { insight_type: string; title: string; description: string; related_entities: string[]; }
interface Props { insight: Insight; }

const TYPE_BORDERS: Record<string, string> = {
  theme: "#fa520f",
  cluster: "#ffa110",
  gap: "#ffd900",
  trend: "#1f1f1f",
};

export default function DiscoveryCard({ insight }: Props) {
  const borderColor = TYPE_BORDERS[insight.insight_type] ?? TYPE_BORDERS.theme;
  return (
    <div
      className="p-4"
      style={{
        background: "var(--bg-surface)",
        boxShadow: "var(--shadow-golden)",
        borderLeft: `4px solid ${borderColor}`,
      }}
    >
      <span className="text-xs uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
        {insight.insight_type}
      </span>
      <h3 className="text-base" style={{ color: "var(--color-text)" }}>{insight.title}</h3>
      <p className="text-sm mt-1" style={{ color: "var(--color-text-secondary)" }}>{insight.description}</p>
      {insight.related_entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {insight.related_entities.slice(0, 5).map(entity => (
            <span key={entity} className="text-xs px-2 py-0.5" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
              {entity}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
