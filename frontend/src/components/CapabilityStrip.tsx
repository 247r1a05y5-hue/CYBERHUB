import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { 
  Cpu, 
  Binary, 
  Radar, 
  Activity, 
  Search, 
  ShieldCheck 
} from "lucide-react";

export const CapabilityStrip: React.FC = () => {
  const prefersReduced = useReducedMotion();

  const capabilities = [
    { label: "Biometric Matching", icon: Cpu },
    { label: "Exposure Discovery", icon: Search },
    { label: "Relationship Graph", icon: Binary },
    { label: "Forensic Evidence", icon: ShieldCheck },
    { label: "Risk Assessment", icon: Activity },
    { label: "Continuous Monitor", icon: Radar },
  ];

  return (
    <section id="capabilities" className="py-5 border-y border-[var(--border)] bg-[var(--surface)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 lg:gap-0 lg:divide-x lg:divide-[var(--border)]">
          {capabilities.map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: prefersReduced ? 0 : 6 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-20px" }}
                transition={{
                  delay: prefersReduced ? 0 : index * 0.03,
                  duration: 0.25,
                  ease: [0.4, 0, 0.2, 1],
                }}
                className="flex items-center justify-center space-x-2.5 px-3 py-1.5 text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <Icon className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                <span className="text-xs font-medium tracking-wide whitespace-nowrap">
                  {item.label}
                </span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
