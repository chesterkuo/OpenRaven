import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { useNavigate, Link } from "react-router-dom";
import { LanguageSelector } from "../components/LanguageSelector";

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err: any) {
      setError(err.message || t('loginFailed'));
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

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email" value={email} onChange={e => setEmail(e.target.value)}
            placeholder={t('email')} aria-label={t('email')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
          <input
            type="password" value={password} onChange={e => setPassword(e.target.value)}
            placeholder={t('password')} aria-label={t('password')} required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
          {error && <p className="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>}
          <button
            type="submit" disabled={loading}
            className="py-2.5 text-base uppercase cursor-pointer disabled:opacity-50"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
          >
            {loading ? t('signingIn') : t('signIn')}
          </button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
          <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>{t('or', { ns: 'common' })}</span>
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
        </div>

        <button
          onClick={loginWithGoogle}
          className="w-full py-2.5 text-base cursor-pointer"
          style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}
        >
          {t('signInGoogle')}
        </button>

        <div className="mt-6 text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
          <Link to="/reset-password" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>
            {t('forgotPassword')}
          </Link>
          <span className="mx-2">·</span>
          <Link to="/signup" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>
            {t('createAccount')}
          </Link>
        </div>
      </div>
    </div>
  );
}
