import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProviderStatusBadge } from "@/components/investigation/StatusBadges";
import { cn } from "@/lib/utils";

type ProviderStatus = "CONFIGURED" | "NOT_CONFIGURED" | "LIVE" | "ERROR" | "RATE_LIMITED";

interface ThreatIntelResultCardProps {
  providerName: string;
  providerStatus: ProviderStatus;
  lastChecked?: string;
  summary?: string;
  children?: React.ReactNode;
  className?: string;
}

/** Provider-neutral threat intel result card.
 *  Shows actual provider state — never fabricates data. */
export const ThreatIntelResultCard: React.FC<ThreatIntelResultCardProps> = ({
  providerName,
  providerStatus,
  lastChecked,
  summary,
  children,
  className,
}) => {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="pb-3 flex flex-row items-center justify-between gap-2">
        <CardTitle className="text-sm font-semibold">{providerName}</CardTitle>
        <div className="flex items-center gap-2 shrink-0">
          <ProviderStatusBadge status={providerStatus} />
        </div>
      </CardHeader>
      <CardContent>
        {providerStatus === "NOT_CONFIGURED" ? (
          <p className="text-xs text-muted-foreground">
            Provider not configured. Set the corresponding API key in backend environment variables.
          </p>
        ) : providerStatus === "ERROR" ? (
          <p className="text-xs text-red-600 dark:text-red-400">
            Provider returned an error. Check API key validity and rate limits.
          </p>
        ) : (
          <>
            {summary && <p className="text-sm text-muted-foreground mb-3">{summary}</p>}
            {children}
            {lastChecked && (
              <p className="text-[10px] text-muted-foreground/70 mt-3 font-mono">
                Last checked: {lastChecked}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};
