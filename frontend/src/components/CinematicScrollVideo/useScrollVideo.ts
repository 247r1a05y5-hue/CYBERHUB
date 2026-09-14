import { useEffect, useRef, useState, useCallback } from "react";

export interface UseScrollVideoOptions {
  smoothingFactor?: number;
  seekThreshold?: number;
  onProgress?: (progress: number) => void;
}

export interface UseScrollVideoReturn {
  containerRef: React.RefObject<HTMLDivElement>;
  videoRef: React.RefObject<HTMLVideoElement>;
  overlayRef: React.RefObject<HTMLDivElement>;
  isLoaded: boolean;
  duration: number;
}

export function useScrollVideo(options: UseScrollVideoOptions = {}): UseScrollVideoReturn {
  const {
    smoothingFactor = 0.1,
    seekThreshold = 0.008,
    onProgress,
  } = options;

  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const [isLoaded, setIsLoaded] = useState(false);
  const [duration, setDuration] = useState(0);

  const targetProgress = useRef(0);
  const currentProgress = useRef(0);
  const durationRef = useRef(0);
  const rafId = useRef<number | null>(null);
  const isSeeking = useRef(false);
  const prefersReducedMotion = useRef(false);

  // Check prefers-reduced-motion
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    prefersReducedMotion.current = mq.matches;

    const handler = (e: MediaQueryListEvent) => {
      prefersReducedMotion.current = e.matches;
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Update target progress from scroll position
  const calculateProgress = useCallback(() => {
    if (!containerRef.current) return 0;
    const rect = containerRef.current.getBoundingClientRect();
    const sectionHeight = rect.height;
    const viewportHeight = window.innerHeight;
    const scrollableDistance = sectionHeight - viewportHeight;

    if (scrollableDistance <= 0) return 0;

    // rect.top is 0 when section enters top of viewport, and becomes negative as user scrolls down
    const scrolled = -rect.top;
    const rawProgress = scrolled / scrollableDistance;
    return Math.max(0, Math.min(1, rawProgress));
  }, []);

  // Handle video metadata loaded
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      const dur = video.duration;
      if (dur && !isNaN(dur) && dur > 0) {
        durationRef.current = dur;
        setDuration(dur);
        setIsLoaded(true);
        // Ensure initial frame at current scroll position
        const initialProgress = calculateProgress();
        targetProgress.current = initialProgress;
        currentProgress.current = initialProgress;
        video.currentTime = initialProgress * dur;
      }
    };

    const handleCanPlay = () => {
      if (!isLoaded && video.duration > 0) {
        handleLoadedMetadata();
      }
    };

    video.addEventListener("loadedmetadata", handleLoadedMetadata);
    video.addEventListener("loadeddata", handleCanPlay);
    video.addEventListener("canplay", handleCanPlay);

    // If metadata was already available before listener attached
    if (video.readyState >= 1 && video.duration > 0) {
      handleLoadedMetadata();
    }

    return () => {
      video.removeEventListener("loadedmetadata", handleLoadedMetadata);
      video.removeEventListener("loadeddata", handleCanPlay);
      video.removeEventListener("canplay", handleCanPlay);
    };
  }, [calculateProgress, isLoaded]);

  // Main animation frame loop for smooth easing and seeking
  useEffect(() => {
    const handleScroll = () => {
      targetProgress.current = calculateProgress();
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleScroll, { passive: true });

    // Initial check
    targetProgress.current = calculateProgress();

    const tick = () => {
      const video = videoRef.current;
      const dur = durationRef.current;

      if (prefersReducedMotion.current) {
        // Under reduced motion, hold at initial frame without scrubbing
        rafId.current = requestAnimationFrame(tick);
        return;
      }

      // Smooth interpolation
      const diff = targetProgress.current - currentProgress.current;
      currentProgress.current += diff * smoothingFactor;

      // Clamp close numbers
      if (Math.abs(diff) < 0.0001) {
        currentProgress.current = targetProgress.current;
      }

      const prog = currentProgress.current;

      // Update overlay styling via CSS variable or transforms for 120fps smoothness without React state churn
      if (containerRef.current) {
        containerRef.current.style.setProperty("--video-progress", prog.toFixed(4));
      }

      if (overlayRef.current) {
        // Stage-based opacity for overlay copy:
        // 0.0 - 0.35: fully visible / crisp hero copy
        // 0.35 - 0.55: smooth fade out as video narrative progresses
        // 0.85 - 1.0: secondary resolution state or prompt
        const opacity = prog < 0.35 ? 1 : Math.max(0, 1 - (prog - 0.35) / 0.2);
        const translateY = prog * -40; // subtle upward drift on scroll
        overlayRef.current.style.opacity = opacity.toString();
        overlayRef.current.style.transform = `translate3d(0, ${translateY}px, 0)`;
      }

      if (onProgress) {
        onProgress(prog);
      }

      // Seek video
      if (video && dur > 0 && !isSeeking.current) {
        const targetTime = Math.max(0, Math.min(dur, prog * dur));
        const timeDiff = Math.abs(video.currentTime - targetTime);

        if (timeDiff > seekThreshold) {
          try {
            // Fast seek without waiting for promise if supported
            if ("fastSeek" in video && typeof (video as any).fastSeek === "function") {
              (video as any).fastSeek(targetTime);
            } else {
              video.currentTime = targetTime;
            }
          } catch {
            // Ignore seek interruptions
          }
        }
      }

      rafId.current = requestAnimationFrame(tick);
    };

    rafId.current = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current);
      }
    };
  }, [calculateProgress, onProgress, seekThreshold, smoothingFactor]);

  return {
    containerRef,
    videoRef,
    overlayRef,
    isLoaded,
    duration,
  };
}
