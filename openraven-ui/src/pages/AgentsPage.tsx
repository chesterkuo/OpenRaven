import { useEffect, useState } from "react";

interface Agent {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  tunnel_url: string;
  created_at: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => { loadAgents(); }, []);

  async function loadAgents() {
    try {
      const res = await fetch("/api/agents");
      setAgents(await res.json());
    } catch { /* ignore */ }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await fetch("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), description: description.trim() }),
      });
      setName("");
      setDescription("");
      setShowCreate(false);
      await loadAgents();
    } catch { /* ignore */ }
    finally { setCreating(false); }
  }

  async function handleDelete(id: string) {
    await fetch(`/api/agents/${id}`, { method: "DELETE" });
    await loadAgents();
  }

  async function handleGenerateToken(id: string) {
    const res = await fetch(`/api/agents/${id}/tokens`, { method: "POST" });
    const data = await res.json();
    if (data.token) {
      await navigator.clipboard.writeText(data.token);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  }

  function copyUrl(agent: Agent) {
    const url = agent.tunnel_url
      ? `${agent.tunnel_url}/agents/${agent.id}`
      : `http://localhost:8741/agents/${agent.id}`;
    navigator.clipboard.writeText(url);
    setCopiedId(agent.id + "-url");
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Expert Agents</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500">
          {showCreate ? "Cancel" : "Create Agent"}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
          <div className="flex flex-col gap-3">
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Agent name (e.g. Legal Expert)"
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500" />
            <input value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (what does this agent know?)"
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500" />
            <button type="submit" disabled={creating || !name.trim()} className="self-start text-sm px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      )}

      {agents.length === 0 && !showCreate && (
        <div className="text-gray-500 text-sm">No agents yet. Create one to deploy your knowledge base as a queryable expert.</div>
      )}

      <div className="flex flex-col gap-4">
        {agents.map(agent => (
          <div key={agent.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="font-semibold">{agent.name}</h2>
                <p className="text-sm text-gray-400">{agent.description}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${agent.tunnel_url ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
                {agent.tunnel_url ? "Deployed" : "Local only"}
              </span>
            </div>
            <div className="text-xs text-gray-500 mb-3 font-mono">
              {agent.tunnel_url
                ? <span className="text-blue-400">{agent.tunnel_url}/agents/{agent.id}</span>
                : <span>http://localhost:8741/agents/{agent.id}</span>
              }
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => copyUrl(agent)} className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-800 text-gray-200 hover:bg-gray-700">
                {copiedId === agent.id + "-url" ? "Copied!" : "Copy URL"}
              </button>
              <button onClick={() => handleGenerateToken(agent.id)} className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-800 text-gray-200 hover:bg-gray-700">
                {copiedId === agent.id ? "Token copied!" : "Generate Token"}
              </button>
              <button onClick={() => handleDelete(agent.id)} className="text-xs px-2 py-1 rounded border border-red-800 bg-gray-800 text-red-400 hover:bg-red-900/30">
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
