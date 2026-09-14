import React from "react";
import { LandingNavbar } from "../components/LandingNavbar";
import { CinematicScrollVideo } from "../components/CinematicScrollVideo";
import { CapabilityStrip } from "../components/CapabilityStrip";
import { PlatformFeatures } from "../components/PlatformFeatures";
import { ProductStorytelling } from "../components/ProductStorytelling";
import { IntelligenceArchitecture } from "../components/IntelligenceArchitecture";
import { InvestigationShowcase } from "../components/InvestigationShowcase";
import { SecurityEnterpriseGrid } from "../components/SecurityEnterpriseGrid";
import { LandingFinalCTA } from "../components/LandingFinalCTA";
import { LandingFooter } from "../components/LandingFooter";

export const Landing: React.FC = () => {
  return (
    <div className="min-h-screen bg-[var(--bg,#0c0c0e)] text-[var(--text-primary,#f4f4f5)] flex flex-col selection:bg-blue-500/20 selection:text-white">
      {/* 1. Elevated Navigation Header */}
      <LandingNavbar />

      {/* 2. Main Page Presentation Sections */}
      <main className="flex-1">
        {/* Section 1: Scroll-Controlled Cinematic Video Hero */}
        <CinematicScrollVideo />

        {/* Section 2: Trust / Capability Strip */}
        <CapabilityStrip />

        {/* Section 3: Platform Features */}
        <PlatformFeatures />

        {/* Section 4: Product-First Storytelling */}
        <ProductStorytelling />

        {/* Section 5: Intelligence Architecture */}
        <IntelligenceArchitecture />

        {/* Section 6: Investigation Showcase */}
        <InvestigationShowcase />

        {/* Section 7: Security & Enterprise Specs Grid */}
        <SecurityEnterpriseGrid />

        {/* Section 8: Final Call to Action */}
        <LandingFinalCTA />
      </main>

      {/* Section 9: Footer */}
      <LandingFooter />
    </div>
  );
};
