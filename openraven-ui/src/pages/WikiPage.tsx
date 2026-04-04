import { useEffect, useState } from "react";

interface WikiListItem { slug: string; title: string; }
interface WikiArticle { slug: string; title: string; content: string; }

export default function WikiPage() {
  const [articles, setArticles] = useState<WikiListItem[]>([]);
  const [selected, setSelected] = useState<WikiArticle | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/wiki").then(r => r.json()).then(setArticles).catch(() => {}).finally(() => setLoading(false));
  }, []);

  async function loadArticle(slug: string) {
    const res = await fetch(`/api/wiki/${encodeURIComponent(slug)}`);
    if (res.ok) setSelected(await res.json());
  }

  if (loading) return <div style={{ color: "var(--color-text-muted)" }}>Loading wiki...</div>;

  if (articles.length === 0) {
    return (
      <div>
        <h1 className="text-3xl mb-2" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Knowledge Wiki</h1>
        <p style={{ color: "var(--color-text-muted)" }}>No articles yet. Add files to start generating wiki articles.</p>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <div className="w-70 shrink-0" style={{ background: "var(--bg-surface-hover)" }}>
        <div className="flex items-center justify-between p-4">
          <h2 className="text-lg" style={{ color: "var(--color-text)" }}>Articles ({articles.length})</h2>
          <a href="/api/wiki/export" download className="text-xs px-3 py-1 uppercase"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>Export</a>
        </div>
        <div className="flex flex-col">
          {articles.map((a) => (
            <button key={a.slug} onClick={() => loadArticle(a.slug)}
              className="text-left text-sm px-4 py-2 truncate cursor-pointer transition-colors"
              style={selected?.slug === a.slug
                ? { background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", borderLeft: "4px solid var(--color-brand)", color: "var(--color-text)" }
                : { color: "var(--color-text-secondary)", borderLeft: "4px solid transparent" }
              }>
              {a.title}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 min-w-0">
        {selected ? (
          <div className="p-12" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)", maxWidth: "720px" }}>
            <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>{selected.title}</h1>
            <div className="whitespace-pre-wrap text-base leading-relaxed" style={{ color: "var(--color-text)" }}>{selected.content}</div>
          </div>
        ) : (
          <div className="text-sm" style={{ color: "var(--color-text-muted)" }}>Select an article to read</div>
        )}
      </div>
    </div>
  );
}
