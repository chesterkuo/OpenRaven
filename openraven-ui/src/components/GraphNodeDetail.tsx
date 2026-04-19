import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { TYPE_COLORS, TYPE_LABELS, extractRelationLabel } from "../constants/graphTypes";

interface GraphNodeDetailProps {
  node: {
    id: string;
    labels: string[];
    properties: Record<string, any>;
  } | null;
  neighbors: { id: string; labels: string[] }[];
  edges?: { target: string; description: string; keywords: string }[];
  onClose: () => void;
  onNavigate: (nodeId: string) => void;
}

interface Excerpt {
  file: string;
  text: string;
  line_start: number;
  line_end: number;
}

export default function GraphNodeDetail({ node, neighbors, edges, onClose, onNavigate }: GraphNodeDetailProps) {
  const { t, i18n } = useTranslation("graph");
  const { isDemo } = useAuth();
  const navigate = useNavigate();
  const [excerpts, setExcerpts] = useState<Excerpt[]>([]);
  const [contextFiles, setContextFiles] = useState<string[]>([]);
  const [loadingContext, setLoadingContext] = useState(false);

  useEffect(() => {
    if (!node) return;
    setLoadingContext(true);
    setExcerpts([]);
    setContextFiles([]);
    fetch(`/api/graph/node/${encodeURIComponent(node.id)}/context`)
      .then((r) => r.json())
      .then((data) => {
        setExcerpts(data.excerpts || []);
        setContextFiles(data.files || []);
        setLoadingContext(false);
      })
      .catch(() => setLoadingContext(false));
  }, [node?.id]);

  const handleAsk = useCallback(() => {
    if (!node) return;
    const prefix = isDemo ? "/demo" : "";
    const isCN = i18n.language?.startsWith("zh");
    const question = isCN ? `請說明「${node.id}」的相關規定` : `Tell me about "${node.id}"`;
    const q = encodeURIComponent(question);
    navigate(`${prefix}/ask?q=${q}`);
  }, [node, isDemo, navigate, i18n.language]);

  if (!node) return null;
  const edgeList = edges ?? [];
  const entityType = node.properties.entity_type ?? node.labels[0] ?? "unknown";
  const description = (node.properties.description ?? "").split("<SEP>")[0];
  const typeColor = TYPE_COLORS[entityType] ?? "var(--color-text-muted)";
  const isChinese = i18n.language?.startsWith("zh");
  const typeLabel = isChinese ? TYPE_LABELS[entityType] || entityType : entityType;

  const rawFilePath = node.properties.file_path ?? "";
  const filePaths = rawFilePath
    .split("<SEP>")
    .map((p: string) => p.trim().split("/").pop() || p.trim())
    .filter((p: string) => p);
  const uniqueFiles = [...new Set([...filePaths, ...contextFiles])];

  return (
    <div className="w-80 p-4 overflow-y-auto" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs uppercase tracking-wider px-2 py-0.5" style={{ background: "var(--bg-surface-warm)", color: typeColor }}>
          {typeLabel}
        </span>
        <button onClick={onClose} aria-label="Close" className="text-sm cursor-pointer hover:opacity-70 p-1" style={{ color: "var(--color-text-muted)" }}>✕</button>
      </div>
      <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>{node.id}</h2>
      {description && (
        <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{description}</p>
      )}

      {loadingContext ? (
        <div className="mb-4 text-xs animate-pulse" style={{ color: "var(--color-text-muted)" }}>{t("loadingContext")}</div>
      ) : excerpts.length > 0 ? (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>{t("excerptHeading")}</h3>
          {excerpts.map((ex, i) => (
            <div key={i} className="text-xs mb-2 p-2 leading-relaxed" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }}>
              <pre className="whitespace-pre-wrap font-sans">{ex.text}</pre>
              <div className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>— {ex.file}</div>
            </div>
          ))}
        </div>
      ) : null}

      {uniqueFiles.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>
            {t("appearsIn", { count: uniqueFiles.length })}
          </h3>
          {uniqueFiles.map((f, i) => (
            <div key={i} className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>📄 {f}</div>
          ))}
        </div>
      )}

      {neighbors.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>
            {t("relatedCount", { count: neighbors.length })}
          </h3>
          <div className="flex flex-col gap-2">
            {neighbors.map((n) => {
              const edge = edgeList.find((e) => e.target === n.id);
              const label = edge ? (isChinese ? extractRelationLabel(edge.keywords) : "") : "";
              return (
                <div key={n.id} className="p-2" style={{ background: "var(--bg-surface-hover)", boxShadow: "var(--shadow-subtle)" }}>
                  <div className="flex items-center gap-2">
                    {label && <span className="text-xs px-1" style={{ color: "var(--color-text-muted)" }}>{label}→</span>}
                    <button
                      onClick={() => onNavigate(n.id)}
                      className="text-left text-sm truncate block cursor-pointer hover:opacity-70"
                      style={{ color: "var(--color-brand)" }}
                    >
                      {n.id}
                    </button>
                  </div>
                  {edge?.description && (
                    <p className="text-xs mt-0.5 ml-2" style={{ color: "var(--color-text-muted)" }}>{edge.description.split("<SEP>")[0].slice(0, 80)}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleAsk}
          className="text-xs px-3 py-1.5 cursor-pointer hover:opacity-80"
          style={{ background: "var(--color-brand)", color: "var(--color-text-on-brand)" }}
        >
          {t("askAbout")}
        </button>
        <button
          onClick={() => {
            const prefix = isDemo ? "/demo" : "";
            const slug = node.id.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\u4e00-\u9fff\u3400-\u4dbf-]/g, "");
            navigate(`${prefix}/documents?q=${encodeURIComponent(slug)}`);
          }}
          className="text-xs px-3 py-1.5 cursor-pointer hover:opacity-80"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          {t("viewWiki")}
        </button>
      </div>
    </div>
  );
}
