import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { severityTone } from "@/lib/rules";
import { ONBOARD, SEVERITY, SHORE } from "@/lib/labels";
import type { OnboardStatus, ShoreStatus } from "@/api/types";
import { Skeleton } from "@/components/ui/skeleton";

const sevCls = { low: "bg-sev-low/15 text-sev-low", mid: "bg-sev-mid/20 text-warn", high: "bg-sev-high/15 text-sev-high" };
const sevDot = { low: "bg-sev-low", mid: "bg-sev-mid", high: "bg-sev-high" };

export function SeverityPill({ s, withLabel = true }: { s: number; withLabel?: boolean }) {
  const t = severityTone(s);
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold", sevCls[t])}>
      <span className={cn("size-1.5 rounded-full", sevDot[t])} />
      {s}{withLabel && ` · ${SEVERITY[s]}`}
    </span>
  );
}
export const severityBar = (s: number) => sevDot[severityTone(s)];

export function Chip({ children, tone = "neutral", className }: { children: ReactNode; tone?: "neutral" | "primary" | "sea" | "warn" | "sand"; className?: string }) {
  const tones = {
    neutral: "bg-muted text-muted-foreground", primary: "bg-primary-soft text-primary", sea: "bg-secondary-soft text-secondary",
    warn: "bg-warn-soft text-warn", sand: "bg-accent text-accent-foreground",
  };
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone], className)}>{children}</span>;
}

export function OnboardChip({ s }: { s: OnboardStatus }) {
  const tone = s === "RESOLVED_ON_BOARD" ? "sea" : s === "SUBMITTED" ? "primary" : "neutral";
  return <Chip tone={tone}>On board · {ONBOARD[s]}</Chip>;
}
export function ShoreChip({ s }: { s: ShoreStatus }) {
  const tone = s === "CLOSED" ? "sea" : s === "REJECTED" ? "sand" : s === "QUEUED" ? "warn" : "neutral";
  return <Chip tone={tone}>Shore · {SHORE[s]}</Chip>;
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <header className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {action}
    </header>
  );
}

export function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export const ListSkeleton = ({ n = 3 }: { n?: number }) => (
  <div className="space-y-3">{Array.from({ length: n }, (_, i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}</div>
);

export function Empty({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed p-8 text-center text-sm text-muted-foreground">
      {icon}
      {text}
    </div>
  );
}
