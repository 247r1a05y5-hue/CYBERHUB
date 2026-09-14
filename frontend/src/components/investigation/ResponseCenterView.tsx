import React, { useState, useEffect } from "react";
import {
  Mail,
  Copy,
  Check,
  Download,
  AlertCircle,
  ShieldAlert,
  FileCode,
  Globe,
  RefreshCw,
  Lock,
} from "lucide-react";
import { api, getApiUrl } from "../../services/api";

interface ResponsePackageItem {
  id: string;
  package_number: string;
  target_domain: string;
  target_entity: string;
  incident_summary: string;
  sha256_hash: string;
  status: string;
  format: string;
  takedown_letter?: string;
  evidence_manifest?: any[];
  contact_channels?: any;
  created_at: string | null;
  evidence_count?: number;
}

interface ResponseCenterViewProps {
  caseId: string;
  caseNumber: string;
  verifiedDomains: string[];
  onNavigateToMonitoring?: () => void;
}

export const ResponseCenterView: React.FC<ResponseCenterViewProps> = ({
  caseId,
  caseNumber,
  verifiedDomains,
  onNavigateToMonitoring,
}) => {
  const [selectedDomain, setSelectedDomain] = useState(verifiedDomains[0] || "social.example.test");
  const [targetEntity, setTargetEntity] = useState("");
  const [packageFormat, setPackageFormat] = useState<"MARKDOWN" | "JSON">("MARKDOWN");
  const [isGenerating, setIsGenerating] = useState(false);
  const [activePackage, setActivePackage] = useState<ResponsePackageItem | null>(null);
  const [packageArchive, setPackageArchive] = useState<ResponsePackageItem[]>([]);
  const [hasCopied, setHasCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (verifiedDomains.length > 0 && !verifiedDomains.includes(selectedDomain)) {
      setSelectedDomain(verifiedDomains[0]);
    }
  }, [verifiedDomains]);

  const fetchPackages = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/investigations/${caseId}/response-packages`);
      if (res.data && res.data.packages) {
        setPackageArchive(res.data.packages);
        if (res.data.packages.length > 0 && !activePackage) {
          // fetch details of first package
          fetchPackageDetail(res.data.packages[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch response packages:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPackageDetail = async (pkgId: string) => {
    try {
      const res = await api.get(`/investigations/${caseId}/response-packages`);
      const found = res.data.packages?.find((p: any) => p.id === pkgId);
      if (found) {
        setActivePackage(found);
      }
    } catch (err) {
      console.error("Failed to fetch package detail:", err);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchPackages();
    }
  }, [caseId]);

  const generatePackage = async () => {
    setIsGenerating(true);
    try {
      const res = await api.post(`/investigations/${caseId}/response-packages`, {
        target_domain: selectedDomain,
        target_entity: targetEntity || undefined,
        format: packageFormat,
      });

      if (res.data) {
        setActivePackage(res.data);
        await fetchPackages();
      }
    } catch (err) {
      console.error("Failed to generate response package:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  const copyToClipboard = () => {
    if (activePackage?.takedown_letter) {
      navigator.clipboard.writeText(activePackage.takedown_letter);
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), 2000);
    }
  };

  const downloadPackage = (pkg: ResponsePackageItem, format: "MARKDOWN" | "JSON") => {
    window.open(getApiUrl(`/api/v1/investigations/${caseId}/response-packages/${pkg.id}/download?format=${format}`), "_blank");
  };

  return (
    <div className="space-y-6">
      {/* Zero-Outbound Warning Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-[var(--text-secondary)]">
          <span className="font-semibold text-amber-400 block mb-0.5">Strict Air-Gapped Package Builder</span>
          This tool assembles cryptographically verified notice envelopes and evidence manifests for manual export and review.
          <span className="font-semibold text-[var(--text-primary)] ml-1">
            Zero automated communications or emails are transmitted to external hosts.
          </span>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Configuration Form (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                Target & Channel Config
              </h3>
              <button
                onClick={fetchPackages}
                disabled={isLoading}
                className="p-1 rounded bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                title="Refresh"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              </button>
            </div>

            {/* Target Domain Input / Dropdown */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Target Domain</label>
              {verifiedDomains.length > 0 ? (
                <select
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--text-primary)] font-mono"
                >
                  {verifiedDomains.map((dom) => (
                    <option key={dom} value={dom}>
                      {dom}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value)}
                  placeholder="e.g. social.example.test"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--text-primary)] font-mono"
                />
              )}
            </div>

            {/* Target Entity Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Target Entity / Department</label>
              <input
                type="text"
                value={targetEntity}
                onChange={(e) => setTargetEntity(e.target.value)}
                placeholder={`Abuse & Compliance (${selectedDomain})`}
                className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--text-primary)]"
              />
            </div>

            {/* Format Toggle */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Package Format</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPackageFormat("MARKDOWN")}
                  className={`py-2 px-3 rounded-lg border text-xs font-semibold transition-all ${
                    packageFormat === "MARKDOWN"
                      ? "bg-[var(--text-primary)] text-[var(--bg)] border-[var(--text-primary)]"
                      : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border)]"
                  }`}
                >
                  Markdown (.md)
                </button>
                <button
                  type="button"
                  onClick={() => setPackageFormat("JSON")}
                  className={`py-2 px-3 rounded-lg border text-xs font-semibold transition-all ${
                    packageFormat === "JSON"
                      ? "bg-[var(--text-primary)] text-[var(--bg)] border-[var(--text-primary)]"
                      : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border)]"
                  }`}
                >
                  JSON (.json)
                </button>
              </div>
            </div>

            {/* Generate Action Button */}
            <button
              onClick={generatePackage}
              disabled={isGenerating || !selectedDomain}
              className="w-full py-2.5 px-4 rounded-lg bg-[var(--text-primary)] text-[var(--bg)] hover:opacity-90 text-xs font-semibold transition-all flex items-center justify-center gap-2"
            >
              <Mail className={`w-4 h-4 ${isGenerating ? "animate-spin" : ""}`} />
              {isGenerating ? "Generating Response Package..." : "Generate Takedown Package"}
            </button>
          </div>

          {/* Package Archive List */}
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-4 space-y-3">
            <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
              Generated Packages ({packageArchive.length})
            </h4>

            {packageArchive.length === 0 ? (
              <p className="text-xs text-[var(--text-tertiary)] py-2">No packages generated yet.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {packageArchive.map((pkg) => (
                  <div
                    key={pkg.id}
                    onClick={() => setActivePackage(pkg)}
                    className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between text-xs ${
                      activePackage?.id === pkg.id
                        ? "border-[var(--text-primary)] bg-[var(--bg-secondary)]"
                        : "border-[var(--border)] hover:border-[var(--border-strong)]"
                    }`}
                  >
                    <div>
                      <span className="font-mono font-bold text-[var(--text-primary)] block">
                        {pkg.package_number}
                      </span>
                      <span className="text-[10px] text-[var(--text-secondary)]">{pkg.target_domain}</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      READY
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Takedown Letter Live Preview (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                  Takedown Notice Envelope Preview
                </h3>
                {activePackage && (
                  <span className="text-[11px] font-mono text-[var(--text-tertiary)]">
                    Ref: {activePackage.package_number} • SHA-256: {activePackage.sha256_hash.slice(0, 12)}...
                  </span>
                )}
              </div>

              {activePackage && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={copyToClipboard}
                    className="px-3 py-1.5 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--card-bg-hover)] border border-[var(--border)] text-xs font-medium text-[var(--text-primary)] transition-all flex items-center gap-1.5"
                  >
                    {hasCopied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        Copy Notice
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => downloadPackage(activePackage, "MARKDOWN")}
                    className="p-1.5 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--card-bg-hover)] border border-[var(--border)] text-[var(--text-primary)] transition-all"
                    title="Download .md"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>

            {/* Letter Preview Window */}
            <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-4 font-mono text-xs text-[var(--text-secondary)] whitespace-pre-wrap max-h-[500px] overflow-y-auto leading-relaxed">
              {activePackage?.takedown_letter || activePackage?.incident_summary ? (
                activePackage.takedown_letter || activePackage.incident_summary
              ) : (
                <div className="text-center py-12 text-[var(--text-tertiary)]">
                  Configure a target domain and click "Generate Takedown Package" to preview the formal notification envelope.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Navigation */}
      {onNavigateToMonitoring && (
        <div className="flex items-center justify-end pt-4 border-t border-[var(--border)] mt-6">
          <button
            type="button"
            onClick={onNavigateToMonitoring}
            className="px-5 py-2.5 bg-[var(--text-primary)] text-[var(--bg)] text-xs font-semibold rounded-lg flex items-center gap-2 hover:opacity-90 active:scale-95 transition-all shadow-sm"
          >
            <span>Proceed to Continuous Monitoring</span>
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
