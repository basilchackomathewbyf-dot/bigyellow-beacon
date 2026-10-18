import { createFileRoute } from "@tanstack/react-router";
import { Anchor, Globe2, Loader2, RefreshCw, Target } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { useBrief, useRegenerateBrief } from "@/hooks/queries";
import { PageHeader, SeverityPill, Chip } from "@/components/beacon/bits";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/_app/master/brief")({
  head: () => ({ meta: [{ title: "Morning brief — Beacon" }, { name: "description", content: "One page to start the day on board." }, { property: "og:title", content: "Morning brief — Beacon" }, { property: "og:description", content: "The Master's morning brief." }] }),
  component: Brief,
});

function Brief() {
  const q = useBrief();
  const regen = useRegenerateBrief();
  const b = q.data;
  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Morning brief" subtitle={b ? new Date(b.generated_at).toLocaleString([], { weekday: "long", hour: "2-digit", minute: "2-digit" }) : undefined}
        action={<Button variant="secondary" className="rounded-xl" onClick={() => regen.mutate()} disabled={regen.isPending}>{regen.isPending ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}Regenerate</Button>} />
      {!b ? <Skeleton className="h-[32rem] rounded-3xl" /> : (
        <article className="surface divide-y overflow-hidden p-0">
          <div className="bg-primary-soft p-6"><p className="text-xl font-semibold leading-snug tracking-tight text-foreground">{b.headline}</p></div>
          <div className="flex items-start gap-3 p-5">
            <Chip tone={b.rest_hours_risk.level === "high" ? "sand" : b.rest_hours_risk.level === "medium" ? "warn" : "sea"} className="capitalize">Rest-hours risk · {b.rest_hours_risk.level}</Chip>
            <p className="text-sm text-muted-foreground">{b.rest_hours_risk.note}</p>
          </div>
          <div className="p-5">
            <p className="mb-2 text-sm font-semibold">Crew mood trend</p>
            {b.mood_trend ? (
              <>
                <div className="h-28"><ResponsiveContainer><AreaChart data={b.mood_trend.points} margin={{ left: -28, right: 4 }}>
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }} tickLine={false} axisLine={false} />
                  <YAxis domain={[1, 5]} hide />
                  <Area dataKey="mood" stroke="var(--color-secondary)" fill="var(--color-secondary-soft)" strokeWidth={2} />
                </AreaChart></ResponsiveContainer></div>
                <p className="text-xs text-muted-foreground">Ship average from {b.mood_trend.n} check-ins. Individual answers are never shown.</p>
              </>
            ) : <p className="text-sm text-muted-foreground">Not enough check-ins to show.</p>}
          </div>
          <div className="space-y-2 p-5">
            <p className="text-sm font-semibold">Open hazards</p>
            {b.open_hazards.map((h) => <div key={h.ticket_no} className="flex items-center gap-3 text-sm"><SeverityPill s={h.severity} withLabel={false} /><span className="flex-1">{h.title}</span><span className="font-mono text-xs text-muted-foreground">{h.ticket_no}</span></div>)}
          </div>
          <div className="flex gap-3 p-5"><Target className="size-5 shrink-0 text-primary" /><div><p className="text-sm font-semibold">Recommended action</p><p className="text-sm text-muted-foreground">{b.recommended_action}</p></div></div>
          <div className="flex gap-3 bg-muted/40 p-5"><Globe2 className="size-5 shrink-0 text-muted-foreground" /><p className="text-sm text-muted-foreground">{b.fleet_context}</p></div>
        </article>
      )}
      <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-muted-foreground"><Anchor className="size-3" />Prepared on board from today's data</p>
    </div>
  );
}
