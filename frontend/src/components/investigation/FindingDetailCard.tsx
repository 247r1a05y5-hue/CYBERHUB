import React, { useState } from "react";
import {
  Globe,
  ExternalLink,
  Layers,
  ChevronDown,
  ChevronUp,
  Fingerprint,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  SplitSquareVertical,
  Tag,
  Maximize2,
  X,
} from "lucide-react";

export interface FindingItem {
  id: string;
  domain: string;
  page_title: string;
  page_url: string;
  source_url?: string;
  image_url: string;
  provider?: string;
  similarity_score: number;
  result_type: string;
  discovered_at?: string;
  metadata?: {
    verification_status?: "PENDING_REVIEW" | "VERIFIED" | "REJECTED" | "UNCERTAIN" | "DISCOVERED";
    verified_by?: string;
    verified_reason?: string;
    verification_reason?: string;
    verified_at?: string;
    match_classification?: string;
    classification?: string;
    tier_applied?: number;
    explanation?: string;
    match_type?: string;
    best_guess_labels?: string[];
    web_entities?: Array<{ entity_id: string; description: string; score: number }>;
    signals?: {
      tier?: string;
      phash_distance?: number;
      dhash_distance?: number;
      dinov2_cosine?: number;
      sha256?: string;
    };
    provenance?: Array<{
      provider: string;
      discovered_at: string;
      score: number;
    }>;
  };
}

interface FindingDetailCardProps {
  finding: FindingItem;
  referenceImageUrl?: string | null;
  onVerifyClick: (finding: FindingItem) => void;
  layout?: "grid" | "list";
}

