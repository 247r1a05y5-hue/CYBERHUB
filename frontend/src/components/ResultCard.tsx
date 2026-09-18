import React, { useState } from "react";
import {
  ExternalLink,
  Split,
  Eye,
  Globe,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

export interface SearchResultItem {
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
  verification_status?: string;
  discovered_at?: string;
  is_dataset_match?: boolean;
  participant_code?: string;
}

interface ResultCardProps {
  item: SearchResultItem;
  onInspect: (item: SearchResultItem) => void;
  onCompare: (item: SearchResultItem) => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({
  item,
  onInspect,
  onCompare,
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
            return "web-source";
          }
        })()
      : "cyberhub-source");

  return (
    <div className="group bg-white rounded-xl border border-gray-200 overflow-hidden shadow-2xs hover:shadow-md transition-all duration-200 flex flex-col justify-between">
      {/* Image Container with Source Pill Overlay */}
      <div
        onClick={() => onInspect(item)}
        className="relative aspect-square w-full bg-gray-50 overflow-hidden cursor-pointer flex items-center justify-center border-b border-gray-100"
      >
        {displayImage && !imageError ? (
          <img
            src={displayImage}
            alt={item.page_title || "Discovered match"}
            loading="lazy"
            onError={() => setImageError(true)}
            className="w-full h-full object-cover group-hover:scale-103 transition-transform duration-300"
          />
        ) : (
          <div className="flex flex-col items-center gap-1.5 p-4 text-center text-gray-400">
            <Globe className="w-8 h-8 stroke-1 text-gray-300" />
            <span className="text-[10px] uppercase font-mono tracking-wider">
              {item.is_dataset_match ? "PROTECTED IDENTITY" : "SOURCE PREVIEW"}
            </span>
          </div>
        )}

        {/* Source Pill Button (Overlaid near bottom of image, matching frame 25/35/60) */}
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between gap-1 pointer-events-none">
          <div className="px-2.5 py-1 rounded-md bg-white/95 backdrop-blur-xs border border-gray-200/80 text-[11px] font-semibold text-gray-800 flex items-center gap-1.5 shadow-xs truncate max-w-[85%]">
            <div className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
            <span className="truncate">{item.source_page_url ? domain : "Open Source"}</span>
          </div>
        </div>

        {/* Hover Quick Action Buttons */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 p-2 pointer-events-auto">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onCompare(item);
            }}
            className="px-3 py-1.5 rounded-lg bg-white text-gray-900 text-xs font-semibold hover:bg-gray-100 transition-all flex items-center gap-1.5 shadow-sm cursor-pointer"
          >
            <Split className="w-3.5 h-3.5" />
            Compare
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onInspect(item);
            }}
            className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition-all flex items-center gap-1.5 shadow-sm cursor-pointer"
          >
            <Eye className="w-3.5 h-3.5" />
            Inspect
          </button>
        </div>
      </div>

      {/* Card Info Details */}
      <div className="p-3 space-y-1.5">
        <h3
          onClick={() => onInspect(item)}
          className="text-xs font-medium text-gray-900 line-clamp-2 hover:underline cursor-pointer leading-snug"
          title={item.page_title || item.source_page_url}
        >
          {item.page_title || item.source_page_url || (item.participant_code ? `Participant ${item.participant_code}` : "Discovered web endpoint")}
        </h3>

        <div className="flex items-center justify-between pt-1 border-t border-gray-100 text-[11px] text-gray-500">
          <span className="font-mono truncate">{domain}</span>
          {item.source_page_url && (
            <a
              href={item.source_page_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-indigo-600 hover:text-indigo-800 flex items-center gap-0.5"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};
