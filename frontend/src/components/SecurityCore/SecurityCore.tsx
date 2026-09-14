/**
 * SecurityCore — Optical aperture identity element for AETHER.SEC
 * Implements: Stage 1 (extended geometry), Stage 2 (mechanical blink),
 * Stage 3 (HUD instrumentation), Stage 4 (state behavior),
 * Stage 5 (cursor orientation).
 * Public API unchanged from Phase 1.
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, useReducedMotion, useSpring, AnimatePresence } from "framer-motion";
import {
  SecurityCoreProps,
  SecurityCoreSize,
  SecurityCoreState,
} from "./SecurityCore.types";
import {
  coreColors,
  frameVariants,
  scanRingVariants,
  centerCoreVariants,
  arcGaugeVariants,
  blinkVariants,
  HUD_LABELS,
  HUD_FRAGMENTS,
  EASING_PREMIUM,
  EASING_STANDARD,
  EASING_MECHANICAL,
} from "./SecurityCore.variants";

// ── Size Configuration ────────────────────────────────────────────────────────
const SIZE_CONFIG: Record<
  SecurityCoreSize,
  {
    width: number;
    height: number;
    strokeWidth: number;
    showTicks: boolean;
    showArcs: boolean;
    showHUD: boolean;
  }
> = {
  hero:    { width: 120, height: 96,  strokeWidth: 1.5,  showTicks: true,  showArcs: true,  showHUD: true  },
  section: { width: 64,  height: 52,  strokeWidth: 1.0,  showTicks: true,  showArcs: true,  showHUD: false },
  nav:     { width: 28,  height: 22,  strokeWidth: 0.75, showTicks: false, showArcs: false, showHUD: false },
  inline:  { width: 18,  height: 14,  strokeWidth: 0.5,  showTicks: false, showArcs: false, showHUD: false },
};

// States that suppress blinking
const BLINK_SUPPRESSED_STATES: SecurityCoreState[] = ["analyzing", "high-risk", "investigating"];

// ── Component ─────────────────────────────────────────────────────────────────
export const SecurityCore: React.FC<SecurityCoreProps> = ({
  state = "idle",
  size = "section",
  interactive = false,
  className = "",
  onStateSettled,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();
  const config = SIZE_CONFIG[size] || SIZE_CONFIG.section;

  // ── Settle callback ─────────────────────────────────────────────────────────
  useEffect(() => {
    const durations: Record<SecurityCoreState, number> = {
      idle: 300,
      observing: 600,
      analyzing: 800,
      "high-risk": 700,
      investigating: 350,
      secure: 500,
    };
    const timer = setTimeout(() => onStateSettled?.(), durations[state] ?? 400);
    return () => clearTimeout(timer);
  }, [state, onStateSettled]);

  // ── Stage 5: Spring-damped pointer orientation ──────────────────────────────
  const rotateX = useSpring(0, { stiffness: 120, damping: 20 });
  const rotateY = useSpring(0, { stiffness: 120, damping: 20 });

  useEffect(() => {
    if (!interactive || prefersReducedMotion) return;
    const hasFinePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    if (!hasFinePointer) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      if (Math.sqrt(dx * dx + dy * dy) < 12) {
        rotateX.set(0); rotateY.set(0); return;
      }
      const maxDeg = 2.5;
      rotateY.set(Math.max(-maxDeg, Math.min(maxDeg, (dx / window.innerWidth) * 5)));
      rotateX.set(Math.max(-maxDeg, Math.min(maxDeg, (-dy / window.innerHeight) * 5)));
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [interactive, prefersReducedMotion, rotateX, rotateY]);

  // ── Stage 2: Mechanical blink scheduler ────────────────────────────────────
  type BlinkPhase = "open" | "closing" | "closed" | "opening";
  const [blinkPhase, setBlinkPhase] = useState<BlinkPhase>("open");
  const blinkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isBlinkSuppressed = BLINK_SUPPRESSED_STATES.includes(state) || prefersReducedMotion;

  const scheduleBlink = useCallback(() => {
    if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current);
    // Randomized interval 4–11s, never fixed
    const delay = 4000 + Math.random() * 7000;
    blinkTimerRef.current = setTimeout(() => {
      // Check suppression at execution time (state may have changed)
      setBlinkPhase("closing");
    }, delay);
  }, []);

  useEffect(() => {
    if (isBlinkSuppressed) {
      if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current);
      setBlinkPhase("open");
      return;
    }
    scheduleBlink();
    return () => { if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current); };
  }, [isBlinkSuppressed, scheduleBlink]);

  // Progress through blink phases
  useEffect(() => {
    if (isBlinkSuppressed || blinkPhase === "open") return;

    let timer: ReturnType<typeof setTimeout>;

    if (blinkPhase === "closing") {
      // Hold closed 40–60ms
      timer = setTimeout(() => setBlinkPhase("closed"), 150 + Math.random() * 30);
    } else if (blinkPhase === "closed") {
      const holdMs = 40 + Math.random() * 20;
      timer = setTimeout(() => {
        // ~1-in-9 chance of double blink
        const doubleBlink = Math.random() < 0.11;
        setBlinkPhase("opening");
        if (doubleBlink) {
          setTimeout(() => setBlinkPhase("closing"), 260);
        }
      }, holdMs);
    } else if (blinkPhase === "opening") {
      // After open, re-schedule next blink
      timer = setTimeout(() => {
        setBlinkPhase("open");
        scheduleBlink();
      }, 180);
    }
    return () => clearTimeout(timer);
  }, [blinkPhase, isBlinkSuppressed, scheduleBlink]);

  // ── Stage 3: HUD — mount once, opacity-toggle (not remounted) ──────────────
  const [hudVisible, setHudVisible] = useState(false);
  const [hudLabel, setHudLabel] = useState<string | null>(null);
  const [hudFragments, setHudFragments] = useState<[string, string] | null>(null);
  const hudTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (hudTimerRef.current) clearTimeout(hudTimerRef.current);

    const label = HUD_LABELS[state];
    const frags = HUD_FRAGMENTS[state];

    if (!label || !config.showHUD) {
      setHudVisible(false);
      return;
    }

    // Update content immediately (DOM already mounted), then toggle opacity
    setHudLabel(label);
    setHudFragments(frags);
    setHudVisible(true);

    // Auto-hide after 2.5s hold
    hudTimerRef.current = setTimeout(() => setHudVisible(false), 2500);
    return () => { if (hudTimerRef.current) clearTimeout(hudTimerRef.current); };
  }, [state, config.showHUD]);

  // ── Derived values ──────────────────────────────────────────────────────────
  const activeColor = coreColors[state] ?? coreColors.idle;
  const activeVariant = prefersReducedMotion && state === "idle" ? "idle-reduced" : state;

  return (
    <div
      ref={containerRef}
      className={`inline-flex items-center justify-center relative select-none ${className}`}
      style={{ width: `${config.width}px`, height: `${config.height}px`, perspective: "600px" }}
      role="img"
      aria-label={`Security aperture status: ${state}`}
    >
      {/* ── Stage 5: 3D orientation wrapper ───────────────────────────────── */}
      <motion.div
        style={{
          width: "100%",
          height: "100%",
          rotateX: interactive && !prefersReducedMotion ? rotateX : 0,
          rotateY: interactive && !prefersReducedMotion ? rotateY : 0,
          transformStyle: "preserve-3d",
        }}
      >
        {/* ── Stage 2: Blink clip mask ───────────────────────────────────── */}
        <motion.div
          variants={blinkVariants}
          animate={prefersReducedMotion ? "open" : blinkPhase}
          style={{
            width: "100%",
            height: "100%",
            transformOrigin: "center center",
            willChange: "transform",
          }}
        >
          <motion.svg
            viewBox="0 0 120 96"
            width={config.width}
            height={config.height}
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            variants={frameVariants}
            animate={activeVariant}
            className="w-full h-full overflow-visible"
          >
            {/* ── STAGE 1 GEOMETRY LAYER STACK ──────────────────────────────
             * Back-to-front:
             * 1a. Outer frame shadow (depth)
             * 1b. Outer structural frame (8-sided faceted)
             * 1c. Inner aperture boundary
             * 1d. Ring 1 — dashed outer (existing)
             * 1e. Ring 2 — solid mid (existing)
             * 1f. Ring 3 — new solid inner
             * 1g. Ring 4 — new thin innermost (hero/section only)
             * 1h. Asymmetric arc segments (2, off-center)
             * 1i. Radial precision tick marks (up to 12, hero/section only)
             * 1j. Scan ring (transient, existing)
             * 1k. Arc gauge (analyzing state only)
             * 1l. Central core (sole severity color carrier)
             * 1m. Axis ticks (existing 4)
             */}

            {/* 1a. Depth shadow */}
            <path
              d="M 36,13 L 84,13 L 109,34 L 109,62 L 84,83 L 36,83 L 11,62 L 11,34 Z"
              stroke="rgba(30, 41, 59, 0.35)"
              strokeWidth={config.strokeWidth + 1}
              strokeLinejoin="bevel"
            />

            {/* 1b. Outer Structural Frame */}
            <path
              d="M 36,12 L 84,12 L 110,34 L 110,62 L 84,84 L 36,84 L 10,62 L 10,34 Z"
              stroke="currentColor"
              strokeWidth={config.strokeWidth}
              strokeLinejoin="bevel"
              className="text-slate-500/80"
            />

            {/* 1c. Inner Aperture Boundary (~70% radius) */}
            <path
              d="M 44,24 L 76,24 L 94,39 L 94,57 L 76,72 L 44,72 L 26,57 L 26,39 Z"
              stroke="currentColor"
              strokeWidth={config.strokeWidth * 0.85}
              strokeLinejoin="bevel"
              className="text-slate-600/70"
            />

            {/* 1d. Ring 1 — dashed outer */}
            <ellipse
              cx="60" cy="48" rx="24" ry="18"
              stroke="currentColor"
              strokeWidth={config.strokeWidth * 0.6}
              strokeDasharray="2 3"
              className="text-slate-600/45"
            />

            {/* 1e. Ring 2 — solid mid */}
            <ellipse
              cx="60" cy="48" rx="18" ry="13.5"
              stroke="currentColor"
              strokeWidth={config.strokeWidth * 0.55}
              className="text-slate-600/55"
            />

            {/* 1f. Ring 3 — new solid inner (Stage 1) */}
            <ellipse
              cx="60" cy="48" rx="13" ry="9.5"
              stroke="currentColor"
              strokeWidth={config.strokeWidth * 0.5}
              className="text-slate-700/50"
            />

            {/* 1g. Ring 4 — thin innermost (hero/section only) */}
            {config.showTicks && (
              <ellipse
                cx="60" cy="48" rx="8.5" ry="6"
                stroke="currentColor"
                strokeWidth={config.strokeWidth * 0.4}
                strokeDasharray="1.5 2.5"
                className="text-slate-700/40"
              />
            )}

            {/* 1h. Asymmetric arc segments — off-center, not mandala-symmetric */}
            {config.showArcs && (
              <>
                {/* Arc A: upper-right, 110° sweep, offset from center */}
                <path
                  d="M 78,28 A 28 22 0 0 1 104,50"
                  stroke="currentColor"
                  strokeWidth={config.strokeWidth * 0.6}
                  strokeLinecap="round"
                  className="text-slate-600/35"
                />
                {/* Arc B: lower-left, ~80° sweep, offset opposite */}
                <path
                  d="M 40,68 A 26 20 0 0 1 18,50"
                  stroke="currentColor"
                  strokeWidth={config.strokeWidth * 0.55}
                  strokeLinecap="round"
                  className="text-slate-700/30"
                />
              </>
            )}

            {/* 1i. Radial precision ticks — 12 marks on Ring 2 circumference */}
            {config.showTicks && (() => {
              const ticks = [];
              const totalTicks = 12;
              for (let i = 0; i < totalTicks; i++) {
                const angle = (i / totalTicks) * 2 * Math.PI - Math.PI / 2;
                const rx = 18, ry = 13.5;
                const innerScale = 0.88;
                const ox = 60 + rx * Math.cos(angle);
                const oy = 48 + ry * Math.sin(angle);
                const ix = 60 + rx * innerScale * Math.cos(angle);
                const iy = 48 + ry * innerScale * Math.sin(angle);
                // Every 3rd tick is slightly longer
                const isLong = i % 3 === 0;
                ticks.push(
                  <line
                    key={i}
                    x1={isLong ? 60 + rx * 0.84 * Math.cos(angle) : ix}
                    y1={isLong ? 48 + ry * 0.84 * Math.sin(angle) : iy}
                    x2={ox} y2={oy}
                    stroke="currentColor"
                    strokeWidth={config.strokeWidth * 0.4}
                    strokeLinecap="round"
                    className={isLong ? "text-slate-500/25" : "text-slate-600/15"}
                  />
                );
              }
              return <g>{ticks}</g>;
            })()}

            {/* 1j. Scan Ring (transient sweep) */}
            <motion.ellipse
              cx="60" cy="48" rx="21" ry="15.5"
              stroke={activeColor}
              strokeWidth={config.strokeWidth * 0.9}
              variants={scanRingVariants}
              animate={state}
            />

            {/* 1k. Arc Gauge — analyzing state only (Stage 1 / Stage 4) */}
            <motion.path
              d="M 60,24 A 28 22 0 0 1 100,54"
              stroke={activeColor}
              strokeWidth={config.strokeWidth * 1.2}
              strokeLinecap="round"
              fill="none"
              variants={arcGaugeVariants}
              animate={state}
              style={{ transformOrigin: "60px 48px" }}
            />

            {/* 1l. Central Core — SOLE severity color carrier */}
            <motion.polygon
              points="60,42.5 65.5,48 60,53.5 54.5,48"
              fill={activeColor}
              variants={centerCoreVariants}
              animate={state}
              style={{
                transformOrigin: "60px 48px",
                filter:
                  state === "high-risk"
                    ? "drop-shadow(0 0 4px rgba(239, 68, 68, 0.38))"
                    : state === "observing" || state === "analyzing"
                    ? "drop-shadow(0 0 3px rgba(59, 130, 246, 0.32))"
                    : "none",
              }}
            />

            {/* 1m. Axis Ticks (existing 4 cardinal marks) */}
            {config.showTicks && (
              <g className="text-slate-500/35" stroke="currentColor" strokeWidth={config.strokeWidth * 0.5} strokeLinecap="round">
                <line x1="60" y1="18" x2="60" y2="22" />
                <line x1="60" y1="74" x2="60" y2="78" />
                <line x1="18" y1="48" x2="22" y2="48" />
                <line x1="98" y1="48" x2="102" y2="48" />
              </g>
            )}
          </motion.svg>
        </motion.div>
      </motion.div>

      {/* ── Stage 3: HUD Instrumentation — single-mounted, opacity-toggled ── */}
      {config.showHUD && (
        <div
          className="absolute inset-0 pointer-events-none overflow-visible"
          aria-hidden="true"
          style={{ zIndex: 1 }}
        >
          {/* HUD Label — top-center */}
          <motion.div
            animate={{ opacity: hudVisible ? 1 : 0 }}
            transition={{ duration: 0.25, ease: EASING_STANDARD }}
            className="absolute left-1/2 -translate-x-1/2 font-mono text-blue-400/80 whitespace-nowrap"
            style={{ top: "-22px", fontSize: "7px", letterSpacing: "0.12em" }}
          >
            {hudLabel}
          </motion.div>

          {/* HUD Fragment Left */}
          <motion.div
            animate={{ opacity: hudVisible && hudFragments ? 1 : 0 }}
            transition={{ duration: 0.2, delay: 0.05, ease: EASING_STANDARD }}
            className="absolute font-mono text-slate-400/70 whitespace-nowrap"
            style={{ bottom: "-18px", left: "4px", fontSize: "6.5px", letterSpacing: "0.1em" }}
          >
            {hudFragments?.[0]}
          </motion.div>

          {/* HUD Fragment Right */}
          <motion.div
            animate={{ opacity: hudVisible && hudFragments ? 1 : 0 }}
            transition={{ duration: 0.2, delay: 0.08, ease: EASING_STANDARD }}
            className="absolute font-mono text-slate-400/70 whitespace-nowrap"
            style={{ bottom: "-18px", right: "4px", fontSize: "6.5px", letterSpacing: "0.1em" }}
          >
            {hudFragments?.[1]}
          </motion.div>
        </div>
      )}
    </div>
  );
};
