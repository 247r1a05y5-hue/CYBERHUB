import React, { useState } from "react";
import {
  ExternalLink,
  Split,
  CheckCircle2,
  Lock,
  Globe,
  Eye,
  Shield,
  FileImage,
  AlertTriangle,
  Layers,
} from "lucide-react";

export interface ResultItemData {
  id: string;
  source_image_url?: string;
  thumbnail_url?: string;
  source_page_url?: string;
  page_title?: string;
  domain?: string;
  match_type?: string;
  similarity_score?: number;
  face_similarity?: number;
  phash_distance?: number;
  dhash_distance?: number;
  provider?: string;
  verification_status?: "PENDING_REVIEW" | "VERIFIED" | "REJECTED" | "UNCERTAIN" | string;
  discovered_at?: string;
  page_date?: string;
  extracted_text?: string;
  category?: string;
  // For dataset candidate results
  participant_code?: string;
  is_dataset_match?: boolean;
}

interface LensoResultCardProps {
  item: ResultItemData;
  onOpenDetail: (item: ResultItemData) => void;
  onOpenCompare: (item: ResultItemData) => void;
  onOpenVerify: (item: ResultItemData) => void;
  onSaveEvidence: (item: ResultItemData) => void;
}

export const LensoResultCard: React.FC<LensoResultCardProps> = ({
  item,
  onOpenDetail,
  onOpenCompare,
  onOpenVerify,
  onSaveEvidence,
}) => {
  const [imageError, setImageError] = useState(false);

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

  const similarityPercent =
    item.similarity_score !== undefined
      ? Math.round(
          item.similarity_score <= 1
            ? item.similarity_score * 100
            : item.similarity_score
        )
      : null;

  const getMatchTypeLabel = (type?: string) => {
    switch (type) {
      case "EXACT":
      case "exact":
        return "EXACT DUPLICATE";
      case "TRANSFORMED":
      case "transformed":
        return "TRANSFORMED COPY";
      case "FACE_MATCH":
      case "same_face":
        return "POTENTIAL FACE MATCH";
      case "SIMILAR":
      case "visually_similar":
        return "VISUALLY SIMILAR";
      case "RELATED":
      case "contextual":
        return "CONTEXTUAL";
      case "HISTORICAL":
      case "wayback":
        return "HISTORICAL CAPTURE";
      default:
        return type || "DISCOVERED MATCH";
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "VERIFIED":
        return (
          <span className="px-1.5 py-0.5 rounded bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30 text-[10px] font-mono font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> VERIFIED
          </span>
        );
      case "REJECTED":
        return (
          <span className="px-1.5 py-0.5 rounded bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/30 text-[10px] font-mono font-semibold">
            REJECTED
          </span>
        );
      case "UNCERTAIN":
        return (
          <span className="px-1.5 py-0.5 rounded bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30 text-[10px] font-mono font-semibold">
            UNCERTAIN
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 rounded bg-[#151515] text-[#777777] border border-[#2B2B2B] text-[10px] font-mono">
            CANDIDATE
          </span>
        );
    }
  };

  return (
    <div className="group relative flex flex-col bg-[#0C0C0C] hover:bg-[#111111] border border-[#1A1A1A] hover:border-[#2B2B2B] rounded-xl overflow-hidden transition-all duration-200 shadow-sm">
      {/* Image Preview Container */}
      <div
        onClick={() => onOpenDetail(item)}
        className="relative aspect-square w-full bg-[#050505] overflow-hidden cursor-pointer flex items-center justify-center border-b border-[#1A1A1A]"
      >
        {displayImage && !imageError ? (
          <img
            src={displayImage}
            alt={item.page_title || "Discovered result"}
            loading="lazy"
            onError={() => setImageError(true)}
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 p-4 text-center">
            <Globe className="w-8 h-8 text-[#2B2B2B]" />
            <span className="text-[10px] text-[#777777] font-mono uppercase tracking-wider">
              {item.is_dataset_match ? "PROTECTED DATASET" : "WEB SOURCE"}
            </span>
          </div>
        )}

        {/* Top Badges Overlay */}
        <div className="absolute top-2 left-2 right-2 flex items-center justify-between gap-1 pointer-events-none">
          {similarityPercent !== null && (
            <span className="px-2 py-0.5 rounded bg-black/85 backdrop-blur-sm border border-[#2B2B2B] font-mono text-[11px] font-bold text-[#F5F5F5] shadow">
              {similarityPercent}% MATCH
            </span>
          )}
          <div>{getStatusBadge(item.verification_status)}</div>
        </div>

        {/* Hover Action Overlay */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 p-2 pointer-events-auto">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenCompare(item);
            }}
            className="px-2.5 py-1.5 rounded-lg bg-[#151515] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#252525] transition-all flex items-center gap-1.5 shadow"
          >
            <Split className="w-3.5 h-3.5" />
            Compare
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenDetail(item);
            }}
            className="px-2.5 py-1.5 rounded-lg bg-[#F5F5F5] text-black text-xs font-semibold hover:bg-white transition-all flex items-center gap-1 shadow"
          >
            <Eye className="w-3.5 h-3.5" />
            Inspect
          </button>
        </div>
      </div>

      {/* Card Body Details */}
      <div className="p-3 flex flex-col justify-between flex-1 gap-2.5">
        <div>
          {/* Domain & Source Tag */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-[11px] font-mono text-[#777777] truncate flex items-center gap-1">
              <Globe className="w-3 h-3 shrink-0" />
              <span className="truncate">{domain}</span>
            </span>
            {item.provider && (
              <span className="text-[9px] font-mono uppercase text-[#4A4A4A] bg-[#111111] px-1 rounded">
                {item.provider}
              </span>
            )}
          </div>

          {/* Page Title / Heading */}
          <h3
            onClick={() => onOpenDetail(item)}
            className="text-xs font-semibold text-[#F5F5F5] line-clamp-2 hover:underline cursor-pointer tracking-normal leading-tight"
            title={item.page_title || item.source_page_url}
          >
            {item.page_title || item.source_page_url || (item.participant_code ? `Participant ${item.participant_code}` : "Discovered Web Endpoint")}
          </h3>

          {/* Match Classification Pill */}
          <div className="mt-2 flex items-center gap-1.5 flex-wrap">
            <span className="px-1.5 py-0.5 rounded bg-[#151515] border border-[#1A1A1A] text-[9px] font-mono text-[#B3B3B3] uppercase">
              {getMatchTypeLabel(item.match_type)}
            </span>
          </div>
        </div>

        {/* Card Footer Actions */}
        <div className="pt-2 border-t border-[#1A1A1A] flex items-center justify-between gap-1 text-xs">
          {item.source_page_url ? (
            <a
              href={item.source_page_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1 text-[#777777] hover:text-[#F5F5F5] transition-colors text-[11px]"
            >
              <ExternalLink className="w-3 h-3" />
              <span>Source</span>
            </a>
          ) : (
            <span className="text-[10px] text-[#4A4A4A]">Local Match</span>
          )}

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenVerify(item);
              }}
              title="Verify Finding"
              className="p-1 rounded text-[#777777] hover:text-[#10B981] hover:bg-[#151515] transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSaveEvidence(item);
              }}
              title="Save to Evidence Vault"
              className="p-1 rounded text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515] transition-colors"
            >
              <Lock className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
