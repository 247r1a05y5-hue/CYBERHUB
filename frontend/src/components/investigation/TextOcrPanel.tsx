import React, { useState } from "react";
import { Type, Copy, Check, ExternalLink, Search, FileText } from "lucide-react";
import { ResultItemData } from "./LensoResultCard";

interface TextOcrPanelProps {
  extractedText?: string;
  textFindings: ResultItemData[];
  onOpenDetail: (item: ResultItemData) => void;
}

export const TextOcrPanel: React.FC<TextOcrPanelProps> = ({
  extractedText,
  textFindings,
  onOpenDetail,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!extractedText) return;
    navigator.clipboard.writeText(extractedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSearchWebForText = () => {
    if (!extractedText) return;
    const query = encodeURIComponent(extractedText.slice(0, 100));
    window.open(`https://www.google.com/search?q=${query}`, "_blank", "noopener,noreferrer");
  };

  if (!extractedText && textFindings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center bg-[#080808] border border-[#1A1A1A] rounded-xl my-4">
        <Type className="w-12 h-12 text-[#2B2B2B] mb-3" />
        <h3 className="text-sm font-semibold text-[#F5F5F5]">
          No Text Detected in Reference Image
        </h3>
        <p className="text-xs text-[#777777] max-w-md mt-1">
          Optical Character Recognition (OCR) did not detect significant readable alphanumeric characters or watermarks in this image.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 my-4">
      {/* OCR Text Card */}
      {extractedText && (
        <div className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl p-4">
          <div className="flex items-center justify-between gap-2 pb-3 border-b border-[#1A1A1A] mb-3">
            <div className="flex items-center gap-2">
              <Type className="w-4 h-4 text-[#F5F5F5]" />
              <span className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider font-mono">
                Extracted Text via OCR
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#151515] border border-[#2B2B2B] text-xs text-[#B3B3B3] hover:text-[#F5F5F5] transition-colors"
              >
                {copied ? <Check className="w-3 h-3 text-[#10B981]" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? "Copied" : "Copy Text"}</span>
              </button>
              <button
                type="button"
                onClick={handleSearchWebForText}
                className="flex items-center gap-1 px-3 py-1 rounded bg-[#F5F5F5] text-black text-xs font-semibold hover:bg-white transition-all shadow"
              >
                <Search className="w-3 h-3 text-black" />
                <span>Search Web for Text</span>
              </button>
            </div>
          </div>

          <div className="p-3 bg-[#050505] border border-[#1A1A1A] rounded-lg font-mono text-xs text-[#F5F5F5] leading-relaxed whitespace-pre-wrap">
            {extractedText}
          </div>
        </div>
      )}
    </div>
  );
};
