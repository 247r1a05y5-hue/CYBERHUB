import React from "react";
import { X, RotateCcw, Search, Check } from "lucide-react";

export interface FilterState {
  sources: string[];
  matchTypes: string[];
  statuses: string[];
  domainQuery: string;
  minSimilarity: number;
}

interface ResultFilterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  filters: FilterState;
  onChangeFilters: (filters: FilterState) => void;
  onResetFilters: () => void;
  availableSources: string[];
  availableDomains: string[];
}

export const ResultFilterDrawer: React.FC<ResultFilterDrawerProps> = ({
  isOpen,
  onClose,
  filters,
  onChangeFilters,
  onResetFilters,
  availableSources,
}) => {
  if (!isOpen) return null;

  const matchTypeOptions = [
    { id: "EXACT", label: "Exact Duplicate" },
    { id: "TRANSFORMED", label: "Transformed Copy" },
    { id: "FACE_MATCH", label: "Same Face / Potential" },
    { id: "SIMILAR", label: "Visually Similar" },
    { id: "RELATED", label: "Contextual / Related" },
  ];

  const statusOptions = [
    { id: "CANDIDATE", label: "Candidate" },
    { id: "VERIFIED", label: "Verified Finding" },
    { id: "REJECTED", label: "Rejected / False Positive" },
    { id: "UNCERTAIN", label: "Pending Review" },
  ];

  const toggleSource = (source: string) => {
    const next = filters.sources.includes(source)
      ? filters.sources.filter((s) => s !== source)
      : [...filters.sources, source];
    onChangeFilters({ ...filters, sources: next });
  };

  const toggleMatchType = (type: string) => {
    const next = filters.matchTypes.includes(type)
      ? filters.matchTypes.filter((t) => t !== type)
      : [...filters.matchTypes, type];
    onChangeFilters({ ...filters, matchTypes: next });
  };

  const toggleStatus = (status: string) => {
    const next = filters.statuses.includes(status)
      ? filters.statuses.filter((s) => s !== status)
      : [...filters.statuses, status];
    onChangeFilters({ ...filters, statuses: next });
  };

  return (
    <div className="w-full bg-[#0C0C0C] border-b border-[#1A1A1A] p-4 animate-in slide-in-from-top-2 duration-200">
      <div className="flex items-center justify-between pb-3 border-b border-[#1A1A1A] mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider">
            Filter Investigation Results
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onResetFilters}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#151515] text-[11px] text-[#777777] hover:text-[#F5F5F5] transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Reset All
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-xs">
        {/* Filter Group 1: Source */}
        <div className="space-y-2">
          <p className="font-bold text-[10px] text-[#777777] uppercase tracking-wider">
            Discovery Source
          </p>
          <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
            {availableSources.length > 0 ? (
              availableSources.map((source) => {
                const checked = filters.sources.includes(source);
                return (
                  <label
                    key={source}
                    className="flex items-center gap-2 px-2 py-1 rounded hover:bg-[#151515] cursor-pointer select-none text-[#B3B3B3]"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleSource(source)}
                      className="rounded border-[#2B2B2B] bg-[#050505] text-white focus:ring-0 w-3.5 h-3.5"
                    />
                    <span className="truncate">{source}</span>
                  </label>
                );
              })
            ) : (
              <p className="text-[11px] text-[#4A4A4A] italic px-2">No dynamic sources</p>
            )}
          </div>
        </div>

        {/* Filter Group 2: Match Type */}
        <div className="space-y-2">
          <p className="font-bold text-[10px] text-[#777777] uppercase tracking-wider">
            Match Classification
          </p>
          <div className="space-y-1">
            {matchTypeOptions.map((opt) => {
              const checked = filters.matchTypes.includes(opt.id);
              return (
                <label
                  key={opt.id}
                  className="flex items-center gap-2 px-2 py-1 rounded hover:bg-[#151515] cursor-pointer select-none text-[#B3B3B3]"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleMatchType(opt.id)}
                    className="rounded border-[#2B2B2B] bg-[#050505] text-white focus:ring-0 w-3.5 h-3.5"
                  />
                  <span>{opt.label}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Filter Group 3: Status */}
        <div className="space-y-2">
          <p className="font-bold text-[10px] text-[#777777] uppercase tracking-wider">
            Verification Status
          </p>
          <div className="space-y-1">
            {statusOptions.map((opt) => {
              const checked = filters.statuses.includes(opt.id);
              return (
                <label
                  key={opt.id}
                  className="flex items-center gap-2 px-2 py-1 rounded hover:bg-[#151515] cursor-pointer select-none text-[#B3B3B3]"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleStatus(opt.id)}
                    className="rounded border-[#2B2B2B] bg-[#050505] text-white focus:ring-0 w-3.5 h-3.5"
                  />
                  <span>{opt.label}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Filter Group 4: Domain Search & Similarity Slider */}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <p className="font-bold text-[10px] text-[#777777] uppercase tracking-wider">
              Filter by Domain / Host
            </p>
            <div className="relative">
              <input
                type="text"
                placeholder="e.g. twitter.com, linkedin..."
                value={filters.domainQuery}
                onChange={(e) =>
                  onChangeFilters({ ...filters, domainQuery: e.target.value })
                }
                className="w-full bg-[#050505] border border-[#1A1A1A] rounded-md px-2.5 py-1.5 text-xs text-[#F5F5F5] placeholder-[#4A4A4A] focus:outline-none focus:border-[#4A4A4A]"
              />
              <Search className="w-3.5 h-3.5 text-[#777777] absolute right-2.5 top-2 pointer-events-none" />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <p className="font-bold text-[10px] text-[#777777] uppercase tracking-wider">
                Min Similarity Score
              </p>
              <span className="font-mono text-[11px] text-[#F5F5F5]">
                {Math.round(filters.minSimilarity * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={filters.minSimilarity}
              onChange={(e) =>
                onChangeFilters({
                  ...filters,
                  minSimilarity: parseFloat(e.target.value),
                })
              }
              className="w-full h-1 bg-[#1A1A1A] rounded-lg appearance-none cursor-pointer accent-[#F5F5F5]"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
