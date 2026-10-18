import { cva } from "class-variance-authority";
import { CheckCircle2, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { OnboardStatus, Severity, ShoreStatus } from "@/api/types";
import { cn } from "@/lib/utils";

const pill = cva("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      low: "bg-severity-low-soft text-severity-low",
      mid: "bg-severity-mid-soft text-severity-mid",
      high: "bg-severity-high-soft text-severity-high",
      NEW: "bg-status-new-soft text-status-new",
      IN_REVIEW: "bg-status-review-soft text-status-review",
      REJECTED: "bg-status-rejected-soft text-status-rejected",
      CLOSED: "bg-status-closed-soft text-status-closed",
      neutral: "bg-muted text-muted-foreground",
      sand: "bg-sand text-sand-foreground",
      ai: "bg-ai text-ai-foreground border border-ai-border",
      success: "bg-severity-low-soft text-severity-low",
      warning: "bg-warning-soft text-warning-foreground",
    },
  },
  defaultVariants: { tone: "neutral" },
});
export type PillTone = NonNullable<Parameters<typeof pill>[0]>["tone"];

export function Pill({ tone, className, children }: { tone?: PillTone; className?: string; children: React.ReactNode }) {
  return <span className={cn(pill({ tone }), className)}>{children}</span>;
}

export const severityTone = (s: Severity): PillTone => (s <= 2 ? "low" : s === 3 ? "mid" : "high");

export function SeverityPill({ value, className }: { value: Severity; className?: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(pill({ tone: severityTone(value) }), "min-w-9 justify-center font-semibold tabular-nums", className)}
      aria-label={`${t("severity.label")} ${value}`}
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {value}
    </span>
  );
}

export function ShoreChip({ value }: { value: ShoreStatus }) {
  const { t } = useTranslation();
  return <Pill tone={value}>{t(`status.${value}`)}</Pill>;
}

export function OnboardChip({ value }: { value: OnboardStatus }) {
  const { t } = useTranslation();
  if (value === "RESOLVED_ON_BOARD")
    return (
      <Pill tone="success">
        <CheckCircle2 className="size-3" aria-hidden />
        {t("onboard.RESOLVED_ON_BOARD")}
      </Pill>
    );
  return <Pill tone={value === "ACTION_IN_PROGRESS" ? "warning" : "neutral"}>{t(`onboard.${value}`)}</Pill>;
}

export function AiBadge({ children }: { children: React.ReactNode }) {
  return (
    <Pill tone="ai">
      <Sparkles className="size-3" aria-hidden />
      {children}
    </Pill>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 animate-fade-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SectionTitle({ children, icon }: { children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      {icon}
      {children}
    </h3>
  );
}
