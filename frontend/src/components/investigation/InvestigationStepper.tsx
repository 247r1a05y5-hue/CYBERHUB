import React from "react";
import { Search, Lock, Activity, Clock, FileText } from "lucide-react";

export type StepId =
  | "image"
  | "discovery"
  | "evidence"
  | "timeline"
  | "graph"
  | "reports"
  | "overview"
  | "attestation"
  | "review"
  | "matches"
  | "risk"
  | "response"
  | "monitoring";

interface InvestigationTabProps {
  currentStep: StepId;
  onStepClick?: (step: StepId) => void;
  resultsCount?: number;
  evidenceCount?: number;
}

export const InvestigationStepper: React.FC<InvestigationTabProps> = ({
  currentStep,
  onStepClick,
  resultsCount = 0,
  evidenceCount = 0,
}) => {
  const tabs = [
    {
      id: "discovery" as StepId,
      label: "Results",
      icon: Search,
      count: resultsCount,
    },
    {
      id: "evidence" as StepId,
      label: "Evidence",
      icon: Lock,
      count: evidenceCount,
    },
    {
      id: "timeline" as StepId,
      label: "Timeline",
      icon: Clock,
    },
    {
      id: "graph" as StepId,
      label: "Graph",
      icon: Activity,
    },
    {
      id: "reports" as StepId,
      label: "Report",
      icon: FileText,
    },
  ];

  const getActiveTabId = (step: StepId): StepId => {
    if (step === "discovery" || step === "matches" || step === "review" || step === "image" || step === "overview") {
      return "discovery";
    }
    return step;
  };

  const activeTab = getActiveTabId(currentStep);

  return (
    <div className="flex items-center justify-between border-b border-[#1A1A1A] mb-5 overflow-x-auto no-scrollbar gap-1">
      <div className="flex items-center gap-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onStepClick && onStepClick(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-t-md transition-colors border-b-2 -mb-px whitespace-nowrap ${
                isActive
                  ? "border-[#F5F5F5] text-[#F5F5F5] bg-[#111111]"
                  : "border-transparent text-[#777777] hover:text-[#B3B3B3] hover:bg-[#0C0C0C]"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#F5F5F5]" : "text-[#777777]"}`} />
              <span>{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                    isActive
                      ? "bg-[#232323] text-[#F5F5F5]"
                      : "bg-[#151515] text-[#777777] border border-[#232323]"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
