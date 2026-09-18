import React from "react";
import { X, ExternalLink, Split, Globe, CheckCircle2, ShieldCheck, Tag } from "lucide-react";
import { SearchResultItem } from "./ResultCard";

interface ResultDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: SearchResultItem | null;
  onCompare: (item: SearchResultItem) => void;
}

export const ResultDetailModal: React.FC<ResultDetailModalProps> = ({
  isOpen,
  onClose,
  item,
  onCompare,
}) => {
  if (!isOpen || !item) return null;

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl max-w-xl w-full p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-indigo-600" />
            <h3 className="text-base font-bold text-gray-900">Result Inspection</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Large Preview */}
        <div className="aspect-video rounded-xl bg-gray-50 border border-gray-100 overflow-hidden flex items-center justify-center">
          {displayImage ? (
            <img
              src={displayImage}
              alt={item.page_title || "Discovered result"}
              className="w-full h-full object-contain"
            />
          ) : (
            <ShieldCheck className="w-12 h-12 text-emerald-500" />
          )}
        </div>

        {/* Details List */}
        <div className="space-y-2.5 text-xs">
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 space-y-2">
            <div>
              <span className="text-[10px] text-gray-500 block uppercase font-mono">
                Domain / Host
              </span>
              <p className="font-semibold text-gray-900">{domain}</p>
            </div>

            <div>
              <span className="text-[10px] text-gray-500 block uppercase font-mono">
                Page Title
              </span>
              <p className="font-medium text-gray-800 leading-snug">
                {item.page_title || "Untitled Public Document"}
              </p>
            </div>

            {item.source_page_url && (
              <div>
                <span className="text-[10px] text-gray-500 block uppercase font-mono">
                  Canonical URL
                </span>
                <a
                  href={item.source_page_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:underline break-all block mt-0.5"
                >
                  {item.source_page_url}
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
          <button
            type="button"
            onClick={() => {
              onClose();
              onCompare(item);
            }}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 text-xs font-semibold shadow-2xs transition"
          >
            <Split className="w-3.5 h-3.5" />
            <span>Compare Side-by-Side</span>
          </button>

          {item.source_page_url && (
            <a
              href={item.source_page_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Open Source</span>
            </a>
          )}
        </div>
      </div>
    </div>
  );
};
