import React, { useState, useEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { 
  ShieldAlert, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Terminal, 
  ExternalLink,
  Layers,
  Cpu,
  Search,
  Filter
} from "lucide-react";

export const HeroDashboardPreview: React.FC = () => {
  const [riskScore, setRiskScore] = useState<number>(0);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();

  // Single-run eased count-up on load (0 -> 74 over 900ms)
  useEffect(() => {
    if (prefersReducedMotion) {
      setRiskScore(74);
      return;
    }

    const duration = 900; // ms
    const targetScore = 74;
    const startTime = performance.now();

    const animateCount = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      const currentVal = Math.round(easedProgress * targetScore);
      setRiskScore(currentVal);

      if (progress < 1) {
        requestAnimationFrame(animateCount);
      }
    };

    const frameId = requestAnimationFrame(animateCount);
    return () => cancelAnimationFrame(frameId);
  }, [prefersReducedMotion]);

  // Subtle 2-4px mouse parallax
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = ((e.clientX - rect.left) / rect.width - 0.5) * 6; // max 3px
    const y = ((e.clientY - rect.top) / rect.height - 0.5) * 6;
    setMousePos({ x, y });
  };

  const handleMouseLeave = () => {
    setMousePos({ x: 0, y: 0 });
  };

  const activityRows = [
    {
      id: "SEC-9842",
      type: "Pipeline Analysis",
      target: "auth-service.production",
      severity: "high",
      status: "Investigating",
      time: "2m ago",
      score: 82,
    },
    {
      id: "SEC-9841",
      type: "Anomalous Credential Flow",
      target: "iam-admin-role",
      severity: "critical",
      status: "Escalated",
      time: "8m ago",
      score: 94,
    },
    {
      id: "SEC-9839",
      type: "Ingestion Payload Check",
      target: "gateway-ingress-02",
      severity: "medium",
      status: "Triaged",
      time: "14m ago",
      score: 56,
    },
    {
      id: "SEC-9835",
      type: "Signature Integrity Match",
      target: "container-registry/pkg-v2",
      severity: "low",
      status: "Resolved",
      time: "31m ago",
      score: 28,
    },
  ];

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative w-full rounded-xl border border-[#1e293b] bg-[#0b0f19] p-2 sm:p-4 shadow-2xl overflow-hidden transition-transform duration-300 ease-out"
      style={{
        transform: `translate3d(${mousePos.x}px, ${mousePos.y}px, 0)`,
        willChange: "transform",
      }}
    >
      {/* Top Application Window Bar */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1e293b]/80 px-2 text-xs">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-700/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-slate-700/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-slate-700/80 inline-block" />
          </div>
          <span className="text-slate-500 font-mono text-[11px] ml-2 flex items-center gap-1.5">
            <Terminal className="w-3 h-3 text-slate-400" />
            <span>app.aether-sec.internal/live-telemetry</span>
          </span>
        </div>
        <div className="flex items-center space-x-3 text-slate-400 font-mono text-[11px]">
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
            LIVE PIPELINE
          </span>
          <span className="hidden sm:inline-block text-slate-600">|</span>
          <span className="hidden sm:inline-block text-slate-400 tabular-nums">LATENCY: 18ms</span>
        </div>
      </div>

      {/* Dashboard Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3 mb-3">
        {/* Risk Score Card */}
        <motion.div
          whileHover={{ y: -2 }}
          transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-lg bg-[#0f172a] border border-[#1e293b] p-3 shadow-sm flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">Calculated Risk Index</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20">
              ELEVATED
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-white tabular-nums">
              {riskScore}
            </span>
            <span className="text-xs text-slate-500 font-mono">/ 100</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Aggregated Confidence</span>
            <span className="font-mono text-slate-300 tabular-nums">96.4%</span>
          </div>
        </motion.div>

        {/* Active Findings */}
        <motion.div
          whileHover={{ y: -2 }}
          transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-lg bg-[#0f172a] border border-[#1e293b] p-3 shadow-sm flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">Active Threat Signals</span>
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-white tabular-nums">
              14
            </span>
            <span className="text-[11px] text-red-400 font-mono tabular-nums">+2 crit</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <div className="h-1 flex-1 bg-red-500/80 rounded-full" />
            <div className="h-1 flex-1 bg-orange-500/80 rounded-full" />
            <div className="h-1 flex-1 bg-yellow-500/80 rounded-full" />
            <div className="h-1 flex-1 bg-slate-700 rounded-full" />
          </div>
        </motion.div>

        {/* Pipeline Analyzers */}
        <motion.div
          whileHover={{ y: -2 }}
          transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-lg bg-[#0f172a] border border-[#1e293b] p-3 shadow-sm flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">Analyzer Fleet</span>
            <Cpu className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-white tabular-nums">
              12 / 12
            </span>
            <span className="text-[10px] text-emerald-400 font-mono">100% HEALTHY</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Model Inference</span>
            <span className="font-mono text-slate-300 tabular-nums">14.2ms avg</span>
          </div>
        </motion.div>

        {/* Ingestion Velocity Sparkline */}
        <motion.div
          whileHover={{ y: -2 }}
          transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-lg bg-[#0f172a] border border-[#1e293b] p-3 shadow-sm flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">Ingestion Rate</span>
            <Activity className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-white tabular-nums">
              2.4k
            </span>
            <span className="text-xs text-slate-400 font-mono">events/sec</span>
          </div>
          {/* Sparkline SVG with single smooth draw-in */}
          <div className="mt-1 h-5 w-full">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 100 20">
              <motion.path
                d="M 0,16 L 15,14 L 30,17 L 45,8 L 60,11 L 75,5 L 90,9 L 100,4"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              />
            </svg>
          </div>
        </motion.div>
      </div>

      {/* Activity Stream Table with Staggered Rows */}
      <div className="rounded-lg bg-[#0f172a] border border-[#1e293b] overflow-hidden">
        <div className="px-3 py-2.5 bg-[#0b0f19]/60 border-b border-[#1e293b] flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-200">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Active Incident & Threat Stream</span>
          </div>
          <div className="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
            <span>STREAMING REAL-TIME</span>
          </div>
        </div>

        <div className="divide-y divide-[#1e293b]/60 text-xs">
          {activityRows.map((row, idx) => (
            <motion.div
              key={row.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 0.3 + idx * 0.04,
                duration: 0.4,
                ease: [0.16, 1, 0.3, 1],
              }}
              whileHover={{ backgroundColor: "rgba(30, 41, 59, 0.4)" }}
              className="px-3 py-2.5 flex items-center justify-between transition-colors duration-150"
            >
              <div className="flex items-center space-x-3">
                <span className="font-mono text-[11px] text-slate-400 w-16">
                  {row.id}
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                    row.severity === "critical"
                      ? "bg-red-500/10 text-red-400 border border-red-500/30"
                      : row.severity === "high"
                      ? "bg-orange-500/10 text-orange-400 border border-orange-500/30"
                      : row.severity === "medium"
                      ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/30"
                      : "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                  }`}
                >
                  {row.severity}
                </span>
                <span className="text-slate-200 font-medium truncate max-w-[140px] sm:max-w-[240px]">
                  {row.type}
                </span>
                <span className="hidden md:inline-block font-mono text-[11px] text-slate-400">
                  {row.target}
                </span>
              </div>

              <div className="flex items-center space-x-3 font-mono text-[11px]">
                <span className="hidden sm:inline-block text-slate-400 tabular-nums">
                  Score: <span className="text-white font-semibold">{row.score}</span>
                </span>
                <span className="text-slate-400 tabular-nums flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {row.time}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};
