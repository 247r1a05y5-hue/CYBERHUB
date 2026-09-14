import React, { useState } from "react";
import { Shield, Lock, FileCheck, AlertCircle, ArrowLeft, ArrowRight, Loader2 } from "lucide-react";

interface AttestationStepProps {
  investigationTitle: string;
  onConfirm: () => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const AttestationStep: React.FC<AttestationStepProps> = ({
  investigationTitle,
  onConfirm,
  onBack,
  isLoading,
}) => {
  const [hasAgreed, setHasAgreed] = useState(false);

  const policyClauses = [
    {
      title: "1. AUTHORIZED USER",
      description: "You confirm you are the verified subject, asset owner, or an authorized representative acting under lawful authorization.",
    },
    {
      title: "2. NON-PERSONAL IDENTIFICATION",
      description: "This inquiry is restricted solely to authorized digital exposure discovery and reverse asset identification.",
    },
    {
      title: "3. LEGITIMATE USE",
      description: "Inquiry is initiated strictly for copyright enforcement, privacy leakage mitigation, or authorized security auditing.",
    },
    {
      title: "4. PRIVACY-COMPLIANT",
      description: "Operates in compliance with GDPR Art. 9, CCPA, and SOC-2 privacy preservation governance boundaries.",
    },
    {
      title: "5. NO UNRESTRICTED SURVEILLANCE",
      description: "System strictly prohibits mass biometric scraping, stranger stalking, or arbitrary public surveillance.",
    },
    {
      title: "6. AUDIT LOGGED",
      description: "This authorization is cryptographically referenced by image SHA-256 and committed to an immutable append-only audit trail.",
    },
  ];

  return (
    <div
      className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 sm:p-8 max-w-2xl mx-auto transition-all"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      {/* Title & Badge */}
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-lg bg-[var(--icon-box-bg)] border border-[var(--icon-box-border)] flex items-center justify-center">
          <Shield className="w-4 h-4 text-[var(--icon-color)]" />
        </div>
        <div>
          <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] tracking-tight">
            Authorization Attestation
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">
            Investigation: <span className="font-semibold text-[var(--text-primary)]">{investigationTitle}</span>
          </p>
        </div>
      </div>

      {/* Main Attestation Heading Box */}
      <div className="mt-4 p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)]">
        <h3 className="text-xs sm:text-sm font-semibold text-[var(--text-primary)] mb-1">
          I attest I have full legal authorization to investigate this image.
        </h3>
        <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
          Please review the binding enterprise compliance guidelines prior to initiating image processing:
        </p>
      </div>

      {/* Policy Clauses List */}
      <div className="mt-4 space-y-3 max-h-60 overflow-y-auto pr-1">
        {policyClauses.map((clause, idx) => (
          <div
            key={idx}
            className="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-xs"
          >
            <p className="font-bold text-[var(--text-primary)] text-[11px] uppercase tracking-wider mb-0.5">
              {clause.title}
            </p>
            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
              {clause.description}
            </p>
          </div>
        ))}
      </div>

      {/* Compliance Framing Disclaimer (§14, §24) */}
      <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-800 dark:text-amber-300 flex items-start gap-2">
        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
        <p>
          <span className="font-semibold">Policy Notice:</span> Attestation is recorded as an organizational policy and audit control — not proof of ownership, legal advice, or a cryptographic identity signature.
        </p>
      </div>

      {/* Consent Checkbox */}
      <div className="mt-5 pt-4 border-t border-[var(--border)]">
        <label className="flex items-start gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={hasAgreed}
            onChange={(e) => setHasAgreed(e.target.checked)}
            className="mt-0.5 w-4 h-4 rounded border-[var(--border-strong)] text-[var(--text-primary)] focus:ring-[var(--text-primary)] cursor-pointer"
          />
          <span className="text-xs font-medium text-[var(--text-primary)] leading-tight">
            I attest and confirm I have legal authorization to investigate this image under enterprise security policy.
          </span>
        </label>
      </div>

      {/* Navigation Actions */}
      <div className="mt-6 flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={onBack}
          disabled={isLoading}
          className="px-4 py-2 text-xs font-medium border border-[var(--border-strong)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-lg hover:bg-[var(--surface-hover)] transition-colors flex items-center gap-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Image</span>
        </button>

        <button
          type="button"
          onClick={onConfirm}
          disabled={!hasAgreed || isLoading}
          className="h-9 px-5 bg-[var(--text-primary)] text-[var(--bg)] text-xs font-semibold rounded-lg flex items-center gap-2 hover:opacity-90 active:scale-95 transition-all disabled:opacity-40 disabled:pointer-events-none"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Creating & Indexing...</span>
            </>
          ) : (
            <>
              <span>Confirm & Create Investigation</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
