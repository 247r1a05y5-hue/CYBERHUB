import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Case } from "../../types/case";
import { api } from "../../services/api";

export const ActiveInvestigations: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchCases = async () => {
      try {
        const res = await api.get<Case[]>("/cases");
        if (isMounted) {
          setCases(res.data || []);
        }
      } catch (err) {
        // Silently fail if unauthenticated or network error
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    fetchCases();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="mt-10 lg:mt-12">
      {/* Section Title */}
      <h2 className="text-[17px] font-semibold text-[var(--text-primary)] tracking-tight mb-4">
        Active Investigations
      </h2>

      {/* Grid of 4 Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((n) => (
            <div
              key={n}
              className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 h-28 animate-pulse"
              style={{ boxShadow: "var(--card-shadow)" }}
            />
          ))}
        </div>
      ) : cases.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {cases.slice(0, 4).map((c) => (
            <div
              key={c.id}
              onClick={() => navigate("/investigations")}
              className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 cursor-pointer hover:border-[var(--border-strong)] transition-all flex flex-col justify-between"
              style={{ boxShadow: "var(--card-shadow)" }}
            >
              <div>
                <h3 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight mb-1.5">
                  {c.title}
                </h3>
                <p className="text-[12px] text-[var(--text-secondary)] leading-relaxed line-clamp-2">
                  {c.description || c.target_subject_label || `Case ${c.case_number} • Stage ${c.current_stage || 1}/9`}
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Default Empty State structured identically to the reference lower card row */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div
            onClick={() => navigate("/investigations/image-exposure")}
            className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 cursor-pointer hover:border-[var(--border-strong)] transition-all"
            style={{ boxShadow: "var(--card-shadow)" }}
          >
            <h3 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight mb-1.5">
              Image Exposure
            </h3>
            <p className="text-[12px] text-[var(--text-secondary)] leading-relaxed">
              No active scans in progress. Click to start a new image investigation.
            </p>
          </div>

          <div
            onClick={() => navigate("/investigations")}
            className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 cursor-pointer hover:border-[var(--border-strong)] transition-all"
            style={{ boxShadow: "var(--card-shadow)" }}
          >
            <h3 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight mb-1.5">
              Investigations
            </h3>
            <p className="text-[12px] text-[var(--text-secondary)] leading-relaxed">
              Track open inquiries, cluster telemetry, and case history.
            </p>
          </div>

          <div
            onClick={() => navigate("/evidence")}
            className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 cursor-pointer hover:border-[var(--border-strong)] transition-all"
            style={{ boxShadow: "var(--card-shadow)" }}
          >
            <h3 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight mb-1.5">
              Evidence Vault
            </h3>
            <p className="text-[12px] text-[var(--text-secondary)] leading-relaxed">
              Chain-of-custody captures and verified forensic artifacts.
            </p>
          </div>

          <div
            onClick={() => navigate("/reports")}
            className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 cursor-pointer hover:border-[var(--border-strong)] transition-all"
            style={{ boxShadow: "var(--card-shadow)" }}
          >
            <h3 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight mb-1.5">
              Reports
            </h3>
            <p className="text-[12px] text-[var(--text-secondary)] leading-relaxed">
              Compliance summaries and intelligence export dossiers.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
