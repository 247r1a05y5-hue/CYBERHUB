import React from "react";
import {
  Boxes,
  Check,
  Code2,
  Cpu,
  FileCheck2,
  FileCode2,
  Layers,
  Puzzle,
  Settings2,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

export const ExtensionPointsSection: React.FC = () => {
  const extensionPoints = [
    {
      title: "1. SecurityAnalyzer Plugin",
      desc: "Subclass SecurityAnalyzer and register by input_type or analyzer_name. No core routing or DB logic required.",
      code: "class CustomAnalyzer(SecurityAnalyzer):\n    name = 'custom_threat'\n    async def analyze(context): ...",
    },
    {
      title: "2. AI ModelRunner Weights",
      desc: "Implement the ModelRunner ABC to load PyTorch, Hugging Face, or Scikit-learn models lazily on demand.",
      code: "class CustomModelRunner(ModelRunner):\n    async def predict(features): ...",
    },
    {
      title: "3. YAML Detection Rulepack",
      desc: "Drop YAML rule files directly into rules/packs/<domain>/ without writing Python evaluation code.",
      code: "rules:\n  - id: THREAT-001\n    conditions: [{ field: 'payload', ... }]",
    },
    {
      title: "4. Configurable Risk Policy",
      desc: "Adjust relative weights between rules, ML models, and threat intel feeds per detection class.",
      code: "RiskPolicy(weights={'rules': 0.4, 'ml_model': 0.4, ...})",
    },
    {
      title: "5. Threat Intel Adapters",
      desc: "Register new internal or commercial threat intelligence feed providers in the central registry.",
      code: "class CustomIntel(ThreatIntelProvider):\n    async def lookup(type, val): ...",
    },
    {
      title: "6. Custom Evidence Visualizers",
      desc: "Add problem-specific frontend finding widgets via a typed component registry map.",
      code: "const FindingView = registry.get(analyzerName);",
    },
  ];

  return (
    <section id="architecture" className="py-20 border-t border-border/40 bg-card/20">
      <div className="max-w-7xl mx-auto px-6 space-y-12">
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-primary">
            MODULAR EXTENSIBILITY CONTRACT
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight">
            Stable Core &bull; Zero-Rewrite Extension Points
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            The foundation is completely domain-agnostic. When the cybersecurity challenge
            is announced, problem-specific logic plugs into these explicit extension points
            without altering identity, databases, or workflows.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {extensionPoints.map((ep, idx) => (
            <div
              key={idx}
              className="glass-panel p-6 rounded-xl border border-border/70 flex flex-col justify-between hover:border-primary/40 transition group"
            >
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Puzzle className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-bold text-foreground font-mono">{ep.title}</h3>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed font-sans">
                  {ep.desc}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-border/40">
                <pre className="p-3 rounded-lg bg-background/80 border border-border/60 text-[11px] font-mono text-muted-foreground overflow-x-auto leading-tight">
                  {ep.code}
                </pre>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
