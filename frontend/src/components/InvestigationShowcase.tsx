import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Search, 
  Clock, 
  ShieldAlert, 
  FileCode, 
  User, 
  CheckCircle, 
  ExternalLink,
  ChevronRight,
  Database,
  Terminal,
  Activity,
  Layers
} from "lucide-react";

export const InvestigationShowcase: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"summary" | "timeline" | "evidence">("summary");

  const timelineEvents = [
    {
      time: "14:22:04 UTC",
      title: "Ingress Anomaly Triggered",
      desc: "API gateway logged high-entropy token payload from IP 198.51.100.44",
      type: "alert",
    },
    {
      time: "14:22:08 UTC",
      title: "Automated Analyzers Executed",
      desc: "HeuristicV2 and YAML Rule SEC-R-0841 matched payload signatures",
      type: "analyzer",
    },
    {
      time: "14:22:15 UTC",
      title: "Risk Engine Evaluated",
      desc: "Score calculated at 84 (Critical). Incident INC-2026-0819 auto-generated",
      type: "risk",
    },
    {
      time: "14:24:30 UTC",
      title: "Analyst Assigned & Triage Initiated",
      desc: "SOC Tier 3 assigned. Perimeter IP containment rule applied",
      type: "action",
    },
  ];

  const evidenceItems = [
    {
      id: "EVD-01",
      filename: "raw_payload_stream.json",
      type: "Network Ingress Dump",
      hash: "8f4e2b19a0cd...41e8",
      size: "4.2 KB",
    },
    {
      id: "EVD-02",
      filename: "auth_jwt_header.bin",
      type: "Token Artifact",
      hash: "3c91a0ef8811...99aa",
      size: "812 bytes",
    },
    {
      id: "EVD-03",
      filename: "analyzer_execution_trace.log",
      type: "Audit Log Trace",
      hash: "61ab9338fa02...cd72",
      size: "18.4 KB",
    },
  ];

  return (
    <section id="investigation" className="py-20 bg-[#0a0e17] border-t border-[#1e293b] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="max-w-3xl mb-12">
          <div className="text-xs font-mono uppercase tracking-wider text-blue-400 font-semibold mb-2">
            INVESTIGATION SHOWCASE
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-4">
            From alert to understanding.
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            Eliminate alert fatigue with full context: inspect correlated evidence,
            chronological timelines, and actionable mitigation in a single pane.
          </p>
        </div>

        {/* Large Investigation Workspace Panel */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-xl bg-[#0f172a] border border-[#1e293b] shadow-2xl overflow-hidden"
        >
          {/* Panel Top Header Bar */}
          <div className="px-5 py-3.5 bg-[#0b0f19] border-b border-[#1e293b] flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/30 font-semibold">
                INC-2026-0819
              </span>
              <h3 className="text-sm sm:text-base font-bold text-white">
                Anomalous Ingress Token Flow & Signature Mismatch
              </h3>
            </div>

            {/* Tab Navigation */}
            <div className="flex items-center bg-[#080c14] p-1 rounded-lg border border-[#1e293b] text-xs font-medium">
              {(["summary", "timeline", "evidence"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`relative px-3.5 py-1 rounded-md capitalize transition-colors duration-150 ${
                    activeTab === tab
                      ? "text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {activeTab === tab && (
                    <motion.div
                      layoutId="investigationTabIndicator"
                      className="absolute inset-0 bg-[#1e293b] rounded-md shadow-sm"
                      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    />
                  )}
                  <span className="relative z-10">{tab}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Panel Main Body */}
          <div className="p-6">
            <AnimatePresence mode="wait">
              {activeTab === "summary" && (
                <motion.div
                  key="summary"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  className="grid grid-cols-1 lg:grid-cols-3 gap-6"
                >
                  {/* Left 2 Cols: Incident Details & Notes */}
                  <div className="lg:col-span-2 space-y-4">
                    <div className="rounded-lg bg-[#0b0f19] border border-[#1e293b] p-4">
                      <div className="text-xs font-mono text-slate-400 mb-2 font-semibold">
                        INCIDENT SUMMARY & ROOT CAUSE
                      </div>
                      <p className="text-sm text-slate-300 leading-relaxed mb-4">
                        A sequence of token exchange requests was submitted to the ingress
                        gateway originating from an unclassified foreign AS network. Multiple
                        declarative YAML rules triggered due to signature byte anomalies and
                        timestamp skew.
                      </p>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
                        <div className="bg-[#0f172a] p-2.5 rounded border border-[#1e293b]">
                          <div className="text-slate-500 text-[10px]">RISK SCORE</div>
                          <div className="text-red-400 font-bold text-sm mt-0.5 tabular-nums">84 / 100</div>
                        </div>
                        <div className="bg-[#0f172a] p-2.5 rounded border border-[#1e293b]">
                          <div className="text-slate-500 text-[10px]">SEVERITY</div>
                          <div className="text-red-400 font-bold text-sm mt-0.5">CRITICAL</div>
                        </div>
                        <div className="bg-[#0f172a] p-2.5 rounded border border-[#1e293b]">
                          <div className="text-slate-500 text-[10px]">FSM STATE</div>
                          <div className="text-blue-400 font-bold text-sm mt-0.5">TRIAGED</div>
                        </div>
                      </div>
                    </div>

                    {/* Analyst Recommendations */}
                    <div className="rounded-lg bg-[#0b0f19] border border-[#1e293b] p-4">
                      <div className="text-xs font-mono text-slate-400 mb-2 font-semibold">
                        RECOMMENDED CONTAINMENT PLAYBOOK
                      </div>
                      <ul className="space-y-2 text-xs text-slate-300">
                        <li className="flex items-center space-x-2">
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>Revoke active session tokens associated with client IP 198.51.100.44</span>
                        </li>
                        <li className="flex items-center space-x-2">
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>Enforce ephemeral MFA verification challenge on tenant IAM ingress</span>
                        </li>
                        <li className="flex items-center space-x-2">
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>Export forensic evidence bundle to tamper-evident audit repository</span>
                        </li>
                      </ul>
                    </div>
                  </div>

                  {/* Right 1 Col: Key Indicators */}
                  <div className="space-y-4">
                    <div className="rounded-lg bg-[#0b0f19] border border-[#1e293b] p-4">
                      <div className="text-xs font-mono text-slate-400 mb-3 font-semibold">
                        IDENTIFIED INDICATORS (IOCs)
                      </div>
                      <div className="space-y-2">
                        {[
                          { label: "Client IP", val: "198.51.100.44", tag: "External" },
                          { label: "Target Route", val: "/api/v1/auth/token", tag: "Ingress" },
                          { label: "Sign. Digest", val: "e3b0c44...a820", tag: "Payload" },
                        ].map((ioc, idx) => (
                          <motion.div
                            key={idx}
                            whileHover={{ y: -2, borderColor: "#334155" }}
                            transition={{ duration: 0.15 }}
                            className="p-2 rounded bg-[#0f172a] border border-[#1e293b] text-xs font-mono flex justify-between items-center transition-colors"
                          >
                            <div>
                              <div className="text-slate-500 text-[10px]">{ioc.label}</div>
                              <div className="text-slate-200">{ioc.val}</div>
                            </div>
                            <span className="text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                              {ioc.tag}
                            </span>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {activeTab === "timeline" && (
                <motion.div
                  key="timeline"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  className="space-y-4 relative pl-6 border-l border-[#1e293b]"
                >
                  {timelineEvents.map((evt, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.06, duration: 0.3 }}
                      className="relative"
                    >
                      {/* Node point */}
                      <span className="absolute -left-[31px] top-1.5 w-2.5 h-2.5 rounded-full bg-blue-500 ring-4 ring-[#0f172a]" />
                      <div className="rounded-lg bg-[#0b0f19] border border-[#1e293b] p-3 text-xs">
                        <div className="flex items-center justify-between font-mono text-slate-400 mb-1">
                          <span className="text-white font-semibold">{evt.title}</span>
                          <span className="text-[11px] tabular-nums">{evt.time}</span>
                        </div>
                        <p className="text-slate-300">{evt.desc}</p>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              )}

              {activeTab === "evidence" && (
                <motion.div
                  key="evidence"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  className="grid grid-cols-1 md:grid-cols-3 gap-4"
                >
                  {evidenceItems.map((evd, idx) => (
                    <motion.div
                      key={evd.id}
                      whileHover={{ y: -2, borderColor: "#334155" }}
                      transition={{ duration: 0.15 }}
                      className="rounded-lg bg-[#0b0f19] border border-[#1e293b] p-4 text-xs font-mono space-y-2 transition-all"
                    >
                      <div className="flex items-center justify-between text-slate-400">
                        <span className="text-blue-400 font-bold">{evd.id}</span>
                        <span className="text-slate-500 tabular-nums">{evd.size}</span>
                      </div>
                      <div className="font-semibold text-white truncate">{evd.filename}</div>
                      <div className="text-slate-400 text-[11px]">{evd.type}</div>
                      <div className="text-[10px] text-slate-500 pt-1 border-t border-[#1e293b] truncate">
                        SHA: {evd.hash}
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
