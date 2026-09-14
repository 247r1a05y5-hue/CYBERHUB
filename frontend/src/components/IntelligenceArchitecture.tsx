import React, { useState } from "react";
import { motion } from "framer-motion";
import { 
  Cpu, 
  Binary, 
  Radar, 
  Activity, 
  Check, 
  ArrowRight,
  ShieldAlert,
  Server
} from "lucide-react";
import { SecurityCore } from "./SecurityCore";

export const IntelligenceArchitecture: React.FC = () => {
  const [pulseDone, setPulseDone] = useState(false);

  const signalCards = [
    {
      id: "model",
      title: "Model Intelligence",
      tag: "INFERENCE ENGINE",
      icon: Cpu,
      weight: "40% WEIGHT",
      metrics: "Entropy, Heuristic, Anomaly Classifier",
      latency: "14ms",
      status: "Calculated",
    },
    {
      id: "rules",
      title: "Rule Intelligence",
      tag: "DETERMINISTIC LOGIC",
      icon: Binary,
      weight: "35% WEIGHT",
      metrics: "Declarative YAML, Regex, Thresholds",
      latency: "2ms",
      status: "Matched",
    },
    {
      id: "intel",
      title: "Threat Intelligence",
      tag: "EXTERNAL FEEDS",
      icon: Radar,
      weight: "25% WEIGHT",
      metrics: "Known IOCs, IP Reputation, CVE Feeds",
      latency: "22ms",
      status: "Queried",
    },
  ];

  return (
    <section id="intelligence" className="py-20 bg-[#080c14] border-t border-[#1e293b] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="text-xs font-mono uppercase tracking-wider text-blue-400 font-semibold mb-2">
            INTELLIGENCE SYNTHESIS
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-4">
            Unified multi-signal risk computation.
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            Deterministic combination of statistical inference, policy rules, and
            live threat intelligence feeds into an auditable risk evaluation.
          </p>
        </div>

        {/* Architecture Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center max-w-6xl mx-auto">
          {/* 3 Left/Top Input Signal Cards (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            {signalCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <motion.div
                  key={card.id}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: "-40px" }}
                  transition={{
                    delay: index * 0.1,
                    duration: 0.5,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                  className="rounded-xl bg-[#0f172a] border border-[#1e293b] p-4 shadow-md flex items-center justify-between"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-[#0b0f19] border border-[#1e293b] flex items-center justify-center text-blue-400">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-bold text-white">
                          {card.title}
                        </h4>
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {card.metrics}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      {card.weight}
                    </span>
                    <div className="text-[10px] font-mono text-slate-500 mt-1 tabular-nums">
                      {card.latency}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* SVG Animated Connector in Desktop View (2 cols) */}
          <div className="hidden lg:flex lg:col-span-2 flex-col items-center justify-center h-full relative">
            <svg
              className="w-full h-48 overflow-visible"
              viewBox="0 0 100 120"
              fill="none"
            >
              {/* Top line to center */}
              <motion.path
                d="M 0,20 C 50,20 50,60 100,60"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="4 4"
                initial={{ pathLength: 0, opacity: 0 }}
                whileInView={{ pathLength: 1, opacity: 0.8 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              />
              {/* Middle line straight to center */}
              <motion.path
                d="M 0,60 L 100,60"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="4 4"
                initial={{ pathLength: 0, opacity: 0 }}
                whileInView={{ pathLength: 1, opacity: 0.8 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              />
              {/* Bottom line to center */}
              <motion.path
                d="M 0,100 C 50,100 50,60 100,60"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="4 4"
                initial={{ pathLength: 0, opacity: 0 }}
                whileInView={{ pathLength: 1, opacity: 0.8 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
                onAnimationComplete={() => setPulseDone(true)}
              />
            </svg>
          </div>

          {/* Central Converged Risk Assessment Card (5 cols) */}
          <div className="lg:col-span-5">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.35, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className={`rounded-xl bg-[#0f172a] border ${
                pulseDone ? "border-blue-500/60" : "border-[#1e293b]"
              } p-6 shadow-xl transition-all duration-400`}
            >
              <div className="flex items-center justify-between pb-4 border-b border-[#1e293b]">
                <div className="flex items-center space-x-3">
                  <div className="scale-75 origin-left">
                    <SecurityCore
                      state={pulseDone ? "analyzing" : "idle"}
                      size="inline"
                    />
                  </div>
                  <div>
                    <span className="font-bold text-white text-base block">
                      Risk Engine Synthesis
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      APERTURE EVALUATION
                    </span>
                  </div>
                </div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  REAL-TIME SYNTHESIS
                </span>
              </div>

              <div className="py-4 space-y-3">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-slate-400 font-mono">
                    CALCULATED RISK SCORE
                  </span>
                  <div className="flex items-baseline space-x-1">
                    <span className="text-3xl font-extrabold text-white font-mono tabular-nums">
                      74
                    </span>
                    <span className="text-xs text-slate-500 font-mono">/ 100</span>
                  </div>
                </div>

                <div className="w-full bg-[#1e293b] h-2 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: "74%" }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
                    className="h-full bg-gradient-to-r from-blue-500 to-amber-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs pt-2 font-mono">
                  <div className="bg-[#0b0f19] p-2 rounded border border-[#1e293b]">
                    <div className="text-slate-500 text-[10px]">SEVERITY TIER</div>
                    <div className="text-amber-400 font-semibold mt-0.5">HIGH RISK</div>
                  </div>
                  <div className="bg-[#0b0f19] p-2 rounded border border-[#1e293b]">
                    <div className="text-slate-500 text-[10px]">DECISION ROUTE</div>
                    <div className="text-slate-200 font-semibold mt-0.5">AUTO-TRIAGE</div>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-[#1e293b] flex items-center justify-between text-xs text-slate-400">
                <span>Deterministic & Explainable</span>
                <span className="font-mono text-emerald-400 text-[11px]">✓ Audit Proof #942</span>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
};
