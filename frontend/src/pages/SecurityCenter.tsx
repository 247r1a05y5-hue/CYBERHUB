import React from "react";
import { AppShell as LegacyAppShell } from "@/components/shell/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, AlertCircle, XCircle, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

type ControlStatus = "PASS" | "PARTIAL" | "NOT_IMPLEMENTED";

interface SecurityControl {
  id: string;
  name: string;
  description: string;
  category: string;
  status: ControlStatus;
  notes?: string;
}

const CONTROLS: SecurityControl[] = [
  {
    id: "auth",
    name: "Authentication",
    description: "JWT-based login with token storage and rotation.",
    category: "Identity",
    status: "PASS",
    notes: "Email + password login via /api/v1/auth/token. Token stored in localStorage.",
  },
  {
    id: "authz",
    name: "Authorization",
    description: "Role-based access control enforced on protected API routes.",
    category: "Identity",
    status: "PARTIAL",
    notes: "Backend protects endpoints via JWT dependency. Frontend route-guards present. Role-scoped actions not yet enforced UI-side.",
  },
  {
    id: "tenant-isolation",
    name: "Tenant Isolation",
    description: "Each investigation is scoped to the authenticated user/org context.",
    category: "Data",
    status: "PARTIAL",
    notes: "Case rows include user_id. Full org-level multi-tenancy is scaffolded but not enforced in all queries.",
  },
  {
    id: "ssrf",
    name: "SSRF Protection",
    description: "Server-side requests to external URLs are validated.",
    category: "Input Validation",
    status: "PASS",
    notes: "Temporary image service validates URL schemes before forwarding to SearchAPI.",
  },
  {
    id: "secure-upload",
    name: "Secure Image Upload",
    description: "Uploaded files are type-validated, size-limited, and handled server-side.",
    category: "Input Validation",
    status: "PASS",
    notes: "MIME type and magic-bytes validation in reference image service. Max size enforced.",
  },
  {
    id: "rate-limiting",
    name: "Rate Limiting",
    description: "API endpoints protected from abuse via rate limits.",
    category: "Availability",
    status: "PARTIAL",
    notes: "SearchAPI calls rate-limited per investigation. Global API rate limiting not yet deployed.",
  },
  {
    id: "audit-logging",
    name: "Audit Logging",
    description: "Forensic event log for all significant investigation actions.",
    category: "Logging",
    status: "PASS",
    notes: "InvestigationEvent model records all phase transitions, verification actions, and evidence captures.",
  },
  {
    id: "input-validation",
    name: "Input Validation",
    description: "All API inputs are validated with Pydantic schemas.",
    category: "Input Validation",
    status: "PASS",
    notes: "FastAPI + Pydantic enforced on all request bodies and query params.",
  },
  {
    id: "secrets",
    name: "Secrets Management",
    description: "API keys and credentials stored in environment variables, never in source.",
    category: "Configuration",
    status: "PASS",
    notes: "SEARCHAPI_API_KEY, DATABASE_URL, JWT_SECRET_KEY loaded from .env. Not committed.",
  },
  {
    id: "security-headers",
    name: "Security Headers",
    description: "HTTP security headers (CSP, HSTS, X-Frame-Options, etc.) on all responses.",
    category: "Transport",
    status: "NOT_IMPLEMENTED",
    notes: "No security header middleware configured yet on the FastAPI backend.",
  },
];

const STATUS_CONFIG: Record<ControlStatus, {
  label: string;
  icon: React.ElementType;
  badgeClass: string;
}> = {
  PASS:            { label: "Pass",            icon: CheckCircle2, badgeClass: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20" },
  PARTIAL:         { label: "Partial",         icon: AlertCircle,  badgeClass: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20" },
  NOT_IMPLEMENTED: { label: "Not Implemented", icon: XCircle,      badgeClass: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20" },
};

const ControlRow: React.FC<{ control: SecurityControl }> = ({ control }) => {
  const config = STATUS_CONFIG[control.status];
  const Icon = config.icon;
  return (
    <div className="flex items-start gap-4 py-4">
      <div className="w-6 shrink-0 mt-0.5">
        <Icon
          className={cn(
            "w-4 h-4",
            control.status === "PASS" ? "text-emerald-600 dark:text-emerald-400" :
            control.status === "PARTIAL" ? "text-amber-600 dark:text-amber-400" :
            "text-zinc-500"
          )}
          aria-hidden="true"
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-medium text-foreground">{control.name}</p>
          <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0 shrink-0", config.badgeClass)}>
            {config.label}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">{control.description}</p>
        {control.notes && (
          <p className="text-[11px] text-muted-foreground/70 mt-1 leading-relaxed font-mono">
            {control.notes}
          </p>
        )}
      </div>
      <Badge variant="secondary" className="text-[10px] shrink-0 hidden sm:inline-flex">
        {control.category}
      </Badge>
    </div>
  );
};

export const SecurityCenter: React.FC = () => {
  const categories = Array.from(new Set(CONTROLS.map((c) => c.category)));
  const passCount = CONTROLS.filter((c) => c.status === "PASS").length;
  const partialCount = CONTROLS.filter((c) => c.status === "PARTIAL").length;
  const notImplCount = CONTROLS.filter((c) => c.status === "NOT_IMPLEMENTED").length;

  return (
    <LegacyAppShell>
      <div className="max-w-3xl mx-auto py-2">
        <PageHeader
          title="Security Center"
          subtitle="Honest inventory of implemented security controls. PASS only where verified."
          badge={<Shield className="w-4 h-4 text-muted-foreground" />}
        />

        {/* Summary */}
        <div className="grid grid-cols-3 gap-3 mt-6">
          {[
            { label: "Pass", value: passCount, cls: "text-emerald-600 dark:text-emerald-400" },
            { label: "Partial", value: partialCount, cls: "text-amber-600 dark:text-amber-400" },
            { label: "Not Implemented", value: notImplCount, cls: "text-zinc-500" },
          ].map((s) => (
            <Card key={s.label} className="text-center py-4">
              <p className={cn("text-2xl font-bold tabular-nums", s.cls)}>{s.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>

        {/* Controls by category */}
        <div className="mt-8 space-y-6">
          {categories.map((cat) => {
            const catControls = CONTROLS.filter((c) => c.category === cat);
            return (
              <Card key={cat}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                    {cat}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  {catControls.map((control, i) => (
                    <React.Fragment key={control.id}>
                      {i > 0 && <Separator />}
                      <ControlRow control={control} />
                    </React.Fragment>
                  ))}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </LegacyAppShell>
  );
};
