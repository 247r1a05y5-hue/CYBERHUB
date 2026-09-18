import React from "react";
import {
  Users,
  Copy,
  Layers,
  Sparkles,
  ShieldCheck,
  Eye,
  ArrowUpDown,
  Filter,
  Search,
  Radio,
} from "lucide-react";

export type CategoryKey =
  | "all"
  | "people"
  | "duplicates"
  | "related"
  | "similar"
  | "dataset";

interface CategoryTabsProps {
  activeCategory: CategoryKey;
  onSelectCategory: (key: CategoryKey) => void;
  onOpenSort: () => void;
  onOpenFilter: () => void;
  onOpenResearchMode: () => void;
  counts?: Record<CategoryKey, number>;
}

export const CategoryTabs: React.FC<CategoryTabsProps> = ({
  activeCategory,
  onSelectCategory,
  onOpenSort,
  onOpenFilter,
  onOpenResearchMode,
  counts,
}) => {
  const tabs = [
    {
      key: "all" as CategoryKey,
      label: "All",
      icon: null,
      activeClass: "bg-gray-900 text-white shadow-sm",
      inactiveClass: "bg-gray-100 text-gray-700 hover:bg-gray-200",
    },
    {
      key: "people" as CategoryKey,
      label: "People",
      icon: Users,
      activeClass: "bg-[#DC2626] text-white shadow-sm",
      inactiveClass: "bg-red-50 text-red-700 hover:bg-red-100",
      iconColor: "text-red-500",
    },
    {
      key: "duplicates" as CategoryKey,
      label: "Duplicates",
      icon: Copy,
      activeClass: "bg-[#2563EB] text-white shadow-sm",
      inactiveClass: "bg-blue-50 text-blue-700 hover:bg-blue-100",
      iconColor: "text-blue-500",
    },
    {
      key: "related" as CategoryKey,
      label: "Related",
      icon: Layers,
      activeClass: "bg-[#D97706] text-white shadow-sm",
      inactiveClass: "bg-amber-50 text-amber-800 hover:bg-amber-100",
      iconColor: "text-amber-600",
    },
    {
      key: "similar" as CategoryKey,
      label: "Similar",
      icon: Sparkles,
      activeClass: "bg-[#7C3AED] text-white shadow-sm",
      inactiveClass: "bg-purple-50 text-purple-700 hover:bg-purple-100",
      iconColor: "text-purple-500",
    },
    {
      key: "dataset" as CategoryKey,
      label: "Dataset",
      icon: ShieldCheck,
      activeClass: "bg-[#059669] text-white shadow-sm",
      inactiveClass: "bg-emerald-50 text-emerald-800 hover:bg-emerald-100",
      iconColor: "text-emerald-600",
    },
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-2 border-b border-gray-100">
      {/* Category Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
        {tabs.map((tab) => {
          const isActive = activeCategory === tab.key;
          const Icon = tab.icon;
          const count = counts ? counts[tab.key] : undefined;

          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => onSelectCategory(tab.key)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                isActive ? tab.activeClass : tab.inactiveClass
              }`}
            >
              {Icon && (
                <Icon
                  className={`w-3.5 h-3.5 ${
                    isActive ? "text-white" : tab.iconColor || "text-gray-500"
                  }`}
                />
              )}
              <span>{tab.label}</span>
              {count !== undefined && count > 0 && (
                <span
                  className={`text-[10px] font-mono px-1 rounded-full ${
                    isActive
                      ? "bg-white/20 text-white"
                      : "bg-black/5 text-gray-600"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Right Controls: Sort, Filter, Research Mode */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Sort Button */}
        <button
          type="button"
          onClick={onOpenSort}
          title="Sort search results"
          className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 transition border border-gray-200 cursor-pointer shadow-2xs"
        >
          <ArrowUpDown className="w-3.5 h-3.5" />
        </button>

        {/* Filter Button */}
        <button
          type="button"
          onClick={onOpenFilter}
          title="Filter search results"
          className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 transition border border-gray-200 cursor-pointer shadow-2xs"
        >
          <Filter className="w-3.5 h-3.5" />
        </button>

        {/* Research Mode Button */}
        <button
          type="button"
          onClick={onOpenResearchMode}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#4379E6] hover:bg-[#346cd9] text-white font-semibold text-xs transition-all shadow-sm cursor-pointer"
        >
          <Radio className="w-3.5 h-3.5" />
          <span>Research Mode</span>
        </button>
      </div>
    </div>
  );
};
