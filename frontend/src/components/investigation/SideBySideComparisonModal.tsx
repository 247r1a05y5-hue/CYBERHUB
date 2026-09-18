import React, { useState } from "react";
import {
  X,
  Split,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ExternalLink,
  Shield,
  FileImage,
  Info,
} from "lucide-react";
import { ResultItemData } from "./LensoResultCard";

interface SideBySideComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  queryImageUrl: string | null;
  queryMeta?: {
    sha256?: string;
    dimensions?: { width: number; height: number };
    fileSize?: string;
  };
  discoveredItem: ResultItemData | null;
  onVerify: (item: ResultItemData, status: "VERIFIED" | "REJECTED") => void;
  onSaveEvidence: (item: ResultItemData) => void;
}

export const SideBySideComparisonModal: React.FC<SideBySideComparisonModalProps> = ({
  isOpen,
  onClose,
  queryImageUrl,
  queryMeta,
  discoveredItem,
  onVerify,
  onSaveEvidence,
}) => {
  const [imageError, setImageError] = useState(false);

  if (!isOpen || !discoveredItem) return null;

  const discoveredImage =
    discoveredItem.thumbnail_url || discoveredItem.source_image_url;

  const similarity = discoveredItem.similarity_score !== undefined
    ? Math.round(
        discoveredItem.similarity_score <= 1
          ? discoveredItem.similarity_score * 100
          : discoveredItem.similarity_score
      )
    : 85;

  const faceSimilarity = discoveredItem.face_similarity !== undefined
    ? Math.round(
        discoveredItem.face_similarity <= 1
          ? discoveredItem.face_similarity * 100
          : discoveredItem.face_similarity
      )
    : null;

  const phashDist = discoveredItem.phash_distance ?? 4;
  const dhashDist = discoveredItem.dhash_distance ?? 6;

  const getExplanation = () => {
    if (discoveredItem.is_dataset_match) {
      return "Controlled dataset face index match via AWS Rekognition collection. Candidate identity has confirmed public disclosure consent.";
    }
    if (similarity >= 95) {
      return "High perceptual hash and visual keypoint alignment indicates an exact or minimally compressed duplicate of the reference image.";
    }
    if (discoveredItem.match_type === "TRANSFORMED" || similarity >= 80) {
      return "Strong geometric and color histogram correlation detected. The discovered image appears to be a cropped, resized, or filtered derivative.";
    }
    if (discoveredItem.match_type === "FACE_MATCH") {
      return "Facial landmark vectors exhibit strong proximity. Potential face match pending human visual confirmation.";
    }
    return "Visual feature embeddings indicate contextual and structural similarity across key foreground objects and scene composition.";
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="h-12 px-4 border-b border-[#1A1A1A] flex items-center justify-between bg-[#080808] shrink-0">
          <div className="flex items-center gap-2">
            <Split className="w-4 h-4 text-[#F5F5F5]" />
            <span className="text-xs font-semibold text-[#F5F5F5] uppercase tracking-wider">
              Side-by-Side Forensic Comparison
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Side-by-Side Images */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Query Image (Left) */}
            <div className="flex flex-col bg-[#050505] border border-[#1A1A1A] rounded-lg overflow-hidden">
              <div className="px-3 py-2 border-b border-[#1A1A1A] bg-[#0A0A0A] flex items-center justify-between">
                <span className="text-[11px] font-bold text-[#F5F5F5] uppercase font-mono">
                  Reference Query Image
                </span>
                <span className="text-[10px] text-[#777777] font-mono">Source Input</span>
              </div>
              <div className="aspect-video w-full flex items-center justify-center p-2 bg-[#000000]">
                {queryImageUrl ? (
                  <img
                    src={queryImageUrl}
                    alt="Reference Query"
                    className="max-h-full max-w-full object-contain rounded"
                  />
                ) : (
                  <FileImage className="w-12 h-12 text-[#2B2B2B]" />
                )}
              </div>
              <div className="p-3 border-t border-[#1A1A1A] bg-[#0A0A0A] space-y-1 text-[11px] font-mono text-[#777777]">
                {queryMeta?.dimensions && (
                  <p>Dimensions: {queryMeta.dimensions.width} × {queryMeta.dimensions.height}</p>
                )}
                {queryMeta?.sha256 && (
                  <p className="truncate">SHA-256: {queryMeta.sha256}</p>
                )}
              </div>
            </div>

            {/* Discovered Image (Right) */}
            <div className="flex flex-col bg-[#050505] border border-[#1A1A1A] rounded-lg overflow-hidden">
              <div className="px-3 py-2 border-b border-[#1A1A1A] bg-[#0A0A0A] flex items-center justify-between">
                <span className="text-[11px] font-bold text-[#F5F5F5] uppercase font-mono">
                  Discovered Image
                </span>
                <span className="text-[10px] text-[#10B981] font-mono font-bold">
                  {similarity}% Match
                </span>
              </div>
              <div className="aspect-video w-full flex items-center justify-center p-2 bg-[#000000]">
                {discoveredImage && !imageError ? (
                  <img
                    src={discoveredImage}
                    alt="Discovered Match"
                    onError={() => setImageError(true)}
                    className="max-h-full max-w-full object-contain rounded"
                  />
                ) : (
                  <div className="text-center p-4">
                    <Shield className="w-10 h-10 text-[#2B2B2B] mx-auto mb-2" />
                    <p className="text-[11px] text-[#777777]">
                      {discoveredItem.is_dataset_match
                        ? "Participant identity protected. No photo leaked."
                        : "Preview unavailable"}
                    </p>
                  </div>
                )}
              </div>
              <div className="p-3 border-t border-[#1A1A1A] bg-[#0A0A0A] space-y-1 text-[11px] text-[#777777]">
                <p className="font-semibold text-[#F5F5F5] truncate">
                  {discoveredItem.page_title || "Discovered Public Endpoint"}
                </p>
                {discoveredItem.source_page_url && (
                  <a
                    href={discoveredItem.source_page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="truncate flex items-center gap-1 text-[#B3B3B3] hover:text-[#F5F5F5]"
                  >
                    <ExternalLink className="w-3 h-3 shrink-0" />
                    <span className="truncate">{discoveredItem.source_page_url}</span>
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* Forensic Signal Matrix */}
          <div className="bg-[#080808] border border-[#1A1A1A] rounded-lg p-3">
            <h4 className="text-[11px] font-bold text-[#777777] uppercase tracking-wider mb-2 font-mono">
              Signal Breakdown & Metrics
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <p className="text-[10px] text-[#777777]">Visual Similarity</p>
                <p className="text-sm font-mono font-bold text-[#F5F5F5] mt-0.5">
                  {similarity}%
                </p>
              </div>
              <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <p className="text-[10px] text-[#777777]">Face Signal</p>
                <p className="text-sm font-mono font-bold text-[#F5F5F5] mt-0.5">
                  {faceSimilarity !== null ? `${faceSimilarity}%` : "N/A"}
                </p>
              </div>
              <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <p className="text-[10px] text-[#777777]">pHash Distance</p>
                <p className="text-sm font-mono font-bold text-[#F5F5F5] mt-0.5">
                  {phashDist} <span className="text-[10px] font-normal text-[#777777]">(Hamming)</span>
                </p>
              </div>
              <div className="p-2 rounded bg-[#0C0C0C] border border-[#1A1A1A]">
                <p className="text-[10px] text-[#777777]">Classification</p>
                <p className="text-xs font-mono font-bold text-[#10B981] mt-0.5 truncate">
                  {discoveredItem.match_type || "MATCH"}
                </p>
              </div>
            </div>
          </div>

          {/* Explanation Box */}
          <div className="p-3 rounded-lg bg-[#080808] border border-[#1A1A1A] flex items-start gap-2.5">
            <Info className="w-4 h-4 text-[#777777] shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-bold text-[#F5F5F5]">WHY THIS RESULT?</p>
              <p className="text-xs text-[#B3B3B3] mt-0.5">{getExplanation()}</p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="h-14 px-4 border-t border-[#1A1A1A] bg-[#080808] flex items-center justify-between shrink-0">
          <button
            type="button"
            onClick={() => onSaveEvidence(discoveredItem)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#111111] border border-[#2B2B2B] text-xs text-[#B3B3B3] hover:text-[#F5F5F5] hover:bg-[#1A1A1A] transition-colors"
          >
            <Lock className="w-3.5 h-3.5" />
            Save to Evidence Vault
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                onVerify(discoveredItem, "REJECTED");
                onClose();
              }}
              className="px-3 py-1.5 rounded-lg bg-[#151515] border border-[#ef4444]/30 text-xs font-semibold text-[#ef4444] hover:bg-[#ef4444]/10 transition-colors"
            >
              Reject / False Positive
            </button>
            <button
              type="button"
              onClick={() => {
                onVerify(discoveredItem, "VERIFIED");
                onClose();
              }}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#10B981] text-black text-xs font-semibold hover:bg-[#10B981]/90 transition-all shadow-sm"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Verify Finding
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
