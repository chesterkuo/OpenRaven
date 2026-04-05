import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import FileUploader from "../components/FileUploader";

interface IngestResult { files_processed: number; entities_extracted: number; articles_generated: number; errors: string[]; }
interface SchemaOption { id: string; name: string; description: string; }

export default function IngestPage() {
  const { t } = useTranslation('ingest');
  const [result, setResult] = useState<IngestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [schemas, setSchemas] = useState<SchemaOption[]>([]);
  const [selectedSchema, setSelectedSchema] = useState("auto");

  useEffect(() => {
    fetch("/api/schemas")
      .then((res) => res.json())
      .then((data: SchemaOption[]) => setSchemas(data))
      .catch(() => setSchemas([]));
  }, []);

  async function handleUpload(files: File[]) {
    setLoading(true); setResult(null); setStage("uploading");
    const formData = new FormData();
    for (const file of files) formData.append("files", file);
    formData.append("schema", selectedSchema);
    try {
      setStage("processing");
      const res = await fetch("/api/ingest", { method: "POST", body: formData });
      const data = await res.json();
      setResult(data);
      setStage("done");
    } catch {
      setResult({ files_processed: 0, entities_extracted: 0, articles_generated: 0, errors: [t('uploadError')] });
      setStage("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>{t('title')}</h1>

      <div className="mb-6">
        <label
          htmlFor="schema-select"
          className="block text-sm mb-2"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {t('schemaLabel')}
        </label>
        <select
          id="schema-select"
          value={selectedSchema}
          onChange={(e) => setSelectedSchema(e.target.value)}
          disabled={loading}
          className="w-full max-w-xs px-3 py-2 text-sm"
          style={{
            background: "var(--bg-surface)",
            color: "var(--color-text)",
            border: "1px solid var(--color-border)",
            borderRadius: "4px",
          }}
        >
          <option value="auto">{t('schemaAuto')}</option>
          {schemas.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {selectedSchema !== "auto" && (
          <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
            {schemas.find((s) => s.id === selectedSchema)?.description ?? ""}
          </p>
        )}
      </div>

      <FileUploader onUpload={handleUpload} disabled={loading} />
      <p className="mt-3 text-xs" style={{ color: "var(--color-text-muted)" }}>
        {t('importHint')}
      </p>
      {loading && stage && (
        <div className="mt-6">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--color-brand)", borderTopColor: "transparent" }} />
            <span style={{ color: "var(--color-text-secondary)" }}>{t(`stages.${stage}`, { defaultValue: stage })}</span>
          </div>
          <div className="mt-2 h-1 overflow-hidden" style={{ background: "var(--color-border)" }}>
            <div className="h-full animate-pulse" style={{ background: "var(--color-brand)", width: stage === "processing" ? "60%" : "20%" }} />
          </div>
        </div>
      )}
      {result && !loading && (
        <div className="mt-8 grid grid-cols-3 gap-6 text-center">
          {[
            { label: t('stats.filesProcessed'), value: result.files_processed },
            { label: t('stats.entitiesExtracted'), value: result.entities_extracted },
            { label: t('stats.articlesGenerated'), value: result.articles_generated },
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
