import { useState } from "react";
import FileUploader from "../components/FileUploader";

interface IngestResult { files_processed: number; entities_extracted: number; articles_generated: number; errors: string[]; }

const STAGE_LABELS: Record<string, string> = {
  uploading: "Uploading files...",
  processing: "Processing documents...",
  done: "Complete",
  error: "Error occurred",
};

export default function IngestPage() {
  const [result, setResult] = useState<IngestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string | null>(null);

  async function handleUpload(files: File[]) {
    setLoading(true); setResult(null); setStage("uploading");
    const formData = new FormData();
    for (const file of files) formData.append("files", file);
    try {
      setStage("processing");
      const res = await fetch("/api/ingest", { method: "POST", body: formData });
      const data = await res.json();
      setResult(data);
      setStage("done");
    } catch {
      setResult({ files_processed: 0, entities_extracted: 0, articles_generated: 0, errors: ["Failed to connect to the knowledge engine."] });
      setStage("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Add Documents</h1>
      <FileUploader onUpload={handleUpload} disabled={loading} />
      {loading && stage && (
        <div className="mt-6">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--color-brand)", borderTopColor: "transparent" }} />
            <span style={{ color: "var(--color-text-secondary)" }}>{STAGE_LABELS[stage] ?? stage}</span>
          </div>
          <div className="mt-2 h-1 overflow-hidden" style={{ background: "var(--color-border)" }}>
            <div className="h-full animate-pulse" style={{ background: "var(--color-brand)", width: stage === "processing" ? "60%" : "20%" }} />
          </div>
        </div>
      )}
      {result && !loading && (
        <div className="mt-8 grid grid-cols-3 gap-6 text-center">
          {[
            { label: "Files processed", value: result.files_processed },
            { label: "Entities extracted", value: result.entities_extracted },
            { label: "Articles generated", value: result.articles_generated },
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
