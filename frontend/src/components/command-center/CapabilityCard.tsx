import React from "react";
import { LucideIcon } from "lucide-react";

interface CapabilityCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  onClick: () => void;
}

export const CapabilityCard: React.FC<CapabilityCardProps> = ({
  title,
  description,
  icon: Icon,
  onClick,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group w-full bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-7 sm:p-8 flex flex-col items-center text-center cursor-pointer transition-all duration-180 hover:border-[var(--border-strong)] hover:shadow-md hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-[var(--border-strong)]"
      style={{
        boxShadow: "var(--card-shadow)",
      }}
    >
      {/* Centered Icon Container */}
      <div className="w-16 h-16 rounded-2xl bg-[var(--icon-box-bg)] border border-[var(--icon-box-border)] flex items-center justify-center transition-transform duration-180 group-hover:scale-105">
        <Icon
          className="w-7 h-7 text-[var(--icon-color)]"
          strokeWidth={1.75}
        />
      </div>

      {/* Card Title */}
      <h3 className="text-[17px] font-semibold text-[var(--text-primary)] mt-5 tracking-tight">
        {title}
      </h3>

      {/* Card Description */}
      <p className="text-[12px] text-[var(--text-secondary)] mt-2 leading-relaxed max-w-[210px] mx-auto">
        {description}
      </p>
    </button>
  );
};
