import React, { useState, useEffect } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Eye,
  EyeOff,
  Globe,
  Loader2,
  Play,
  Pause,
  RefreshCw,
  Shield,
  ShieldAlert,
  Sparkles,
  Zap,
} from "lucide-react";
import { api } from "../../services/api";
import { formatErrorMessage, safeRenderText } from "../../utils/errorUtils";

interface MonitoringRunItem {
  id: string;
  started_at: string;
  completed_at?: string;
  status: string;
  provider_status: string;
  new_count: number;
  unchanged_count: number;
  not_observed_count: number;
  reappeared_count: number;
  candidate_count: number;
}

interface MonitoringData {
  investigation_id: string;
  case_number: string;
  is_configured: boolean;
  enabled: boolean;
  frequency: "DAILY" | "WEEKLY";
  last_status: string;
  last_run_at?: string;
  next_run_at?: string;
  new_delta_count: number;
  current_count: number;
  recent_runs: MonitoringRunItem[];
}

interface MonitoringViewProps {
  caseId: string;
  caseNumber: string;
  onNavigateToDiscovery?: () => void;
}

export const MonitoringView: React.FC<MonitoringViewProps> = ({
  caseId,
  caseNumber,
  onNavigateToDiscovery,
}) => {
  const [data, setData] = useState<MonitoringData | null>(null);
  const [frequency, setFrequency] = useState<"DAILY" | "WEEKLY">("DAILY");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchMonitoringStatus = async () => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const res = await api.get(`/investigations/${caseId}/monitoring`);
      setData(res.data);
      if (res.data.frequency) {
        setFrequency(res.data.frequency);
      }
    } catch (err: any) {
      console.error("Failed to load monitoring status:", err);
      setErrorMessage(
        formatErrorMessage(err, "Failed to load continuous monitoring configuration.")
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchMonitoringStatus();
    }
  }, [caseId]);

  const handleToggleMonitoring = async (enable: boolean) => {
    try {
      setIsActionLoading(true);
      setErrorMessage(null);
      setSuccessMessage(null);
      await api.post(`/investigations/${caseId}/monitoring`, {
        frequency,
        enabled: enable,
      });
      setSuccessMessage(
        enable
          ? `Continuous exposure monitoring activated (${frequency}).`
          : "Monitoring paused."
      );
      await fetchMonitoringStatus();
    } catch (err: any) {
      console.error("Failed to update monitoring:", err);
      setErrorMessage(formatErrorMessage(err, "Failed to update monitoring state."));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleTriggerScanNow = async () => {
    try {
      setIsScanning(true);
      setErrorMessage(null);
      setSuccessMessage(null);
      const res = await api.post(`/investigations/${caseId}/monitoring/scan-now`);
      setSuccessMessage(
        res.data?.message || "Continuous exposure discovery scan dispatched successfully."
      );
      await fetchMonitoringStatus();
    } catch (err: any) {
      console.error("Manual monitoring scan failed:", err);
      setErrorMessage(formatErrorMessage(err, "Manual monitoring re-scan failed."));
    } finally {
      setIsScanning(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-12 text-center text-xs text-[var(--text-secondary)] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        <span>Loading continuous monitoring telemetry...</span>
      </div>
    );
  }

  const isEnabled = data?.enabled || false;
  const recentRuns = data?.recent_runs || [];

  return (
    <div className="space-y-6 max-w-5xl mx-auto text-left">
      {/* Messages */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-600 dark:text-red-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{safeRenderText(errorMessage)}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="font-semibold underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-700 dark:text-emerald-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="font-semibold underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Monitoring Header Card */}
      <div
        className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 sm:p-8 transition-all"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
          <div className="flex items-start gap-3.5">
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center ${
                isEnabled
                  ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-500"
                  : "bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-tertiary)]"
              }`}
            >
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5 mb-1">
                <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)]">
                  Automated Exposure Monitoring
                </h2>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    isEnabled
                      ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                      : "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                  }`}
                >
                  {isEnabled ? "ACTIVE" : "PAUSED"}
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Periodic re-scan engine monitoring registered search adapters for newly surfaced candidate appearances.
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5 shrink-0">
            {isEnabled ? (
              <button
                type="button"
                onClick={() => handleToggleMonitoring(false)}
                disabled={isActionLoading || isScanning}
                className="h-9 px-3.5 bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-primary)] text-xs font-semibold rounded-lg hover:bg-[var(--surface-hover)] transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                <Pause className="w-3.5 h-3.5 text-amber-500" />
                <span>Pause</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleToggleMonitoring(true)}
                disabled={isActionLoading || isScanning}
                className="h-9 px-4 bg-emerald-600 text-white text-xs font-semibold rounded-lg hover:bg-emerald-700 transition-all flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Activate Monitoring</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleTriggerScanNow}
              disabled={isScanning || isActionLoading}
              className="h-9 px-4 bg-[var(--text-primary)] text-[var(--bg)] text-xs font-semibold rounded-lg hover:opacity-90 active:scale-95 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              {isScanning ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Run Re-Scan Now</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Cadence & Telemetry Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-6">
          <div className="p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] flex items-center gap-1 mb-1 font-medium">
              <Clock className="w-3.5 h-3.5 text-blue-500" />
              Scan Frequency
            </span>
            <div className="flex items-center gap-2 mt-1">
              <select
                value={frequency}
                onChange={(e) => {
                  const val = e.target.value as "DAILY" | "WEEKLY";
                  setFrequency(val);
                }}
                className="h-8 px-2 text-xs bg-[var(--search-bg)] border border-[var(--search-border)] rounded-md text-[var(--text-primary)] font-semibold focus:outline-none"
              >
                <option value="DAILY">Daily (24h)</option>
                <option value="WEEKLY">Weekly (168h)</option>
              </select>
              {frequency !== data?.frequency && (
                <button
                  type="button"
                  onClick={() => handleToggleMonitoring(isEnabled)}
                  className="px-2 py-1 bg-blue-600 text-white text-[10px] font-bold rounded"
                >
                  Save
                </button>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] flex items-center gap-1 mb-1 font-medium">
              <RefreshCw className="w-3.5 h-3.5 text-emerald-500" />
              Last Scan
            </span>
            <p className="text-xs font-semibold text-[var(--text-primary)] mt-1">
              {data?.last_run_at ? new Date(data.last_run_at).toLocaleString() : "Never"}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] flex items-center gap-1 mb-1 font-medium">
              <Zap className="w-3.5 h-3.5 text-purple-500" />
              Next Scheduled Scan
            </span>
            <p className="text-xs font-semibold text-[var(--text-primary)] mt-1">
              {isEnabled && data?.next_run_at
                ? new Date(data.next_run_at).toLocaleString()
                : "Paused / Inactive"}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
            <span className="text-[11px] text-[var(--text-tertiary)] flex items-center gap-1 mb-1 font-medium">
              <Globe className="w-3.5 h-3.5 text-amber-500" />
              Historical Discoveries
            </span>
            <p className="text-xs font-semibold text-[var(--text-primary)] mt-1">
              {data?.current_count || 0} total findings
            </p>
          </div>
        </div>
      </div>

      {/* Semantic Delta Classification Guide */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3.5 rounded-xl bg-blue-500/5 border border-blue-500/20">
          <span className="font-bold text-blue-600 dark:text-blue-400 block mb-0.5 flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            NEW (Candidate)
          </span>
          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
            Newly discovered source appearance. Requires human verification before confirmed exposure status.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
          <span className="font-bold text-[var(--text-primary)] block mb-0.5">UNCHANGED</span>
          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
            Persistent exposure endpoint confirmed in both historical and current discovery sweeps.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20">
          <span className="font-bold text-amber-600 dark:text-amber-400 block mb-0.5 flex items-center gap-1">
            <EyeOff className="w-3 h-3" />
            NOT OBSERVED
          </span>
          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
            Source absent in latest scan. Historical verified exposure record is preserved and not deleted.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-purple-500/5 border border-purple-500/20">
          <span className="font-bold text-purple-600 dark:text-purple-400 block mb-0.5 flex items-center gap-1">
            <Eye className="w-3 h-3" />
            REAPPEARED
          </span>
          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
            Previously unobserved source re-detected in current provider discovery sweep.
          </p>
        </div>
      </div>

      {/* Historical Monitoring Runs Table */}
      <div
        className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 transition-all"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-500" />
              <span>Monitoring Execution History</span>
            </h3>
            <p className="text-[11px] text-[var(--text-secondary)]">
              Chronological ledger of scheduled and on-demand discovery sweeps.
            </p>
          </div>
          {onNavigateToDiscovery && (
            <button
              type="button"
              onClick={onNavigateToDiscovery}
              className="text-xs font-semibold text-blue-500 hover:underline flex items-center gap-1"
            >
              <span>View Discovery Triage</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>

        {recentRuns.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--text-tertiary)] font-medium">
                  <th className="py-2.5 px-3">Execution Time</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Provider</th>
                  <th className="py-2.5 px-3 text-center">New</th>
                  <th className="py-2.5 px-3 text-center">Unchanged</th>
                  <th className="py-2.5 px-3 text-center">Not Observed</th>
                  <th className="py-2.5 px-3 text-center">Reappeared</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)] text-[var(--text-primary)]">
                {recentRuns.map((r) => (
                  <tr key={r.id} className="hover:bg-[var(--surface-hover)] transition-colors">
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {new Date(r.started_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        {r.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-[var(--text-secondary)] font-mono">
                      {r.provider_status}
                    </td>
                    <td className="py-2.5 px-3 text-center font-bold text-blue-500">
                      +{r.new_count}
                    </td>
                    <td className="py-2.5 px-3 text-center text-[var(--text-secondary)]">
                      {r.unchanged_count}
                    </td>
                    <td className="py-2.5 px-3 text-center text-amber-500">
                      {r.not_observed_count}
                    </td>
                    <td className="py-2.5 px-3 text-center text-purple-500">
                      {r.reappeared_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-[var(--text-secondary)] border border-dashed border-[var(--border)] rounded-xl">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-30 text-blue-500" />
            <p className="font-semibold text-[var(--text-primary)]">No monitoring scans executed yet.</p>
            <p className="text-[11px] text-[var(--text-tertiary)] mt-1">
              Click &ldquo;Run Re-Scan Now&rdquo; above to execute an immediate delta scan.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
