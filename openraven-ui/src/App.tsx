import { Routes, Route, NavLink, useLocation, Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { LanguageSelector } from "./components/LanguageSelector";
import AskPage from "./pages/AskPage";
import StatusPage from "./pages/StatusPage";
import IngestPage from "./pages/IngestPage";
import GraphPage from "./pages/GraphPage";
import WikiPage from "./pages/WikiPage";
import ConnectorsPage from "./pages/ConnectorsPage";
import AgentsPage from "./pages/AgentsPage";
import CoursesPage from "./pages/CoursesPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import AuditLogPage from "./pages/AuditLogPage";

function BlockLogo() {
  return (
    <div className="flex gap-0.5">
      <div className="w-1 h-5" style={{ background: "#ffd900" }} />
      <div className="w-1 h-5" style={{ background: "#ffa110" }} />
      <div className="w-1 h-5" style={{ background: "#fb6424" }} />
      <div className="w-1 h-5" style={{ background: "#fa520f" }} />
    </div>
  );
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? "text-[var(--color-brand)] border-b-2 border-[var(--color-brand)] pb-1 text-sm"
    : "text-[var(--color-text-secondary)] hover:text-[var(--color-brand)] text-sm pb-1";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const { t } = useTranslation('common');
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-page)" }}>
      <span style={{ color: "var(--color-text-muted)" }}>{t('loading')}</span>
    </div>
  );
  if (!user) return <Navigate to="/login" />;
  return <>{children}</>;
}

function AppShell() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { t } = useTranslation('common');
  const isGraphPage = location.pathname === "/graph";

  return (
    <div className="h-screen flex flex-col" style={{ background: "var(--bg-page)", color: "var(--color-text)" }}>
      <nav className="px-6 py-3 flex items-center gap-6 shrink-0 sticky top-0 z-50"
        style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)" }}>
        <div className="flex items-center gap-2">
          <BlockLogo />
          <span className="text-lg tracking-tight" style={{ color: "var(--color-text)", letterSpacing: "-0.5px" }}>OpenRaven</span>
        </div>
        <NavLink to="/" end className={navLinkClass}>{t('nav.ask')}</NavLink>
        <NavLink to="/ingest" className={navLinkClass}>{t('nav.addFiles')}</NavLink>
        <NavLink to="/graph" className={navLinkClass}>{t('nav.graph')}</NavLink>
        <NavLink to="/wiki" className={navLinkClass}>{t('nav.wiki')}</NavLink>
        <NavLink to="/connectors" className={navLinkClass}>{t('nav.connectors')}</NavLink>
        <NavLink to="/agents" className={navLinkClass}>{t('nav.agents')}</NavLink>
        <NavLink to="/courses" className={navLinkClass}>{t('nav.courses')}</NavLink>
        <NavLink to="/status" className={navLinkClass}>{t('nav.status')}</NavLink>
        <NavLink to="/audit" className={navLinkClass}>Audit</NavLink>
        {user && (
          <div className="ml-auto flex items-center gap-3">
            <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>{user.email}</span>
            <LanguageSelector />
            <button onClick={logout} className="text-sm cursor-pointer hover:opacity-70" style={{ color: "var(--color-brand)" }}>
              {t('signOut')}
            </button>
          </div>
        )}
      </nav>
      <main className={isGraphPage ? "flex-1 flex flex-col min-h-0" : "max-w-4xl mx-auto px-6 py-8 w-full flex-1"}>
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/wiki" element={<WikiPage />} />
          <Route path="/connectors" element={<ConnectorsPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/courses" element={<CoursesPage />} />
          <Route path="/status" element={<StatusPage />} />
          <Route path="/audit" element={<AuditLogPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/*" element={
          <AuthGuard>
            <AppShell />
          </AuthGuard>
        } />
      </Routes>
    </AuthProvider>
  );
}
