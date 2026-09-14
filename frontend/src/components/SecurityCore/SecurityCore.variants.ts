import { Variants } from "framer-motion";
import { SecurityCoreState } from "./SecurityCore.types";

export const EASING_PREMIUM = [0.16, 1, 0.3, 1] as const;
export const EASING_STANDARD = [0.4, 0, 0.2, 1] as const;
// Firm mechanical ease for blink — sharp, not bouncy
export const EASING_MECHANICAL = [0.55, 0, 0.45, 1] as const;

export const coreColors: Record<SecurityCoreState, string> = {
  idle: "#3b82f6",
  observing: "#3b82f6",
  analyzing: "#60a5fa",
  "high-risk": "#ef4444",
  investigating: "#3b82f6",
  secure: "#10b981",
};

// ── Outer Frame Variants ────────────────────────────────────────────────────
export const frameVariants: Variants = {
  idle: {
    scale: [1, 1.018, 1],
    opacity: 0.85,
    transition: {
      scale: { repeat: Infinity, duration: 4.0, ease: "easeInOut" },
      opacity: { duration: 0.3 },
    },
  },
  "idle-reduced": {
    scale: 1,
    opacity: 0.85,
    transition: { duration: 0.15 },
  },
  observing: {
    scale: 1.01,
    opacity: 0.95,
    transition: { duration: 0.5, ease: EASING_PREMIUM },
  },
  analyzing: {
    scale: [1, 0.96, 1.02, 1],
    opacity: 1,
    transition: { duration: 0.8, times: [0, 0.4, 0.7, 1], ease: EASING_PREMIUM },
  },
  "high-risk": {
    scale: [1, 1.04, 1],
    opacity: 1,
    transition: { duration: 0.5, times: [0, 0.7, 1], ease: EASING_PREMIUM },
  },
  investigating: {
    scale: 0.98,
    opacity: 0.95,
    transition: { duration: 0.35, ease: EASING_PREMIUM },
  },
  secure: {
    scale: 1,
    opacity: 0.85,
    transition: { duration: 0.5, ease: EASING_STANDARD },
  },
};

// ── Scan Ring Transient Variants ─────────────────────────────────────────────
export const scanRingVariants: Variants = {
  idle: { opacity: 0, scale: 0.8 },
  observing: {
    opacity: [0, 0.75, 0],
    scale: [0.7, 1.28],
    transition: { duration: 0.55, ease: EASING_PREMIUM },
  },
  analyzing: {
    opacity: [0, 0.9, 0],
    scale: [0.6, 1.32],
    transition: { duration: 0.75, delay: 0.1, ease: EASING_PREMIUM },
  },
  "high-risk": {
    opacity: [0, 0.65, 0],
    scale: [0.8, 1.2],
    transition: { duration: 0.5, ease: EASING_PREMIUM },
  },
  investigating: { opacity: 0, scale: 1, transition: { duration: 0.2 } },
  secure: {
    opacity: [0, 0.45, 0],
    scale: [0.8, 1.08],
    transition: { duration: 0.4, ease: EASING_STANDARD },
  },
};

// ── Central Core Pulse Variants ──────────────────────────────────────────────
export const centerCoreVariants: Variants = {
  idle: {
    scale: 1,
    opacity: 0.6,
    transition: { duration: 0.3 },
  },
  observing: {
    scale: 1.1,
    opacity: 1,
    transition: { duration: 0.3, ease: EASING_PREMIUM },
  },
  analyzing: {
    scale: [1, 1.28, 1],
    opacity: [0.8, 1, 0.9],
    transition: { duration: 0.8, ease: EASING_PREMIUM },
  },
  "high-risk": {
    scale: [1, 1.35, 1.15],
    opacity: 1,
    transition: { duration: 0.5, ease: EASING_PREMIUM },
  },
  investigating: {
    scale: 1.18,
    opacity: 1,
    transition: { duration: 0.35, ease: EASING_PREMIUM },
  },
  secure: {
    scale: 1,
    opacity: 0.7,
    transition: { duration: 0.5, ease: EASING_STANDARD },
  },
};

// ── Arc Gauge Fill Variants (Stage 1 / Stage 4: analyzing only) ──────────────
export const arcGaugeVariants: Variants = {
  idle: { pathLength: 0, opacity: 0, transition: { duration: 0.2 } },
  observing: { pathLength: 0, opacity: 0, transition: { duration: 0.2 } },
  analyzing: {
    pathLength: [0, 0.72],
    opacity: [0, 0.85],
    transition: { duration: 0.7, delay: 0.15, ease: EASING_PREMIUM },
  },
  "high-risk": { pathLength: 0, opacity: 0, transition: { duration: 0.2 } },
  investigating: { pathLength: 0, opacity: 0, transition: { duration: 0.2 } },
  secure: { pathLength: 0, opacity: 0, transition: { duration: 0.3 } },
};

// ── Aperture Blink Clip Variants (Stage 2) ────────────────────────────────
// Values describe the vertical clip range (0=fully closed, 1=fully open)
// Implemented as clipPath scaleY on the aperture mask group
export const blinkVariants: Variants = {
  open: {
    scaleY: 1,
    transition: { duration: 0.18, ease: EASING_MECHANICAL },
  },
  closing: {
    scaleY: 0.04,
    transition: { duration: 0.15, ease: EASING_MECHANICAL },
  },
  closed: {
    scaleY: 0.04,
    transition: { duration: 0.05 },
  },
  opening: {
    scaleY: 1,
    transition: { duration: 0.175, ease: EASING_MECHANICAL },
  },
};

// ── HUD label definitions (Stage 3) ─────────────────────────────────────────
export const HUD_LABELS: Record<SecurityCoreState, string | null> = {
  idle: null,
  observing: "OBSERVATION ACTIVE",
  analyzing: "ANALYSIS IN PROGRESS",
  "high-risk": "RISK ASSESSED",
  investigating: "INVESTIGATION ACTIVE",
  secure: "SIGNAL ACQUIRED",
};

export const HUD_FRAGMENTS: Record<SecurityCoreState, [string, string] | null> = {
  idle: null,
  observing: ["SIG:94.2%", "BAND:C1"],
  analyzing: ["CONF:96.4%", "DEPTH:L3"],
  "high-risk": ["SCORE:84/100", "TIER:CRIT"],
  investigating: ["CHAIN:4/4", "ANCHORED"],
  secure: ["CLR:100%", "BASELINE"],
};
