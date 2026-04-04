import { useEffect, useState } from "react";

interface Status { total_files: number; total_entities: number; total_connections: number; topic_count: number; top_topics: string[]; confidence_avg: number; }

export default function StatusPage() {
  const [status, setStatus] = useState<Status | null>(null);
  useEffect(() => { fetch("/api/status").then(r => r.json()).then(setStatus).catch(() => {}); }, []);

  const [provider, setProvider] = useState<{provider: string; llm_model: string} | null>(null);
  useEffect(() => { fetch("/api/config/provider").then(r => r.json()).then(setProvider).catch(() => {}); }, []);

  if (!status) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Knowledge Base Status</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Files", value: status.total_files, color: "text-blue-400" },
          { label: "Concepts", value: status.total_entities, color: "text-green-400" },
          { label: "Connections", value: status.total_connections, color: "text-purple-400" },
          { label: "Topics", value: status.topic_count, color: "text-amber-400" },
        ].map(stat => (
          <div key={stat.label} className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
            <div className={`text-3xl font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>
      {provider && (
        <div className="mb-8 text-sm text-gray-500">
          LLM: <span className="text-gray-300">{provider.provider}/{provider.llm_model}</span>
        </div>
      )}
      {status.top_topics.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Top Topics</h2>
          <div className="flex flex-wrap gap-2">
            {status.top_topics.map(topic => <span key={topic} className="bg-gray-800 border border-gray-700 rounded-full px-3 py-1 text-sm text-gray-300">{topic}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}
