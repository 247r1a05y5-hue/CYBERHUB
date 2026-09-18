import React, { useState } from "react";
import { X, Globe, PenLine, Check, RotateCcw } from "lucide-react";

export interface FilterOptions {
  websiteQuery: string;
  keywordQuery: string;
}

interface FilterModalProps {
  isOpen: boolean;
  onClose: () => void;
  filters: FilterOptions;
  onApplyFilters: (filters: FilterOptions) => void;
  onResetFilters: () => void;
}

export const FilterModal: React.FC<FilterModalProps> = ({
  isOpen,
  onClose,
  filters,
  onApplyFilters,
  onResetFilters,
}) => {
  const [localWebsite, setLocalWebsite] = useState(filters.websiteQuery);
  const [localKeyword, setLocalKeyword] = useState(filters.keywordQuery);

  if (!isOpen) return null;

  const exampleKeywords = ["red", "night", "grayscale", "rain", "text", "portrait", "studio"];

  const handleApply = () => {
    onApplyFilters({
      websiteQuery: localWebsite,
      keywordQuery: localKeyword,
    });
    onClose();
  };

  const handleReset = () => {
    setLocalWebsite("");
    setLocalKeyword("");
    onResetFilters();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl max-w-md w-full p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-gray-100">
          <h3 className="text-base font-bold text-gray-900">Filter search results</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filter 1: Website */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-gray-800">
            Filter by website:
          </label>
          <div className="relative flex items-center">
            <Globe className="w-4 h-4 text-gray-400 absolute left-3 pointer-events-none" />
            <input
              type="text"
              placeholder="Paste or type..."
              value={localWebsite}
              onChange={(e) => setLocalWebsite(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 text-xs text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-gray-50/50"
            />
          </div>
        </div>

        {/* Filter 2: Keywords */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-gray-800">
            Or filter by text keywords:
          </label>
          <div className="relative flex items-center">
            <PenLine className="w-4 h-4 text-gray-400 absolute left-3 pointer-events-none" />
            <input
              type="text"
              placeholder="Keywords (in English)"
              value={localKeyword}
              onChange={(e) => setLocalKeyword(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 text-xs text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-gray-50/50"
            />
          </div>
        </div>

        {/* Example Keyword Chips */}
        <div className="space-y-2">
          <p className="text-[11px] text-gray-500">Use examples below to try:</p>
          <div className="flex flex-wrap gap-1.5">
            {exampleKeywords.map((kw) => (
              <button
                key={kw}
                type="button"
                onClick={() => setLocalKeyword(kw)}
                className="px-2.5 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 text-[11px] font-medium text-gray-700 transition cursor-pointer"
              >
                {kw}
              </button>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-2 flex items-center gap-2">
          {(localWebsite || localKeyword) && (
            <button
              type="button"
              onClick={handleReset}
              className="px-3.5 py-2.5 rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 text-gray-600 font-semibold text-xs transition cursor-pointer"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}

          <button
            type="button"
            onClick={handleApply}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#5B50E6] hover:bg-[#4F46E5] text-white font-semibold text-xs transition shadow-sm cursor-pointer"
          >
            <Check className="w-4 h-4 text-white" />
            <span>Apply filter</span>
          </button>
        </div>
      </div>
    </div>
  );
};
