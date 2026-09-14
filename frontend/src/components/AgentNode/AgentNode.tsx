import React, { useEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  AgentNodeProps,
  AgentNodeSize,
  AgentNodeState,
  ACTION_LABELS,
} from "./AgentNode.types";
import {
  frameVariants,
  lensVariants,
  signalLineVariants,
  confirmVariants,
  SETTLE_DURATIONS,
  EASING_PREMIUM,
} from "./AgentNode.variants";

// ── Size Configuration ───────────────────────────────────────────────────────
const SIZE_CONFIG: Record<
  AgentNodeSize,
  { width: number; height: number; strokeWidth: number; showTicks: boolean }
> = {
  default: { width: 40, height: 40, strokeWidth: 1.0, showTicks: true },
  small:   { width: 28, height: 28, strokeWidth: 0.75, showTicks: false },
};

// ── Component ────────────────────────────────────────────────────────────────
export const AgentNode: React.FC<AgentNodeProps> = ({
  action,
  state,
  size = "default",
  onSettled,
  className = "",
}) => {
  const prefersReducedMotion = useReducedMotion();
  const config = SIZE_CONFIG[size];

  // Fire onSettled after the transient animation completes
  useEffect(() => {
    const delay = prefersReducedMotion ? 100 : SETTLE_DURATIONS[state] ?? 200;
    const timer = setTimeout(() => {
      onSettled?.();
    }, delay);
    return () => clearTimeout(timer);
  }, [state, onSettled, prefersReducedMotion]);

  // Under reduced motion: collapse all transitions to instant fades, no movement
  const reducedVariant = prefersReducedMotion ? "idle" : state;

  const ariaLabel = `${ACTION_LABELS[action]} — ${state}`;

  return (
    <div
      className={`inline-flex items-center justify-center select-none ${className}`}
      style={{ width: `${config.width}px`, height: `${config.height}px` }}
      role="img"
      aria-label={ariaLabel}
    >
      {/*
       * Single SVG, viewBox="0 0 40 40" — geometry defined in the 40×40 space,
       * scaled via width/height props. Same convention as SecurityCore's viewBox approach.
       *
       * Layer stack (back to front):
       * 1. Outer softly-faceted module frame
       * 2. Inner inset boundary (simplified — no ring system, respecting hierarchy)
       * 3. Signal traveling line (executing transient only)
       * 4. Axis tick marks (default size only)
       * 5. Central lens (sole carrier of state color)
       * 6. Confirm shape (completed state only)
       */}
      <motion.svg
        viewBox="0 0 40 40"
        width={config.width}
        height={config.height}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        variants={frameVariants}
        animate={prefersReducedMotion ? { opacity: 0.85, transition: { duration: 0.1 } } : state}
        className="overflow-visible"
        style={{ willChange: "opacity" }}
      >
        {/* ── 1. Outer Module Frame (softly faceted, rhymes with SecurityCore) ─ */}
        {/*
         * 8-point path: clipped corners giving a softly faceted square.
         * Not a rounded rect (too generic), not a perfect octagon (too regular).
         * Corner clip ~5px — same "precision-cut" language as SecurityCore.
         */}
        <path
          d="M 6,2 L 34,2 L 38,6 L 38,34 L 34,38 L 6,38 L 2,34 L 2,6 Z"
          stroke="currentColor"
          strokeWidth={config.strokeWidth}
          strokeLinejoin="bevel"
          fill="#0f172a"
          className="text-slate-600/70 transition-colors duration-200"
        />

        {/* ── 2. Inner Inset Boundary (simpler than SecurityCore — respects hierarchy) */}
        <path
          d="M 9,5 L 31,5 L 35,9 L 35,31 L 31,35 L 9,35 L 5,31 L 5,9 Z"
          stroke="currentColor"
          strokeWidth={config.strokeWidth * 0.7}
          strokeLinejoin="bevel"
          fill="none"
          className="text-slate-700/50"
        />

        {/* ── 3. Traveling Signal Line (executing transient only) ────────────── */}
        <motion.line
          x1="5"
          y1="20"
          x2="20"
          y2="20"
          stroke="#60a5fa"
          strokeWidth={config.strokeWidth}
          strokeLinecap="round"
          variants={prefersReducedMotion ? undefined : signalLineVariants}
          animate={prefersReducedMotion ? { opacity: 0 } : state}
          style={{ transformOrigin: "5px 20px", willChange: "opacity, transform" }}
        />

        {/* ── 4. Axis Tick Marks (default size only, ≤15% opacity as in SecurityCore) */}
        {config.showTicks && (
          <g
            stroke="currentColor"
            strokeWidth={config.strokeWidth * 0.65}
            strokeLinecap="round"
            className="text-slate-500/40"
          >
            {/* Top tick */}
            <line x1="20" y1="5"  x2="20" y2="8"  />
            {/* Bottom tick */}
            <line x1="20" y1="32" x2="20" y2="35" />
          </g>
        )}

        {/* ── 5. Central Lens — SOLE carrier of state color ─────────────────── */}
        {/*
         * Small circle — direct echo of SecurityCore's central diamond/core.
         * Radius 4 at default size gives ~12.5% of the 40px box → within spec range.
         */}
        <motion.circle
          cx="20"
          cy="20"
          r="4"
          variants={prefersReducedMotion ? undefined : lensVariants}
          animate={
            prefersReducedMotion
              ? {
                  opacity: state === "idle" ? 0.5 : state === "completed" ? 0.65 : 1.0,
                  fill: state === "executing" ? "#60a5fa" : "#3b82f6",
                  scale: 1,
                  y: 0,
                  transition: { duration: 0.1 },
                }
              : state
          }
          style={{
            transformOrigin: "20px 20px",
            filter:
              state === "executing"
                ? "drop-shadow(0 0 3px rgba(96, 165, 250, 0.4))"
                : state === "processing"
                ? "drop-shadow(0 0 2px rgba(59, 130, 246, 0.3))"
                : "none",
            willChange: "opacity, transform",
          }}
        />

        {/* ── 6. Confirm Shape (completed state only) ────────────────────────── */}
        {/*
         * Two-segment checkmark-adjacent stroke, centered on the lens.
         * Not a Lucide icon — hand-drawn path using the same strokeWidth as the frame.
         * Layered on top of (not replacing) the lens so the central dot holds position.
         */}
        <motion.path
          d="M 16.5,20.5 L 19,23 L 23.5,17.5"
          stroke="#3b82f6"
          strokeWidth={config.strokeWidth * 1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          variants={prefersReducedMotion ? undefined : confirmVariants}
          animate={
            prefersReducedMotion
              ? { opacity: state === "completed" ? 1 : 0, scale: 1, transition: { duration: 0.1 } }
              : state
          }
          style={{
            transformOrigin: "20px 20px",
            willChange: "opacity, transform",
          }}
        />
      </motion.svg>
    </div>
  );
};
