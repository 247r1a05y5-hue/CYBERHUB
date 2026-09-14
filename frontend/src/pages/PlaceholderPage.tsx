import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Construction } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";

interface PlaceholderPageProps {
  title: string;
  subtitle: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  subtitle,
}) => {
  const navigate = useNavigate();

  return (
    <AppShell>
      <div className="mb-6">
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="inline-flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Command Center</span>
        </button>

        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] tracking-tight">
          {title}
        </h1>
        <p className="text-xs sm:text-sm text-[var(--text-secondary)] mt-1">
          {subtitle}
        </p>
      </div>

      <div
        className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-12 text-center max-w-2xl mx-auto mt-8"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <div className="w-14 h-14 rounded-2xl bg-[var(--icon-box-bg)] border border-[var(--icon-box-border)] flex items-center justify-center mx-auto mb-5">
          <Construction className="w-7 h-7 text-[var(--icon-color)]" />
        </div>
        <h2 className="text-base font-semibold text-[var(--text-primary)] mb-2">
          {title} — Connected Route
        </h2>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed max-w-md mx-auto mb-6">
          This route is registered and ready. Implementation of the full workflow UI will commence in the next phase upon receiving the reference design.
        </p>
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="px-4 py-2 text-xs font-medium bg-[var(--accent)] text-white dark:text-zinc-900 rounded-lg hover:opacity-90 transition-opacity"
        >
          Return to Command Center
        </button>
      </div>
    </AppShell>
  );
};
