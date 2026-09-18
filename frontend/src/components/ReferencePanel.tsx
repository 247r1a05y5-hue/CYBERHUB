import React from "react";
import {
  Search,
  RotateCw,
  Bell,
  Radio,
  Image as ImageIcon,
  Sparkles,
} from "lucide-react";

interface ReferencePanelProps {
  previewUrl: string | null;
  onNewSearch: () => void;
  onRefresh: () => void;
  onOpenAlert: () => void;
  onOpenResearchMode: () => void;
  metadata?: {
    dimensions?: { width: number; height: number };
    fileSize?: string;
  };
}

export const ReferencePanel: React.FC<ReferencePanelProps> = ({
  previewUrl,
  onNewSearch,
  onRefresh,
  onOpenAlert,
  onOpenResearchMode,
}) => {
  return (
    <aside className="w-full lg:w-80 shrink-0 space-y-4">
      {/* Primary Reference Image Card */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-3.5 space-y-3">
        <div className="aspect-[4/5] sm:aspect-square lg:aspect-[4/5] w-full rounded-xl bg-gray-50 border border-gray-100 overflow-hidden flex items-center justify-center relative">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="Search reference query"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-400">
              <ImageIcon className="w-10 h-10 stroke-1" />
              <span className="text-xs">No reference image</span>
            </div>
          )}
        </div>

        {/* Action Button Row */}
        <div className="flex items-center gap-2 pt-1">
          {/* New Search Button (Amber Accent) */}
          <button
            type="button"
            onClick={onNewSearch}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#C27803] hover:bg-[#B45309] text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
          >
            <Search className="w-3.5 h-3.5 text-white" />
            <span>New search</span>
          </button>

          {/* Refresh / Retake Button */}
          <button
            type="button"
            onClick={onRefresh}
            title="Refresh search"
            className="p-2 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors cursor-pointer"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>

          {/* Alert Button */}
          <button
            type="button"
            onClick={onOpenAlert}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 text-xs font-semibold transition-colors cursor-pointer"
          >
            <Bell className="w-3.5 h-3.5 text-gray-600" />
            <span>Alert</span>
          </button>
        </div>
      </div>

      {/* Get More Results / Research Mode Card */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 space-y-3">
        <div>
          <h4 className="text-sm font-bold text-gray-900">Get more results</h4>
          <p className="text-xs text-gray-500 mt-1 leading-relaxed">
            Explore more pictures in the Research Mode!
          </p>
        </div>

        <button
          type="button"
          onClick={onOpenResearchMode}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#4379E6] hover:bg-[#346cd9] text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
        >
          <Radio className="w-3.5 h-3.5" />
          <span>Research mode</span>
        </button>
      </div>
    </aside>
  );
};
