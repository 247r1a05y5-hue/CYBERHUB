import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ChevronDown, ShieldCheck, Activity, Radio } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { HeroDashboardPreview } from "./HeroDashboardPreview";
import { SecurityCore } from "./SecurityCore";
import { SecurityCoreState } from "./SecurityCore/SecurityCore.types";
import { TelemetryField } from "./TelemetryField";

export const LandingHero: React.FC = () => {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const [coreState, setCoreState] = useState<SecurityCoreState>("idle");
  const [signalActive, setSignalActive] = useState(false);

  // Stage 8: Signature Hero Sequence on page load
  useEffect(() => {
    if (prefersReducedMotion) return;

    // Sequence timing:
    // 0ms: idle
    // 600ms: telemetry signal packet fires towards aperture
    // 900ms: aperture detects & transitions to analyzing
    // 2100ms: risk threshold crossed -> high-risk alert
    // 3400ms: containment verified -> returns to settled idle
    const t1 = setTimeout(() => {
      setSignalActive(true);
    }, 600);

    const t2 = setTimeout(() => {
      setCoreState("analyzing");
    }, 950);

    const t3 = setTimeout(() => {
      setSignalActive(false);
      setCoreState("high-risk");
    }, 2100);

    const t4 = setTimeout(() => {
      setCoreState("idle");
    }, 3600);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [prefersReducedMotion]);

  const headlineLines = [
    "Detect Threats.",
    "Understand Risk.",
    "Respond With Confidence.",
  ];

  const scrollToCapabilities = () => {
    const el = document.getElementById("platform");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="relative pt-24 pb-16 md:pt-32 md:pb-24 overflow-hidden">
      {/* Stage 9: Ambient Falling Telemetry Background */}
      <TelemetryField />

      {/* Background subtle radial gradient */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[450px] bg-blue-600/5 blur-[120px] rounded-full pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-4xl mx-auto">
          {/* Eyebrow & Core Status Indicator */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center space-x-3 px-3.5 py-1.5 rounded-full bg-[#0f172a]/90 border border-[#1e293b] text-xs font-mono mb-6 backdrop-blur-sm shadow-md"
          >
            <div className="flex items-center space-x-1.5 text-blue-400">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
              <span className="font-semibold uppercase tracking-wider">AETHER.SEC</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="flex items-center space-x-1.5 text-slate-400">
              <span
                className={`w-2 h-2 rounded-full ${
                  coreState === "high-risk"
                    ? "bg-red-400 animate-ping"
                    : coreState === "analyzing"
                    ? "bg-blue-400 animate-pulse"
                    : "bg-emerald-400"
                }`}
              />
              <span className="text-[11px] text-slate-300">
                CORE: {coreState.toUpperCase()}
              </span>
            </div>
          </motion.div>

          {/* Central Optical Aperture SecurityCore Element (Hero Focus) */}
          <div className="relative flex items-center justify-center my-4 py-2">
            {/* Stage 10: Signal-to-Core Reactive Trajectory Line */}
            {signalActive && (
              <motion.div
                initial={{ opacity: 0, x: -80, scale: 0.8 }}
                animate={{ opacity: [0, 1, 0.9, 0], x: 0, scale: [0.8, 1, 0.6] }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="absolute z-20 pointer-events-none flex items-center space-x-2 text-[10px] font-mono text-blue-400 bg-blue-950/80 px-2 py-0.5 rounded border border-blue-500/40"
              >
                <Radio className="w-3 h-3 text-blue-400 animate-spin" />
                <span>PACKET_INGRESS_0x9B</span>
              </motion.div>
            )}

            <motion.div
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="relative cursor-crosshair group"
            >
              <SecurityCore
                state={coreState}
                size="hero"
                interactive={true}
                className="transition-transform duration-300 group-hover:scale-[1.03]"
              />
            </motion.div>
          </div>

          {/* 2. Headline with clipped-reveal stagger */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.1] mb-6">
            {headlineLines.map((line, index) => (
              <div key={index} className="overflow-hidden">
                <motion.div
                  initial={{ y: "100%", opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{
                    delay: index * 0.07,
                    duration: 0.5,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                  className={index === 2 ? "text-slate-300 font-semibold" : ""}
                >
                  {line}
                </motion.div>
              </div>
            ))}
          </h1>

          {/* 3. Supporting text */}
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.22, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed mb-8"
          >
            A modern cybersecurity platform for analyzing threats, understanding
            risk, investigating evidence, and accelerating security decisions.
          </motion.p>

          {/* 4. CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col sm:flex-row items-center justify-center gap-3.5 mb-14"
          >
            <motion.button
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
              onClick={() => navigate("/dashboard")}
              className="w-full sm:w-auto px-6 py-3 rounded-md bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm shadow-md border border-blue-500/50 flex items-center justify-center space-x-2 transition-colors duration-150"
            >
              <span>Launch Platform</span>
              <ArrowRight className="w-4 h-4" />
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
              onClick={scrollToCapabilities}
              className="w-full sm:w-auto px-6 py-3 rounded-md bg-[#0f172a] hover:bg-[#1e293b] text-slate-300 hover:text-white font-semibold text-sm border border-[#1e293b] flex items-center justify-center space-x-2 transition-colors duration-150"
            >
              <span>Explore Platform</span>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </motion.button>
          </motion.div>
        </div>

        {/* 5. Realistic Dashboard Preview */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-6xl mx-auto"
        >
          <HeroDashboardPreview />
        </motion.div>
      </div>
    </section>
  );
};
