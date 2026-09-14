import React, { useEffect, useRef } from "react";

/**
 * TelemetryField — ambient animated canvas background with falling telemetry "packets".
 * Renders behind the Hero section as a subtle depth layer.
 */
export const TelemetryField: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const PARTICLE_COUNT = 40;

    interface Particle {
      x: number;
      y: number;
      speed: number;
      opacity: number;
      size: number;
      label: string;
    }

    const LABELS = [
      "0xA3F1", "INGRESS", "PKT::9B", "SYN", "RST", "ACK",
      "0xFF00", "SCAN", "PROBE", "TRACE", "0x4E2A", "ALERT",
    ];

    const particles: Particle[] = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      speed: 0.3 + Math.random() * 0.6,
      opacity: 0.04 + Math.random() * 0.1,
      size: 8 + Math.random() * 3,
      label: LABELS[Math.floor(Math.random() * LABELS.length)],
    }));

    const tick = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (const p of particles) {
        ctx.save();
        ctx.globalAlpha = p.opacity;
        ctx.fillStyle = "#60a5fa"; // blue-400
        ctx.font = `${p.size}px 'Courier New', monospace`;
        ctx.fillText(p.label, p.x, p.y);
        ctx.restore();

        p.y += p.speed;
        if (p.y > canvas.height + 20) {
          p.y = -20;
          p.x = Math.random() * canvas.width;
          p.label = LABELS[Math.floor(Math.random() * LABELS.length)];
        }
      }

      animationId = requestAnimationFrame(tick);
    };

    tick();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none opacity-60"
      aria-hidden="true"
      style={{ zIndex: -1 }}
    />
  );
};
