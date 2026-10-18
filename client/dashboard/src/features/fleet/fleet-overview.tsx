import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { format, parseISO } from "date-fns";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Clock, Inbox, Info, Minus, Sparkles, TrendingUp, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis, Legend } from "recharts";
import { useFleetOverview, useHazardClusters } from "@/hooks/use-content";
import { canShowWellbeing } from "@/lib/rules";
import { pct } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { PageHeader, SeverityPill } from "@/components/beacon/chips";
import type { Severity } from "@/api/types";
import { Button } from "@/components/ui/button";

const axis = { fontSize: 11, fill: "var(--color-muted-foreground)" };
const tooltipStyle = { borderRadius: 12, border: "1px solid var(--color-border)", boxShadow: "var(--shadow-soft)", fontSize: 12 };

function Kpi({ icon: Icon, label, value, children }: { icon: typeof Inbox; label: string; value: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="surface-card p-5 animate-fade-up">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <span className="grid size-7 place-items-center rounded-lg bg-primary-soft text-primary"><Icon className="size-3.5" aria-hidden /></span>
        {label}
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight tabular-nums">{value}</div>
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}

const Trend = ({ dir, goodWhenUp }: { dir: "up" | "down" | "flat"; goodWhenUp: boolean }) => {
  const Icon = dir === "up" ? ArrowUpRight : dir === "down" ? ArrowDownRight : Minus;
  const good = dir === "flat" ? null : (dir === "up") === goodWhenUp;
  return <Icon className={good === null ? "size-4 text-muted-foreground" : good ? "size-4 text-severity-low" : "size-4 text-severity-high"} aria-label={dir} />;
};

export function FleetOverviewView() {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch } = useFleetOverview();
  const { data: clusters } = useHazardClusters();

  if (isError) return <div role="alert" className="space-y-3 py-10 text-center">
    <p className="text-muted-foreground">{t("common.error")}</p>
    <Button variant="outline" onClick={() => refetch()}>{t("common.retry")}</Button>
  </div>;
  if (isLoading || !data)
    return (
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-2xl" />)}
      </div>
    );

  const openTotal = Object.values(data.open_by_severity).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      <PageHeader title={t("fleet.title")} subtitle={t("fleet.subtitle")} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Kpi icon={Inbox} label={t("fleet.open")} value={openTotal}>
          <div className="flex flex-wrap gap-1">
            {([5, 4, 3, 2, 1] as Severity[]).filter((s) => data.open_by_severity[s] > 0).map((s) => (
              <span key={s} className="inline-flex items-center gap-1 text-xs text-muted-foreground"><SeverityPill value={s} />×{data.open_by_severity[s]}</span>
            ))}
          </div>
        </Kpi>
        <Kpi icon={TrendingUp} label={t("fleet.new24")} value={data.new_last_24h} />
        <Kpi icon={Clock} label={t("fleet.median")} value={t("fleet.hours", { n: data.median_accept_hours })} />
        <Kpi icon={Users} label={t("fleet.ackRate")} value={pct(data.learning_ack_rate)}>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-seaglass" style={{ width: pct(data.learning_ack_rate) }} /></div>
        </Kpi>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <div className="surface-card p-5">
          <h2 className="mb-4 text-sm font-semibold">{t("fleet.perVessel")}</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.per_vessel} barSize={28}>
              <CartesianGrid vertical={false} stroke="var(--color-border)" />
              <XAxis dataKey="vessel" tick={axis} axisLine={false} tickLine={false} />
              <YAxis tick={axis} axisLine={false} tickLine={false} allowDecimals={false} width={24} />
              <RTooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--color-muted)" }} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="s1" stackId="a" name="S1" fill="var(--color-severity-low)" fillOpacity={0.6} />
              <Bar dataKey="s2" stackId="a" name="S2" fill="var(--color-severity-low)" />
              <Bar dataKey="s3" stackId="a" name="S3" fill="var(--color-chart-2)" />
              <Bar dataKey="s4" stackId="a" name="S4" fill="var(--color-chart-3)" />
              <Bar dataKey="s5" stackId="a" name="S5" fill="var(--color-severity-high)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="surface-card p-5">
          <h2 className="mb-4 text-sm font-semibold">{t("fleet.topHazards")}</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.top_hazards.map((h) => ({ ...h, name: t(`hazard.${h.hazard_type}`) }))} layout="vertical" barSize={16}>
              <XAxis type="number" hide allowDecimals={false} />
              <YAxis type="category" dataKey="name" tick={axis} axisLine={false} tickLine={false} width={120} />
              <RTooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--color-muted)" }} />
              <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="surface-card p-5">
        <h2 className="mb-4 text-sm font-semibold">{t("fleet.trend")}</h2>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data.trend}>
            <CartesianGrid vertical={false} stroke="var(--color-border)" />
            <XAxis dataKey="date" tick={axis} axisLine={false} tickLine={false} tickFormatter={(d) => format(parseISO(d), "d MMM")} interval={4} />
            <YAxis tick={axis} axisLine={false} tickLine={false} width={28} />
            <RTooltip contentStyle={tooltipStyle} labelFormatter={(d) => format(parseISO(String(d)), "d MMM yyyy")} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="reports" name={t("fleet.reports")} stroke="var(--color-primary)" strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="checkins" name={t("fleet.checkins")} stroke="var(--color-seaglass)" strokeWidth={2} dot={false} strokeDasharray="4 4" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Sparkles className="size-4 text-ai-foreground" aria-hidden />{t("fleet.clusters")}</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {clusters?.map((c) => (
            <div key={c.id} className="ai-panel p-5">
              <div className="text-base font-semibold">{c.label}</div>
              <div className="mt-1 text-sm text-muted-foreground">{t("fleet.clusterMeta", { v: c.vessel_count, t: c.ticket_count })}</div>
              <Link to="/tickets" search={{ status: "ALL", hazard: [c.hazard_type], q: c.q || undefined }} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
                {t("fleet.viewTickets")} <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          {t("fleet.wellbeing")}
          <Tooltip>
            <TooltipTrigger aria-label={t("fleet.kRule")}><Info className="size-3.5 text-muted-foreground" /></TooltipTrigger>
            <TooltipContent className="max-w-xs">{t("fleet.kRule")}</TooltipContent>
          </Tooltip>
        </h2>
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {data.wellbeing.map((w) => (
            <div key={w.vessel_id} className="surface-card p-4">
              <div className="truncate text-sm font-medium">{w.vessel}</div>
              <div className="mb-3 text-[11px] text-muted-foreground">{t("fleet.nCheckins", { n: w.n })}</div>
              {canShowWellbeing(w.n) && w.mood !== null && w.fatigue !== null ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{t("fleet.mood")}</span>
                    <span className="flex items-center gap-1 font-semibold tabular-nums">{w.mood}<Trend dir={w.mood_trend} goodWhenUp /></span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{t("fleet.fatigue")}</span>
                    <span className="flex items-center gap-1 font-semibold tabular-nums">{w.fatigue}<Trend dir={w.fatigue_trend} goodWhenUp={false} /></span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">{t("fleet.notEnough")}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
