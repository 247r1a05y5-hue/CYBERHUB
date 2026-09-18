import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Clock, Search, ArrowRight, Shield, Globe, FileImage, RefreshCw } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { api } from "../services/api";

export const RecentSearchesPage: React.FC = () => {
  const navigate = useNavigate();
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSearches = async () => {
      setIsLoading(true);
      try {
        const res = await api.get("/investigations/");
        if (res.data && Array.isArray(res.data)) {
          setInvestigations(res.data);
        }
      } catch {
        // Fallback
      } finally {
        setIsLoading(false);
      }
    };
    fetchSearches();
  }, []);

  return (
    <AppShell>
      <div className="p-6 max-w-6xl mx-auto w-full space-y-6 bg-[#000000] text-[#F5F5F5] min-h-[calc(100vh-3.5rem)]">
        {/* Page Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#1A1A1A]">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#F5F5F5] flex items-center gap-2">
              <Clock className="w-5 h-5 text-[#F5F5F5]" />
              Recent Investigations
            </h1>
            <p className="text-xs text-[#777777] mt-0.5">
              Historical reverse-image scans and visual forensic searches.
            </p>
          </div>

          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#F5F5F5] text-black text-xs font-semibold hover:bg-white transition-all shadow"
          >
            <Search className="w-3.5 h-3.5" />
            New Image Search
          </Link>
        </div>

        {/* Investigation List */}
        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <RefreshCw className="w-6 h-6 text-[#777777] animate-spin" />
          </div>
        ) : investigations.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {investigations.map((inv) => (
              <div
                key={inv.id}
                onClick={() => navigate(`/investigations/image-exposure?caseId=${inv.id}`)}
                className="bg-[#0C0C0C] border border-[#1A1A1A] hover:border-[#2B2B2B] rounded-xl p-4 cursor-pointer transition-all flex flex-col justify-between gap-3 group"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="font-mono text-[10px] text-[#777777]">
                      {inv.case_number || `CASE-${inv.id.substring(0, 6)}`}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[#151515] border border-[#2B2B2B] font-mono text-[10px] text-[#10B981]">
                      {inv.status || "COMPLETED"}
                    </span>
                  </div>

                  <h3 className="text-xs font-bold text-[#F5F5F5] group-hover:text-white line-clamp-1">
                    {inv.title || "Untitled Image Investigation"}
                  </h3>
                  <p className="text-[11px] text-[#777777] mt-1">
                    {inv.created_at ? new Date(inv.created_at).toLocaleString() : "Recent Scan"}
                  </p>
                </div>

                <div className="pt-2 border-t border-[#1A1A1A] flex items-center justify-between text-xs text-[#777777]">
                  <span className="text-[11px] font-mono">
                    {inv.findings_count || 0} findings recorded
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#777777] group-hover:text-[#F5F5F5] group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-16 text-center bg-[#080808] border border-[#1A1A1A] rounded-2xl">
            <Clock className="w-12 h-12 text-[#2B2B2B] mb-3" />
            <h3 className="text-sm font-semibold text-[#F5F5F5]">
              No Recent Searches Yet
            </h3>
            <p className="text-xs text-[#777777] max-w-sm mt-1 mb-4">
              Perform your first reverse-image investigation to preserve search history and forensic discoveries.
            </p>
            <Link
              to="/dashboard"
              className="px-4 py-2 rounded-lg bg-[#151515] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#202020]"
            >
              Start Search
            </Link>
          </div>
        )}
      </div>
    </AppShell>
  );
};
