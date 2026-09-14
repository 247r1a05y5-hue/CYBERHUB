/**
 * ImageExposureOverlay
 *
 * A purely cinematic, CSS-keyframe-driven visualization that floats ON TOP of
 * the existing Earth cinematic video — strictly as a visual landing-page
 * animation.
 *
 * IMPORTANT PRODUCT BOUNDARY:
 * - This is visual storytelling only. No real search results, no real AI outputs.
 * - Labels describe image investigation concepts (REFERENCE IMAGE, MATCH SIGNAL, etc.)
 * - Does NOT claim person identification, face recognition, or biometric tracking.
 *
 * Layer order inside .cinematic-sticky-frame:
 *   video (z: auto)
 *   .cinematic-gradient-top / vignette / bottom (z: 2–3)
 *   → THIS COMPONENT (z: 6)
 *   .cinematic-hero-overlay (z: 12)
 *   .cinematic-timeline-indicator (z: 15)
 *
 * Animation timeline:
 *   0–3s   Earth establishes (no overlay)
 *   3–6s   Reference tile gently appears (bottom-left quadrant)
 *   6–9s   Investigation line from reference → primary card
 *   9–12s  Primary match card materialises (right quadrant)
 *  12–16s  Secondary exposure tiles propagate subtly
 *
 * All animation via CSS keyframes. Zero React state updates per frame.
 * Prefers-reduced-motion: overlay hidden entirely.
 */
import React, { useId } from "react";
import "./imageExposureOverlay.css";

/** Line endpoint data for the SVG investigation lines */
interface LineData {
  id: string;
  x1: string;
  y1: string;
  x2: string;
  y2: string;
  lineClass: string;
  dotClass: string;
}

export const ImageExposureOverlay: React.FC = () => {
  const uid = useId();

  // SVG lines are expressed in % viewport units via a viewBox="0 0 100 100"
  // preserveAspectRatio="none" so they stretch to the container
  const lines: LineData[] = [
    {
      id: `${uid}-a`,
      x1: "22",  y1: "62",   // anchor: reference tile center-right
      x2: "60",  y2: "36",   // anchor: primary card center-left
      lineClass: "iev-line iev-line-a",
      dotClass:  "iev-dot iev-dot-a",
    },
    {
      id: `${uid}-b`,
      x1: "27",  y1: "28",   // anchor: sec tile A center-right
      x2: "60",  y2: "34",   // anchor: primary card top
      lineClass: "iev-line iev-line-b",
      dotClass:  "iev-dot iev-dot-b",
    },
    {
      id: `${uid}-c`,
      x1: "70",  y1: "38",   // anchor: primary card right edge
      x2: "80",  y2: "47",   // anchor: sec tile C center-left
      lineClass: "iev-line iev-line-c",
      dotClass:  "iev-dot iev-dot-c",
    },
  ];

  return (
    <div className="iev-root" aria-hidden="true" role="presentation">

      {/* ── SVG investigation lines ── */}
      <svg
        className="iev-lines-svg"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Subtle animated dash — advances with CSS animation */}
          <filter id={`${uid}-glow`} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="0.4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {lines.map((l) => (
          <g key={l.id} filter={`url(#${uid}-glow)`}>
            <line
              className={l.lineClass}
              x1={l.x1} y1={l.y1}
              x2={l.x2} y2={l.y2}
            />
            <circle
              className={l.dotClass}
              cx={l.x2} cy={l.y2}
              r="0"
            />
          </g>
        ))}
      </svg>

      {/* ── TILE 1 — Reference image (appears at 3s) ── */}
      <div className="iev-tile iev-tile-ref">
        <span className="iev-label-tag">Reference Image</span>
        <div className="iev-divider" />
        <span className="iev-label-sub">Authorized source asset</span>
        <span className="iev-label-sub" style={{ marginTop: 3 }}>
          Initiating scan…
        </span>
        <div className="iev-signal-bar-track" style={{ marginTop: 8 }}>
          <div className="iev-signal-bar-fill" style={{ animationDelay: "6.5s" }} />
        </div>
      </div>

      {/* ── TILE 2 — Primary match card (appears at 9s) ── */}
      <div className="iev-tile iev-tile-primary">
        {/* pulsing ring accent */}
        <div className="iev-glow-ring" />

        <span className="iev-label-tag">
          <span className="iev-status-dot" />
          Image Match
        </span>
        <span className="iev-label-title">Potential Exposure</span>
        <div className="iev-divider" />
        <span className="iev-label-sub">Public domain appearance</span>
        <span className="iev-label-sub" style={{ marginTop: 3 }}>
          Match Signal · Tier 2
        </span>
        <div className="iev-signal-bar-track">
          <div className="iev-signal-bar-fill" />
        </div>
        <div className="iev-verify-chip">Verify →</div>
      </div>

      {/* ── TILE 3 — Secondary exposure A (appears at 12s) ── */}
      <div className="iev-tile iev-tile-sec-a">
        <span className="iev-label-tag">Public Exposure</span>
        <div className="iev-divider" />
        <span className="iev-label-sub">Related image</span>
        <span className="iev-label-sub" style={{ marginTop: 3, opacity: 0.7 }}>
          Signal detected
        </span>
      </div>

      {/* ── TILE 4 — Secondary exposure B (appears at 13s) ── */}
      <div className="iev-tile iev-tile-sec-b">
        <span className="iev-label-tag">Exposure Node</span>
        <div className="iev-divider" />
        <span className="iev-label-sub">Under review</span>
      </div>

      {/* ── TILE 5 — Secondary exposure C (appears at 14.5s) ── */}
      <div className="iev-tile iev-tile-sec-c">
        <span className="iev-label-tag">Related Image</span>
        <div className="iev-divider" />
        <span className="iev-label-sub">Similarity signal</span>
      </div>
    </div>
  );
};
