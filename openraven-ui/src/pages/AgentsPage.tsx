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

  const statusBadge = (deployed: boolean) => (
    <span className="text-xs px-2 py-0.5 flex items-center gap-1.5"
      style={{ background: deployed ? "var(--bg-surface-warm)" : "var(--bg-surface-hover)", color: deployed ? "var(--color-success)" : "var(--color-text-muted)" }}>
      {deployed && <span className="inline-block w-1.5 h-1.5" style={{ background: "var(--color-success)", borderRadius: "50%" }} />}
      {deployed ? "Deployed" : "Local only"}
    </span>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Expert Agents</h1>
        <button onClick={() => setShowCreate(!showCreate)}
          className="text-sm px-3 py-1.5 uppercase"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
          {showCreate ? "Cancel" : "Create Agent"}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="p-4 mb-6" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
          <div className="flex flex-col gap-3">
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Agent name (e.g. Legal Expert)"
              className="px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <input value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (what does this agent know?)"
              className="px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <button type="submit" disabled={creating || !name.trim()}
              className="self-start text-sm px-4 py-2 uppercase disabled:opacity-50"
              style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      )}

      {agents.length === 0 && !showCreate && (
        <div className="text-sm" style={{ color: "var(--color-text-muted)" }}>No agents yet. Create one to deploy your knowledge base as a queryable expert.</div>
      )}

      <div className="flex flex-col gap-6">
        {agents.map(agent => (
          <div key={agent.id} className="p-4" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="text-lg" style={{ color: "var(--color-text)" }}>{agent.name}</h2>
                <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>{agent.description}</p>
              </div>
              {statusBadge(!!agent.tunnel_url)}
            </div>
            <div className="text-xs mb-3 font-mono" style={{ color: "var(--color-text-muted)" }}>
              {agent.tunnel_url
                ? <span style={{ color: "var(--color-brand)" }}>{agent.tunnel_url}/agents/{agent.id}</span>
                : <span>http://localhost:8741/agents/{agent.id}</span>
              }
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => copyUrl(agent)}
                className="text-xs px-2 py-1 uppercase"
                style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
                {copiedId === agent.id + "-url" ? "Copied!" : "Copy URL"}
              </button>
              <button onClick={() => handleGenerateToken(agent.id)}
                className="text-xs px-2 py-1 uppercase"
                style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
                {copiedId === agent.id ? "Token copied!" : "Generate Token"}
              </button>
              <button onClick={() => handleDelete(agent.id)}
                className="text-xs px-2 py-1 uppercase"
                style={{ background: "var(--bg-surface-hover)", color: "var(--color-error)" }}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
