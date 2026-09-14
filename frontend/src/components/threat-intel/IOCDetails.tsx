import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RiskBadge } from "@/components/investigation/StatusBadges";
import { cn } from "@/lib/utils";

type IndicatorType = "ip" | "domain" | "url" | "hash" | "email" | "image_hash";

interface IOCIndicator {
  type: IndicatorType;
  value: string;
  riskLevel?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  source?: string;
}

interface IndicatorCardProps {
  indicator: IOCIndicator;
  className?: string;
}

const TYPE_LABELS: Record<IndicatorType, string> = {
  ip:         "IP Address",
  domain:     "Domain",
  url:        "URL",
  hash:       "File Hash",
  email:      "Email",
  image_hash: "Image Hash",
};

export const IndicatorCard: React.FC<IndicatorCardProps> = ({ indicator, className }) => (
  <Card className={cn("p-3", className)}>
    <div className="flex items-start justify-between gap-2">
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          {TYPE_LABELS[indicator.type]}
        </p>
        <p className="text-sm font-mono text-foreground break-all">{indicator.value}</p>
        {indicator.source && (
          <p className="text-[10px] text-muted-foreground mt-1">Source: {indicator.source}</p>
        )}
      </div>
      {indicator.riskLevel && (
        <RiskBadge level={indicator.riskLevel} className="shrink-0" />
      )}
    </div>
  </Card>
);

interface ThreatScoreProps {
  score: number;        // 0–100
  label?: string;
  className?: string;
}

/** Threat score gauge — numeric only, no artificial inflation */
export const ThreatScore: React.FC<ThreatScoreProps> = ({ score, label = "Threat Score", className }) => {
  const riskLevel =
    score >= 80 ? "CRITICAL" :
    score >= 60 ? "HIGH" :
    score >= 40 ? "MEDIUM" : "LOW";

  return (
    <div className={cn("flex items-center gap-3 p-3 rounded-md border border-border bg-card", className)}>
      <div className="flex flex-col items-center shrink-0 w-14">
        <span className="text-2xl font-bold tabular-nums text-foreground">{score}</span>
        <span className="text-[10px] text-muted-foreground">/100</span>
      </div>
      <Separator orientation="vertical" className="h-8" />
      <div>
        <p className="text-xs font-medium text-foreground">{label}</p>
        <div className="mt-1">
          <RiskBadge level={riskLevel} />
        </div>
      </div>
    </div>
  );
};

export const IOCDetails: React.FC<{ indicators: IOCIndicator[]; className?: string }> = ({
  indicators,
  className,
}) => {
  if (!indicators.length) {
    return (
      <p className="text-xs text-muted-foreground">No indicators of compromise found for this subject.</p>
    );
  }
  return (
    <div className={cn("space-y-2", className)}>
      {indicators.map((ind, i) => (
        <IndicatorCard key={`${ind.type}-${i}`} indicator={ind} />
      ))}
    </div>
  );
};
