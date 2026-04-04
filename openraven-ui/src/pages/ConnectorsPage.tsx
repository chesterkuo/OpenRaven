import { useEffect, useState } from "react";

interface ConnectorStatus {
  gdrive: { connected: boolean };
  gmail: { connected: boolean };
  meet: { connected: boolean };
  otter: { connected: boolean };
  google_configured: boolean;
}

interface SyncResult {
  files_synced: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export default function ConnectorsPage() {
  const [status, setStatus] = useState<ConnectorStatus | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [otterKey, setOtterKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);

  useEffect(() => {
    fetch("/api/connectors/status").then(r => r.json()).then(setStatus).catch(() => {});
  }, []);

  async function handleConnect() {
    const res = await fetch("/api/connectors/google/auth-url");
    const data = await res.json();
    if (data.auth_url) {
      window.open(data.auth_url, "_blank", "width=500,height=600");
      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch("/api/connectors/status");
          const statusData = await statusRes.json();
          if (statusData.gdrive?.connected) {
            clearInterval(poll);
            setStatus(statusData);
          }
        } catch { /* ignore polling errors */ }
      }, 2000);
      setTimeout(() => clearInterval(poll), 120_000);
    }
  }

  async function handleSaveOtterKey() {
    if (!otterKey.trim()) return;
    setSavingKey(true);
    try {
      await fetch("/api/connectors/otter/save-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: otterKey.trim() }),
      });
      const statusRes = await fetch("/api/connectors/status");
      setStatus(await statusRes.json());
      setOtterKey("");
    } catch { /* ignore */ }
    finally { setSavingKey(false); }
  }

  async function handleSync(connector: "gdrive" | "gmail" | "meet" | "otter") {
    setSyncing(connector);
    setResult(null);
    try {
      const res = await fetch(`/api/connectors/${connector}/sync`, { method: "POST" });
      setResult(await res.json());
    } catch {
      setResult({ files_synced: 0, entities_extracted: 0, articles_generated: 0, errors: ["Sync failed"] });
    } finally {
      setSyncing(null);
    }
  }

  if (!status) return <div style={{ color: "var(--color-text-muted)" }}>Loading...</div>;

  const connectorBtn = (connected: boolean, connector: string, label: string) => {
    if (!connected) {
      return (
        <button onClick={handleConnect} disabled={!status.google_configured}
          className="text-sm px-3 py-2 uppercase cursor-pointer disabled:opacity-50 disabled:cursor-default"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>Connect</button>
      );
    }
    return (
      <button onClick={() => handleSync(connector as "gdrive" | "gmail" | "meet" | "otter")} disabled={syncing !== null}
        className="text-sm px-3 py-2 uppercase cursor-pointer disabled:opacity-50 disabled:cursor-default"
        style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
        {syncing === connector ? "Syncing..." : label}
      </button>
    );
  };

  const statusBadge = (connected: boolean) => (
    <span className="text-xs px-2 py-0.5 flex items-center gap-1.5"
      style={{ background: connected ? "var(--bg-surface-warm)" : "var(--bg-surface-hover)", color: connected ? "var(--color-success)" : "var(--color-text-muted)" }}>
      {connected && <span className="inline-block w-1.5 h-1.5" style={{ background: "var(--color-success)", borderRadius: "50%" }} />}
      {connected ? "Connected" : "Not connected"}
    </span>
  );

  const connectors = [
    { key: "gdrive", name: "Google Drive", desc: "Import documents from your Google Drive (PDF, Docs, Sheets, Slides).", connected: status.gdrive.connected, syncLabel: "Sync Now" },
    { key: "gmail", name: "Gmail", desc: "Import emails from your Gmail account as knowledge base entries.", connected: status.gmail.connected, syncLabel: "Sync Now" },
    { key: "meet", name: "Google Meet", desc: "Import meeting transcripts from Google Meet.", connected: status.meet.connected, syncLabel: "Sync Transcripts" },
  ];

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Connectors</h1>
      {!status.google_configured && (
        <div className="p-4 mb-6 text-sm" style={{ background: "var(--bg-surface-warm)", borderLeft: "4px solid var(--color-brand-amber)", color: "var(--color-text)" }}>
          Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env to enable connectors.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {connectors.map(c => (
          <div key={c.key} className="p-4" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg" style={{ color: "var(--color-text)" }}>{c.name}</h2>
              {statusBadge(c.connected)}
            </div>
            <p className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>{c.desc}</p>
            {connectorBtn(c.connected, c.key, c.syncLabel)}
          </div>
        ))}
        <div className="p-4" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg" style={{ color: "var(--color-text)" }}>Otter.ai</h2>
            {statusBadge(status.otter.connected)}
          </div>
          <p className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>Import meeting transcripts from Otter.ai.</p>
          {!status.otter.connected ? (
            <div className="flex gap-2">
              <input type="password" value={otterKey} onChange={(e) => setOtterKey(e.target.value)} placeholder="Otter.ai API key"
                aria-label="Otter.ai API key"
                className="flex-1 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
              <button onClick={handleSaveOtterKey} disabled={savingKey || !otterKey.trim()}
                className="text-sm px-3 py-2 uppercase cursor-pointer disabled:opacity-50 disabled:cursor-default"
                style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
                {savingKey ? "Saving..." : "Save"}
              </button>
            </div>
          ) : (
            <button onClick={() => handleSync("otter")} disabled={syncing !== null}
              className="text-sm px-3 py-2 uppercase cursor-pointer disabled:opacity-50 disabled:cursor-default"
              style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
              {syncing === "otter" ? "Syncing..." : "Sync Now"}
            </button>
          )}
        </div>
      </div>
      {result && (
        <div className="grid grid-cols-3 gap-6 text-center">
          {[
            { label: "Files synced", value: result.files_synced },
            { label: "Entities", value: result.entities_extracted },
            { label: "Articles", value: result.articles_generated },
          ].map(stat => (
            <div key={stat.label} className="p-6" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
              <div className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>{stat.value}</div>
              <div className="text-sm mt-2" style={{ color: "var(--color-text-muted)" }}>{stat.label}</div>
            </div>
          ))}
          {result.errors.length > 0 && (
            <div className="col-span-3 text-sm" style={{ color: "var(--color-error)" }}>
              {result.errors.map((e, i) => <div key={i}>{e}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
