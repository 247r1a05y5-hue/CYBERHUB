import React, { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Shield, ArrowRight, Lock, Mail, AlertCircle, Loader2 } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { formatErrorMessage, safeRenderText } from "../utils/errorUtils";

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading } = useAuthStore();

  const [email, setEmail] = useState("admin@cyberhub.dev");
  const [password, setPassword] = useState("Admin1234!");
  const [error, setError] = useState<string | null>(null);

  const from = (location.state as any)?.from?.pathname || "/dashboard";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const success = await login(email, password);
      if (success) {
        navigate(from, { replace: true });
      } else {
        setError("Invalid credentials or server unreachable.");
      }
    } catch (err: any) {
      setError(formatErrorMessage(err, "Authentication failed. Please check credentials."));
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg)] flex flex-col justify-center py-12 sm:px-6 lg:px-8 transition-colors">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Brand */}
        <Link to="/" className="flex items-center justify-center gap-2.5 mb-6 focus:outline-none">
          <div className="w-8 h-8 rounded-full border-2 border-[var(--text-primary)] flex items-center justify-center font-bold text-sm">
            C
          </div>
          <span className="font-bold text-base tracking-[0.2em] uppercase text-[var(--text-primary)]">
            CYBERHUB
          </span>
        </Link>

        <h2 className="text-center text-xl font-bold tracking-tight text-[var(--text-primary)]">
          Sign In to Command Center
        </h2>
        <p className="mt-1 text-center text-xs text-[var(--text-secondary)]">
          Authorized security intelligence and forensic investigation portal
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div
          className="bg-[var(--surface)] py-8 px-6 shadow-xl sm:rounded-2xl border border-[var(--border)] sm:px-10"
          style={{ boxShadow: "var(--card-shadow)" }}
        >
          {error && (
            <div className="mb-5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center gap-2.5 text-rose-500 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{safeRenderText(error)}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[var(--text-tertiary)] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@domain.com"
                  className="w-full h-10 pl-9 pr-3 text-xs bg-[var(--search-bg)] border border-[var(--search-border)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-[var(--text-primary)] transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[var(--text-tertiary)] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full h-10 pl-9 pr-3 text-xs bg-[var(--search-bg)] border border-[var(--search-border)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-[var(--text-primary)] transition-all"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full h-10 px-4 bg-[var(--text-primary)] text-[var(--bg)] text-xs font-semibold rounded-lg flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.99] transition-all disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Authenticating...</span>
                  </>
                ) : (
                  <>
                    <span>Enter Command Center</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 pt-5 border-t border-[var(--border)] text-center text-[11px] text-[var(--text-tertiary)] flex items-center justify-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-emerald-500" />
            <span>FIPS-140-3 & SOC 2 Type II Certified Session</span>
          </div>
        </div>

        <div className="text-center mt-6">
          <Link
            to="/"
            className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            ← Return to Landing Page
          </Link>
        </div>
      </div>
    </div>
  );
};
