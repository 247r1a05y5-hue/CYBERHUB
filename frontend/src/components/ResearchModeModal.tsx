import React, { useState } from "react";
import { Sparkles, X, Check, Shield, Search, ArrowRight, Globe } from "lucide-react";

interface ResearchModeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartResearch: (options: { deepWeb: boolean; darkWeb: boolean; osintArchive: boolean }) => void;
  isResearching?: boolean;
}

export const ResearchModeModal: React.FC<ResearchModeModalProps> = ({
  isOpen,
  onClose,
  onStartResearch,
  isResearching = false,
}) => {
  const [deepWeb, setDeepWeb] = useState(true);
  const [darkWeb, setDarkWeb] = useState(false);
  const [osintArchive, setOsintArchive] = useState(true);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 max-w-lg w-full p-6 relative animate-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Research Mode</h3>
            <p className="text-xs text-slate-500">
              Unleash deep visual search & archived web discovery
            </p>
          </div>
        </div>

        <div className="space-y-3 my-6">
          <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50/70 transition cursor-pointer">
            <input
              type="checkbox"
              checked={deepWeb}
              onChange={(e) => setDeepWeb(e.target.checked)}
              className="mt-1 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <div>
              <div className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                <Globe className="w-4 h-4 text-indigo-500" /> Deep Public Web Search
              </div>
              <div className="text-xs text-slate-500">
                Expanded domain crawling, image forums, social indexing & public repositories.
              </div>
            </div>
          </label>

          <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50/70 transition cursor-pointer">
            <input
              type="checkbox"
              checked={osintArchive}
              onChange={(e) => setOsintArchive(e.target.checked)}
              className="mt-1 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <div>
              <div className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                <Search className="w-4 h-4 text-amber-500" /> Wayback & Historic Visual Archives
              </div>
              <div className="text-xs text-slate-500">
                Cross-reference historical snapshots for deleted or modified images.
              </div>
            </div>
          </label>

          <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50/70 transition cursor-pointer">
            <input
              type="checkbox"
              checked={darkWeb}
              onChange={(e) => setDarkWeb(e.target.checked)}
              className="mt-1 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <div>
              <div className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                <Shield className="w-4 h-4 text-slate-600" /> Breach & Darknet Indexes
              </div>
              <div className="text-xs text-slate-500">
                Check indexed breach leak caches for sensitive identity matching.
              </div>
            </div>
          </label>
        </div>

        <div className="bg-amber-50 border border-amber-200/60 rounded-xl p-3 text-xs text-amber-900 mb-6 flex items-start gap-2">
          <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <span>
            Research Mode scans run in background queue and append new discovered endpoints live via SSE stream.
          </span>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-100">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onStartResearch({ deepWeb, darkWeb, osintArchive });
              onClose();
            }}
            disabled={isResearching}
            className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm hover:shadow flex items-center gap-2 transition disabled:opacity-50"
          >
            {isResearching ? (
              <>Scanning In Background...</>
            ) : (
              <>
                Launch Research Mode <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
