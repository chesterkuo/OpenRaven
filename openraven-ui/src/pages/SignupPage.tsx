import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { useNavigate, Link } from "react-router-dom";

export default function SignupPage() {
  const { signup, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) { setError("Passwords do not match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await signup(name, email, password);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-page)" }}>
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
          <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="Full name" aria-label="Full name" required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" aria-label="Email" required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password (min 8 chars)" aria-label="Password" required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Confirm password" aria-label="Confirm password" required
            className="px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          {error && <p className="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>}
          <button type="submit" disabled={loading}
            className="py-2.5 text-base uppercase cursor-pointer disabled:opacity-50"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
          <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>or</span>
          <div className="flex-1 h-px" style={{ background: "var(--color-border)" }} />
        </div>

        <button onClick={loginWithGoogle} className="w-full py-2.5 text-base cursor-pointer"
          style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
          Sign up with Google
        </button>

        <div className="mt-6 text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
          Already have an account?{" "}
          <Link to="/login" className="hover:opacity-70" style={{ color: "var(--color-brand)" }}>Sign in</Link>
        </div>
      </div>
    </div>
  );
}
