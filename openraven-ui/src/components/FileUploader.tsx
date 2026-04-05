import { useCallback } from "react";
import { useTranslation } from "react-i18next";

interface Props { onUpload: (files: File[]) => void; disabled?: boolean; }

export default function FileUploader({ onUpload, disabled }: Props) {
  const { t } = useTranslation('ingest');
  const handleDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); if (disabled) return; const files = Array.from(e.dataTransfer.files); if (files.length > 0) onUpload(files); }, [onUpload, disabled]);
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => { const files = Array.from(e.target.files ?? []); if (files.length > 0) onUpload(files); }, [onUpload]);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={e => e.preventDefault()}
      className="p-12 text-center transition-colors"
      style={{
        border: `2px dashed ${disabled ? "var(--color-border)" : "var(--color-brand-amber)"}`,
        background: disabled ? "var(--bg-surface)" : "var(--bg-surface-hover)",
        color: disabled ? "var(--color-text-muted)" : "var(--color-text-secondary)",
        cursor: disabled ? "default" : "pointer",
        minHeight: "200px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <p className="text-2xl mb-2" style={{ color: disabled ? "var(--color-text-muted)" : "var(--color-text)" }}>
        {t('dropFiles')}
      </p>
      <p className="text-sm mb-4" style={{ color: "var(--color-text-muted)" }}>
        {t('fileTypes')}
      </p>
      <label
        className="inline-block px-4 py-2 text-sm cursor-pointer"
        style={{
          background: disabled ? "var(--color-border)" : "var(--color-dark)",
          color: disabled ? "var(--color-text-muted)" : "var(--color-text-on-brand)",
        }}
      >
        {t('browseFiles')}
        <input type="file" multiple onChange={handleChange} disabled={disabled} className="hidden" accept=".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.png,.jpg,.jpeg,.heic,.webp,.zip" />
      </label>
    </div>
  );
}
