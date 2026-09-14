import React, { useState } from "react";
import {
  CheckCircle2,
  Sparkles,
  Layers,
  AlertTriangle,
  Info,
  Search,
  Maximize2,
  Filter,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { CandidateItem, MatchComparisonModal } from "./MatchComparisonModal";

interface MatchResultsViewProps {
  candidates: CandidateItem[];
  referenceImageUrl: string | null;
  referenceSha256?: string;
  investigationId: string;
  caseNumber: string;
  onContinue: () => void;
}

export const MatchResultsView: React.FC<MatchResultsViewProps> = ({
  candidates,
  referenceImageUrl,
  referenceSha256,
  investigationId,
  caseNumber,
  onContinue,
}) => {
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [activeModalCandidate, setActiveModalCandidate] = useState<CandidateItem | null>(null);

  const filterOptions = [
    { id: "ALL", label: "All Candidates", count: candidates.length },
    {
      id: "EXACT",
      label: "Exact Match",
      count: candidates.filter((c) => c.classification === "EXACT").length,
    },
    {
      id: "SAME_TRANSFORMED_IMAGE",
      label: "Transformed Variants",
      count: candidates.filter((c) => c.classification === "SAME_TRANSFORMED_IMAGE").length,
    },
    {
      id: "PROBABLE_RELATED",
      label: "Probable Related",
      count: candidates.filter((c) => c.classification === "PROBABLE_RELATED").length,
    },
    {
      id: "UNRELATED",
      label: "Unrelated",
      count: candidates.filter((c) => c.classification === "UNRELATED").length,
    },
  ];

  const filteredCandidates = candidates.filter((c) => {
    if (selectedFilter === "ALL") return true;
    return c.classification === selectedFilter;
  });

  const getBadgeStyle = (classification: string) => {
    switch (classification) {
      case "EXACT":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
      case "SAME_TRANSFORMED_IMAGE":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
      case "PROBABLE_RELATED":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      case "VISUALLY_SIMILAR":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20";
      default:
        return "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20";
    }
  };

  const exactCount = candidates.filter((c) => c.classification === "EXACT").length;
  const transformedCount = candidates.filter((c) => c.classification === "SAME_TRANSFORMED_IMAGE").length;

  return (
    <div className="space-y-6 text-left max-w-5xl mx-auto">
      {/* Header Summary Banner */}
      <div
        className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 transition-all"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[var(--border)]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-500 border border-blue-500/20">
                PHASE 3 ACTIVE
              </span>
              <span className="text-xs font-mono text-[var(--text-secondary)]">Case: {caseNumber}</span>
            </div>
            <h2 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              Image Matching & Reuse Engine Results
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Evaluated against tenant-safe benchmark corpus & reference pool. Matches are unconfirmed candidates.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onContinue}
              className="px-4 py-2 bg-[var(--text-primary)] text-[var(--bg)] text-xs font-semibold rounded-lg flex items-center gap-1.5 hover:opacity-90 transition-opacity"
            >
              <span>Continue to Case Dashboard</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] font-medium block mb-0.5">Evaluated Pool</span>
            <p className="text-base font-bold text-[var(--text-primary)]">{candidates.length} Candidates</p>
          </div>
          <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] font-medium block mb-0.5">Exact Matches</span>
            <p className="text-base font-bold text-emerald-600 dark:text-emerald-400">{exactCount}</p>
          </div>
          <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] font-medium block mb-0.5">Transformed Variants</span>
            <p className="text-base font-bold text-blue-600 dark:text-blue-400">{transformedCount}</p>
          </div>
          <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] font-medium block mb-0.5">Engine Status</span>
            <p className="text-base font-bold text-[var(--text-primary)] flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Calibrated</span>
            </p>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        {filterOptions.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setSelectedFilter(f.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
              selectedFilter === f.id
                ? "bg-[var(--text-primary)] text-[var(--bg)] font-semibold shadow-sm"
                : "bg-[var(--surface)] text-[var(--text-secondary)] border border-[var(--border)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <span>{f.label}</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                selectedFilter === f.id
                  ? "bg-[var(--bg)] text-[var(--text-primary)] font-bold"
                  : "bg-[var(--surface-raised)] text-[var(--text-tertiary)]"
              }`}
            >
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* Candidate Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCandidates.map((candidate) => {
          const badgeClass = getBadgeStyle(candidate.classification);
          const scorePct = Math.round(candidate.similarity_score * 100);

          return (
            <div
              key={candidate.id}
              className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-4 flex flex-col justify-between hover:border-[var(--text-secondary)] transition-all group"
              style={{ boxShadow: "var(--card-shadow)" }}
            >
              <div>
                {/* Candidate Image Frame */}
                <div className="relative aspect-video w-full rounded-xl bg-black/40 border border-[var(--border)] overflow-hidden mb-3.5 flex items-center justify-center">
                  <img
                    src={candidate.candidate_image_url}
                    alt={candidate.candidate_identifier}
                    className="max-h-full max-w-full object-contain group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute top-2 right-2 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-black/70 text-white backdrop-blur-sm">
                    {scorePct}% SIMILARITY
                  </div>
                </div>

                {/* Candidate Info */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-mono font-semibold text-[var(--text-primary)] truncate">
                      {candidate.candidate_identifier}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${badgeClass}`}>
                      {candidate.classification.replace(/_/g, " ")}
                    </span>
                  </div>

                  <p className="text-[11px] text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
                    {candidate.explanation}
                  </p>
                </div>
              </div>

              {/* Card Footer */}
              <div className="mt-4 pt-3 border-t border-[var(--border)] flex items-center justify-between text-xs">
                <span className="text-[11px] text-[var(--text-tertiary)] font-medium">
                  Tier {candidate.tier_applied} Applied
                </span>
                <button
                  type="button"
                  onClick={() => setActiveModalCandidate(candidate)}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--text-primary)] hover:underline"
                >
                  <Maximize2 className="w-3 h-3" />
                  <span>Inspect Details</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Comparison Modal */}
      {activeModalCandidate && (
        <MatchComparisonModal
          candidate={activeModalCandidate}
          referenceImageUrl={referenceImageUrl}
          referenceSha256={referenceSha256}
          onClose={() => setActiveModalCandidate(null)}
        />
      )}
    </div>
  );
};
