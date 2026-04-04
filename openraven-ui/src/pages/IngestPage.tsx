import { useState } from "react";
import FileUploader from "../components/FileUploader";

interface IngestResult { files_processed: number; entities_extracted: number; articles_generated: number; errors: string[]; }

export default function IngestPage() {
  const [result, setResult] = useState<IngestResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleUpload(files: File[]) {
    setLoading(true); setResult(null);
    const formData = new FormData();
    for (const file of files) formData.append("files", file);
    try {
      const res = await fetch("/api/ingest", { method: "POST", body: formData });
      setResult(await res.json());
    } catch { setResult({ files_processed: 0, entities_extracted: 0, articles_generated: 0, errors: ["Failed to connect to the knowledge engine."] }); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Add Documents</h1>
      <FileUploader onUpload={handleUpload} disabled={loading} />
      {loading && <div className="mt-6 text-gray-400 animate-pulse">Processing documents... This may take a few minutes.</div>}
      {result && (
        <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="font-semibold mb-2">Results</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div><div className="text-2xl font-bold text-blue-400">{result.files_processed}</div><div className="text-xs text-gray-500">Files processed</div></div>
            <div><div className="text-2xl font-bold text-green-400">{result.entities_extracted}</div><div className="text-xs text-gray-500">Entities extracted</div></div>
            <div><div className="text-2xl font-bold text-purple-400">{result.articles_generated}</div><div className="text-xs text-gray-500">Articles generated</div></div>
          </div>
          {result.errors.length > 0 && <div className="mt-3 text-red-400 text-sm">{result.errors.map((e, i) => <div key={i}>{e}</div>)}</div>}
        </div>
      )}
    </div>
  );
}
