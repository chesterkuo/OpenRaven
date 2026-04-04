import { useState, useRef, useEffect } from "react";
import ChatMessage from "../components/ChatMessage";
import DiscoveryCard from "../components/DiscoveryCard";

interface SourceRef { document: string; excerpt: string; char_start: number; char_end: number; }
interface Message { role: "user" | "assistant"; content: string; sources?: SourceRef[]; }
interface Insight { insight_type: string; title: string; description: string; related_entities: string[]; }

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetch("/api/discovery").then(r => r.json()).then(setInsights).catch(() => {}); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, mode: "mix" }) });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.answer, sources: data.sources ?? [] }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Error: Could not reach the knowledge engine." }]);
    } finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {messages.length === 0 && insights.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-medium text-gray-500 mb-3">Discoveries from your knowledge base</h2>
          <div className="grid gap-3">{insights.map((insight, i) => <DiscoveryCard key={i} insight={insight} />)}</div>
        </div>
      )}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((msg, i) => (
          <div key={i}>
            <ChatMessage role={msg.role} content={msg.content} />
            {msg.sources && msg.sources.length > 0 && (
              <div className="ml-4 mt-1 mb-2 border-l-2 border-gray-800 pl-3">
                <div className="text-xs text-gray-500 mb-1">Sources ({msg.sources.length})</div>
                {msg.sources.map((s, j) => (
                  <div key={j} className="text-xs text-gray-400 mb-0.5">
                    <span className="text-blue-400">{s.document}</span>
                    {s.excerpt && <span className="ml-2 text-gray-500">— {s.excerpt}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-gray-500 text-sm animate-pulse">Thinking...</div>}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSubmit} className="flex gap-3 pt-4 border-t border-gray-800">
        <input type="text" value={input} onChange={e => setInput(e.target.value)} placeholder="Ask your knowledge base..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500" />
        <button type="submit" disabled={loading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-5 py-2.5 rounded-lg font-medium transition-colors">Ask</button>
      </form>
    </div>
  );
}
