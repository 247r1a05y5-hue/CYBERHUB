import React from "react";
import { motion } from "framer-motion";
import { 
  Cpu, 
  Activity, 
  Search, 
  ShieldAlert, 
  Layers, 
  CheckCircle, 
  ArrowRight,
  TrendingUp,
  FileText
} from "lucide-react";
import { AgentNode } from "./AgentNode";

export const PlatformFeatures: React.FC = () => {
  const features = [
    {
      id: "analysis",
      icon: Cpu,
      title: "Threat Analysis",
      tag: "INGESTION & ML",
      description:
        "High-throughput multi-analyzer pipeline combining heuristic models, static rules, and metadata inspection.",
      visual: (
        <div className="rounded bg-[#0b0f19] border border-[#1e293b] p-3 text-xs font-mono space-y-2">
          <div className="flex justify-between items-center text-slate-400 text-[11px] pb-1 border-b border-[#1e293b]">
            <span>ANOMALY DETECTOR</span>
            <span className="text-emerald-400">STATUS: MATCHED</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
            <div className="bg-[#0f172a] p-1.5 rounded border border-[#1e293b]">
              <div className="text-slate-500">PAYLOAD</div>
              <div className="text-slate-200 font-semibold mt-0.5">0.94 CONF</div>
            </div>
            <div className="bg-[#0f172a] p-1.5 rounded border border-[#1e293b]">
              <div className="text-slate-500">HEURISTIC</div>
              <div className="text-slate-200 font-semibold mt-0.5">FLAGGED</div>
            </div>
            <div className="bg-[#0f172a] p-1.5 rounded border border-[#1e293b]">
              <div className="text-slate-500">SIGNATURE</div>
              <div className="text-slate-200 font-semibold mt-0.5">SHA-256</div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "risk",
      icon: Activity,
      title: "Risk Intelligence",
      tag: "EXPLAINABLE SCORING",
      description:
        "Deterministic weighted risk computation mapping findings to standardized severity tiers with audit-grade transparency.",
      visual: (
        <div className="rounded bg-[#0b0f19] border border-[#1e293b] p-3 text-xs font-mono space-y-2">
          <div className="flex justify-between items-center text-slate-400 text-[11px]">
            <span>WEIGHTED RISK FORMULA</span>
            <span className="text-white font-bold tabular-nums">74.0 / 100</span>
          </div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between text-slate-400">
              <span>Model Weight (40%)</span>
              <span className="text-slate-200 tabular-nums">37.6</span>
            </div>
            <div className="w-full bg-[#1e293b] h-1.5 rounded-full overflow-hidden">
              <div className="bg-blue-500 h-full w-[94%]" />
            </div>
            <div className="flex justify-between text-slate-400 pt-0.5">
              <span>Rule Engine (35%)</span>
              <span className="text-slate-200 tabular-nums">24.5</span>
            </div>
            <div className="w-full bg-[#1e293b] h-1.5 rounded-full overflow-hidden">
              <div className="bg-amber-500 h-full w-[70%]" />
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "investigation",
      icon: Search,
      title: "Investigation",
      tag: "EVIDENCE & CONTEXT",
      description:
        "Interactive SOC analyst workspace correlating correlated events, timeline artifacts, and contextual telemetry.",
      visual: (
        <div className="rounded bg-[#0b0f19] border border-[#1e293b] p-3 text-xs font-mono space-y-2">
          <div className="flex items-center space-x-2 text-[11px] text-slate-400 pb-1 border-b border-[#1e293b]">
            <FileText className="w-3 h-3 text-blue-400" />
            <span>ARTIFACT CHAIN (3 ATTACHED)</span>
          </div>
          <div className="space-y-1 text-[11px]">
            <div className="flex items-center justify-between text-slate-300 bg-[#0f172a] px-2 py-1 rounded">
              <span>payload_dump_0911.bin</span>
              <span className="text-[10px] text-slate-400">HASH MATCH</span>
            </div>
            <div className="flex items-center justify-between text-slate-300 bg-[#0f172a] px-2 py-1 rounded">
              <span>jwt_bearer_token.header</span>
              <span className="text-[10px] text-amber-400">EXP FORGED</span>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "response",
      icon: ShieldAlert,
      title: "Incident Response",
      tag: "FSM ORCHESTRATION",
      description:
        "Stateful incident lifecycles with strict transition validation, containment playbooks, and immutable audit logs.",
      visual: (
        <div className="rounded bg-[#0b0f19] border border-[#1e293b] p-3 text-xs font-mono space-y-3">
          <div className="flex justify-between items-center text-slate-400 text-[11px]">
            <span>AUTONOMOUS AGENT NODE</span>
            <span className="text-emerald-400">ACTIVE: CONTAIN</span>
          </div>
          <div className="flex items-center justify-center py-1">
            <AgentNode
              size="small"
              state="executing"
              action="contain"
            />
          </div>
          <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-[#1e293b]">
            <span>Containment Playbook #08</span>
            <span className="text-emerald-400 font-mono">0.42s latency</span>
          </div>
        </div>
      ),
    },
  ];

  return (
    <section id="platform" className="py-20 bg-[#080c14] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="max-w-3xl mb-14">
          <div className="text-xs font-mono uppercase tracking-wider text-blue-400 font-semibold mb-2">
            CORE PLATFORM CAPABILITIES
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-4">
            One platform from detection to decision.
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            Eliminate fragmented tools. A unified security foundation designed
            to ingest telemetry, run explainable models, and empower SOC teams
            to triage with precision.
          </p>
        </div>

        {/* 4 Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{
                  delay: idx * 0.08,
                  duration: 0.5,
                  ease: [0.16, 1, 0.3, 1],
                }}
                whileHover={{
                  y: -4,
                  borderColor: "rgba(51, 65, 85, 0.9)",
                  boxShadow: "0 12px 30px -10px rgba(0, 0, 0, 0.6)",
                }}
                className="rounded-xl bg-[#0f172a] border border-[#1e293b] p-6 flex flex-col justify-between transition-all duration-200"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-lg bg-[#0b0f19] border border-[#1e293b] flex items-center justify-center text-blue-400">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-[#1e293b]/70 text-slate-300 border border-[#334155]/50">
                      {feature.tag}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-white mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-slate-400 leading-relaxed mb-6">
                    {feature.description}
                  </p>
                </div>

                <div className="mt-auto">{feature.visual}</div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