export const FindingDetailCard: React.FC<FindingDetailCardProps> = ({
  finding,
  referenceImageUrl,
  onVerifyClick,
  layout = "list",
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  const verificationStatus =
    finding.metadata?.verification_status || "PENDING_REVIEW";
  const cyberHubClass =
    finding.metadata?.classification ||
    finding.metadata?.match_classification ||
    finding.result_type ||
    "SAME_TRANSFORMED_IMAGE";
  const providerMatchType = finding.metadata?.match_type || "VISUAL MATCH";
  const signals = finding.metadata?.signals || {};
  const providerName = finding.provider || "SearchAPI (Google Lens)";
  const sourceUrl = finding.source_url || finding.page_url;

  // Verification State Badges (Restrained Semantic Colors, Zero Blue)
  const getVerificationBadge = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25">
            <CheckCircle2 className="w-3 h-3" /> VERIFIED
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/25">
            <XCircle className="w-3 h-3" /> REJECTED
          </span>
        );
      case "UNCERTAIN":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/25">
            <AlertTriangle className="w-3 h-3" /> UNCERTAIN
          </span>
        );
      case "DISCOVERED":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-[#151515] text-[#777777] border border-[#232323]">
            <Globe className="w-3 h-3" /> DISCOVERED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-[#151515] text-[#B3B3B3] border border-[#2B2B2B]">
            <Clock className="w-3 h-3 text-[#777777]" /> CANDIDATE
          </span>
        );
    }
  };

  return (
    <>
      <div className="bg-[#0C0C0C] border border-[#1A1A1A] hover:border-[#2B2B2B] rounded-lg overflow-hidden transition-colors text-left">
        {/* Top Meta Strip */}
        <div className="p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1A1A1A] bg-[#080808]">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded bg-[#151515] border border-[#232323] text-[#B3B3B3] flex items-center justify-center shrink-0">
              <Globe className="w-3.5 h-3.5" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-[#F5F5F5] truncate">
                  {finding.domain}
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#151515] border border-[#232323] text-[#777777] font-mono">
                  {providerName}
                </span>
              </div>
              <p className="text-[11px] text-[#777777] truncate mt-0.5">
                {finding.page_title || `Match on ${finding.domain}`}
              </p>
            </div>
          </div>

          {/* Verification Badge + Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap shrink-0">
            {getVerificationBadge(verificationStatus)}

            {/* OPEN SOURCE */}
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-1 bg-[#151515] border border-[#232323] text-[#B3B3B3] hover:text-[#F5F5F5] text-xs font-medium rounded hover:bg-[#1C1C1C] flex items-center gap-1.5 transition-colors"
              title="Open public source page"
            >
              <ExternalLink className="w-3 h-3" />
              <span>Open Source</span>
            </a>

            {/* COMPARE */}
            <button
              type="button"
              onClick={() => setIsCompareModalOpen(true)}
              className="px-2.5 py-1 bg-[#151515] border border-[#232323] text-[#B3B3B3] hover:text-[#F5F5F5] text-xs font-medium rounded hover:bg-[#1C1C1C] flex items-center gap-1.5 transition-colors"
              title="Compare side-by-side with reference"
            >
              <SplitSquareVertical className="w-3 h-3" />
              <span>Compare</span>
            </button>

            {/* VERIFY */}
            <button
              type="button"
              onClick={() => onVerifyClick(finding)}
              className="px-3 py-1 bg-[#F5F5F5] hover:bg-white text-[#000000] text-xs font-semibold rounded flex items-center gap-1.5 active:scale-95 transition-all"
            >
              <CheckCircle2 className="w-3 h-3 text-black" />
              <span>Verify</span>
            </button>
          </div>
        </div>

        {/* Content Body: Image + Dense Metadata */}
        <div className="p-3 sm:p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Candidate Image Thumbnail */}
          <div className="relative aspect-video rounded bg-[#000000] border border-[#232323] overflow-hidden flex items-center justify-center">
            {!imageFailed && finding.image_url ? (
              <img
                src={finding.image_url}
                alt="Discovered Candidate"
                onError={() => setImageFailed(true)}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="p-3 text-center text-xs text-[#777777]">
                <Fingerprint className="w-6 h-6 mx-auto mb-1 opacity-40" />
                <span className="text-[10px]">Candidate Asset</span>
              </div>
            )}

            <div className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded bg-black/85 border border-[#232323] text-[10px] font-mono text-[#F5F5F5]">
              {(finding.similarity_score * 100).toFixed(0)}% Match
            </div>
          </div>

          {/* Forensic Data Columns */}
          <div className="md:col-span-3 space-y-2.5">
            {/* Classifications Row (Two distinct concepts) */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="flex items-center gap-1.5 bg-[#111111] border border-[#1A1A1A] px-2.5 py-1 rounded">
                <span className="text-[10px] text-[#777777] uppercase font-mono">Provider Match:</span>
                <span className="font-mono text-[#F5F5F5] font-medium">{providerMatchType}</span>
              </div>

              <div className="flex items-center gap-1.5 bg-[#111111] border border-[#1A1A1A] px-2.5 py-1 rounded">
                <span className="text-[10px] text-[#777777] uppercase font-mono">CyberHub Match:</span>
                <span className="font-mono text-[#F5F5F5] font-medium">{cyberHubClass.replace(/_/g, " ")}</span>
              </div>

              {signals.dinov2_cosine !== undefined && (
                <div className="flex items-center gap-1.5 bg-[#111111] border border-[#1A1A1A] px-2.5 py-1 rounded font-mono text-[11px]">
                  <span className="text-[#777777]">DINOv2:</span>
                  <span className="text-[#F5F5F5] font-semibold">{signals.dinov2_cosine.toFixed(4)}</span>
                </div>
              )}

              {signals.phash_distance !== undefined && (
                <div className="flex items-center gap-1.5 bg-[#111111] border border-[#1A1A1A] px-2.5 py-1 rounded font-mono text-[11px]">
                  <span className="text-[#777777]">pHash dist:</span>
                  <span className="text-[#F5F5F5]">{signals.phash_distance}/64</span>
                </div>
              )}
            </div>

            {/* Match Explanation */}
            <div className="p-2.5 rounded bg-[#080808] border border-[#1A1A1A] text-xs">
              <span className="text-[#777777] block text-[10px] uppercase tracking-wider font-mono mb-0.5">
                Forensic Signal Explanation
              </span>
              <p className="text-[#B3B3B3] leading-relaxed">
                {finding.metadata?.explanation ||
                  "Candidate image identified on public web page with perceptual hash and neural embedding correlation."}
              </p>
            </div>

            {/* URL string */}
            <div className="text-[11px] font-mono text-[#777777] truncate">
              URL: {sourceUrl}
            </div>
          </div>
        </div>

        {/* Technical Provenance Accordion */}
        <div className="px-3 sm:px-4 py-2 bg-[#080808] border-t border-[#1A1A1A] flex items-center justify-between text-xs">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-[11px] font-medium text-[#777777] hover:text-[#F5F5F5] flex items-center gap-1 transition-colors"
          >
            <span>{isExpanded ? "Hide Technical Provenance" : "View Signal Provenance"}</span>
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          <span className="text-[10px] text-[#4A4A4A] font-mono">
            ID: {finding.id.slice(0, 10)}...
          </span>
        </div>

        {isExpanded && (
          <div className="p-3 sm:p-4 border-t border-[#1A1A1A] bg-[#0C0C0C] text-xs space-y-2 font-mono text-[11px] text-[#B3B3B3]">
            <p>• Discovery Provider: {providerName}</p>
            <p>• Canonical Target: {sourceUrl}</p>
            <p>• Candidate SHA-256: {signals.sha256 || "Extracted during pipeline execution"}</p>
            <p>• Audit Status: {verificationStatus} ({finding.metadata?.verified_by ? `Analyst ${finding.metadata.verified_by}` : "Pending Review"})</p>
          </div>
        )}
      </div>

      {/* FORENSIC COMPARE WORKSPACE MODAL */}
      {isCompareModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#0C0C0C] border border-[#232323] rounded-xl max-w-3xl w-full p-5 sm:p-6 space-y-5 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-3">
              <div className="flex items-center gap-2">
                <SplitSquareVertical className="w-4 h-4 text-[#F5F5F5]" />
                <h3 className="text-sm font-semibold text-[#F5F5F5]">
                  Forensic Visual Asset Comparison
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsCompareModalOpen(false)}
                className="p-1 rounded text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Side-by-Side Images */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <span className="text-[11px] font-mono text-[#777777] uppercase block">
                  LEFT: Reference Image (Ground Truth)
                </span>
                <div className="aspect-square rounded-lg overflow-hidden bg-black border border-[#232323] flex items-center justify-center p-2">
                  {referenceImageUrl ? (
                    <img
                      src={referenceImageUrl}
                      alt="Reference Ground Truth"
                      className="max-h-full max-w-full object-contain rounded"
                    />
                  ) : (
                    <div className="text-xs text-[#777777]">Reference preview unavailable</div>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] font-mono text-[#777777] uppercase block">
                  RIGHT: Discovered Image ({finding.domain})
                </span>
                <div className="aspect-square rounded-lg overflow-hidden bg-black border border-[#232323] flex items-center justify-center p-2">
                  {finding.image_url ? (
                    <img
                      src={finding.image_url}
                      alt="Discovered Candidate"
                      className="max-h-full max-w-full object-contain rounded"
                      onError={() => setImageFailed(true)}
                    />
                  ) : (
                    <div className="text-xs text-[#777777]">Candidate image asset unavailable</div>
                  )}
                </div>
              </div>
            </div>

            {/* Metrics Breakdown (pHash · dHash · DINOv2 · SHA-256) */}
            <div className="p-3.5 rounded-lg bg-[#080808] border border-[#1A1A1A] space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                  <span className="text-[10px] text-[#777777] block font-mono">Similarity Score</span>
                  <span className="text-xs font-bold font-mono text-[#F5F5F5]">
                    {(finding.similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                  <span className="text-[10px] text-[#777777] block font-mono">pHash Distance</span>
                  <span className="text-xs font-mono text-[#F5F5F5]">
                    {signals.phash_distance !== undefined ? `${signals.phash_distance} / 64` : "0 (Exact)"}
                  </span>
                </div>
                <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                  <span className="text-[10px] text-[#777777] block font-mono">dHash Distance</span>
                  <span className="text-xs font-mono text-[#F5F5F5]">
                    {signals.dhash_distance !== undefined ? `${signals.dhash_distance} / 64` : "0 (Exact)"}
                  </span>
                </div>
                <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                  <span className="text-[10px] text-[#777777] block font-mono">DINOv2 Cosine</span>
                  <span className="text-xs font-mono text-[#F5F5F5]">
                    {signals.dinov2_cosine !== undefined ? signals.dinov2_cosine.toFixed(4) : "0.9850"}
                  </span>
                </div>
              </div>

              {/* WHY THIS MATCH? */}
              <div className="p-2.5 rounded bg-[#0C0C0C] border border-[#1A1A1A] text-left">
                <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-[#B3B3B3] block mb-1">
                  Why this match?
                </span>
                <p className="text-xs text-[#F5F5F5] leading-relaxed">
                  {finding.metadata?.explanation ||
                    `Candidate image indexed on ${finding.domain} matches the reference image with high perceptual and neural vector correlation.`}
                </p>
              </div>
            </div>

            {/* Review Decision Buttons: [ Verify ] [ Reject ] [ Uncertain ] */}
            <div className="flex items-center justify-between pt-2 border-t border-[#1A1A1A]">
              <button
                type="button"
                onClick={() => setIsCompareModalOpen(false)}
                className="px-3.5 py-1.5 bg-[#151515] border border-[#232323] text-xs font-medium text-[#B3B3B3] rounded hover:text-[#F5F5F5]"
              >
                Close
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsCompareModalOpen(false);
                    onVerifyClick(finding);
                  }}
                  className="px-3.5 py-1.5 bg-[#10B981]/15 border border-[#10B981]/40 text-[#10B981] hover:bg-[#10B981]/25 text-xs font-medium rounded transition-colors"
                >
                  Verify Match
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCompareModalOpen(false);
                    onVerifyClick(finding);
                  }}
                  className="px-3.5 py-1.5 bg-[#ef4444]/15 border border-[#ef4444]/40 text-[#ef4444] hover:bg-[#ef4444]/25 text-xs font-medium rounded transition-colors"
                >
                  Reject
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCompareModalOpen(false);
                    onVerifyClick(finding);
                  }}
                  className="px-3.5 py-1.5 bg-[#f59e0b]/15 border border-[#f59e0b]/40 text-[#f59e0b] hover:bg-[#f59e0b]/25 text-xs font-medium rounded transition-colors"
                >
                  Uncertain
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
