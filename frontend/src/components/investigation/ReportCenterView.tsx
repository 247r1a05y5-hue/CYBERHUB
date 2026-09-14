import React, { useState, useEffect } from "react";
import {
  FileText,
  Download,
  CheckCircle2,
  FileCode,
  FileSpreadsheet,
  FileCheck,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  Lock,
  Layers,
} from "lucide-react";
import { api, getApiUrl } from "../../services/api";

interface ReportItem {
  id: string;
  title: string;
  format: string;
  status: string;
  sha256_hash: string;
  content_hash: string | null;
  created_at: string | null;
  summary: Record<string, any>;
}

interface ReportCenterViewProps {
  caseId: string;
  caseNumber: string;
}

export const ReportCenterView: React.FC<ReportCenterViewProps> = ({ caseId, caseNumber }) => {
  const [selectedFormat, setSelectedFormat] = useState<"PDF" | "JSON" | "CSV" | "TEXT">("PDF");
  const [includeAuditTrail, setIncludeAuditTrail] = useState(true);
  const [reportTitle, setReportTitle] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [reportsList, setReportsList] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/investigations/${caseId}/reports`);
      if (res.data && res.data.reports) {
        setReportsList(res.data.reports);
      }
    } catch (err) {
      console.error("Failed to fetch reports:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchReports();
    }
  }, [caseId]);

  const generateReport = async () => {
    setIsGenerating(true);
    try {
      const res = await api.post(
        `/investigations/${caseId}/report`,
        {
          format: selectedFormat,
          title: reportTitle || undefined,
          include_audit_trail: includeAuditTrail,
        },
        { responseType: "blob" }
      );

      // Create browser download
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      const ext = selectedFormat.toLowerCase();
      link.href = url;
      link.download = `report_${caseNumber}_${Date.now()}.${ext === "text" ? "txt" : ext}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      await fetchReports();
    } catch (err) {
      console.error("Failed to generate report:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadReport = (report: ReportItem) => {
    window.open(getApiUrl(`/api/v1/investigations/${caseId}/reports/${report.id}/download`), "_blank");
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold text-[var(--text-primary)]">Report Generation & Export Center</h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Produce reproducible, tamper-evident forensic dossiers with cryptographic SHA-256 content verification.
          </p>
        </div>

        <button
          onClick={fetchReports}
          disabled={isLoading}
          className="p-1.5 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--card-bg-hover)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all shrink-0"
          title="Refresh Archive"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Generator Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Configuration Form (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-5 space-y-4">
            <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
              Export Configuration
            </h3>

            {/* Format Selection Cards */}
            <div className="grid grid-cols-2 gap-2">
              <div
                onClick={() => setSelectedFormat("PDF")}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedFormat === "PDF"
                    ? "border-cyan-500/50 bg-cyan-500/10"
                    : "border-[var(--border)] bg-[var(--bg-secondary)] hover:border-[var(--border-strong)]"
                }`}
              >
                <FileCheck className="w-4 h-4 text-cyan-400 mb-1" />
                <span className="text-xs font-bold text-[var(--text-primary)] block">Formal PDF</span>
                <span className="text-[10px] text-[var(--text-tertiary)]">Executive Dossier</span>
              </div>

              <div
                onClick={() => setSelectedFormat("JSON")}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedFormat === "JSON"
                    ? "border-blue-500/50 bg-blue-500/10"
                    : "border-[var(--border)] bg-[var(--bg-secondary)] hover:border-[var(--border-strong)]"
                }`}
              >
                <FileCode className="w-4 h-4 text-blue-400 mb-1" />
                <span className="text-xs font-bold text-[var(--text-primary)] block">Audit JSON</span>
                <span className="text-[10px] text-[var(--text-tertiary)]">Machine-Readable</span>
              </div>

              <div
                onClick={() => setSelectedFormat("CSV")}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedFormat === "CSV"
                    ? "border-emerald-500/50 bg-emerald-500/10"
                    : "border-[var(--border)] bg-[var(--bg-secondary)] hover:border-[var(--border-strong)]"
                }`}
              >
                <FileSpreadsheet className="w-4 h-4 text-emerald-400 mb-1" />
                <span className="text-xs font-bold text-[var(--text-primary)] block">Tabular CSV</span>
                <span className="text-[10px] text-[var(--text-tertiary)]">Findings Export</span>
              </div>

              <div
                onClick={() => setSelectedFormat("TEXT")}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedFormat === "TEXT"
                    ? "border-purple-500/50 bg-purple-500/10"
                    : "border-[var(--border)] bg-[var(--bg-secondary)] hover:border-[var(--border-strong)]"
                }`}
              >
                <FileText className="w-4 h-4 text-purple-400 mb-1" />
                <span className="text-xs font-bold text-[var(--text-primary)] block">Plain Text</span>
                <span className="text-[10px] text-[var(--text-tertiary)]">Terminal Summary</span>
              </div>
            </div>

            {/* Optional Title Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Dossier Custom Title</label>
              <input
                type="text"
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                placeholder={`Forensic Exposure Dossier (${selectedFormat})`}
                className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--text-primary)]"
              />
            </div>

            {/* Checkbox Options */}
            <div className="pt-2 border-t border-[var(--border)]">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeAuditTrail}
                  onChange={(e) => setIncludeAuditTrail(e.target.checked)}
                  className="rounded border-[var(--border)] text-cyan-500 focus:ring-0"
                />
                <span className="text-xs text-[var(--text-primary)]">
                  Include Complete Immutable Audit Trail
                </span>
              </label>
            </div>

            {/* Generate Action Button */}
            <button
              onClick={generateReport}
              disabled={isGenerating}
              className="w-full py-2.5 px-4 rounded-lg bg-[var(--text-primary)] text-[var(--bg)] hover:opacity-90 text-xs font-semibold transition-all flex items-center justify-center gap-2"
            >
              <Download className={`w-4 h-4 ${isGenerating ? "animate-bounce" : ""}`} />
              {isGenerating ? "Generating Forensic Dossier..." : `Export ${selectedFormat} Report`}
            </button>
          </div>
        </div>

        {/* Right: Generated Reports Archive (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Report Archive & Content Signatures ({reportsList.length} generated)
          </h3>

          {reportsList.length === 0 ? (
            <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-8 text-center">
              <FileText className="w-8 h-8 text-[var(--text-tertiary)] mx-auto mb-2" />
              <p className="text-xs text-[var(--text-secondary)]">
                No reports generated yet. Choose a format and export your first forensic dossier.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {reportsList.map((rep) => (
                <div
                  key={rep.id}
                  className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--border-strong)] transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-cyan-400">
                        {rep.format}
                      </span>
                      <h4 className="text-xs font-bold text-[var(--text-primary)]">{rep.title}</h4>
                    </div>
                    <p className="text-[10px] font-mono text-[var(--text-tertiary)] truncate max-w-sm">
                      CONTENT-SHA256: {rep.content_hash || rep.sha256_hash}
                    </p>
                    <p className="text-[10px] text-[var(--text-tertiary)]">
                      {rep.created_at ? new Date(rep.created_at).toLocaleString() : "Recently generated"}
                    </p>
                  </div>

                  <button
                    onClick={() => downloadReport(rep)}
                    className="px-3 py-1.5 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--card-bg-hover)] border border-[var(--border)] text-xs font-medium text-[var(--text-primary)] transition-all flex items-center gap-1.5 shrink-0 self-start sm:self-center"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
