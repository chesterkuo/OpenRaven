import SourceCitation from "./SourceCitation";

interface Props { role: "user" | "assistant"; content: string; }

function renderContentWithCitations(content: string) {
  const sourcePattern = /\[Source:\s*([^\]]+?)(?::(\d+)-(\d+))?\]/g;
  const parts: (string | { document: string; charStart?: number; charEnd?: number })[] = [];
  let lastIndex = 0;
  for (const match of content.matchAll(sourcePattern)) {
    if (match.index! > lastIndex) parts.push(content.slice(lastIndex, match.index!));
    parts.push({ document: match[1].trim(), charStart: match[2] ? Number(match[2]) : undefined, charEnd: match[3] ? Number(match[3]) : undefined });
    lastIndex = match.index! + match[0].length;
  }
  if (lastIndex < content.length) parts.push(content.slice(lastIndex));
  return parts.map((part, i) => typeof part === "string" ? <span key={i}>{part}</span> : <SourceCitation key={i} document={part.document} excerpt="" charStart={part.charStart} charEnd={part.charEnd} />);
}

export default function ChatMessage({ role, content }: Props) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className="max-w-[80%] px-4 py-2.5 text-sm leading-relaxed"
        style={isUser
          ? { background: "linear-gradient(135deg, #fb6424, #fa520f)", color: "var(--color-text-on-brand)" }
          : { background: "var(--bg-surface)", color: "var(--color-text)", boxShadow: "var(--shadow-card)" }
        }
      >
        <div className="whitespace-pre-wrap">{isUser ? content : renderContentWithCitations(content)}</div>
      </div>
    </div>
  );
}
