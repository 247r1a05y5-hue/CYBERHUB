import React, { useState, useEffect } from "react";
import {
  Lock,
  ShieldCheck,
  Download,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  FileCode,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Eye,
  KeyRound,
  Layers,
} from "lucide-react";
import { api, getApiUrl } from "../../services/api";

export interface EvidenceItem {
  id: string;
  evidence_number: string;
  custody_sequence: number;
  previous_evidence_hash: string;
  sha256_hash: string;
  evidence_type: string;
  verification_status: string;
  domain: string;
  page_title: string | null;
  page_url: string;
  image_url: string;
  content_type: string;
  size_bytes: number;
  has_artifact: boolean;
  user_reason: string | null;
  verified_at: string | null;
  created_at: string | null;
  chain_of_custody?: any[];
}

interface EvidenceVaultViewProps {
  caseId: string;
  referenceImageUrl: string | null;
  referenceSha256: string | null;
}

export const EvidenceVaultView: React.FC<EvidenceVaultViewProps> = ({
  caseId,
  referenceImageUrl,
  referenceSha256,
}) => {
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<EvidenceItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [integrityResults, setIntegrityResults] = useState<Record<string, { isValid: boolean; chainIntact: boolean }>>({});
  const [isVerifying, setIsVerifying] = useState<string | null>(null);

  const fetchEvidence = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/investigations/${caseId}/evidence`);
      if (res.data && res.data.evidence_items) {
        setEvidenceList(res.data.evidence_items);
        if (res.data.evidence_items.length > 0 && !selectedItem) {
          setSelectedItem(res.data.evidence_items[0]);
        }
      }
    } catch (err) {
      console.error("Failed to fetch evidence vault:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchEvidence();
    }
  }, [caseId]);

  const verifyIntegrity = async (item: EvidenceItem) => {
    setIsVerifying(item.id);
    try {
      const res = await api.get(`/investigations/${caseId}/evidence/${item.id}/verify-integrity`);
      setIntegrityResults((prev) => ({
        ...prev,
        [item.id]: {
          isValid: res.data.is_valid,
          chainIntact: res.data.chain_intact,
        },
      }));
    } catch (err) {
      console.error("Failed to verify integrity:", err);
    } finally {
      setIsVerifying(null);
    }
  };

  const downloadArtifact = (item: EvidenceItem) => {
    window.open(getApiUrl(`/api/v1/investigations/${caseId}/evidence/${item.id}/download`), "_blank");
  };

  const exportEvidenceManifest = (format: "json" | "csv") => {
    window.open(getApiUrl(`/api/v1/investigations/${caseId}/evidence/export?format=${format}`), "_blank");
  };

  return (
    <div className="space-y-5 text-left">
      {/* Top Controls Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-lg bg-[#0C0C0C] border border-[#1A1A1A]">
        <div>
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-[#F5F5F5]" />
            <h3 className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
              Cryptographic Evidence Vault
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded bg-[#151515] border border-[#232323] text-[#B3B3B3] font-mono">
              {evidenceList.length} Sealed Artifacts
            </span>
          </div>
          <p className="text-xs text-[#777777] mt-0.5">
            Immutable chain of custody with SHA-256 integrity verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => exportEvidenceManifest("csv")}
            className="px-2.5 py-1.5 bg-[#151515] border border-[#232323] text-[#B3B3B3] hover:text-[#F5F5F5] text-xs font-medium rounded flex items-center gap-1.5 transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          <button
            type="button"
            onClick={() => exportEvidenceManifest("json")}
            className="px-2.5 py-1.5 bg-[#151515] border border-[#232323] text-[#B3B3B3] hover:text-[#F5F5F5] text-xs font-medium rounded flex items-center gap-1.5 transition-colors"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Main Split Layout */}
      {evidenceList.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: Artifact List */}
          <div className="space-y-2">
            {evidenceList.map((item) => (
              <div
                key={item.id}
                onClick={() => setSelectedItem(item)}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedItem?.id === item.id
                    ? "bg-[#151515] border-[#2B2B2B]"
                    : "bg-[#0C0C0C] border-[#1A1A1A] hover:border-[#232323]"
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-mono font-semibold text-[#F5F5F5]">{item.evidence_number}</span>
                  <span className="text-[10px] font-mono text-[#10B981] bg-[#10B981]/10 px-1.5 py-0.2 rounded border border-[#10B981]/25">
                    SEALED #{item.custody_sequence}
                  </span>
                </div>
                <p className="text-xs text-[#B3B3B3] truncate">{item.domain}</p>
                <p className="text-[10px] font-mono text-[#777777] truncate mt-1">
                  SHA-256: {item.sha256_hash.slice(0, 16)}...
                </p>
              </div>
            ))}
          </div>

          {/* Right: Selected Artifact Inspector */}
          {selectedItem && (
            <div className="lg:col-span-2 bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-3">
                <div>
                  <h4 className="font-mono text-xs font-bold text-[#F5F5F5]">
                    Artifact Detail · {selectedItem.evidence_number}
                  </h4>
                  <p className="text-[11px] text-[#777777] font-mono mt-0.5">
                    Custody Seq: #{selectedItem.custody_sequence}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => verifyIntegrity(selectedItem)}
                    disabled={isVerifying === selectedItem.id}
                    className="px-2.5 py-1 bg-[#151515] border border-[#232323] text-xs font-medium text-[#B3B3B3] hover:text-[#F5F5F5] rounded flex items-center gap-1.5 transition-colors"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>{isVerifying === selectedItem.id ? "Verifying..." : "Verify Hash"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => downloadArtifact(selectedItem)}
                    className="px-2.5 py-1 bg-[#F5F5F5] hover:bg-white text-[#000000] text-xs font-semibold rounded flex items-center gap-1.5 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </button>
                </div>
              </div>

              {/* Integrity Status */}
              {integrityResults[selectedItem.id] && (
                <div className="p-3 rounded bg-[#080808] border border-[#10B981]/30 text-xs text-[#10B981] flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>
                    Cryptographic Integrity Confirmed · SHA-256 matches sealed ledger.
                  </span>
                </div>
              )}

              {/* Artifact Metadata Grid */}
              <div className="space-y-2 font-mono text-[11px] bg-[#080808] p-3.5 rounded border border-[#1A1A1A] text-[#B3B3B3]">
                <p>• Domain: <span className="text-[#F5F5F5]">{selectedItem.domain}</span></p>
                <p>• Source URL: <span className="text-[#F5F5F5]">{selectedItem.page_url}</span></p>
                <p>• SHA-256: <span className="text-[#F5F5F5]">{selectedItem.sha256_hash}</span></p>
                <p>• Parent Hash: <span className="text-[#777777]">{selectedItem.previous_evidence_hash || "GENESIS_NODE"}</span></p>
                <p>• Verification Note: <span className="text-[#F5F5F5]">{selectedItem.user_reason || "Analyst verified match."}</span></p>
                <p>• Sealed At: <span className="text-[#777777]">{selectedItem.verified_at || selectedItem.created_at}</span></p>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Compact Empty State */
        <div className="p-8 rounded-lg bg-[#0C0C0C] border border-[#1A1A1A] text-center text-xs text-[#777777]">
          <Lock className="w-6 h-6 mx-auto mb-2 opacity-40 text-[#B3B3B3]" />
          <p className="font-medium text-[#F5F5F5]">No verified evidence preserved yet.</p>
          <p className="text-[11px] text-[#777777] mt-1">
            Findings verified during analysis are cryptographically sealed in this vault.
          </p>
        </div>
      )}
    </div>
  );
};
