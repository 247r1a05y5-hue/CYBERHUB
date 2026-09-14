import React from "react";
import { motion } from "framer-motion";
import { 
  Lock, 
  Building2, 
  ScrollText, 
  ShieldCheck, 
  Cpu, 
  Network, 
  ServerCrash, 
  Radio 
} from "lucide-react";

export const SecurityEnterpriseGrid: React.FC = () => {
  const specs = [
    {
      icon: Lock,
      title: "Role-Based Access Control",
      description:
        "Strict permission boundaries across Admin, Analyst, and ReadOnly roles enforced at the API route layer.",
    },
    {
      icon: Building2,
      title: "Organization Isolation",
      description:
        "Multi-tenant separation across all database repositories, analyzer queues, and stored evidence artifacts.",
    },
    {
      icon: ScrollText,
      title: "Immutable Audit Logging",
      description:
        "Tamper-evident chronological recording for every state mutation, user login, and rule modification.",
    },
    {
      icon: ShieldCheck,
      title: "Secure Payload Ingestion",
      description:
        "Memory-safe file validation with strict size limits, MIME verification, and SHA-256 integrity checks.",
    },
    {
      icon: Cpu,
      title: "Explainable Risk Scoring",
      description:
        "Deterministic 0–100 risk formula breaking down model confidence, rule hits, and threat intelligence.",
    },
    {
      icon: Network,
      title: "Controlled Integrations",
      description:
        "Pluggable analyzer contract allowing secure addition of custom models and third-party threat feeds.",
    },
    {
      icon: ServerCrash,
      title: "Resilient Pipeline Execution",
      description:
        "Asynchronous task queues with configurable timeouts, retries, and decoupled worker pools.",
    },
    {
      icon: Radio,
      title: "Real-Time Telemetry Streaming",
      description:
        "Server-Sent Events (SSE) providing sub-second dashboard updates without aggressive polling.",
    },
  ];

  return (
    <section id="security" className="py-20 bg-[#080c14] border-t border-[#1e293b]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="max-w-3xl mb-14">
          <div className="text-xs font-mono uppercase tracking-wider text-blue-400 font-semibold mb-2">
            SECURITY & ENTERPRISE ARCHITECTURE
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-4">
            Engineered for enterprise trust and auditability.
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            Built from the ground up on verifiable architectural principles,
            cryptographic integrity, and deterministic execution.
          </p>
        </div>

        {/* 8 Factual Specification Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {specs.map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{
                  delay: index * 0.04,
                  duration: 0.4,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="rounded-lg bg-[#0f172a] border border-[#1e293b] p-5 flex flex-col justify-between"
              >
                <div>
                  <div className="w-8 h-8 rounded bg-[#0b0f19] border border-[#1e293b] flex items-center justify-center text-blue-400 mb-3.5">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-bold text-white mb-1.5">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
