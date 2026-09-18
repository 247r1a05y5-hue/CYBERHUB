import React from "react";
import {
  Layers,
  Shield,
  Globe,
  Copy,
  Users,
  Eye,
  Link2,
  MapPin,
  Type,
  History,
  CheckCircle2,
} from "lucide-react";

export type SearchCategoryType =
  | "ALL"
  | "DATASET"
  | "WEB"
  | "DUPLICATES"
  | "PEOPLE"
  | "SIMILAR"
  | "RELATED"
  | "PLACES"
  | "TEXT"
  | "HISTORICAL"
  | "VERIFIED";

export interface CategoryCounts {
  all: number;
  dataset: number;
  web: number;
  duplicates: number;
  people: number;
  similar: number;
  related: number;
  places: number;
  text: number;
  historical: number;
  verified: number;
}

interface SearchCategoryBarProps {
  activeCategory: SearchCategoryType;
  onSelectCategory: (category: SearchCategoryType) => void;
  counts: CategoryCounts;
}

export const SearchCategoryBar: React.FC<SearchCategoryBarProps> = ({
  activeCategory,
  onSelectCategory,
  counts,
}) => {
  const categories: {
    id: SearchCategoryType;
    label: string;
    icon: React.ElementType;
    count: number;
  }[] = [
    { id: "ALL", label: "ALL", icon: Layers, count: counts.all },
    { id: "DATASET", label: "DATASET MATCH", icon: Shield, count: counts.dataset },
    { id: "WEB", label: "WEB EXPOSURE", icon: Globe, count: counts.web },
    { id: "DUPLICATES", label: "DUPLICATES", icon: Copy, count: counts.duplicates },
    { id: "PEOPLE", label: "PEOPLE", icon: Users, count: counts.people },
    { id: "SIMILAR", label: "SIMILAR", icon: Eye, count: counts.similar },
    { id: "RELATED", label: "RELATED", icon: Link2, count: counts.related },
    { id: "PLACES", label: "PLACES", icon: MapPin, count: counts.places },
    { id: "TEXT", label: "TEXT", icon: Type, count: counts.text },
    { id: "HISTORICAL", label: "HISTORICAL", icon: History, count: counts.historical },
    { id: "VERIFIED", label: "VERIFIED", icon: CheckCircle2, count: counts.verified },
  ];

  return (
    <div className="w-full border-b border-[#1A1A1A] bg-[#050505] sticky top-0 z-30">
      <div className="flex items-center overflow-x-auto no-scrollbar px-3 py-1.5 gap-1">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.id;

          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => onSelectCategory(cat.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all select-none ${
                isActive
                  ? "bg-[#1A1A1A] text-[#F5F5F5] border border-[#2B2B2B] shadow-sm"
                  : "text-[#777777] hover:text-[#B3B3B3] hover:bg-[#0C0C0C] border border-transparent"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#F5F5F5]" : "text-[#777777]"}`} />
              <span>{cat.label}</span>
              <span
                className={`px-1.5 py-0.2 rounded-full font-mono text-[10px] ${
                  isActive
                    ? "bg-[#252525] text-[#F5F5F5]"
                    : "bg-[#111111] text-[#777777]"
                }`}
              >
                {cat.count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
