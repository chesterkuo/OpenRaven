interface Props { document: string; excerpt: string; charStart?: number; charEnd?: number; }

export default function SourceCitation({ document, excerpt, charStart, charEnd }: Props) {
  const location = charStart != null && charEnd != null ? ` (chars ${charStart}-${charEnd})` : "";
  return (
    <span className="inline-flex items-center gap-1 text-xs text-blue-400 bg-blue-500/10 rounded px-1.5 py-0.5 mx-0.5 cursor-help" title={`${document}${location}\n${excerpt}`}>
      {document}
    </span>
  );
}
