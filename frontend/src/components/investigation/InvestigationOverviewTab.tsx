import React from "react";
import {
  ShieldCheck,
  AlertTriangle,
  FileText,
  Lock,
  Clock,
  Layers,
  Globe,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Database,
  ArrowUpRight,
} from "lucide-react";
import { StepId } from "./InvestigationStepper";

interface OverviewProps {
  caseData: {
    id: string;
    case_number: string;
    title: string;
    status: string;
    created_at?: string;
  } | null;
  pipelineResult: {
    reference_image_id?: string;
    sha256?: string;
    dimensions?: { width: number; height: number };
    quality?: { sharpness: number; brightness: number; contrast: number; is_usable: boolean };
    dinov2?: { model: string; dimension: number };
  } | null;
  previewUrl: string | null;
  metrics: {
    total_findings: number;
    verified_count: number;
    rejected_count: number;
    uncertain_count: number;
    cluster_count: number;
    evidence_count: number;
    reports_count: number;
    response_packages_count: number;
  };
  riskData: {
    risk_level: string;
    score: number;
    explanation: string;
    risk_policy_version?: string;
  } | null;
  recentTimeline: Array<{
    id: string;
    event_type: string;
    title: string;
    timestamp: string;
  }>;
  onNavigateStep: (step: StepId) => void;
}

export const InvestigationOverviewTab: React.FC<OverviewProps> = ({
  caseData,
  pipelineResult,
  previewUrl,
  metrics,
  riskData,
  recentTimeline,
  onNavigateStep,
}) => {
  const getRiskBadgeColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case "CRITICAL":
        return "bg-red-500/10 text-red-400 border-red-500/30";
      case "HIGH":
        return "bg-orange-500/10 text-orange-400 border-orange-500/30";
      case "MEDIUM":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
      case "LOW":
      default:
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-6 relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] overflow-hidden flex items-center justify-center shrink-0">
              {previewUrl ? (
                <img src={previewUrl} alt="Reference Subject" className="w-full h-full object-cover" />
              ) : (
                <ShieldCheck className="w-8 h-8 text-[var(--text-tertiary)]" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-secondary)]">
                  {caseData?.case_number || "EXP-PENDING"}
                </span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full border font-semibold ${getRiskBadgeColor(riskData?.risk_level || "LOW")}`}>
                  {riskData?.risk_level || "LOW"} RISK TIER
                </span>
              </div>
              <h2 className="text-lg font-bold text-[var(--text-primary)]">
                {caseData?.title || "Image Exposure Investigation"}
              </h2>
              <p className="text-xs text-[var(--text-secondary)] font-mono mt-0.5 truncate max-w-xl">
                SHA-256: {pipelineResult?.sha256 || "Pending verification"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => onNavigateStep("reports")}
              className="px-3.5 py-2 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--card-bg-hover)] border border-[var(--border)] text-xs font-medium text-[var(--text-primary)] transition-all flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5" />
              Generate Report
            </button>
            <button
              onClick={() => onNavigateStep("response")}
              className="px-3.5 py-2 rounded-lg bg-[var(--text-primary)] text-[var(--bg)] hover:opacity-90 text-xs font-semibold transition-all flex items-center gap-1.5"
            >
              <Lock className="w-3.5 h-3.5" />
              Response Center
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div
          onClick={() => onNavigateStep("discovery")}
          className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 cursor-pointer hover:border-[var(--border-strong)] transition-all"
        >
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)] mb-1">
            <span>Discovered Findings</span>
            <Globe className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">{metrics.total_findings}</div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1 flex items-center gap-1">
            <span>{metrics.cluster_count} correlation clusters</span>
          </div>
        </div>

        <div
          onClick={() => onNavigateStep("evidence")}
          className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 cursor-pointer hover:border-[var(--border-strong)] transition-all"
        >
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)] mb-1">
            <span>Verified Evidence</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{metrics.verified_count}</div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1">
            {metrics.evidence_count} sealed vault artifacts
          </div>
        </div>

        <div
          onClick={() => onNavigateStep("risk")}
          className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 cursor-pointer hover:border-[var(--border-strong)] transition-all"
        >
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)] mb-1">
            <span>Risk Score (v1)</span>
            <AlertTriangle className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {riskData?.score !== undefined ? `${riskData.score.toFixed(1)}/100` : "0.0/100"}
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1">
            Policy Version {riskData?.risk_policy_version || "v1"}
          </div>
        </div>

        <div
          onClick={() => onNavigateStep("matches")}
          className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 cursor-pointer hover:border-[var(--border-strong)] transition-all"
        >
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)] mb-1">
            <span>Internal Matches</span>
            <Database className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">15</div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1">
            DINOv2 + pHash / dHash
          </div>
        </div>
      </div>

      {/* Main Grid: Pipeline Summary & Recent Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Stage Navigation Cards */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
            Investigation Workflows
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div
              onClick={() => onNavigateStep("evidence")}
              className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--border-strong)] transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                  <Lock className="w-4 h-4" />
                </div>
                <ArrowUpRight className="w-4 h-4 text-[var(--text-tertiary)] group-hover:text-[var(--text-primary)] transition-colors" />
              </div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)]">Evidence Vault</h4>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Tamper-evident chain of custody with SHA-256 integrity signatures and side-by-side verification.
              </p>
            </div>

            <div
              onClick={() => onNavigateStep("risk")}
              className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--border-strong)] transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-orange-500/10 text-orange-400">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <ArrowUpRight className="w-4 h-4 text-[var(--text-tertiary)] group-hover:text-[var(--text-primary)] transition-colors" />
              </div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)]">Deterministic Risk Engine</h4>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Multi-factor risk assessment strictly evaluated on verified public exposure endpoints.
              </p>
            </div>

            <div
              onClick={() => onNavigateStep("graph")}
              className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--border-strong)] transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                  <Globe className="w-4 h-4" />
                </div>
                <ArrowUpRight className="w-4 h-4 text-[var(--text-tertiary)] group-hover:text-[var(--text-primary)] transition-colors" />
              </div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)]">Exposure Graph</h4>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Interactive relationship topology connecting reference asset to discovered domains and clusters.
              </p>
            </div>

            <div
              onClick={() => onNavigateStep("reports")}
              className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--border-strong)] transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                  <FileText className="w-4 h-4" />
                </div>
                <ArrowUpRight className="w-4 h-4 text-[var(--text-tertiary)] group-hover:text-[var(--text-primary)] transition-colors" />
              </div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)]">Report Engine</h4>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Generate reproducible PDF, JSON, CSV, and Text forensic dossiers with deterministic hash verification.
              </p>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Audit Timeline Snippet */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
              Forensic Activity Trail
            </h3>
            <button
              onClick={() => onNavigateStep("timeline")}
              className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center gap-0.5 transition-colors"
            >
              <span>Full Log</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 space-y-3">
            {recentTimeline.length === 0 ? (
              <div className="text-center py-6 text-xs text-[var(--text-tertiary)]">
                No timeline events recorded yet.
              </div>
            ) : (
              recentTimeline.map((evt) => (
                <div key={evt.id} className="flex items-start gap-2.5 pb-2.5 border-b border-[var(--border)] last:border-0 last:pb-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[var(--text-primary)] truncate">{evt.title}</p>
                    <p className="text-[10px] text-[var(--text-tertiary)] font-mono">
                      {new Date(evt.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
