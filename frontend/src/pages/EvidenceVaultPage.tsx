import React from "react";
import { Lock, FileCheck, Shield, Download, FileText } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { EvidenceVaultView } from "../components/investigation/EvidenceVaultView";

export const EvidenceVaultPage: React.FC = () => {
  return (
    <AppShell>
      <div className="p-6 max-w-6xl mx-auto w-full space-y-6 bg-[#000000] text-[#F5F5F5] min-h-[calc(100vh-3.5rem)]">
        <div className="flex items-center justify-between pb-4 border-b border-[#1A1A1A]">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#F5F5F5] flex items-center gap-2">
              <Lock className="w-5 h-5 text-[#F5F5F5]" />
              Evidence Vault & Chain of Custody
            </h1>
            <p className="text-xs text-[#777777] mt-0.5">
              Cryptographically sealed forensic artifacts, SHA-256 hashes, and timestamped dossiers.
            </p>
          </div>
        </div>

        <EvidenceVaultView
          caseId="global"
          referenceImageUrl={null}
          referenceSha256={null}
        />
      </div>
    </AppShell>
  );
};
