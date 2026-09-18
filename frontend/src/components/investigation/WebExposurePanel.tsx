import React from "react";
import {
  Globe,
  CheckCircle2,
  AlertCircle,
  Clock,
  ExternalLink,
  Shield,
  Layers,
} from "lucide-react";
import { ResultItemData } from "./LensoResultCard";

interface WebExposurePanelProps {
  results: ResultItemData[];
  onOpenDetail: (item: ResultItemData) => void;
  onOpenCompare: (item: ResultItemData) => void;
  onOpenVerify: (item: ResultItemData) => void;
  onSaveEvidence: (item: ResultItemData) => void;
}

export const WebExposurePanel: React.FC<WebExposurePanelProps> = ({
  results,
  onOpenDetail,
  onOpenCompare,
  onOpenVerify,
  onSaveEvidence,
}) => {
  const providers = [
    { name: "Google Lens / SearchAPI", status: "LIVE", description: "Visual search & public link index" },
    { name: "Google Cloud Vision", status: "CONFIGURED", description: "Web entities & OCR text extraction" },
    { name: "SerpApi Visual", status: "CONFIGURED", description: "Secondary public search crawler" },
    { name: "Wayback Machine", status: "LIVE", description: "Archival internet snapshots" },
    { name: "Common Crawl Index", status: "LIVE", description: "Public web archive corpus" },
    { name: "TinEye Reverse Search", status: "NOT CONFIGURED", description: "Commercial reverse image index" },
    { name: "Lenso Visual", status: "NOT CONFIGURED", description: "Facial & domain visual matcher" },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "LIVE":
        return (
          <span className="px-2 py-0.5 rounded bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30 text-[10px] font-mono font-bold">
            LIVE
          </span>
        );
      case "CONFIGURED":
        return (
          <span className="px-2 py-0.5 rounded bg-[#151515] text-[#B3B3B3] border border-[#2B2B2B] text-[10px] font-mono">
            CONFIGURED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded bg-[#0A0A0A] text-[#4A4A4A] border border-[#1A1A1A] text-[10px] font-mono">
            NOT CONFIGURED
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 my-4">
      {/* Provider Matrix */}
      <div className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl p-4">
        <h3 className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider mb-3 font-mono">
          Public Visual Discovery Providers
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {providers.map((p) => (
            <div
              key={p.name}
              className="p-3 bg-[#080808] border border-[#1A1A1A] rounded-lg flex items-center justify-between gap-2"
            >
              <div className="min-w-0">
                <p className="text-xs font-semibold text-[#F5F5F5] truncate">{p.name}</p>
                <p className="text-[10px] text-[#777777] truncate">{p.description}</p>
              </div>
              {getStatusBadge(p.status)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
