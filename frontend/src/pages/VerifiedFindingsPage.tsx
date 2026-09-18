import React, { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Search, ExternalLink, Lock } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";

export const VerifiedFindingsPage: React.FC = () => {
  const [verifiedItems] = useState<any[]>([]);

  return (
    <AppShell>
      <div className="p-6 max-w-6xl mx-auto w-full space-y-6 bg-[#000000] text-[#F5F5F5] min-h-[calc(100vh-3.5rem)]">
        <div className="flex items-center justify-between pb-4 border-b border-[#1A1A1A]">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#F5F5F5] flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#10B981]" />
              Verified Findings
            </h1>
            <p className="text-xs text-[#777777] mt-0.5">
              Analyst-confirmed exposure endpoints, forensic matches, and verified public appearances.
            </p>
          </div>
        </div>

        {verifiedItems.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Render items */}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-16 text-center bg-[#080808] border border-[#1A1A1A] rounded-2xl">
            <CheckCircle2 className="w-12 h-12 text-[#2B2B2B] mb-3" />
            <h3 className="text-sm font-semibold text-[#F5F5F5]">
              No Verified Findings Yet
            </h3>
            <p className="text-xs text-[#777777] max-w-sm mt-1 mb-4">
              When you manually review and verify candidate matches during an investigation, they are preserved in this verified vault.
            </p>
            <Link
              to="/dashboard"
              className="px-4 py-2 rounded-lg bg-[#151515] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#202020]"
            >
              Start Investigation
            </Link>
          </div>
        )}
      </div>
    </AppShell>
  );
};
