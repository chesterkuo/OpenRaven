interface Props { document: string; excerpt: string; charStart?: number; charEnd?: number; }

export default function SourceCitation({ document, excerpt, charStart, charEnd }: Props) {
  const location = charStart != null && charEnd != null ? ` (chars ${charStart}-${charEnd})` : "";
  return (
    <span
      className="inline-flex items-center gap-1 text-xs cursor-help mx-0.5 px-1.5 py-0.5"
      style={{
        background: "var(--bg-surface-hover)",
        border: "1px solid var(--color-brand-amber)",
        color: "var(--color-text)",
      }}
      title={`${document}${location}\n${excerpt}`}
    >
      {document}
    </span>
  );
}
