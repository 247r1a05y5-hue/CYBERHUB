import React from "react";
import {
  CheckCircle2,
  Database,
  FileKey,
  Lock,
  Server,
  Shield,
  ShieldCheck,
} from "lucide-react";

export const LandingCompliance: React.FC = () => {
  const specs = [
    {
      title: "Argon2id Memory-Hard Hashing",
      desc: "All credentials stored using OWASP-recommended Argon2id with random 128-bit salts. Zero plaintext or password hashes ever logged or returned.",
      icon: Lock,
    },
    {
      title: "15-Min Access + 7-Day Rotating Refresh",
      desc: "Short-lived stateless JWTs paired with single-use rotating refresh tokens stored as SHA-256 hashes in database for instant revocation.",
      icon: FileKey,
    },
    {
      title: "Tenant Isolation at Repository Layer",
      desc: "Every database query is strictly scoped by organization_id derived exclusively from JWT tokens—never from user-supplied query or path params.",
      icon: Server,
    },
    {
      title: "Immutable Tamper-Evident Audit Trail",
      desc: "Append-only audit table logging all sensitive actions, status transitions, artifact uploads, and logins with actor attribution and IP stamps.",
      icon: Database,
    },
    {
      title: "Security Headers & Strict Origin CORS",
      desc: "Hardened middleware enforcing X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy, and explicit origin allowlists.",
      icon: ShieldCheck,
    },
    {
      title: "Path Traversal Protected Storage",
      desc: "Local and object storage backends enforce canonical path resolution preventing any arbitrary directory escape or SSRF exploits.",
      icon: Shield,
    },
  ];

  return (
    <section id="compliance" className="py-20 border-t border-border/40">
      <div className="max-w-7xl mx-auto px-6 space-y-12">
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-primary">
            ENTERPRISE DEFENSE-IN-DEPTH
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight">
            Built with Strict Security Rigor
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Enterprise SOC platforms must adhere to uncompromising security standards.
            The platform foundation implements defense-in-depth at every layer.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {specs.map((s, idx) => {
            const Icon = s.icon;
            return (
              <div
                key={idx}
                className="glass-panel p-6 rounded-xl border border-border/70 space-y-3 hover:border-primary/40 transition"
              >
                <div className="p-2.5 rounded-lg bg-primary/10 text-primary w-fit">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-foreground font-mono">{s.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed font-sans">
                  {s.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
