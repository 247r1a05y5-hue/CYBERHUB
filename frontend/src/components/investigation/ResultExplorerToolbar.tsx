import React from "react";
import {
  SlidersHorizontal,
  LayoutGrid,
  List,
  ChevronDown,
  ArrowUpDown,
  PlusCircle,
  Clock,
  Sparkles,
  Shield,
  Layers,
} from "lucide-react";

export type SortOption = "best_match" | "newest" | "most_similar" | "most_relevant";

interface ResultExplorerToolbarProps {
  referencePreviewUrl: string | null;
  referenceMeta?: {
    sha256?: string;
    dimensions?: { width: number; height: number };
    fileSize?: string;
  };
  totalCount: number;
  filteredCount: number;
  currentSort: SortOption;
  onSortChange: (sort: SortOption) => void;
  viewMode: "grid" | "list";
  onViewModeChange: (mode: "grid" | "list") => void;
  isFilterOpen: boolean;
  onToggleFilter: () => void;
  activeFilterCount: number;
  onNewSearch: () => void;
}

export const ResultExplorerToolbar: React.FC<ResultExplorerToolbarProps> = ({
  referencePreviewUrl,
  referenceMeta,
  totalCount,
  filteredCount,
  currentSort,
  onSortChange,
  viewMode,
  onViewModeChange,
  isFilterOpen,
  onToggleFilter,
  activeFilterCount,
  onNewSearch,
}) => {
  return (
    <div className="w-full bg-[#080808] border-b border-[#1A1A1A] px-4 py-3 flex flex-wrap items-center justify-between gap-3">
      {/* Left: Reference Image thumbnail & Query Info */}
      <div className="flex items-center gap-3 min-w-0">
        {referencePreviewUrl && (
          <div className="w-10 h-10 rounded-md bg-[#0C0C0C] border border-[#2B2B2B] overflow-hidden shrink-0 flex items-center justify-center">
            <img
              src={referencePreviewUrl}
              alt="Query reference"
              className="w-full h-full object-cover"
            />
          </div>
        )}

        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#F5F5F5] tracking-wide">
              Search Results
            </h2>
            <span className="px-2 py-0.5 rounded bg-[#151515] border border-[#2B2B2B] font-mono text-[11px] text-[#B3B3B3]">
              {filteredCount} {filteredCount === 1 ? "result" : "results"}
              {filteredCount !== totalCount && ` (filtered from ${totalCount})`}
            </span>
          </div>
          {referenceMeta?.sha256 && (
            <p className="text-[10px] font-mono text-[#777777] truncate max-w-xs mt-0.5">
              SHA: {referenceMeta.sha256.substring(0, 16)}...
            </p>
          )}
        </div>
      </div>

      {/* Right: Controls (Filters, Sort, View, New Search) */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Filter Drawer Toggle */}
        <button
          type="button"
          onClick={onToggleFilter}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isFilterOpen || activeFilterCount > 0
              ? "bg-[#1A1A1A] text-[#F5F5F5] border border-[#2B2B2B]"
              : "bg-[#0C0C0C] text-[#B3B3B3] hover:text-[#F5F5F5] hover:bg-[#151515] border border-[#1A1A1A]"
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Filters</span>
          {activeFilterCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-[#F5F5F5] text-black text-[10px] font-bold flex items-center justify-center ml-0.5">
              {activeFilterCount}
            </span>
          )}
        </button>

        {/* Sort Select */}
        <div className="relative flex items-center">
          <select
            value={currentSort}
            onChange={(e) => onSortChange(e.target.value as SortOption)}
            className="appearance-none bg-[#0C0C0C] text-[#B3B3B3] hover:text-[#F5F5F5] border border-[#1A1A1A] rounded-lg pl-3 pr-7 py-1.5 text-xs font-medium focus:outline-none focus:border-[#4A4A4A] cursor-pointer"
          >
            <option value="best_match">Sort: Best Match</option>
            <option value="newest">Sort: Newest</option>
            <option value="most_similar">Sort: Most Similar</option>
            <option value="most_relevant">Sort: Most Relevant</option>
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-[#777777] absolute right-2 pointer-events-none" />
        </div>

        {/* View Mode Toggle (Grid / List) */}
        <div className="flex items-center bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => onViewModeChange("grid")}
            title="Grid View"
            className={`p-1.5 rounded-md text-xs transition-colors ${
              viewMode === "grid"
                ? "bg-[#1A1A1A] text-[#F5F5F5]"
                : "text-[#777777] hover:text-[#B3B3B3]"
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onViewModeChange("list")}
            title="List View"
            className={`p-1.5 rounded-md text-xs transition-colors ${
              viewMode === "list"
                ? "bg-[#1A1A1A] text-[#F5F5F5]"
                : "text-[#777777] hover:text-[#B3B3B3]"
            }`}
          >
            <List className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* New Search Button */}
        <button
          type="button"
          onClick={onNewSearch}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#111111] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#1A1A1A] transition-all ml-1"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">New Search</span>
        </button>
      </div>
    </div>
  );
};
