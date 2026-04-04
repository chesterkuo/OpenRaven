import { useEffect, useState } from "react";

interface Status { total_files: number; total_entities: number; total_connections: number; topic_count: number; top_topics: string[]; confidence_avg: number; }

export default function StatusPage() {
  const [status, setStatus] = useState<Status | null>(null);
  useEffect(() => { fetch("/api/status").then(r => r.json()).then(setStatus).catch(() => {}); }, []);

  const [provider, setProvider] = useState<{provider: string; llm_model: string} | null>(null);
  useEffect(() => { fetch("/api/config/provider").then(r => r.json()).then(setProvider).catch(() => {}); }, []);

  const [insights, setInsights] = useState<{insight_type: string; title: string; description: string; severity: string}[]>([]);
  useEffect(() => { fetch("/api/health/insights").then(r => r.json()).then(setInsights).catch(() => {}); }, []);

  if (!status) return <div style={{ color: "var(--color-text-muted)" }}>Loading...</div>;

  const BORDER_COLORS: Record<string, string> = {
    warning: "var(--color-brand-amber)",
    critical: "var(--color-error)",
    info: "var(--color-brand)",
  };

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Knowledge Base Status</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: "Files", value: status.total_files },
          { label: "Concepts", value: status.total_entities },
          { label: "Connections", value: status.total_connections },
          { label: "Topics", value: status.topic_count },
        ].map(stat => (
          <div key={stat.label} className="p-4 text-center" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
            <div className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>{stat.value}</div>
            <div className="text-sm mt-2" style={{ color: "var(--color-text-muted)" }}>{stat.label}</div>
          </div>
        ))}
      </div>
      {provider && (
        <div className="mb-8 p-4" style={{ background: "var(--bg-surface-warm)" }}>
          <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>LLM: </span>
          <span className="text-sm" style={{ color: "var(--color-text)" }}>{provider.provider}/{provider.llm_model}</span>
          <span className="inline-block w-2 h-2 ml-2" style={{ background: "var(--color-success)", borderRadius: "50%" }} />
        </div>
      )}
      {status.top_topics.length > 0 && (
        <div className="mb-6">
          <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>Top Topics</h2>
          <div className="flex flex-wrap gap-2">
            {status.top_topics.map(topic => (
              <span key={topic} className="px-3 py-1 text-sm" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", color: "var(--color-text)" }}>{topic}</span>
            ))}
          </div>
        </div>
      )}
      {insights.length > 0 && (
        <div className="mt-6">
          <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>Health Insights</h2>
          <div className="flex flex-col gap-3">
            {insights.map((insight, i) => (
              <div key={i} className="p-4 text-sm" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)", borderLeft: `4px solid ${BORDER_COLORS[insight.severity] ?? "var(--color-brand)"}` }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{insight.insight_type}</span>
                  <span style={{ color: "var(--color-text)" }}>{insight.title}</span>
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>{insight.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
