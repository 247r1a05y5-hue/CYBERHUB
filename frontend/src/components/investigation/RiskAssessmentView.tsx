import React, { useState } from "react";
import {
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  Info,
  CheckCircle2,
  TrendingUp,
  Globe,
  Database,
  Layers,
} from "lucide-react";
import { api } from "../../services/api";

interface RiskFactor {
  name: string;
  weight: number;
  contribution: number;
  detail: string;
}

interface RiskAssessmentProps {
  caseId: string;
  riskData: {
    risk_level: string;
    score: number;
    explanation: string;
    risk_policy_version?: string;
    contributing_factors?: RiskFactor[];
    verified_count?: number;
    unique_domains?: number;
  } | null;
  onRiskUpdated: (newRiskData: any) => void;
}

export const RiskAssessmentView: React.FC<RiskAssessmentProps> = ({
  caseId,
  riskData,
  onRiskUpdated,
}) => {
  const [isCalculating, setIsCalculating] = useState(false);

  const recalculateRisk = async () => {
    setIsCalculating(true);
    try {
      const res = await api.post(`/investigations/${caseId}/risk`);
      if (res.data) {
        onRiskUpdated(res.data);
      }
    } catch (err) {
      console.error("Failed to recalculate risk:", err);
    } finally {
      setIsCalculating(false);
    }
  };

  const getTierColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case "CRITICAL":
        return {
          bg: "bg-red-500/10",
          border: "border-red-500/30",
          text: "text-red-400",
          ring: "ring-red-500/20",
        };
      case "HIGH":
        return {
          bg: "bg-orange-500/10",
          border: "border-orange-500/30",
          text: "text-orange-400",
          ring: "ring-orange-500/20",
        };
      case "MEDIUM":
        return {
          bg: "bg-yellow-500/10",
          border: "border-yellow-500/30",
          text: "text-yellow-400",
          ring: "ring-yellow-500/20",
        };
      case "LOW":
      default:
        return {
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/30",
          text: "text-emerald-400",
          ring: "ring-emerald-500/20",
        };
    }
  };

  const currentLevel = riskData?.risk_level || "LOW";
  const colors = getTierColor(currentLevel);
  const score = riskData?.score !== undefined ? riskData.score : 0.0;
  const verifiedCount = riskData?.verified_count !== undefined ? riskData.verified_count : 0;
  const factors = riskData?.contributing_factors || [];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-5">
        <div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-400" />
            <h2 className="text-base font-bold text-[var(--text-primary)]">Deterministic Risk Assessment Engine</h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Standardized multi-factor exposure scoring strictly gated by human-verified public occurrences.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-secondary)]">
            Policy: {riskData?.risk_policy_version || "v1"}
          </span>
          <button
            onClick={recalculateRisk}
            disabled={isCalculating}
            className="px-3.5 py-1.5 rounded-lg bg-[var(--text-primary)] text-[var(--bg)] hover:opacity-90 text-xs font-semibold transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isCalculating ? "animate-spin" : ""}`} />
            {isCalculating ? "Recalculating..." : "Recalculate Risk"}
          </button>
        </div>
      </div>

      {/* Main Score Hero Card */}
      <div className={`bg-[var(--card-bg)] border ${colors.border} rounded-xl p-6 relative overflow-hidden`}>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <span className="text-[11px] uppercase font-bold tracking-wider text-[var(--text-tertiary)]">
              Composite Exposure Tier
            </span>
            <div className="flex items-baseline gap-3 mt-1">
              <span className={`text-3xl font-extrabold ${colors.text}`}>
                {currentLevel} RISK
              </span>
              <span className="text-lg font-mono text-[var(--text-secondary)]">
                Score: {score.toFixed(1)} / 100.0
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-2 max-w-2xl leading-relaxed">
              {riskData?.explanation || "Zero verified exposure endpoints confirmed. Minimal exposure risk detected."}
            </p>
          </div>

          <div className="flex items-center gap-4 shrink-0 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-3">
            <div className="text-center px-2">
              <span className="text-[10px] uppercase font-bold text-[var(--text-tertiary)] block">Verified Endpoints</span>
              <span className="text-lg font-bold text-emerald-400 font-mono">{verifiedCount}</span>
            </div>
            <div className="w-px h-8 bg-[var(--border)]" />
            <div className="text-center px-2">
              <span className="text-[10px] uppercase font-bold text-[var(--text-tertiary)] block">Domain Spread</span>
              <span className="text-lg font-bold text-blue-400 font-mono">{riskData?.unique_domains || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Factor Cards Grid */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
          Multi-Factor Risk Breakdown (Weights & Contributions)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Factor 1: Verified Findings Volume */}
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                1. Verified Findings Volume
              </span>
              <span className="text-xs font-mono text-[var(--text-secondary)]">Weight: 35%</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              {factors.find((f) => f.name.includes("Volume"))?.detail || `${verifiedCount} verified exposure endpoints confirmed.`}
            </p>
            <div className="pt-2 border-t border-[var(--border)] flex items-center justify-between text-[11px] font-mono">
              <span className="text-[var(--text-tertiary)]">Contribution:</span>
              <span className="text-[var(--text-primary)] font-bold">
                {factors.find((f) => f.name.includes("Volume"))?.contribution !== undefined
                  ? `+${factors.find((f) => f.name.includes("Volume"))?.contribution} pts`
                  : "+0.0 pts"}
              </span>
            </div>
          </div>

          {/* Factor 2: Domain Spread */}
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-blue-400" />
                2. Domain Spread & Proliferation
              </span>
              <span className="text-xs font-mono text-[var(--text-secondary)]">Weight: 25%</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              {factors.find((f) => f.name.includes("Spread"))?.detail || "Discovered across distinct public domains."}
            </p>
            <div className="pt-2 border-t border-[var(--border)] flex items-center justify-between text-[11px] font-mono">
              <span className="text-[var(--text-tertiary)]">Contribution:</span>
              <span className="text-[var(--text-primary)] font-bold">
                {factors.find((f) => f.name.includes("Spread"))?.contribution !== undefined
                  ? `+${factors.find((f) => f.name.includes("Spread"))?.contribution} pts`
                  : "+0.0 pts"}
              </span>
            </div>
          </div>

          {/* Factor 3: Breach & High Risk */}
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-purple-400" />
                3. Breach & High-Risk Repositories
              </span>
              <span className="text-xs font-mono text-[var(--text-secondary)]">Weight: 30%</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              {factors.find((f) => f.name.includes("Breach"))?.detail || "No high-risk breach repositories identified."}
            </p>
            <div className="pt-2 border-t border-[var(--border)] flex items-center justify-between text-[11px] font-mono">
              <span className="text-[var(--text-tertiary)]">Contribution:</span>
              <span className="text-[var(--text-primary)] font-bold">
                {factors.find((f) => f.name.includes("Breach"))?.contribution !== undefined
                  ? `+${factors.find((f) => f.name.includes("Breach"))?.contribution} pts`
                  : "+0.0 pts"}
              </span>
            </div>
          </div>

          {/* Factor 4: Forensic Completeness */}
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-yellow-400" />
                4. Forensic Completeness & Clustering
              </span>
              <span className="text-xs font-mono text-[var(--text-secondary)]">Weight: 10%</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              {factors.find((f) => f.name.includes("Completeness"))?.detail || "Evidence artifacts sealed across correlation clusters."}
            </p>
            <div className="pt-2 border-t border-[var(--border)] flex items-center justify-between text-[11px] font-mono">
              <span className="text-[var(--text-tertiary)]">Contribution:</span>
              <span className="text-[var(--text-primary)] font-bold">
                {factors.find((f) => f.name.includes("Completeness"))?.contribution !== undefined
                  ? `+${factors.find((f) => f.name.includes("Completeness"))?.contribution} pts`
                  : "+0.0 pts"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
