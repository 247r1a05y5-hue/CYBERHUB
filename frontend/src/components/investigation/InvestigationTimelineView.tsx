import React, { useState, useEffect } from "react";
import {
  Clock,
  ShieldCheck,
  Search,
  CheckCircle2,
  Lock,
  AlertTriangle,
  FileText,
  Mail,
  ArrowUpDown,
} from "lucide-react";
import { api } from "../../services/api";

interface TimelineEventItem {
  id: string;
  case_id: string;
  event_type: string;
  title: string;
  description: string;
  actor_id: string | null;
  timestamp: string;
  metadata: Record<string, any>;
}

interface TimelineViewProps {
  caseId: string;
}

export const InvestigationTimelineView: React.FC<TimelineViewProps> = ({ caseId }) => {
  const [events, setEvents] = useState<TimelineEventItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isAscending, setIsAscending] = useState(false);

  const fetchTimeline = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/investigations/${caseId}/timeline`);
      if (res.data && res.data.events) {
        setEvents(res.data.events);
      }
    } catch (err) {
      console.error("Failed to fetch timeline:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchTimeline();
    }
  }, [caseId]);

  const sortedEvents = [...events].sort((a, b) => {
    const timeA = new Date(a.timestamp).getTime();
    const timeB = new Date(b.timestamp).getTime();
    return isAscending ? timeA - timeB : timeB - timeA;
  });

  const getEventIcon = (type: string) => {
    switch (type?.toUpperCase()) {
      case "ATTESTATION":
        return <ShieldCheck className="w-3.5 h-3.5 text-[#F5F5F5]" />;
      case "SCAN_STARTED":
      case "SCAN_COMPLETED":
      case "WEB_SEARCH_EXECUTED":
        return <Search className="w-3.5 h-3.5 text-[#F5F5F5]" />;
      case "FINDING_VERIFIED":
        return <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />;
      case "EVIDENCE_CAPTURED":
        return <Lock className="w-3.5 h-3.5 text-[#10B981]" />;
      case "RISK_EVALUATED":
        return <AlertTriangle className="w-3.5 h-3.5 text-[#f59e0b]" />;
      case "REPORT_GENERATED":
        return <FileText className="w-3.5 h-3.5 text-[#F5F5F5]" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-[#777777]" />;
    }
  };

  return (
    <div className="space-y-5 text-left">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg p-4">
        <div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#F5F5F5]" />
            <h2 className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
              Investigation Audit Trail
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#151515] border border-[#232323] text-[#B3B3B3]">
              {events.length} Events
            </span>
          </div>
          <p className="text-xs text-[#777777] mt-0.5">
            Chronological audit log recording every analysis step and evidence action.
          </p>
        </div>

        <button
          onClick={() => setIsAscending(!isAscending)}
          className="px-2.5 py-1.5 bg-[#151515] border border-[#232323] text-xs font-medium text-[#B3B3B3] hover:text-[#F5F5F5] rounded flex items-center gap-1.5 transition-colors"
        >
          <ArrowUpDown className="w-3 h-3" />
          <span>{isAscending ? "Oldest First" : "Newest First"}</span>
        </button>
      </div>

      {/* Events List */}
      {sortedEvents.length > 0 ? (
        <div className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg p-5 space-y-4">
          <div className="relative border-l border-[#232323] ml-3.5 space-y-5 pl-5">
            {sortedEvents.map((evt) => (
              <div key={evt.id} className="relative group">
                {/* Dot */}
                <div className="absolute -left-[27px] top-0.5 w-3.5 h-3.5 rounded-full bg-[#151515] border border-[#2B2B2B] flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#777777]" />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {getEventIcon(evt.event_type)}
                    <span className="text-xs font-semibold text-[#F5F5F5]">{evt.title}</span>
                    <span className="text-[10px] font-mono text-[#777777]">
                      {new Date(evt.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-xs text-[#B3B3B3] leading-relaxed pl-5">
                    {evt.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-8 rounded-lg bg-[#0C0C0C] border border-[#1A1A1A] text-center text-xs text-[#777777]">
          <Clock className="w-6 h-6 mx-auto mb-2 opacity-40 text-[#B3B3B3]" />
          <p className="font-medium text-[#F5F5F5]">No timeline events recorded yet.</p>
        </div>
      )}
    </div>
  );
};
