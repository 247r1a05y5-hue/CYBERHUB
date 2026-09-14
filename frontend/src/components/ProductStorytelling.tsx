import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  AlertCircle, 
  Cpu, 
  FileSearch, 
  Activity, 
  Search, 
  ShieldCheck,
  CheckCircle2,
  Terminal,
  Clock,
  ArrowRight
} from "lucide-react";

export const ProductStorytelling: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(0);

  const steps = [
    {
      id: "problem",
      number: "01",
      title: "Problem Detection",
      badge: "INGESTION EVENT",
      subtitle: "Unprocessed security signal detected at ingress",
      description:
        "High-volume raw telemetry streams into the ingress layer. Payloads and metadata are safely staged into org-isolated queues with zero data loss.",
      uiSnippet: (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
            <span className="flex items-center gap-1.5 text-amber-400">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>UNVALIDATED PAYLOAD INGESTED</span>
            </span>
            <span className="text-[10px] text-slate-500">ID: EVT-90412</span>
          </div>
          <div className="bg-[#0b0f19] p-3 rounded border border-[#1e293b] text-slate-300 space-y-1">
            <div className="text-slate-500">// Raw Ingestion Header</div>
            <div>POST /api/v1/auth/token-exchange</div>
            <div className="text-slate-400">Host: gateway.internal.prod</div>
            <div className="text-amber-400">X-Forwarded-Client: 198.51.100.44</div>
            <div className="text-slate-400">Payload Size: 4,120 bytes [BASE64]</div>
          </div>
        </div>
      ),
    },
    {
      id: "analysis",
      number: "02",
      title: "Deep Analysis",
      badge: "MULTI-ENGINE",
      subtitle: "Concurrent execution across analyzers and static rules",
      description:
        "Parallel analyzers inspect payloads, run heuristic inferences, and apply declarative YAML security rules with sub-25ms latency.",
      uiSnippet: (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
            <span className="flex items-center gap-1.5 text-blue-400">
              <Cpu className="w-3.5 h-3.5" />
              <span>CONCURRENT ANALYZER EXECUTION</span>
            </span>
            <span className="text-[10px] text-emerald-400">3/3 COMPLETED</span>
          </div>
          <div className="space-y-2">
            <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1e293b] flex justify-between items-center">
              <div>
                <div className="text-slate-200 font-semibold">ModelRunner: HeuristicV2</div>
                <div className="text-[11px] text-slate-400">Entropy Score: 7.92 (Threshold: 6.5)</div>
              </div>
              <span className="text-red-400 text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/10 border border-red-500/20">FLAGGED</span>
            </div>
            <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1e293b] flex justify-between items-center">
              <div>
                <div className="text-slate-200 font-semibold">RuleEngine: YAML Signatures</div>
                <div className="text-[11px] text-slate-400">Matched rule: SEC-R-0841 (Token Mismatch)</div>
              </div>
              <span className="text-orange-400 text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-500/10 border border-orange-500/20">MATCH</span>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "evidence",
      number: "03",
      title: "Evidence Extraction",
      badge: "FORENSIC CHAIN",
      subtitle: "Artifact hashing and cryptographic proof collection",
      description:
        "Key forensic indicators, headers, cryptographic hashes, and stack snapshots are extracted and sealed for chain-of-custody compliance.",
      uiSnippet: (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
            <span className="flex items-center gap-1.5 text-blue-400">
              <FileSearch className="w-3.5 h-3.5" />
              <span>FORENSIC EVIDENCE VAULT</span>
            </span>
            <span className="text-[10px] text-slate-400">SHA-256 SEALED</span>
          </div>
          <div className="bg-[#0b0f19] p-3 rounded border border-[#1e293b] space-y-2">
            <div className="text-slate-300 flex justify-between text-[11px]">
              <span className="text-slate-400">Evidence SHA:</span>
              <span className="text-blue-400 font-bold">e3b0c44298fc1c149afbf4...</span>
            </div>
            <div className="text-slate-300 flex justify-between text-[11px]">
              <span className="text-slate-400">Associated IOCs:</span>
              <span className="text-slate-200">1 IP, 2 Domain Names, 1 Header</span>
            </div>
            <div className="text-slate-400 text-[10px] pt-1 border-t border-[#1e293b]">
              Encrypted at rest: AES-256-GCM | Tenant Isolation: Strict
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "risk",
      number: "04",
      title: "Risk Calculation",
      badge: "EXPLAINABLE 0-100",
      subtitle: "Deterministic weighted risk formula",
      description:
        "Every signal is weighted according to tenant configuration, producing an explainable 0–100 score and clear severity tiering.",
      uiSnippet: (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
            <span className="flex items-center gap-1.5 text-orange-400">
              <Activity className="w-3.5 h-3.5" />
              <span>AGGREGATED RISK CALCULATION</span>
            </span>
            <span className="text-white font-bold text-sm tabular-nums">SCORE: 84</span>
          </div>
          <div className="bg-[#0b0f19] p-3 rounded border border-[#1e293b] space-y-2">
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-400">Severity Tier:</span>
              <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/30 font-bold">CRITICAL SEVERITY</span>
            </div>
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-400">Confidence Interval:</span>
              <span className="text-slate-200 tabular-nums">98.2% (+/- 0.6%)</span>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "investigation",
      number: "05",
      title: "SOC Investigation",
      badge: "WORKSPACE VIEW",
      subtitle: "Unified analyst panel for timeline and telemetry",
      description:
        "Analysts inspect the complete chronological audit trail, correlated indicators, and recommended mitigation actions on a single pane.",
      uiSnippet: (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
            <span className="flex items-center gap-1.5 text-blue-400">
              <Search className="w-3.5 h-3.5" />
              <span>ACTIVE INCIDENT WORKSPACE</span>
            </span>
            <span className="text-[10px] text-slate-400">INC-2026-0819</span>
          </div>
          <div className="bg-[#0b0f19] p-3 rounded border border-[#1e293b] space-y-1.5 text-[11px]">
            <div className="text-slate-300 font-semibold">Incident: Unauthorized Ingress Token Anomaly</div>
            <div className="text-slate-400">Assigned: Lead SecOps Engineer (Tier 3)</div>
            <div className="text-slate-400">Correlated Findings: 4 signals across 2 microservices</div>
          </div>
        </div>
      ),
    },
    {
      id: "response",
      number: "06",
      title: "Response & Audit",
      badge: "LIFECYCLE FSM",
      subtitle: "Stateful containment with signed audit records",
      description:
        "Execute mitigation workflows, isolate compromised entities, and commit immutable audit entries to guarantee post-incident compliance.",
      uiSnippet: (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-[#1e293b]">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>CONTAINMENT PLAYBOOK EXECUTED</span>
            </span>
            <span className="text-[10px] text-emerald-400">STATUS: ISOLATED</span>
          </div>
          <div className="bg-[#0b0f19] p-3 rounded border border-[#1e293b] space-y-1.5 text-[11px]">
            <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>IP 198.51.100.44 blocked at perimeter firewall</span>
            </div>
            <div className="text-slate-400">Audit Record: #AUD-88219 signed and committed</div>
          </div>
        </div>
      ),
    },
  ];

  return (
    <section className="py-20 bg-[#0a0e17] border-t border-[#1e293b] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="max-w-3xl mb-12">
          <div className="text-xs font-mono uppercase tracking-wider text-blue-400 font-semibold mb-2">
            END-TO-END WORKFLOW
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-4">
            How security signals become decisions.
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            Follow the continuous pipeline flow from raw telemetry ingestion to
            explainable mitigation and audited response.
          </p>
        </div>

        {/* Interactive Step Selector and Preview Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Step Navigation (6 columns) */}
          <div className="lg:col-span-5 space-y-2">
            {steps.map((step, idx) => {
              const isActive = activeStep === idx;
              return (
                <button
                  key={step.id}
                  onClick={() => setActiveStep(idx)}
                  className={`w-full text-left p-3.5 rounded-lg border transition-all duration-150 flex items-start space-x-3.5 ${
                    isActive
                      ? "bg-[#0f172a] border-blue-500/50 shadow-sm"
                      : "bg-[#090d16] border-[#1e293b]/80 hover:border-[#334155] text-slate-400"
                  }`}
                >
                  <span
                    className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                      isActive
                        ? "bg-blue-600 text-white"
                        : "bg-[#1e293b] text-slate-400"
                    }`}
                  >
                    {step.number}
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-sm font-semibold truncate ${
                          isActive ? "text-white" : "text-slate-300"
                        }`}
                      >
                        {step.title}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {step.badge}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                      {step.subtitle}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right Product UI Snippet (7 columns) */}
          <div className="lg:col-span-7">
            <div className="rounded-xl bg-[#0f172a] border border-[#1e293b] p-6 shadow-xl">
              <AnimatePresence mode="wait">
                <motion.div
                  key={steps[activeStep].id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  className="space-y-5"
                >
                  <div>
                    <div className="flex items-center space-x-2 text-xs font-mono text-blue-400 mb-1">
                      <span>STEP {steps[activeStep].number} OF 06</span>
                      <span>—</span>
                      <span>{steps[activeStep].badge}</span>
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">
                      {steps[activeStep].title}
                    </h3>
                    <p className="text-sm text-slate-300 leading-relaxed">
                      {steps[activeStep].description}
                    </p>
                  </div>

                  {/* UI Snippet Box */}
                  <div className="pt-2">{steps[activeStep].uiSnippet}</div>

                  <div className="pt-3 border-t border-[#1e293b] flex items-center justify-between text-xs text-slate-400 font-mono">
                    <span className="flex items-center gap-1 text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      PIPELINE STAGE ACTIVE
                    </span>
                    <button
                      onClick={() =>
                        setActiveStep((prev) => (prev + 1) % steps.length)
                      }
                      className="text-blue-400 hover:text-blue-300 flex items-center gap-1 font-sans font-medium"
                    >
                      <span>Next Stage</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
