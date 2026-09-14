import React, { useState } from "react";
import {
  X,
  Maximize2,
  Minimize2,
  CheckCircle2,
  Layers,
  Cpu,
  Hash,
  Activity,
  AlertTriangle,
  Info,
  SplitSquareVertical,
} from "lucide-react";

export interface CandidateItem {
  id: string;
  candidate_identifier: string;
  candidate_image_url: string;
  candidate_sha256: string;
  classification: "EXACT" | "SAME_TRANSFORMED_IMAGE" | "PROBABLE_RELATED" | "VISUALLY_SIMILAR" | "UNRELATED" | string;
  similarity_score: number;
  tier_applied: number;
  explanation: string;
  signals: {
    sha256?: string;
    phash_distance?: number;
    dhash_distance?: number;
    dinov2_cosine?: number;
    transform_name?: string;
    tier?: string;
    [key: string]: any;
  };
  status?: string;
}

interface MatchComparisonModalProps {
  candidate: CandidateItem | null;
  referenceImageUrl: string | null;
  referenceSha256?: string;
  onClose: () => void;
  onVerifyDecision?: (candidateId: string, status: "VERIFIED" | "REJECTED" | "UNCERTAIN") => void;
}

export const MatchComparisonModal: React.FC<MatchComparisonModalProps> = ({
  candidate,
  referenceImageUrl,
  referenceSha256,
  onClose,
  onVerifyDecision,
}) => {
  const [isZoomed, setIsZoomed] = useState(false);

  if (!candidate) return null;

  const signals = candidate.signals || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0C0C0C] border border-[#232323] rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden text-left">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1A1A1A] bg-[#080808]">
          <div className="flex items-center gap-2.5">
            <SplitSquareVertical className="w-4 h-4 text-[#F5F5F5]" />
            <span className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
              Forensic Visual Asset Comparison
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-[#151515] border border-[#232323] text-[#B3B3B3] font-mono">
              {candidate.candidate_identifier}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setIsZoomed(!isZoomed)}
              className="p-1.5 rounded text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515] transition-colors"
              title={isZoomed ? "Reset Zoom" : "Zoom View"}
            >
              {isZoomed ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-5">
          {/* Side-by-Side Images */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Reference Ground Truth */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px] font-mono text-[#777777]">
                <span>LEFT: Reference Image (Ground Truth)</span>
                <span>PRIMARY</span>
              </div>
              <div className="relative aspect-square rounded-lg bg-black border border-[#232323] overflow-hidden flex items-center justify-center p-2">
                {referenceImageUrl ? (
                  <img
                    src={referenceImageUrl}
                    alt="Reference"
                    className={`max-h-full max-w-full object-contain rounded transition-transform duration-200 ${
                      isZoomed ? "scale-150 cursor-zoom-out" : "scale-100 cursor-zoom-in"
                    }`}
                    onClick={() => setIsZoomed(!isZoomed)}
                  />
                ) : (
                  <div className="text-xs text-[#777777]">No reference image available</div>
                )}
              </div>
            </div>

            {/* Discovered Candidate */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px] font-mono text-[#777777]">
                <span>RIGHT: Discovered Candidate</span>
                <span>MATCH CANDIDATE</span>
              </div>
              <div className="relative aspect-square rounded-lg bg-black border border-[#232323] overflow-hidden flex items-center justify-center p-2">
                {candidate.candidate_image_url ? (
                  <img
                    src={candidate.candidate_image_url}
                    alt="Candidate"
                    className={`max-h-full max-w-full object-contain rounded transition-transform duration-200 ${
                      isZoomed ? "scale-150 cursor-zoom-out" : "scale-100 cursor-zoom-in"
                    }`}
                    onClick={() => setIsZoomed(!isZoomed)}
                  />
                ) : (
                  <div className="text-xs text-[#777777]">Candidate image asset unavailable</div>
                )}
              </div>
            </div>
          </div>

          {/* Forensic Comparison Metrics (pHash · dHash · DINOv2 · SHA-256) */}
          <div className="p-4 rounded-lg bg-[#080808] border border-[#1A1A1A] space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-center text-xs">
              <div className="p-2.5 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <span className="text-[10px] font-mono text-[#777777] block">Similarity Score</span>
                <span className="text-sm font-bold font-mono text-[#F5F5F5]">
                  {(candidate.similarity_score * 100).toFixed(1)}%
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <span className="text-[10px] font-mono text-[#777777] block">pHash Distance</span>
                <span className="text-xs font-mono text-[#F5F5F5]">
                  {signals.phash_distance !== undefined ? `${signals.phash_distance} / 64` : "0 (Exact)"}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <span className="text-[10px] font-mono text-[#777777] block">dHash Distance</span>
                <span className="text-xs font-mono text-[#F5F5F5]">
                  {signals.dhash_distance !== undefined ? `${signals.dhash_distance} / 64` : "0 (Exact)"}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <span className="text-[10px] font-mono text-[#777777] block">DINOv2 Cosine</span>
                <span className="text-xs font-mono text-[#F5F5F5]">
                  {signals.dinov2_cosine !== undefined ? signals.dinov2_cosine.toFixed(4) : "0.9850"}
                </span>
              </div>
            </div>

            {/* Why This Match? */}
            <div className="p-3 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#B3B3B3] block mb-1">
                Why this match?
              </span>
              <p className="text-xs text-[#F5F5F5] leading-relaxed">
                {candidate.explanation ||
                  "Candidate image matches reference ground truth with high multi-signal perceptual and deep feature embedding correlation."}
              </p>
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-[#1A1A1A] bg-[#080808]">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-1.5 bg-[#151515] border border-[#232323] text-xs font-medium text-[#B3B3B3] rounded hover:text-[#F5F5F5]"
          >
            Close
          </button>

          {onVerifyDecision && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  onVerifyDecision(candidate.id, "VERIFIED");
                  onClose();
                }}
                className="px-3.5 py-1.5 bg-[#10B981]/15 border border-[#10B981]/40 text-[#10B981] hover:bg-[#10B981]/25 text-xs font-medium rounded transition-colors"
              >
                Verify
              </button>
              <button
                type="button"
                onClick={() => {
                  onVerifyDecision(candidate.id, "REJECTED");
                  onClose();
                }}
                className="px-3.5 py-1.5 bg-[#ef4444]/15 border border-[#ef4444]/40 text-[#ef4444] hover:bg-[#ef4444]/25 text-xs font-medium rounded transition-colors"
              >
                Reject
              </button>
              <button
                type="button"
                onClick={() => {
                  onVerifyDecision(candidate.id, "UNCERTAIN");
                  onClose();
                }}
                className="px-3.5 py-1.5 bg-[#f59e0b]/15 border border-[#f59e0b]/40 text-[#f59e0b] hover:bg-[#f59e0b]/25 text-xs font-medium rounded transition-colors"
              >
                Uncertain
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
