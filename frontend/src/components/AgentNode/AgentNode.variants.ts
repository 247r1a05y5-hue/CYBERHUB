import { Variants } from "framer-motion";

export const EASING_PREMIUM = [0.16, 1, 0.3, 1] as const;
export const EASING_STANDARD = [0.4, 0, 0.2, 1] as const;

// State settle durations in ms — used by the component for onSettled timing
export const SETTLE_DURATIONS: Record<string, number> = {
  idle: 150,
  processing: 400,
  executing: 450,
  completed: 450,
};

// Central lens color per state — reuses existing design tokens only
export const LENS_COLORS: Record<string, string> = {
  idle: "#3b82f6",       // accent token, muted via opacity
  processing: "#3b82f6", // accent token, full opacity
  executing: "#60a5fa",  // info token
  completed: "#3b82f6",  // accent back to neutral
};

// Lens opacity per state
export const LENS_OPACITY: Record<string, number> = {
  idle: 0.5,
  processing: 1.0,
  executing: 1.0,
  completed: 0.65,
};

// Module frame (outer shell) variants
export const frameVariants: Variants = {
  idle: {
    opacity: 0.8,
    transition: { duration: 0.15, ease: EASING_STANDARD },
  },
  processing: {
    opacity: 0.9,
    transition: { duration: 0.3, ease: EASING_PREMIUM },
  },
  executing: {
    opacity: 1.0,
    transition: { duration: 0.2, ease: EASING_PREMIUM },
  },
  completed: {
    opacity: 0.85,
    transition: { duration: 0.4, ease: EASING_STANDARD },
  },
};

// Central lens variants — transient pulse/shift on entry, static hold after
export const lensVariants: Variants = {
  idle: {
    opacity: 0.5,
    scale: 1,
    y: 0,
    fill: "#3b82f6",
    transition: { duration: 0.15, ease: EASING_STANDARD },
  },
  processing: {
    // Single dim→brighten with a subtle ≤2px vertical drift, settles static
    opacity: [0.5, 0.25, 1.0],
    y: [0, -1.5, 0],
    scale: 1,
    fill: "#3b82f6",
    transition: {
      duration: 0.4,
      ease: EASING_PREMIUM,
      times: [0, 0.45, 1],
    },
  },
  executing: {
    opacity: 1.0,
    scale: [1, 1.2, 1],
    y: 0,
    fill: "#60a5fa",
    transition: {
      duration: 0.4,
      ease: EASING_PREMIUM,
      times: [0, 0.5, 1],
    },
  },
  completed: {
    opacity: 0.65,
    scale: 1,
    y: 0,
    fill: "#3b82f6",
    transition: { duration: 0.5, ease: EASING_STANDARD },
  },
};

// Traveling signal line — visible only during `executing` transient
export const signalLineVariants: Variants = {
  idle: {
    opacity: 0,
    x: "-100%",
    transition: { duration: 0 },
  },
  processing: {
    opacity: 0,
    x: "-100%",
    transition: { duration: 0 },
  },
  executing: {
    // Travels from left edge toward center, fades out on arrival
    opacity: [0, 0.85, 0],
    x: ["-45%", "0%", "0%"],
    transition: {
      duration: 0.42,
      ease: EASING_PREMIUM,
      times: [0, 0.65, 1],
    },
  },
  completed: {
    opacity: 0,
    x: "0%",
    transition: { duration: 0.15, ease: EASING_STANDARD },
  },
};

// Confirm shape (checkmark geometry) — visible only during/after `completed` entry
export const confirmVariants: Variants = {
  idle: {
    opacity: 0,
    scale: 0,
    transition: { duration: 0.1 },
  },
  processing: {
    opacity: 0,
    scale: 0,
    transition: { duration: 0.1 },
  },
  executing: {
    opacity: 0,
    scale: 0,
    transition: { duration: 0.1 },
  },
  completed: {
    // Resolves in, briefly holds — stays visible until parent changes state
    opacity: [0, 1, 1],
    scale: [0.4, 1.1, 1.0],
    transition: {
      duration: 0.4,
      ease: EASING_PREMIUM,
      times: [0, 0.6, 1],
    },
  },
};
