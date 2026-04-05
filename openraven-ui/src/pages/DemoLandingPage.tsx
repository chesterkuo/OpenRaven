import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTranslation } from "react-i18next";

interface ThemeInfo {
  slug: string;
  name: string;
  description: string;
}

export default function DemoLandingPage() {
  const [themes, setThemes] = useState<ThemeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const { startDemo } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  useEffect(() => {
    fetch("/api/demo/themes")
      .then((r) => r.json())
      .then(setThemes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleStart(slug: string) {
    setStarting(slug);
    try {
      await startDemo(slug);
      navigate("/demo/ask");
    } catch {
      setStarting(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-page)" }}>
        <span style={{ color: "var(--color-text-muted)" }}>{t("loading")}</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-8 p-8" style={{ background: "var(--bg-page)" }}>
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--color-text)" }}>
          Try OpenRaven
        </h1>
        <p style={{ color: "var(--color-text-muted)" }}>
          Explore a sample knowledge base — no account required.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
        {themes.map((theme) => (
          <button
            key={theme.slug}
            onClick={() => handleStart(theme.slug)}
            disabled={starting !== null}
            className="p-6 rounded-xl text-left transition-transform hover:scale-105"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <h2 className="text-xl font-semibold mb-2" style={{ color: "var(--color-text)" }}>
              {theme.name}
            </h2>
            <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              {theme.description}
            </p>
            {starting === theme.slug && (
              <span className="text-xs mt-2 block" style={{ color: "var(--color-primary)" }}>
                Starting...
              </span>
            )}
          </button>
        ))}
      </div>
      <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
        Want the full experience?{" "}
        <a href="/signup" style={{ color: "var(--color-primary)" }}>
          Create an account
        </a>
      </p>
    </div>
  );
}
