import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { LanguageSelector } from "../components/LanguageSelector";

export default function ResetPasswordPage() {
  const { t } = useTranslation('auth');
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setSent(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative" style={{ background: "var(--bg-page)" }}>
      <div className="absolute top-4 right-4">
        <LanguageSelector />
      </div>
      <div className="w-full max-w-sm p-8" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="flex gap-0.5">
            <div className="w-1.5 h-6" style={{ background: "#ffd900" }} />
            <div className="w-1.5 h-6" style={{ background: "#ffa110" }} />
            <div className="w-1.5 h-6" style={{ background: "#fb6424" }} />
            <div className="w-1.5 h-6" style={{ background: "#fa520f" }} />
          </div>
          <span className="text-2xl" style={{ color: "var(--color-text)", letterSpacing: "-0.5px" }}>OpenRaven</span>
        </div>

        {sent ? (
          <div className="text-center">
            <p className="text-base mb-4" style={{ color: "var(--color-text)" }}>
              {t('resetSent')}
            </p>
            <Link to="/login" style={{ color: "var(--color-brand)" }}>{t('backToSignIn')}</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              {t('resetInstructions')}
            </p>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder={t('email')} aria-label={t('email')} required
              className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <button type="submit" disabled={loading}
              className="py-2.5 text-base uppercase cursor-pointer disabled:opacity-50"
              style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
              {loading ? t('sending') : t('sendResetLink')}
            </button>
            <div className="text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
              <Link to="/login" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>{t('backToSignIn')}</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
