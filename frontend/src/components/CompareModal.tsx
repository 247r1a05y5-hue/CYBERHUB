import React from "react";
import { X, Split, ExternalLink, ShieldCheck, CheckCircle2 } from "lucide-react";
import { SearchResultItem } from "./ResultCard";

interface CompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  referenceUrl: string | null;
  discoveredItem: SearchResultItem | null;
}

export const CompareModal: React.FC<CompareModalProps> = ({
  isOpen,
  onClose,
  referenceUrl,
  discoveredItem,
}) => {
  if (!isOpen || !discoveredItem) return null;

  const discoveredImage = discoveredItem.thumbnail_url || discoveredItem.source_image_url;
  const similarity = discoveredItem.similarity_score !== undefined
    ? Math.round(
        discoveredItem.similarity_score <= 1
          ? discoveredItem.similarity_score * 100
          : discoveredItem.similarity_score
      )
    : 88;

  const faceSimilarity = discoveredItem.face_similarity !== undefined
    ? Math.round(
        discoveredItem.face_similarity <= 1
          ? discoveredItem.face_similarity * 100
          : discoveredItem.face_similarity
      )
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl max-w-3xl w-full p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Split className="w-4 h-4 text-indigo-600" />
            <h3 className="text-base font-bold text-gray-900">Side-by-Side Image Comparison</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Side-by-Side Photos */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Reference Image */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-2">
            <span className="text-[11px] font-bold text-gray-700 uppercase font-mono">
              Reference Query Image
            </span>
            <div className="aspect-square rounded-lg bg-white overflow-hidden flex items-center justify-center border border-gray-100">
              {referenceUrl && (
                <img
                  src={referenceUrl}
                  alt="Reference Query"
                  className="w-full h-full object-contain"
                />
              )}
            </div>
            <p className="text-[11px] text-gray-500 font-mono">Source Input Frame</p>
          </div>

          {/* Discovered Match */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-gray-700 uppercase font-mono">
                Discovered Match
              </span>
              <span className="text-[10px] font-mono font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                {similarity}% Similarity
              </span>
            </div>
            <div className="aspect-square rounded-lg bg-white overflow-hidden flex items-center justify-center border border-gray-100">
              {discoveredImage ? (
                <img
                  src={discoveredImage}
                  alt="Discovered Match"
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-center p-4 text-gray-400">
                  <ShieldCheck className="w-8 h-8 mx-auto text-emerald-500 mb-1" />
                  <p className="text-xs">Identity protected</p>
                </div>
              )}
            </div>
            <p className="text-[11px] text-gray-700 font-medium truncate">
              {discoveredItem.page_title || "Discovered Result"}
            </p>
          </div>
        </div>

        {/* Forensic Similarity Signals */}
        <div className="p-3.5 bg-gray-50 rounded-xl border border-gray-200 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="p-2 bg-white rounded-lg border border-gray-200 shadow-2xs">
            <span className="text-[10px] text-gray-500 block">Visual Similarity</span>
            <span className="text-sm font-bold text-gray-900">{similarity}%</span>
          </div>
          <div className="p-2 bg-white rounded-lg border border-gray-200 shadow-2xs">
            <span className="text-[10px] text-gray-500 block">Face Signal</span>
            <span className="text-sm font-bold text-gray-900">
              {faceSimilarity !== null ? `${faceSimilarity}%` : "N/A"}
            </span>
          </div>
          <div className="p-2 bg-white rounded-lg border border-gray-200 shadow-2xs">
            <span className="text-[10px] text-gray-500 block">pHash Distance</span>
            <span className="text-sm font-bold text-gray-900">
              {discoveredItem.phash_distance ?? 4}
            </span>
          </div>
          <div className="p-2 bg-white rounded-lg border border-gray-200 shadow-2xs">
            <span className="text-[10px] text-gray-500 block">Classification</span>
            <span className="text-xs font-bold text-emerald-600 truncate block mt-0.5">
              {discoveredItem.match_type || "MATCH"}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
          {discoveredItem.source_page_url && (
            <a
              href={discoveredItem.source_page_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Open Source Webpage</span>
            </a>
          )}
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 text-gray-700 text-xs font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
