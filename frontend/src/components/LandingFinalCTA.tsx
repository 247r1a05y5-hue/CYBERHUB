import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Shield } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

export const LandingFinalCTA: React.FC = () => {
  const navigate = useNavigate();

  return (
    <section className="py-20 bg-[var(--surface)] border-t border-[var(--border)] relative overflow-hidden">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          className="space-y-5"
        >
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--surface-raised)] text-zinc-300 text-xs font-mono">
            <Shield className="w-3 h-3 text-blue-400" />
            <span>ENTERPRISE DIGITAL EXPOSURE INVESTIGATION</span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--text-primary)] leading-tight">
            Know exactly where your identity appears.
          </h2>

          <p className="text-sm text-zinc-400 max-w-xl mx-auto leading-relaxed">
            Run an end-to-end investigation with biometric verification, exposure discovery,
            forensic evidence preservation, and takedown reporting.
          </p>

          <div className="pt-2 flex justify-center">
            <Button
              size="lg"
              onClick={() => navigate("/dashboard")}
              className="gap-2"
            >
              Start Investigation
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
