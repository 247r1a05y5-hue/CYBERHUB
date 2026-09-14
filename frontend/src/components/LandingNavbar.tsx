import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export const LandingNavbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 h-14 flex items-center px-6 md:px-10 transition-all"
      style={{
        backgroundColor: scrolled ? "rgba(12,12,14,0.92)" : "transparent",
        borderBottom: scrolled ? "1px solid var(--border)" : "1px solid transparent",
        backdropFilter: scrolled ? "blur(12px)" : "none",
        transitionDuration: "200ms",
        transitionTimingFunction: "cubic-bezier(0.4,0,0.2,1)",
      }}
    >
      {/* Wordmark */}
      <Link
        to="/"
        className="text-[13px] font-semibold tracking-[0.2em] text-[--text-primary] hover:text-white transition-colors flex-1"
        style={{ transitionDuration: "160ms" }}
      >
        CYBERHUB
      </Link>

      {/* Login */}
      <Link
        to="/login"
        className="text-[13px] text-[--text-secondary] hover:text-[--text-primary] transition-colors"
        style={{ transitionDuration: "160ms" }}
      >
        Login
      </Link>
    </header>
  );
};
