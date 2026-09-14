import React from "react";
import { useNavigate } from "react-router-dom";
import { Terminal } from "lucide-react";
import { useScrollVideo } from "./useScrollVideo";
import { ImageExposureOverlay } from "../ImageExposureOverlay";
import "./cinematicScrollVideo.css";

export interface CinematicScrollVideoProps {
  videoSrc?: string;
  onExploreClick?: () => void;
}

export const CinematicScrollVideo: React.FC<CinematicScrollVideoProps> = ({
  videoSrc = "/assets/cyberhub-hero.mp4",
  onExploreClick,
}) => {
  const navigate = useNavigate();
  const { containerRef, videoRef, overlayRef, isLoaded, duration } = useScrollVideo({
    smoothingFactor: 0.1,
    seekThreshold: 0.008,
  });

  const handleExplore = () => {
    if (onExploreClick) {
      onExploreClick();
    } else {
      const el = document.getElementById("platform");
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  return (
    <section ref={containerRef} className="cinematic-scroll-section" id="hero">
      {/* Pinned 100vh Sticky Viewport Frame */}
      <div className="cinematic-sticky-frame">
        {/* Loading Fallback */}
        {!isLoaded && (
          <div className="cinematic-fallback-bg">
            <div className="flex flex-col items-center space-y-3 text-slate-500 font-mono text-xs">
              <div className="w-8 h-8 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
              <span>INITIALIZING SECURE VIDEO STREAM...</span>
            </div>
          </div>
        )}

        {/* Video Element — Unmodified Single Source of Truth */}
        <video
          ref={videoRef}
          src={videoSrc}
          muted
          playsInline
          preload="auto"
          className={`cinematic-video ${!isLoaded ? "is-loading" : ""}`}
          aria-label="CyberHub Cinematic Video Experience"
        />

        {/* Non-destructive ambient lighting gradients */}
        <div className="cinematic-gradient-top" />
        <div className="cinematic-ambient-vignette" />
        <div className="cinematic-gradient-bottom" />

        {/* Image Exposure cinematic visualization — z:6, above gradients, below hero copy */}
        <ImageExposureOverlay />

        {/* Hero Copy Overlay — Pure DOM layer, decoupled from video */}
        <div ref={overlayRef} className="cinematic-hero-overlay">
          <div className="max-w-3xl mx-auto text-center">
            {/* Headline */}
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight text-white leading-[1.05] mb-6 uppercase">
              Digital Exposure
              <br />
              Investigation
            </h1>

            {/* Subtext */}
            <p
              className="text-base sm:text-lg text-slate-300 max-w-xl mx-auto leading-relaxed mb-10"
              style={{ fontWeight: 400 }}
            >
              Understand where your digital presence appears across public sources.
            </p>

            {/* Single CTA */}
            <button
              onClick={() => navigate("/login")}
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded text-[14px] font-medium text-white transition-all"
              style={{
                backgroundColor: "var(--accent)",
                border: "1px solid rgba(59,130,246,0.4)",
                transitionDuration: "160ms",
              }}
            >
              Start Investigation
            </button>
          </div>
        </div>

        {/* Interactive Scrub Timeline Indicator */}
        <div className="cinematic-timeline-indicator">
          <div className="cinematic-progress-track">
            <div className="cinematic-progress-bar" />
          </div>
          <div className="flex items-center space-x-2 text-[10px] font-mono text-slate-400/80 uppercase tracking-widest">
            <Terminal className="w-3 h-3 text-blue-400/80" />
            <span>Scroll to Scrub Timeline</span>
          </div>
        </div>
      </div>
    </section>
  );
};
