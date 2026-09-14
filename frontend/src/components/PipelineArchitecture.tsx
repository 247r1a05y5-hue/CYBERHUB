import React from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  FileSearch,
  Fingerprint,
  Layers,
  Radio,
  Scale,
  ShieldAlert,
  Terminal,
} from "lucide-react";

export const PipelineArchitecture: React.FC = () => {
  const steps = [
    {
      num: "01",
      title: "Ingestion & Content Hashing",
      badge: "Idempotency",
      icon: FileSearch,
      desc: "Validates payload, checks SHA-256 for instant deduplication, deposits binary to StorageBackend, and queues async job via Redis RQ.",
      tech: "Pydantic v2 • SHA-256 • Redis RQ",
    },
    {
      num: "02",
      title: "Heuristic & Rule Engine",
      badge: "Signature Match",
      icon: Terminal,
      desc: "Executes YAML-defined rulepacks across extracted tokens, regex patterns, headers, and metadata to identify known exploit patterns.",
      tech: "YAML Rules • Regex Engine",
    },
    {
      num: "03",
      title: "AI Model Runner Abstraction",
      badge: "ML Inference",
      icon: BrainCircuit,
      desc: "Passes feature vectors to an abstract ModelRunner producing probability distributions, anomaly scores, and feature importances.",
      tech: "ModelRunner ABC • Scikit-Learn",
    },
    {
      num: "04",
      title: "Threat Intel Correlation",
      badge: "IoC Sighting",
      icon: Fingerprint,
      desc: "Extracts atomic observables (IPs, domains, hashes, URLs) and checks reputation across registered threat feeds.",
      tech: "ThreatIntelRegistry • IoC Feed",
    },
    {
      num: "05",
      title: "Contextual Risk Fusion",
      badge: "Action Synthesis",
      icon: Scale,
      desc: "Synthesizes multi-source signals using configurable policy weights, applies asset criticality multipliers, and auto-spawns SOC alerts.",
      tech: "RiskEngine • Severity Mapping",
    },
  ];

  return (
    <section id="pipeline" className="py-20 border-t border-border/40">
      <div className="max-w-7xl mx-auto px-6 space-y-12">
        {/* Section Header */}
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-primary">
            THE UNIFIED INGESTION ENGINE
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight">
            5-Stage Automated Analysis Pipeline
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Every submission—regardless of type or domain—flows through a standardized,
            resilient lifecycle that decouples telemetry ingestion from problem-specific intelligence.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 relative">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={step.num}
                className="glass-panel p-5 rounded-xl border border-border/70 flex flex-col justify-between hover:border-primary/50 transition-all duration-300 group relative"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-2xl font-black text-primary/40 group-hover:text-primary transition-colors">
                      {step.num}
                    </span>
                    <span className="text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                      {step.badge}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-primary/10 text-primary w-fit">
                    <Icon className="w-5 h-5" />
                  </div>

                  <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">
                    {step.title}
                  </h3>

                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {step.desc}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-border/40 text-[10px] font-mono text-muted-foreground/80">
                  {step.tech}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
