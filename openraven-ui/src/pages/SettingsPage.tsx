import { useEffect, useState } from "react";

interface Member { user_id: string; email: string; name: string; role: string; joined_at: string | null; }
interface Invitation { id: string; token: string; expires_at: string | null; max_uses: number | null; use_count: number; }
interface AccountInfo { user_id: string; email: string; name: string; created_at: string | null; deletion: { eligible: boolean; reason: string; member_count: number; }; }

export default function SettingsPage() {
  const [tab, setTab] = useState<"team" | "account" | "sync">("team");

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Settings</h1>
      <div className="flex gap-4 mb-8" style={{ borderBottom: "2px solid var(--color-border)" }}>
        {(["team", "account", "sync"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className="px-4 py-2 text-sm cursor-pointer capitalize"
            style={{
              color: tab === t ? "var(--color-brand)" : "var(--color-text-muted)",
              borderBottom: tab === t ? "2px solid var(--color-brand)" : "2px solid transparent",
              background: "transparent", marginBottom: "-2px",
            }}
          >{t}</button>
        ))}
      </div>
      {tab === "team" && <TeamTab />}
      {tab === "account" && <AccountTab />}
      {tab === "sync" && <SyncTab />}
    </div>
  );
}

function TeamTab() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [inviteLink, setInviteLink] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/team/members").then(r => r.json()).then(setMembers).catch(() => {});
    fetch("/api/team/invitations").then(r => r.json()).then(setInvitations).catch(() => {});
  }, []);

  async function createInvite() {
    setLoading(true);
    try {
      const res = await fetch("/api/team/invite", { method: "POST" });
      const data = await res.json();
      setInviteLink(`${window.location.origin}/invite/${data.token}`);
      const inv = await fetch("/api/team/invitations").then(r => r.json());
      setInvitations(inv);
    } finally { setLoading(false); }
  }

  async function removeMember(userId: string) {
    await fetch(`/api/team/members/${userId}`, { method: "DELETE" });
    setMembers(prev => prev.filter(m => m.user_id !== userId));
  }

  async function revokeInvitation(id: string) {
    await fetch(`/api/team/invitations/${id}`, { method: "DELETE" });
    setInvitations(prev => prev.filter(i => i.id !== id));
  }

  return (
    <div>
      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Team Members</h2>
      <table className="w-full text-sm mb-8" style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
            {["Email", "Name", "Role", ""].map(h => (
              <th key={h} className="text-left py-2 px-3 text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {members.map(m => (
            <tr key={m.user_id} style={{ borderBottom: "1px solid var(--color-border)" }}>
              <td className="py-2 px-3" style={{ color: "var(--color-text)" }}>{m.email}</td>
              <td className="py-2 px-3" style={{ color: "var(--color-text-secondary)" }}>{m.name}</td>
              <td className="py-2 px-3">
                <span className="text-xs px-2 py-0.5" style={{
                  background: m.role === "owner" ? "var(--color-brand)" : "var(--bg-surface)",
                  color: m.role === "owner" ? "var(--color-text-on-brand)" : "var(--color-text)",
                }}>{m.role}</span>
              </td>
              <td className="py-2 px-3 text-right">
                {m.role !== "owner" && (
                  <button onClick={() => removeMember(m.user_id)} className="text-xs cursor-pointer" style={{ color: "var(--color-error, #dc2626)" }}>Remove</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Invite Link</h2>
      <div className="flex gap-3 mb-4">
        <button onClick={createInvite} disabled={loading}
          className="px-4 py-2 text-sm cursor-pointer disabled:opacity-50"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >{loading ? "Creating..." : "Create Invite Link"}</button>
      </div>
      {inviteLink && (
        <div className="flex gap-2 mb-6">
          <input readOnly value={inviteLink} className="flex-1 px-3 py-2 text-sm"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <button onClick={() => { navigator.clipboard.writeText(inviteLink); }}
            className="px-3 py-2 text-sm cursor-pointer"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}>Copy</button>
        </div>
      )}

      {invitations.length > 0 && (
        <>
          <h3 className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>Active Invitations</h3>
          <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                {["Token", "Uses", "Expires", ""].map(h => (
                  <th key={h} className="text-left py-1 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invitations.map(inv => (
                <tr key={inv.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td className="py-1 px-3 text-xs font-mono" style={{ color: "var(--color-text)" }}>{inv.token.slice(0, 8)}...</td>
                  <td className="py-1 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{inv.use_count}{inv.max_uses != null ? `/${inv.max_uses}` : ""}</td>
                  <td className="py-1 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{inv.expires_at ? new Date(inv.expires_at).toLocaleString() : "—"}</td>
                  <td className="py-1 px-3 text-right">
                    <button onClick={() => revokeInvitation(inv.id)} className="text-xs cursor-pointer" style={{ color: "var(--color-error, #dc2626)" }}>Revoke</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function SyncTab() {
  const [status, setStatus] = useState<{ configured: boolean; last_sync_at: string | null; snapshot_count: number; total_size: number; snapshots: any[] } | null>(null);
  const [passphrase, setPassphrase] = useState("");
  const [confirm, setConfirm] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/sync/status").then(r => r.json()).then(setStatus).catch(() => {});
  }, []);

  async function handleSetup() {
    if (passphrase.length < 8) { setMessage("Passphrase must be at least 8 characters"); return; }
    if (passphrase !== confirm) { setMessage("Passphrases do not match"); return; }
    const res = await fetch("/api/sync/setup", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase }),
    });
    if (res.ok) { setMessage("Sync passphrase configured!"); setPassphrase(""); setConfirm(""); fetch("/api/sync/status").then(r => r.json()).then(setStatus); }
    else { setMessage("Failed to configure"); }
  }

  async function handleSync() {
    const pp = prompt("Enter your sync passphrase:");
    if (!pp) return;
    setSyncing(true); setMessage("");
    const res = await fetch("/api/sync/upload", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase: pp }),
    });
    if (res.ok) { setMessage("Snapshot uploaded successfully!"); fetch("/api/sync/status").then(r => r.json()).then(setStatus); }
    else { const d = await res.json(); setMessage(d.detail || "Sync failed"); }
    setSyncing(false);
  }

  async function handleDownload(snapshotId?: string) {
    const pp = prompt("Enter your sync passphrase to download:");
    if (!pp) return;
    const res = await fetch("/api/sync/download", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase: pp, snapshot_id: snapshotId }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "openraven_snapshot.zip"; a.click();
      URL.revokeObjectURL(url);
    } else { const d = await res.json(); alert(d.detail || "Download failed"); }
  }

  async function handleDelete(id: string) {
    await fetch(`/api/sync/snapshots/${id}`, { method: "DELETE" });
    fetch("/api/sync/status").then(r => r.json()).then(setStatus);
  }

  return (
    <div>
      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Cloud Sync (E2EE)</h2>
      {!status?.configured ? (
        <div className="mb-6">
          <p className="text-sm mb-4" style={{ color: "var(--color-text-muted)" }}>Set a sync passphrase to enable encrypted cloud sync. This passphrase encrypts your knowledge base — if you forget it, your synced data cannot be recovered.</p>
          <div className="flex flex-col gap-3 max-w-sm">
            <input type="password" value={passphrase} onChange={e => setPassphrase(e.target.value)} placeholder="Sync passphrase (min 8 chars)" aria-label="Sync passphrase"
              className="px-3 py-2 text-sm" style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Confirm passphrase" aria-label="Confirm sync passphrase"
              className="px-3 py-2 text-sm" style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <button onClick={handleSetup} className="px-4 py-2 text-sm cursor-pointer" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>Set Passphrase</button>
          </div>
        </div>
      ) : (
        <div className="mb-6">
          <div className="flex gap-4 mb-4">
            <button onClick={handleSync} disabled={syncing} className="px-4 py-2 text-sm cursor-pointer disabled:opacity-50"
              style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{syncing ? "Syncing..." : "Sync Now"}</button>
            <button onClick={() => handleDownload()} className="px-4 py-2 text-sm cursor-pointer"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}>Download Latest</button>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-6 text-sm">
            <div><div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Last sync</div><div style={{ color: "var(--color-text)" }}>{status.last_sync_at ? new Date(status.last_sync_at).toLocaleString() : "Never"}</div></div>
            <div><div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Snapshots</div><div style={{ color: "var(--color-text)" }}>{status.snapshot_count}</div></div>
            <div><div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Total size</div><div style={{ color: "var(--color-text)" }}>{(status.total_size / 1024 / 1024).toFixed(1)} MB</div></div>
          </div>
          {status.snapshots.length > 0 && (
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead><tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                {["Date", "Size", ""].map(h => <th key={h} className="text-left py-2 px-3 text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{h}</th>)}
              </tr></thead>
              <tbody>{status.snapshots.map((s: any) => (
                <tr key={s.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text)" }}>{s.created_at ? new Date(s.created_at).toLocaleString() : s.id}</td>
                  <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{(s.size / 1024).toFixed(0)} KB</td>
                  <td className="py-2 px-3 text-right flex gap-2 justify-end">
                    <button onClick={() => handleDownload(s.id)} className="text-xs cursor-pointer" style={{ color: "var(--color-brand)" }}>Download</button>
                    <button onClick={() => handleDelete(s.id)} className="text-xs cursor-pointer" style={{ color: "var(--color-error, #dc2626)" }}>Delete</button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}
      {message && <p className="text-sm mt-2" style={{ color: "var(--color-brand)" }}>{message}</p>}
    </div>
  );
}

function AccountTab() {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [showDelete, setShowDelete] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetch("/api/account/").then(r => r.json()).then(setAccount).catch(() => {});
  }, []);

  async function handleExport() {
    window.open("/api/account/export", "_blank");
  }

  async function handleDelete() {
    setDeleting(true);
    setError("");
    try {
      const res = await fetch("/api/account/", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        window.location.href = "/login";
      } else {
        const data = await res.json();
        setError(data.detail || "Deletion failed");
      }
    } catch {
      setError("Failed to connect");
    } finally { setDeleting(false); }
  }

  if (!account) return <div className="text-sm" style={{ color: "var(--color-text-muted)" }}>Loading...</div>;

  return (
    <div>
      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Account</h2>
      <div className="grid grid-cols-2 gap-4 mb-8 text-sm">
        <div>
          <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Email</div>
          <div style={{ color: "var(--color-text)" }}>{account.email}</div>
        </div>
        <div>
          <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Name</div>
          <div style={{ color: "var(--color-text)" }}>{account.name}</div>
        </div>
        <div>
          <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Member since</div>
          <div style={{ color: "var(--color-text)" }}>{account.created_at ? new Date(account.created_at).toLocaleDateString() : "—"}</div>
        </div>
      </div>

      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Export</h2>
      <button onClick={handleExport} className="px-4 py-2 text-sm cursor-pointer mb-8"
        style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
        Export Knowledge Base
      </button>

      <div className="p-6 mt-4" style={{ border: "2px solid var(--color-error, #dc2626)" }}>
        <h2 className="text-xl mb-2" style={{ color: "var(--color-error, #dc2626)" }}>Danger Zone</h2>
        {!account.deletion.eligible ? (
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>{account.deletion.reason}</p>
        ) : !showDelete ? (
          <div>
            <p className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>
              Permanently delete your account, knowledge base, and all associated data. This cannot be undone.
            </p>
            <button onClick={() => setShowDelete(true)} className="px-4 py-2 text-sm cursor-pointer"
              style={{ background: "var(--color-error, #dc2626)", color: "white" }}>Delete Account</button>
          </div>
        ) : (
          <div>
            <p className="text-sm mb-3" style={{ color: "var(--color-text)" }}>Enter your password to confirm:</p>
            <div className="flex gap-3">
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                placeholder="Your password" aria-label="Confirm password for account deletion"
                className="px-3 py-2 text-sm" style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
              <button onClick={handleDelete} disabled={!password || deleting}
                className="px-4 py-2 text-sm cursor-pointer disabled:opacity-50"
                style={{ background: "var(--color-error, #dc2626)", color: "white" }}>
                {deleting ? "Deleting..." : "Delete My Account"}
              </button>
              <button onClick={() => { setShowDelete(false); setPassword(""); setError(""); }}
                className="px-4 py-2 text-sm cursor-pointer"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}>Cancel</button>
            </div>
            {error && <p className="text-sm mt-2" style={{ color: "var(--color-error, #dc2626)" }}>{error}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
