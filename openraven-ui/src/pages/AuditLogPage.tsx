import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

interface AuditLog {
  id: number;
  user_id: string | null;
  action: string;
  details: string | null;
  ip_address: string | null;
  timestamp: string | null;
}

interface AuditResponse {
  logs: AuditLog[];
  total: number;
  limit: number;
  offset: number;
}

const ACTION_OPTIONS = [
  "", "login", "logout", "signup", "password_reset",
  "file_ingest", "kb_query", "agent_deploy", "agent_undeploy",
];

export default function AuditLogPage() {
  const { t } = useTranslation('audit');
  const [data, setData] = useState<AuditResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: String(limit), offset: String(page * limit) });
    if (action) params.set("action", action);

    fetch(`/api/audit?${params}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [action, page]);

  function handleExport() {
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    window.open(`/api/audit/export?${params}`, "_blank");
  }

  const COLUMN_KEYS = ['timestamp', 'user', 'action', 'details', 'ip'] as const;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>{t('title')}</h1>
        <button
          onClick={handleExport}
          className="px-4 py-2 text-sm cursor-pointer"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          {t('exportCsv')}
        </button>
      </div>

      <div className="flex gap-4 mb-6">
        <div>
          <label htmlFor="action-filter" className="block text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>{t('actionLabel')}</label>
          <select
            id="action-filter"
            value={action}
            onChange={e => { setAction(e.target.value); setPage(0); }}
            className="px-3 py-2 text-sm cursor-pointer"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          >
            <option value="">{t('allActions')}</option>
            {ACTION_OPTIONS.filter(Boolean).map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
      </div>

      {loading && (
        <div className="text-sm animate-pulse" style={{ color: "var(--color-text-muted)" }}>{t('loading', { ns: 'common' })}</div>
      )}

      {data && !loading && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                  {COLUMN_KEYS.map(h => (
                    <th key={h} className="text-left py-2 px-3 text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{t(`columns.${h}`)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.logs.map(log => (
                  <tr key={log.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : "—"}
                    </td>
                    <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text)" }}>{log.user_id ?? t('system')}</td>
                    <td className="py-2 px-3">
                      <span className="text-xs px-2 py-0.5" style={{ background: "var(--bg-surface)", color: "var(--color-text)" }}>
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-xs max-w-xs truncate" style={{ color: "var(--color-text-muted)" }}>
                      {log.details ?? "—"}
                    </td>
                    <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{log.ip_address ?? "—"}</td>
                  </tr>
                ))}
                {data.logs.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-sm" style={{ color: "var(--color-text-muted)" }}>{t('noLogs')}</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4">
            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              {t('showing', { start: data.offset + 1, end: Math.min(data.offset + data.logs.length, data.total), total: data.total })}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 text-xs cursor-pointer disabled:opacity-50 disabled:cursor-default"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
              >{t('prev')}</button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={data.offset + data.logs.length >= data.total}
                className="px-3 py-1 text-xs cursor-pointer disabled:opacity-50 disabled:cursor-default"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
              >{t('next')}</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
