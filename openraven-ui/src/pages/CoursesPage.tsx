import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

interface Course {
  id: string;
  title: string;
  audience: string;
  chapter_count: number;
  created_at: string;
}

interface GenerateJob {
  job_id: string;
  stage: string;
  chapters_total: number;
  chapters_done: number;
  course_id: string;
  error: string;
}

export default function CoursesPage() {
  const { t } = useTranslation('courses');
  const [courses, setCourses] = useState<Course[]>([]);
  const [title, setTitle] = useState("");
  const [audience, setAudience] = useState("");
  const [objectives, setObjectives] = useState("");
  const [generating, setGenerating] = useState(false);
  const [job, setJob] = useState<GenerateJob | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadCourses();
  }, []);

  async function loadCourses() {
    try {
      const res = await fetch("/api/courses");
      setCourses(await res.json());
    } catch { /* ignore */ }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setGenerating(true);
    setError("");
    setJob(null);
    try {
      const res = await fetch("/api/courses/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          audience: audience.trim() || "General",
          objectives: objectives.trim()
            ? objectives.split("\n").map(o => o.trim()).filter(Boolean)
            : [],
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || t('generationFailed')); setGenerating(false); return; }

      const jobId = data.job_id;
      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/courses/generate/${jobId}`);
          const statusData: GenerateJob = await statusRes.json();
          setJob(statusData);
          if (statusData.stage === "done" || statusData.stage === "error") {
            clearInterval(poll);
            setGenerating(false);
            if (statusData.stage === "error") setError(statusData.error || t('generationFailed'));
            else { setTitle(""); setAudience(""); setObjectives(""); loadCourses(); }
          }
        } catch { /* ignore polling errors */ }
      }, 2000);
      setTimeout(() => { clearInterval(poll); setGenerating(false); }, 600_000);
    } catch {
      setError(t('startFailed'));
      setGenerating(false);
    }
  }

  async function handleDelete(courseId: string) {
    try {
      await fetch(`/api/courses/${courseId}`, { method: "DELETE" });
      loadCourses();
    } catch { /* ignore */ }
  }

  function handleDownload(courseId: string) {
    window.open(`/api/courses/${courseId}/download`, "_blank");
  }

  const progressText = job
    ? job.stage === "planning" ? t('progress.planning')
    : job.stage === "generating" ? t('progress.generating', { done: job.chapters_done, total: job.chapters_total })
    : job.stage === "done" ? t('progress.done')
    : job.stage === "error" ? t('progress.error')
    : job.stage
    : "";

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>
        {t('title')}
      </h1>

      <div className="p-6 mb-8" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
        <h2 className="text-lg mb-4" style={{ color: "var(--color-text)" }}>{t('generateCourse')}</h2>
        <form onSubmit={handleGenerate}>
          <div className="mb-4">
            <label className="block text-sm mb-1" style={{ color: "var(--color-text-muted)" }}>
              {t('courseTitle')}
            </label>
            <input
              type="text" value={title} onChange={e => setTitle(e.target.value)}
              placeholder={t('courseTitlePlaceholder')}
              required
              className="w-full px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm mb-1" style={{ color: "var(--color-text-muted)" }}>
              {t('targetAudience')}
            </label>
            <input
              type="text" value={audience} onChange={e => setAudience(e.target.value)}
              placeholder={t('audiencePlaceholder')}
              className="w-full px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm mb-1" style={{ color: "var(--color-text-muted)" }}>
              {t('learningObjectives')}
            </label>
            <textarea
              value={objectives} onChange={e => setObjectives(e.target.value)}
              placeholder={t('objectivesPlaceholder')}
              rows={3}
              className="w-full px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)", resize: "vertical" }}
            />
          </div>
          <button
            type="submit" disabled={generating || !title.trim()}
            className="text-sm px-4 py-2 uppercase cursor-pointer disabled:opacity-50 disabled:cursor-default"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
          >
            {generating ? t('generating') : t('generate')}
          </button>
        </form>

        {generating && progressText && (
          <div className="mt-4 text-sm" style={{ color: "var(--color-text-muted)" }}>
            {progressText}
            {job && job.stage === "generating" && job.chapters_total > 0 && (
              <div className="mt-2" style={{ height: 4, background: "var(--color-border)", borderRadius: 2 }}>
                <div style={{
                  height: "100%", borderRadius: 2,
                  background: "var(--color-brand)",
                  width: `${Math.round((job.chapters_done / job.chapters_total) * 100)}%`,
                  transition: "width 0.3s",
                }} />
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-4 text-sm" style={{ color: "var(--color-error)" }}>{error}</div>
        )}
      </div>

      {courses.length > 0 && (
        <div>
          <h2 className="text-lg mb-4" style={{ color: "var(--color-text)" }}>{t('generatedCourses')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {courses.map(c => (
              <div key={c.id} className="p-4" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
                <h3 className="text-base mb-1" style={{ color: "var(--color-text)" }}>{c.title}</h3>
                <div className="text-xs mb-3" style={{ color: "var(--color-text-muted)" }}>
                  {t('chaptersCount', { count: c.chapter_count })} &middot; {c.audience} &middot; {new Date(c.created_at).toLocaleDateString()}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDownload(c.id)}
                    className="text-sm px-3 py-1 cursor-pointer"
                    style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}
                  >
                    {t('download', { ns: 'common' })}
                  </button>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="text-sm px-3 py-1 cursor-pointer"
                    style={{ background: "var(--bg-surface-hover)", color: "var(--color-error)" }}
                  >
                    {t('delete', { ns: 'common' })}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {courses.length === 0 && !generating && (
        <div className="text-center py-12" style={{ color: "var(--color-text-muted)" }}>
          {t('emptyMessage')}
        </div>
      )}
    </div>
  );
}
