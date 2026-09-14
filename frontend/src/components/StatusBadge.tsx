import React from "react";

type Status = "active" | "pending" | "resolved" | "closed" | "open" | string;

const COLORS: Record<string, string> = {
  active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  open: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  resolved: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  closed: "bg-zinc-600/20 text-zinc-500 border-zinc-600/30",
};

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = "" }) => {
  const color = COLORS[status] ?? "bg-slate-500/20 text-slate-400 border-slate-500/30";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-mono font-semibold uppercase tracking-wider ${color} ${className}`}
    >
      {status}
    </span>
  );
};
