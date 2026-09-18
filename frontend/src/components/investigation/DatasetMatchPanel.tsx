import React from "react";
import {
  Shield,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Lock,
  Layers,
  FileCheck,
  UserCheck,
} from "lucide-react";
import { ResultItemData } from "./LensoResultCard";

interface DatasetMatchPanelProps {
  candidates: ResultItemData[];
  onOpenCompare: (item: ResultItemData) => void;
  onOpenDetail: (item: ResultItemData) => void;
  onVerify: (item: ResultItemData, status: "VERIFIED" | "REJECTED") => void;
}

export const DatasetMatchPanel: React.FC<DatasetMatchPanelProps> = ({
  candidates,
  onOpenCompare,
  onOpenDetail,
  onVerify,
}) => {
  if (!candidates || candidates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center bg-[#080808] border border-[#1A1A1A] rounded-xl my-4">
        <Shield className="w-12 h-12 text-[#2B2B2B] mb-3" />
        <h3 className="text-sm font-semibold text-[#F5F5F5]">
          No Controlled Dataset Matches Found
        </h3>
        <p className="text-xs text-[#777777] max-w-md mt-1">
          The query image does not match any enrolled participant in the AWS Rekognition collection with authorized consent.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 my-4">
      {/* Privacy Notice Banner */}
      <div className="p-3 bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl flex items-start gap-3">
        <Shield className="w-5 h-5 text-[#10B981] shrink-0 mt-0.5" />
        <div className="text-xs">
          <p className="font-semibold text-[#F5F5F5]">
            Controlled Dataset Identity Match (AWS Rekognition)
          </p>
          <p className="text-[#777777] mt-0.5">
            Target candidate matched against authorized enrollment index. Server-side reference photos are strictly protected and never leaked to the client.
          </p>
        </div>
      </div>

      {/* Candidate List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {candidates.map((cand, idx) => {
          const similarity = cand.similarity_score !== undefined
            ? Math.round(
                cand.similarity_score <= 1
                  ? cand.similarity_score * 100
                  : cand.similarity_score
              )
            : 95;

          return (
            <div
              key={cand.id || idx}
              className="bg-[#0C0C0C] border border-[#1A1A1A] hover:border-[#2B2B2B] rounded-xl p-4 flex flex-col justify-between gap-4 transition-all"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded bg-[#151515] border border-[#2B2B2B] font-mono text-[11px] font-bold text-[#F5F5F5]">
                    #{idx + 1} CANDIDATE
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30 font-mono text-[11px] font-bold">
                    {similarity}% CONFIDENCE
                  </span>
                </div>

                <div className="flex items-center gap-3 my-3">
                  <div className="w-12 h-12 rounded-xl bg-[#151515] border border-[#2B2B2B] flex items-center justify-center shrink-0">
                    <UserCheck className="w-6 h-6 text-[#F5F5F5]" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-[#F5F5F5]">
                      {cand.participant_code ? `Participant ${cand.participant_code}` : "Enrolled Identity"}
                    </h4>
                    <p className="text-[11px] font-mono text-[#777777]">
                      Status: Active Authorized Consent
                    </p>
                  </div>
                </div>

                {/* Confirmed Public Sources */}
                {cand.source_page_url && (
                  <div className="p-2.5 rounded bg-[#080808] border border-[#1A1A1A] text-xs space-y-1">
                    <span className="text-[10px] text-[#777777] block uppercase font-mono">
                      Participant-Confirmed Public Source
                    </span>
                    <a
                      href={cand.source_page_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#B3B3B3] hover:text-[#F5F5F5] underline flex items-center gap-1 truncate"
                    >
                      <ExternalLink className="w-3 h-3 shrink-0" />
                      <span className="truncate">{cand.source_page_url}</span>
                    </a>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="pt-3 border-t border-[#1A1A1A] flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => onOpenCompare(cand)}
                  className="px-3 py-1.5 rounded-lg bg-[#111111] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#1A1A1A] transition-colors"
                >
                  Review Match
                </button>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => onVerify(cand, "REJECTED")}
                    className="px-2.5 py-1.5 rounded-lg bg-[#151515] text-[#ef4444] text-xs hover:bg-[#ef4444]/10 transition-colors"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => onVerify(cand, "VERIFIED")}
                    className="px-3 py-1.5 rounded-lg bg-[#10B981] text-black font-semibold text-xs hover:bg-[#10B981]/90 transition-all"
                  >
                    Confirm Match
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
