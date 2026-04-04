import { useEffect, useState } from "react";

interface ConnectorStatus {
  gdrive: { connected: boolean };
  gmail: { connected: boolean };
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
      // Stop polling after 2 minutes to avoid leak if user closes popup
      setTimeout(() => clearInterval(poll), 120_000);
    }
  }

  async function handleSync(connector: "gdrive" | "gmail") {
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

  if (!status) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Connectors</h1>

      {!status.google_configured && (
        <div className="bg-amber-950/30 border border-amber-700 rounded-lg p-4 mb-6 text-sm text-amber-300">
          Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env to enable connectors.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Google Drive */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Google Drive</h2>
            <span className={`text-xs px-2 py-0.5 rounded ${status.gdrive.connected ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {status.gdrive.connected ? "Connected" : "Not connected"}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-3">Import documents from your Google Drive (PDF, Docs, Sheets, Slides).</p>
          {!status.gdrive.connected ? (
            <button onClick={handleConnect} disabled={!status.google_configured} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
              Connect Google Account
            </button>
          ) : (
            <button onClick={() => handleSync("gdrive")} disabled={syncing !== null} className="text-sm px-3 py-1.5 rounded bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50">
              {syncing === "gdrive" ? "Syncing..." : "Sync Now"}
            </button>
          )}
        </div>

        {/* Gmail */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Gmail</h2>
            <span className={`text-xs px-2 py-0.5 rounded ${status.gmail.connected ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {status.gmail.connected ? "Connected" : "Not connected"}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-3">Import emails from your Gmail account as knowledge base entries.</p>
          {!status.gmail.connected ? (
            <button onClick={handleConnect} disabled={!status.google_configured} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
              Connect Google Account
            </button>
          ) : (
            <button onClick={() => handleSync("gmail")} disabled={syncing !== null} className="text-sm px-3 py-1.5 rounded bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50">
              {syncing === "gmail" ? "Syncing..." : "Sync Now"}
            </button>
          )}
        </div>
      </div>

      {result && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="font-semibold mb-2">Sync Results</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div><div className="text-2xl font-bold text-blue-400">{result.files_synced}</div><div className="text-xs text-gray-500">Files synced</div></div>
            <div><div className="text-2xl font-bold text-green-400">{result.entities_extracted}</div><div className="text-xs text-gray-500">Entities</div></div>
            <div><div className="text-2xl font-bold text-purple-400">{result.articles_generated}</div><div className="text-xs text-gray-500">Articles</div></div>
          </div>
          {result.errors.length > 0 && <div className="mt-3 text-red-400 text-sm">{result.errors.map((e, i) => <div key={i}>{e}</div>)}</div>}
        </div>
      )}
    </div>
  );
}
