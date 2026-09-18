import React, { useState } from "react";
import {
  X,
  ExternalLink,
  Split,
  CheckCircle2,
  Lock,
  Globe,
  Calendar,
  Layers,
  FileText,
  Shield,
  Clock,
  AlertOctagon,
} from "lucide-react";
import { ResultItemData } from "./LensoResultCard";

interface ResultDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  item: ResultItemData | null;
  onOpenCompare: (item: ResultItemData) => void;
  onVerify: (item: ResultItemData, status: "VERIFIED" | "REJECTED") => void;
  onSaveEvidence: (item: ResultItemData) => void;
}

export const ResultDetailDrawer: React.FC<ResultDetailDrawerProps> = ({
  isOpen,
  onClose,
  item,
  onOpenCompare,
  onVerify,
  onSaveEvidence,
}) => {
  const [imageError, setImageError] = useState(false);

  if (!isOpen || !item) return null;

  const displayImage = item.thumbnail_url || item.source_image_url;
  const domain =
    item.domain ||
    (item.source_page_url
      ? (() => {
          try {
            return new URL(item.source_page_url).hostname.replace(/^www\./, "");
          } catch {
            return "public-web";
          }
        })()
      : "public-source");

  const similarity =
    item.similarity_score !== undefined
      ? Math.round(
          item.similarity_score <= 1
            ? item.similarity_score * 100
            : item.similarity_score
        )
      : null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md md:max-w-lg bg-[#0C0C0C] border-l border-[#1A1A1A] flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
          {/* Drawer Header */}
          <div className="h-14 px-4 border-b border-[#1A1A1A] flex items-center justify-between bg-[#080808] shrink-0">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-[#F5F5F5]" />
              <span className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider">
                Source Investigation
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

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            {/* Image Preview */}
            <div className="w-full aspect-video bg-[#050505] border border-[#1A1A1A] rounded-lg overflow-hidden flex items-center justify-center relative">
              {displayImage && !imageError ? (
                <img
                  src={displayImage}
                  alt={item.page_title || "Discovered result"}
                  onError={() => setImageError(true)}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-center p-4">
                  <Shield className="w-10 h-10 text-[#2B2B2B]" />
                  <p className="text-xs text-[#777777]">
                    {item.is_dataset_match
                      ? "Protected Dataset Record"
                      : "Source Image Preview Unavailable"}
                  </p>
                </div>
              )}
              {similarity !== null && (
                <div className="absolute top-2 right-2 px-2 py-1 rounded bg-black/85 border border-[#2B2B2B] font-mono text-xs font-bold text-[#F5F5F5]">
                  {similarity}% Match
                </div>
              )}
            </div>

            {/* Source Information */}
            <div className="space-y-3">
              <p className="text-[11px] font-bold text-[#777777] uppercase font-mono tracking-wider">
                Target Endpoint Details
              </p>

              <div className="p-3 bg-[#080808] border border-[#1A1A1A] rounded-lg space-y-2.5 text-xs">
                <div>
                  <span className="text-[10px] text-[#777777] block">DOMAIN / HOST</span>
                  <span className="font-mono text-[#F5F5F5] font-semibold">{domain}</span>
                </div>

                <div>
                  <span className="text-[10px] text-[#777777] block">PAGE TITLE</span>
                  <p className="text-[#F5F5F5] font-medium leading-snug">
                    {item.page_title || "Untitled Public Document"}
                  </p>
                </div>

                {item.source_page_url && (
                  <div>
                    <span className="text-[10px] text-[#777777] block">CANONICAL URL</span>
                    <a
                      href={item.source_page_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#B3B3B3] hover:text-[#F5F5F5] underline break-all flex items-center gap-1 mt-0.5"
                    >
                      <ExternalLink className="w-3 h-3 shrink-0" />
                      <span className="truncate">{item.source_page_url}</span>
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Forensic Discovery Signals */}
            <div className="space-y-3">
              <p className="text-[11px] font-bold text-[#777777] uppercase font-mono tracking-wider">
                Discovery Metadata
              </p>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-[#080808] border border-[#1A1A1A] rounded-lg">
                  <span className="text-[10px] text-[#777777] block">DISCOVERY SOURCE</span>
                  <span className="font-mono text-[#F5F5F5]">
                    {item.provider || "Public Search Provider"}
                  </span>
                </div>

                <div className="p-2.5 bg-[#080808] border border-[#1A1A1A] rounded-lg">
                  <span className="text-[10px] text-[#777777] block">MATCH TYPE</span>
                  <span className="font-mono text-[#10B981] uppercase">
                    {item.match_type || "DISCOVERED"}
                  </span>
                </div>

                <div className="p-2.5 bg-[#080808] border border-[#1A1A1A] rounded-lg">
                  <span className="text-[10px] text-[#777777] block">FIRST DISCOVERED</span>
                  <span className="font-mono text-[#F5F5F5]">
                    {item.discovered_at ? new Date(item.discovered_at).toLocaleDateString() : "Live Query"}
                  </span>
                </div>

                <div className="p-2.5 bg-[#080808] border border-[#1A1A1A] rounded-lg">
                  <span className="text-[10px] text-[#777777] block">VERIFICATION</span>
                  <span className="font-mono text-[#B3B3B3] font-semibold">
                    {item.verification_status || "PENDING_REVIEW"}
                  </span>
                </div>
              </div>
            </div>

            {/* Context Snippet / OCR */}
            {item.extracted_text && (
              <div className="space-y-2">
                <p className="text-[11px] font-bold text-[#777777] uppercase font-mono tracking-wider">
                  Extracted Text Context
                </p>
                <div className="p-3 bg-[#080808] border border-[#1A1A1A] rounded-lg font-mono text-xs text-[#B3B3B3] leading-relaxed whitespace-pre-wrap">
                  {item.extracted_text}
                </div>
              </div>
            )}
          </div>

          {/* Drawer Footer Actions */}
          <div className="p-4 border-t border-[#1A1A1A] bg-[#080808] space-y-2 shrink-0">
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => onOpenCompare(item)}
                className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#111111] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#1A1A1A] transition-colors"
              >
                <Split className="w-3.5 h-3.5" />
                Compare Side-by-Side
              </button>

              {item.source_page_url ? (
                <a
                  href={item.source_page_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#151515] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#202020] transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open Live Source
                </a>
              ) : (
                <button
                  disabled
                  className="px-3 py-2 rounded-lg bg-[#151515] text-[#4A4A4A] text-xs font-semibold cursor-not-allowed"
                >
                  No Web Link
                </button>
              )}
            </div>

            <div className="grid grid-cols-3 gap-2 pt-1">
              <button
                type="button"
                onClick={() => {
                  onVerify(item, "VERIFIED");
                  onClose();
                }}
                className="flex items-center justify-center gap-1 px-2 py-2 rounded-lg bg-[#10B981] text-black text-xs font-semibold hover:bg-[#10B981]/90 transition-all"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Verify
              </button>

              <button
                type="button"
                onClick={() => {
                  onVerify(item, "REJECTED");
                  onClose();
                }}
                className="flex items-center justify-center gap-1 px-2 py-2 rounded-lg bg-[#151515] border border-[#ef4444]/30 text-xs font-semibold text-[#ef4444] hover:bg-[#ef4444]/10 transition-colors"
              >
                <AlertOctagon className="w-3.5 h-3.5" />
                Reject
              </button>

              <button
                type="button"
                onClick={() => onSaveEvidence(item)}
                className="flex items-center justify-center gap-1 px-2 py-2 rounded-lg bg-[#111111] border border-[#2B2B2B] text-xs text-[#B3B3B3] hover:text-[#F5F5F5] hover:bg-[#1A1A1A] transition-colors"
              >
                <Lock className="w-3.5 h-3.5" />
                Save Vault
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
