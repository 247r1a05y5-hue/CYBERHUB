import React from "react";
import { X, Shuffle } from "lucide-react";

export type SortChoice =
  | "default"
  | "random"
  | "best_to_worst"
  | "worst_to_best"
  | "newest_to_oldest"
  | "oldest_to_newest";

interface SortModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedSort: SortChoice;
  onSelectSort: (sort: SortChoice) => void;
}

export const SortModal: React.FC<SortModalProps> = ({
  isOpen,
  onClose,
  selectedSort,
  onSelectSort,
}) => {
  if (!isOpen) return null;

  const sortOptions: { id: SortChoice; label: string }[] = [
    { id: "default", label: "Default" },
    { id: "random", label: "Random" },
    { id: "best_to_worst", label: "Match: Best to Worst" },
    { id: "worst_to_best", label: "Match: Worst to Best" },
    { id: "newest_to_oldest", label: "Date: Newest to Oldest" },
    { id: "oldest_to_newest", label: "Date: Oldest to Newest" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl max-w-md w-full p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-gray-100">
          <h3 className="text-base font-bold text-gray-900">Sort search results</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs font-medium text-gray-600">
          Choose the order for displaying results:
        </p>

        {/* Radio Option List */}
        <div className="border border-gray-200 rounded-xl divide-y divide-gray-100 overflow-hidden">
          {sortOptions.map((opt) => {
            const isChecked = selectedSort === opt.id;
            return (
              <label
                key={opt.id}
                className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50/80 cursor-pointer select-none transition"
              >
                <div
                  className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                    isChecked
                      ? "border-indigo-600 bg-indigo-600"
                      : "border-gray-300 bg-white"
                  }`}
                >
                  {isChecked && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                </div>
                <input
                  type="radio"
                  name="sortOption"
                  checked={isChecked}
                  onChange={() => {
                    onSelectSort(opt.id);
                    onClose();
                  }}
                  className="hidden"
                />
                <span className="text-xs font-semibold text-gray-800">{opt.label}</span>
              </label>
            );
          })}
        </div>

        <div className="space-y-2 pt-1">
          <p className="text-[11px] text-gray-500">
            Or click a button below to see different results, that you haven't seen before:
          </p>
          <button
            type="button"
            onClick={() => {
              onSelectSort("random");
              onClose();
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-indigo-200 bg-indigo-50/50 hover:bg-indigo-100 text-indigo-700 font-semibold text-xs transition cursor-pointer shadow-2xs"
          >
            <Shuffle className="w-3.5 h-3.5" />
            <span>Show diverse results</span>
          </button>
        </div>
      </div>
    </div>
  );
};
