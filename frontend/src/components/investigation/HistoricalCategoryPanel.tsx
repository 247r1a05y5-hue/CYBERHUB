import React from "react";
import { History, ExternalLink, Calendar, Globe, Archive } from "lucide-react";
import { ResultItemData } from "./LensoResultCard";

interface HistoricalCategoryPanelProps {
  historicalResults: ResultItemData[];
  onOpenDetail: (item: ResultItemData) => void;
  onOpenCompare: (item: ResultItemData) => void;
}

export const HistoricalCategoryPanel: React.FC<HistoricalCategoryPanelProps> = ({
  historicalResults,
  onOpenDetail,
  onOpenCompare,
}) => {
  if (!historicalResults || historicalResults.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center bg-[#080808] border border-[#1A1A1A] rounded-xl my-4">
        <Archive className="w-12 h-12 text-[#2B2B2B] mb-3" />
        <h3 className="text-sm font-semibold text-[#F5F5F5]">
          No Historical Archival Records Found
        </h3>
        <p className="text-xs text-[#777777] max-w-md mt-1">
          Wayback Machine and Common Crawl archives do not indicate historical visual snapshots matching this query.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 my-4">
      <div className="p-3 bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl flex items-start gap-3">
        <History className="w-5 h-5 text-[#B3B3B3] shrink-0 mt-0.5" />
        <div className="text-xs">
          <p className="font-semibold text-[#F5F5F5]">
            Historical Web Archival Records (Wayback Machine & Common Crawl)
          </p>
          <p className="text-[#777777] mt-0.5">
            Archived snapshots preserve past exposure instances. Items absent from current crawls are labeled as <span className="text-[#F5F5F5] font-mono">NOT OBSERVED IN LATEST SEARCH</span>.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {historicalResults.map((item) => (
          <div
            key={item.id}
            className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl p-4 flex flex-col justify-between gap-3"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="px-2 py-0.5 rounded bg-[#151515] border border-[#2B2B2B] font-mono text-[10px] text-[#B3B3B3]">
                  ARCHIVE CAPTURE
                </span>
                <span className="text-[10px] font-mono text-[#777777] flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {item.page_date || "Archived snapshot"}
                </span>
              </div>

              <h4
                onClick={() => onOpenDetail(item)}
                className="text-xs font-semibold text-[#F5F5F5] hover:underline cursor-pointer line-clamp-2"
              >
                {item.page_title || item.source_page_url}
              </h4>
            </div>

            <div className="pt-2 border-t border-[#1A1A1A] flex items-center justify-between text-xs">
              <span className="text-[10px] text-[#777777] font-mono">
                NOT OBSERVED IN LATEST SEARCH
              </span>
              {item.source_page_url && (
                <a
                  href={item.source_page_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#B3B3B3] hover:text-[#F5F5F5] flex items-center gap-1 text-[11px]"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>Snapshot</span>
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
