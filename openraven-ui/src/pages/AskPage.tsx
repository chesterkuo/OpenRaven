import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import ChatMessage from "../components/ChatMessage";
import DiscoveryCard from "../components/DiscoveryCard";
import { useConversations } from "../hooks/useConversations";
import ConversationSidebar from "../components/ConversationSidebar";

const QUERY_MODES = ['mix', 'local', 'global', 'hybrid', 'naive', 'bypass'] as const;

interface SourceRef { document: string; excerpt: string; char_start: number; char_end: number; }
interface Message { role: "user" | "assistant"; content: string; sources?: SourceRef[]; }
interface Insight { insight_type: string; title: string; description: string; related_entities: string[]; }

export default function AskPage() {
  const { t, i18n } = useTranslation('ask');
  const {
    conversations, activeId, messages, setMessages,
    createConversation, loadConversation, deleteConversation, newChat,
  } = useConversations();
  const [searchParams, setSearchParams] = useSearchParams();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [mode, setMode] = useState("mix");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetch("/api/discovery").then(r => r.json()).then(setInsights).catch(() => {}); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    const cId = searchParams.get("c");
    if (cId && cId !== activeId) {
      loadConversation(cId);
    }
  }, []); // only on mount

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");

    // Create conversation if none active
    let convoId = activeId;
    if (!convoId) {
      convoId = await createConversation();
      setSearchParams({ c: convoId });
    }

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const history = messages.slice(-20).map((m) => ({ role: m.role, content: m.content }));
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          mode,
          locale: i18n.language,
          conversation_id: convoId,
          history,
        }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer, sources: data.sources ?? [] }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: t('errorReach') }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full">
      <div className="w-64 flex-shrink-0">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={(id) => { loadConversation(id); setSearchParams({ c: id }); }}
          onDelete={deleteConversation}
          onNewChat={() => { newChat(); setSearchParams({}); }}
        />
      </div>
      <div className="flex-1 flex flex-col h-[calc(100vh-8rem)] px-6">
        {messages.length === 0 && insights.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <h2 className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>
              {t('heroTitle')}
            </h2>
          </div>
        )}
        {messages.length === 0 && insights.length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>{t('discoveriesHeading')}</h2>
            <div className="grid grid-cols-2 gap-4">{insights.map((insight, i) => <DiscoveryCard key={i} insight={insight} />)}</div>
          </div>
        )}
        <div className="flex-1 overflow-y-auto space-y-4 pb-4">
          {messages.map((msg, i) => (
            <div key={i}>
              <ChatMessage role={msg.role} content={msg.content} />
              {msg.sources && msg.sources.length > 0 && (
                <div className="ml-4 mt-1 mb-2 pl-3" style={{ borderLeft: "2px solid var(--color-border)" }}>
                  <div className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>{t('sourcesCount', { count: msg.sources.length })}</div>
                  {msg.sources.map((s, j) => (
                    <div key={j} className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>
                      <span style={{ color: "var(--color-brand)" }}>{s.document}</span>
                      {s.excerpt && <span className="ml-2" style={{ color: "var(--color-text-muted)" }}>— {s.excerpt}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && <div className="text-sm animate-pulse" style={{ color: "var(--color-text-muted)" }}>{t('thinking')}</div>}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={handleSubmit} className="flex gap-3 pt-4 items-end" style={{ borderTop: "1px solid var(--color-border)" }}>
          <div className="flex flex-col gap-1">
            <label htmlFor="mode-select" className="text-xs" style={{ color: "var(--color-text-muted)" }}>{t('modeLabel')}</label>
            <select
              id="mode-select"
              value={mode}
              onChange={e => setMode(e.target.value)}
              className="px-2 py-2.5 text-sm cursor-pointer"
              aria-label="Query mode"
              title={t(`modeDesc.${mode}`)}
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
            >
              {QUERY_MODES.map(m => <option key={m} value={m}>{t(`modes.${m}`)}</option>)}
            </select>
          </div>
          <input type="text" value={input} onChange={e => setInput(e.target.value)} placeholder={t('placeholder')}
            aria-label={t('placeholder')}
            className="flex-1 px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <button type="submit" disabled={loading || !input.trim()}
            className="px-5 py-2.5 text-sm uppercase cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-default"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{t('submit')}</button>
        </form>
      </div>
    </div>
  );
}
