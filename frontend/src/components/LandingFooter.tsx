import React from "react";
import { Link } from "react-router-dom";
import { Shield } from "lucide-react";

export const LandingFooter: React.FC = () => {
  return (
    <footer className="bg-[var(--bg)] border-t border-[var(--border)] py-12 text-xs text-zinc-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-10">
          {/* Brand Col */}
          <div className="col-span-2 space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded bg-[var(--surface-raised)] border border-[var(--border)] flex items-center justify-center">
                <Shield className="w-3 h-3 text-blue-400" />
              </div>
              <span className="font-semibold text-sm tracking-wide text-zinc-100 font-mono">
                CYBERHUB
              </span>
            </div>
            <p className="text-zinc-400 max-w-sm leading-relaxed text-xs">
              Digital exposure investigation platform. Biometric matching,
              exposure graph correlation, and cryptographic evidence vault.
            </p>
            <div className="flex items-center space-x-2 text-[11px] font-mono text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
              <span>Systems Operational</span>
            </div>
          </div>

          {/* Platform Col */}
          <div className="space-y-2.5">
            <h4 className="text-zinc-200 font-medium tracking-wide text-xs uppercase font-mono">
              Platform
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/dashboard" className="hover:text-zinc-200 transition-colors">
                  Command Center
                </Link>
              </li>
              <li>
                <Link to="/cases/new" className="hover:text-zinc-200 transition-colors">
                  New Investigation
                </Link>
              </li>
              <li>
                <a href="#capabilities" className="hover:text-zinc-200 transition-colors">
                  Capabilities
                </a>
              </li>
            </ul>
          </div>

          {/* Investigation Col */}
          <div className="space-y-2.5">
            <h4 className="text-zinc-200 font-medium tracking-wide text-xs uppercase font-mono">
              Investigation
            </h4>
            <ul className="space-y-2">
              <li>
                <span className="text-zinc-400">Biometric Verification</span>
              </li>
              <li>
                <span className="text-zinc-400">Exposure Discovery</span>
              </li>
              <li>
                <span className="text-zinc-400">Evidence Vault</span>
              </li>
            </ul>
          </div>

          {/* Security & Access */}
          <div className="space-y-2.5">
            <h4 className="text-zinc-200 font-medium tracking-wide text-xs uppercase font-mono">
              Security
            </h4>
            <ul className="space-y-2">
              <li>
                <span className="text-zinc-400">SHA-256 Custody</span>
              </li>
              <li>
                <span className="text-zinc-400">Org-Level Isolation</span>
              </li>
              <li>
                <Link to="/login" className="hover:text-zinc-200 transition-colors">
                  Sign In
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom copyright line */}
        <div className="pt-6 border-t border-[var(--border)] flex flex-col sm:flex-row items-center justify-between gap-4 text-zinc-500 font-mono text-[11px]">
          <div>
            &copy; {new Date().getFullYear()} CYBERHUB. ALL RIGHTS RESERVED.
          </div>
          <div className="flex items-center space-x-4">
            <span className="hover:text-zinc-400 cursor-pointer">PRIVACY</span>
            <span className="hover:text-zinc-400 cursor-pointer">TERMS</span>
            <span className="hover:text-zinc-400 cursor-pointer">SECURITY</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
