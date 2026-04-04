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

  if (loading) return <div className="text-gray-500">Loading wiki...</div>;

  if (articles.length === 0) {
    return (
      <div className="text-gray-500">
        <h1 className="text-2xl font-bold text-white mb-2">Knowledge Wiki</h1>
        <p>No articles yet. Add files to start generating wiki articles.</p>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <div className="w-64 shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Articles ({articles.length})</h2>
          <a
            href="/api/wiki/export"
            download
            className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-800 text-gray-200 hover:bg-gray-700"
          >
            Export
          </a>
        </div>
        <div className="flex flex-col gap-1">
          {articles.map((a) => (
            <button
              key={a.slug}
              onClick={() => loadArticle(a.slug)}
              className={`text-left text-sm px-2 py-1 rounded truncate ${
                selected?.slug === a.slug
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              }`}
            >
              {a.title}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 min-w-0">
        {selected ? (
          <div className="whitespace-pre-wrap text-sm text-gray-300 leading-relaxed">{selected.content}</div>
        ) : (
          <div className="text-gray-600 text-sm">Select an article to read</div>
        )}
      </div>
    </div>
  );
}
