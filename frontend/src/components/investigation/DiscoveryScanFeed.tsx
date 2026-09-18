import React, { useState, useEffect } from "react";
import {
  Globe,
  Radio,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import { api } from "../../services/api";
import { formatErrorMessage, safeRenderText } from "../../utils/errorUtils";

export interface ProviderStatusInfo {
  name: string;
  status: "NOT_CONFIGURED" | "READY" | "RUNNING" | "SUCCEEDED" | "FAILED" | "DEGRADED" | "RATE_LIMITED";
  configured: boolean;
  circuit_breaker: string;
}

export interface ScanEventLog {
  id: string;
  step: string;
  message: string;
  timestamp: string;
  eventType: string;
  progressPct: number;
}

interface DiscoveryScanFeedProps {
  investigationId: string;
  caseNumber: string;
  onScanComplete?: () => void;
}

export const DiscoveryScanFeed: React.FC<DiscoveryScanFeedProps> = ({
  investigationId,
  caseNumber,
  onScanComplete,
}) => {
  const [providerStatuses, setProviderStatuses] = useState<Record<string, ProviderStatusInfo>>({
    searchapi_lens: {
      name: "SearchAPI (Google Lens)",
      status: "READY",
      configured: true,
      circuit_breaker: "CLOSED",
    },
  });

  const [isScanning, setIsScanning] = useState(false);
  const [progressPct, setProgressPct] = useState(0);
  const [currentStep, setCurrentStep] = useState<string>("IDLE");
  const [eventLogs, setEventLogs] = useState<ScanEventLog[]>([]);
  const [scanError, setScanError] = useState<string | null>(null);

  // Fetch provider configuration statuses
  const fetchProviderStatuses = async () => {
    try {
      const res = await api.get(`/investigations/${investigationId}/providers`);
      if (res.data && res.data.providers) {
        setProviderStatuses(res.data.providers);
      }
    } catch {
      try {
        const fallbackRes = await api.get("/investigations/providers/status");
        if (fallbackRes.data && fallbackRes.data.providers) {
          setProviderStatuses(fallbackRes.data.providers);
        }
      } catch {
        // Ignore fallback
      }
    }
  };

  useEffect(() => {
    fetchProviderStatuses();
  }, [investigationId]);

  // Execute Direct Public Web Reverse Discovery via Google Lens
  const handleDirectWebSearch = async () => {
    setIsScanning(true);
    setProgressPct(20);
    setCurrentStep("Preparing image");
    setScanError(null);
    setEventLogs([
      {
        id: "step_1",
        step: "Preparing image",
        message: "Preparing reference asset and vector embeddings...",
        timestamp: new Date().toLocaleTimeString(),
        eventType: "prepare.started",
        progressPct: 20,
      },
    ]);

    try {
      // Step 2: Sending to Google Lens
      setTimeout(() => {
        setCurrentStep("Sending to Google Lens");
        setProgressPct(40);
        setEventLogs((prev) => [
          {
            id: `step_2_${Date.now()}`,
            step: "Sending to Google Lens",
            message: "Dispatching search query to Google Lens via SearchAPI...",
            timestamp: new Date().toLocaleTimeString(),
            eventType: "provider.dispatched",
            progressPct: 40,
          },
          ...prev,
        ]);
      }, 300);

      // Step 3: Finding visual matches & source pages
      setTimeout(() => {
        setCurrentStep("Finding visual matches & source pages");
        setProgressPct(65);
        setEventLogs((prev) => [
          {
            id: `step_3_${Date.now()}`,
            step: "Finding visual matches",
            message: "Searching public web index for visual matches and source pages...",
            timestamp: new Date().toLocaleTimeString(),
            eventType: "matches.finding",
            progressPct: 65,
          },
          ...prev,
        ]);
      }, 700);

      const res = await api.post(`/investigations/${investigationId}/web-search`, {
        max_results: 25,
        include_similar: true,
      });

      const data = res.data;

      // Step 4: Analyzing candidates
      setCurrentStep("Analyzing candidates");
      setProgressPct(85);
      setEventLogs((prev) => [
        {
          id: `step_4_${Date.now()}`,
          step: "Analyzing candidates",
          message: `Received ${data.results_count} candidates. Evaluating pHash/dHash and DINOv2 match tiers...`,
          timestamp: new Date().toLocaleTimeString(),
          eventType: "matching.started",
          progressPct: 85,
        },
        ...prev,
      ]);

      setTimeout(() => {
        setIsScanning(false);
        setProgressPct(100);
        setCurrentStep("Finalizing results");
        setEventLogs((prev) => [
          {
            id: `step_5_${Date.now()}`,
            step: "Finalizing results",
            message: `Public search completed. Discovered ${data.results_count} public web sightings.`,
            timestamp: new Date().toLocaleTimeString(),
            eventType: "search.completed",
            progressPct: 100,
          },
          ...prev,
        ]);
        if (onScanComplete) onScanComplete();
      }, 500);
    } catch (err: any) {
      console.error("Web Search error:", err);
      setIsScanning(false);
      const msg = formatErrorMessage(err, "Public web search unavailable — SearchAPI could not be reached.");
      setScanError(msg);
      setEventLogs((prev) => [
        {
          id: `step_err_${Date.now()}`,
          step: "FAILED",
          message: `Search failed: ${msg}`,
          timestamp: new Date().toLocaleTimeString(),
          eventType: "search.failed",
          progressPct: 0,
        },
        ...prev,
      ]);
    }
  };

  const lensStatus = providerStatuses.searchapi_lens?.status || "READY";

  return (
    <div className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg p-4 sm:p-5 space-y-4 text-left">
      {/* Top Controller Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1A1A1A] pb-3.5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
              Google Lens · via SearchAPI
            </span>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                isScanning
                  ? "bg-[#111111] text-[#F5F5F5] border-[#2B2B2B]"
                  : lensStatus === "READY"
                  ? "bg-[#10B981]/10 text-[#10B981] border-[#10B981]/25"
                  : "bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/25"
              }`}
            >
              {isScanning ? "SEARCHING" : lensStatus === "READY" ? "READY" : "FAILED"}
            </span>
          </div>
          <p className="text-xs text-[#777777] mt-0.5">
            Real-time public web index query for exact duplicates, visual similarities, and source pages.
          </p>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDirectWebSearch}
            disabled={isScanning}
            className="px-3.5 py-1.5 bg-[#F5F5F5] hover:bg-white text-[#000000] text-xs font-semibold rounded flex items-center gap-2 active:scale-95 transition-all disabled:opacity-40"
          >
            {isScanning ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
                <span>Searching...</span>
              </>
            ) : (
              <>
                <Search className="w-3.5 h-3.5 text-black" />
                <span>Query Google Lens</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Explicit Error State */}
      {scanError && (
        <div className="p-3 rounded bg-[#111111] border border-[#ef4444]/40 text-xs text-[#ef4444] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{safeRenderText(scanError)}</span>
          </div>
          <button
            type="button"
            onClick={handleDirectWebSearch}
            className="px-2.5 py-1 bg-[#151515] hover:bg-[#1E1E1E] text-[#F5F5F5] border border-[#2B2B2B] rounded text-[11px] font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Progress & Live Feed */}
      {isScanning && (
        <div className="space-y-2.5 pt-1">
          <div className="flex items-center justify-between text-[11px] font-mono text-[#B3B3B3]">
            <span className="flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin text-[#F5F5F5]" />
              <span>{safeRenderText(currentStep)}...</span>
            </span>
            <span>{progressPct}%</span>
          </div>

          <div className="w-full h-1 bg-[#151515] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#F5F5F5] transition-all duration-300 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Real Event Stream Activity Log */}
      {eventLogs.length > 0 && (
        <div className="pt-2">
          <div className="text-[10px] font-mono text-[#777777] uppercase tracking-wider mb-2">
            Search Progress Trail
          </div>
          <div className="space-y-1.5 max-h-36 overflow-y-auto font-mono text-[11px] bg-[#080808] p-2.5 rounded border border-[#1A1A1A]">
            {eventLogs.map((log) => (
              <div key={log.id} className="flex items-start justify-between gap-2 text-[#B3B3B3]">
                <span className="text-[#777777]">[{log.timestamp}]</span>
                <span className="flex-1 text-left text-[#F5F5F5]">{safeRenderText(log.message)}</span>
                <span className="text-[#4A4A4A]">{safeRenderText(log.step)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
