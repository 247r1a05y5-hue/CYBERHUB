import React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { CheckCircle2, Clock, XCircle, AlertCircle, Search, Activity, WifiOff, AlertTriangle, ShieldCheck } from "lucide-react";

/* ─────────────────────────────────────────────
   FindingStatusBadge
   Reflects actual API verification_status.
   VERIFIED is NEVER set automatically — only
   reflects the value returned by the backend.
───────────────────────────────────────────── */
type FindingStatus = "DISCOVERED" | "CANDIDATE" | "VERIFIED" | "REJECTED" | "UNCERTAIN";

const FINDING_STATUS_CONFIG: Record<FindingStatus, {
  label: string;
  icon: React.ElementType;
  className: string;
}> = {
  DISCOVERED: {
    label: "Discovered",
    icon: Search,
    className: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20",
  },
  CANDIDATE: {
    label: "Candidate",
    icon: Clock,
    className: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  },
  VERIFIED: {
    label: "Verified",
    icon: CheckCircle2,
    className: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
  },
  REJECTED: {
    label: "Rejected",
    icon: XCircle,
    className: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20",
  },
  UNCERTAIN: {
    label: "Uncertain",
    icon: AlertCircle,
    className: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20",
  },
};

interface FindingStatusBadgeProps {
  status: FindingStatus;
  className?: string;
}

export const FindingStatusBadge: React.FC<FindingStatusBadgeProps> = ({ status, className }) => {
  const config = FINDING_STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <Badge
      variant="outline"
      className={cn("flex items-center gap-1 text-[11px] font-medium px-2 py-0.5", config.className, className)}
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {config.label}
    </Badge>
  );
};

/* ─────────────────────────────────────────────
   ProviderStatusBadge
   Never fabricates provider state.
───────────────────────────────────────────── */
type ProviderStatus = "CONFIGURED" | "NOT_CONFIGURED" | "LIVE" | "ERROR" | "RATE_LIMITED";

const PROVIDER_STATUS_CONFIG: Record<ProviderStatus, {
  label: string;
  icon: React.ElementType;
  className: string;
}> = {
  CONFIGURED:     { label: "Configured",     icon: ShieldCheck,    className: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20" },
  NOT_CONFIGURED: { label: "Not Configured", icon: WifiOff,        className: "bg-zinc-500/10 text-zinc-500 border-zinc-500/20" },
  LIVE:           { label: "Live",           icon: Activity,       className: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20" },
  ERROR:          { label: "Error",          icon: AlertTriangle,  className: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20" },
  RATE_LIMITED:   { label: "Rate Limited",   icon: Clock,          className: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20" },
};

interface ProviderStatusBadgeProps {
  status: ProviderStatus;
  className?: string;
}

export const ProviderStatusBadge: React.FC<ProviderStatusBadgeProps> = ({ status, className }) => {
  const config = PROVIDER_STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <Badge
      variant="outline"
      className={cn("flex items-center gap-1 text-[11px] font-medium px-2 py-0.5", config.className, className)}
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {config.label}
    </Badge>
  );
};

/* ─────────────────────────────────────────────
   RiskBadge
   Four-tier scale matching the backend risk engine.
   CRITICAL / HIGH / MEDIUM / LOW only.
───────────────────────────────────────────── */
type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

const RISK_CONFIG: Record<RiskLevel, { className: string }> = {
  CRITICAL: { className: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30 font-semibold" },
  HIGH:     { className: "bg-orange-500/15 text-orange-700 dark:text-orange-400 border-orange-500/30" },
  MEDIUM:   { className: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30" },
  LOW:      { className: "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30" },
};

interface RiskBadgeProps {
  level: RiskLevel;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, className }) => (
  <Badge
    variant="outline"
    className={cn("text-[11px] px-2 py-0.5", RISK_CONFIG[level].className, className)}
  >
    {level.charAt(0) + level.slice(1).toLowerCase()}
  </Badge>
);

/* ─────────────────────────────────────────────
   ConfidenceBadge
   Numeric similarity score (0–1) with color tier.
───────────────────────────────────────────── */
interface ConfidenceBadgeProps {
  score: number; // 0.0 – 1.0
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score, className }) => {
  const pct = Math.round(score * 100);
  const tierClass =
    pct >= 90 ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20" :
    pct >= 70 ? "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20" :
    pct >= 50 ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20" :
                "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20";

  return (
    <Badge
      variant="outline"
      className={cn("text-[11px] font-mono px-2 py-0.5 tabular-nums", tierClass, className)}
    >
      {pct}% match
    </Badge>
  );
};

/* ─────────────────────────────────────────────
   VerificationBadge
   Always shows "Requires Analyst Review" until
   human verification is explicitly submitted.
   Never auto-sets VERIFIED.
───────────────────────────────────────────── */
interface VerificationBadgeProps {
  verified: boolean;
  className?: string;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({ verified, className }) => {
  if (verified) {
    return (
      <Badge
        variant="outline"
        className={cn("flex items-center gap-1 text-[11px] px-2 py-0.5 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20", className)}
      >
        <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
        Analyst Verified
      </Badge>
    );
  }
  return (
    <Badge
      variant="outline"
      className={cn("flex items-center gap-1 text-[11px] px-2 py-0.5 bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20", className)}
    >
      <AlertCircle className="w-3 h-3" aria-hidden="true" />
      Requires Review
    </Badge>
  );
};
