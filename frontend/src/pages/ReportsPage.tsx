import React from "react";
import { FileText, Download, Shield } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { ReportCenterView } from "../components/investigation/ReportCenterView";

export const ReportsPage: React.FC = () => {
  return (
    <AppShell>
      <div className="p-6 max-w-6xl mx-auto w-full space-y-6 bg-[#000000] text-[#F5F5F5] min-h-[calc(100vh-3.5rem)]">
        <div className="flex items-center justify-between pb-4 border-b border-[#1A1A1A]">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#F5F5F5] flex items-center gap-2">
              <FileText className="w-5 h-5 text-[#F5F5F5]" />
              Forensic Reports & Dossiers
            </h1>
            <p className="text-xs text-[#777777] mt-0.5">
              Export comprehensive investigative summaries, takedown notices, and audit packages.
            </p>
          </div>
        </div>

        <ReportCenterView caseId="global" caseNumber="GLOBAL-DOSSIER" />
      </div>
    </AppShell>
  );
};
