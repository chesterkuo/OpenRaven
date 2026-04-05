import { useState, useEffect } from "react";

const STORAGE_KEY = "openraven_onboarding_dismissed";

interface StatusData {
  total_files: number;
  total_entities: number;
  topics_count: number;
}

export default function OnboardingBanner() {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(STORAGE_KEY) === "true");

  useEffect(() => {
    if (dismissed) return;
    fetch("/api/status")
      .then(r => r.json())
      .then((data) => {
        const totalFiles = data.total_files ?? 0;
        const totalEntities = data.total_entities ?? 0;
        const topicsCount = data.topic_count ?? 0;
        if (totalFiles > 0) {
          setStatus({ total_files: totalFiles, total_entities: totalEntities, topics_count: topicsCount });
        }
      })
      .catch(() => {});
  }, [dismissed]);

  function handleDismiss() {
    localStorage.setItem(STORAGE_KEY, "true");
    setDismissed(true);
  }

  if (dismissed || !status) return null;

  return (
    <div
      className="mb-6 p-4 flex items-start justify-between gap-4"
      style={{
        background: "var(--color-surface-secondary, #fff8f0)",
        borderLeft: "3px solid var(--color-brand, #fa520f)",
        boxShadow: "var(--shadow-golden, 0 1px 3px rgba(250,82,15,0.1))",
      }}
    >
      <div>
        <p className="text-sm" style={{ color: "var(--color-text)" }}>
          <strong>Your knowledge base is ready!</strong>{" "}
          {status.total_entities > 0
            ? `We found ${status.total_entities} concepts${status.topics_count > 0 ? ` across ${status.topics_count} topics` : ""}. `
            : `${status.total_files} files processed. `}
          Ask a question to explore your knowledge.
        </p>
      </div>
      <button
        onClick={handleDismiss}
        className="text-xs cursor-pointer shrink-0 px-2 py-1"
        style={{ color: "var(--color-text-muted)", background: "transparent", border: "none" }}
        aria-label="Dismiss onboarding banner"
      >
        Dismiss
      </button>
    </div>
  );
}
