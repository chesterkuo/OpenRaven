import { useCallback } from "react";

interface Props { onUpload: (files: File[]) => void; disabled?: boolean; }

export default function FileUploader({ onUpload, disabled }: Props) {
  const handleDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); if (disabled) return; const files = Array.from(e.dataTransfer.files); if (files.length > 0) onUpload(files); }, [onUpload, disabled]);
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => { const files = Array.from(e.target.files ?? []); if (files.length > 0) onUpload(files); }, [onUpload]);

  return (
    <div onDrop={handleDrop} onDragOver={e => e.preventDefault()}
      className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${disabled ? "border-gray-800 text-gray-600" : "border-gray-700 text-gray-400 hover:border-blue-500 hover:text-blue-400 cursor-pointer"}`}>
      <p className="text-lg mb-2">Drop files here</p>
      <p className="text-sm mb-4">PDF, DOCX, PPTX, XLSX, Markdown, TXT</p>
      <label className={`inline-block px-4 py-2 rounded-lg text-sm font-medium ${disabled ? "bg-gray-800 text-gray-600" : "bg-gray-800 text-gray-300 hover:bg-gray-700 cursor-pointer"}`}>
        Browse files
        <input type="file" multiple onChange={handleChange} disabled={disabled} className="hidden" accept=".pdf,.docx,.pptx,.xlsx,.md,.txt,.html" />
      </label>
    </div>
  );
}
