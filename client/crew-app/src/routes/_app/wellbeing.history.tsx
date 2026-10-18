import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft, Flame, Lightbulb, Lock, Trash2 } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { useDeleteHistory, useHistory } from "@/hooks/queries";
import { PageHeader } from "@/components/beacon/bits";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/wellbeing/history")({
  head: () => ({ meta: [{ title: "My mood history — Beacon" }, { name: "description", content: "Your private mood and tiredness trends." }, { property: "og:title", content: "My mood history — Beacon" }, { property: "og:description", content: "Private mood trends." }] }),
  component: History,
});

const moodBg = ["bg-muted", "bg-mood-1", "bg-mood-2", "bg-mood-3", "bg-mood-4", "bg-mood-5"];

function History() {
  const [range, setRange] = useState<"7d" | "30d" | "90d">("30d");
  const q = useHistory(range);
  const del = useDeleteHistory();
  const days = parseInt(range);
  const byDate = new Map(q.data?.entries.map((e) => [e.date, e]));
  const cells = Array.from({ length: days }, (_, i) => new Date(Date.now() - (days - 1 - i) * 86_400_000).toISOString().slice(0, 10));

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/wellbeing" className="tap -ml-2 inline-flex items-center gap-1 px-2 text-sm text-muted-foreground"><ArrowLeft className="size-4" />Wellbeing</Link>
      <PageHeader title="My mood history" action={
        <div className="flex rounded-full bg-muted p-0.5 text-xs">
          {(["7d", "30d", "90d"] as const).map((r) => <button key={r} onClick={() => setRange(r)} className={cn("rounded-full px-3 py-1.5 font-medium", range === r ? "bg-card shadow-soft" : "text-muted-foreground")}>{r.replace("d", " days")}</button>)}
        </div>} />
      <p className="flex items-start gap-2 rounded-2xl bg-primary-soft p-4 text-sm text-primary"><Lock className="mt-0.5 size-4 shrink-0" />Only you can see this. Your Master sees ship averages only when 5 or more people check in.</p>
      {!q.data ? <Skeleton className="h-72 rounded-3xl" /> : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="surface p-4"><p className="text-xs text-muted-foreground">Streak</p><p className="mt-1 flex items-center gap-1.5 text-2xl font-semibold"><Flame className="size-5 text-sev-mid" />{q.data.streak} days</p></div>
            <div className="surface p-4 sm:col-span-2"><p className="text-xs text-muted-foreground">Top tags</p><div className="mt-2 flex flex-wrap gap-1.5">{q.data.top_tags.length ? q.data.top_tags.map((t) => <span key={t.tag} className="rounded-full bg-secondary-soft px-3 py-1 text-sm capitalize text-secondary">{t.tag} · {t.count}</span>) : <span className="text-sm text-muted-foreground">None yet</span>}</div></div>
          </div>
          <div className="surface flex gap-3 bg-accent p-4"><Lightbulb className="size-5 shrink-0 text-accent-foreground" /><p className="text-sm text-foreground">{q.data.insight}</p></div>
          <div className="surface p-4">
            <p className="mb-2 text-sm font-semibold">Mood and tiredness</p>
            <div className="h-56">
              <ResponsiveContainer>
                <LineChart data={q.data.entries.map((e) => ({ ...e, d: e.date.slice(5) }))} margin={{ left: -24, right: 8 }}>
                  <CartesianGrid stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="d" tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }} tickLine={false} axisLine={false} minTickGap={24} />
                  <YAxis domain={[1, 5]} ticks={[1, 3, 5]} tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--color-border)" }} />
                  <Line type="monotone" dataKey="mood" name="Mood" stroke="var(--color-secondary)" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="fatigue" name="Tiredness" stroke="var(--color-accent-foreground)" strokeWidth={2} strokeDasharray="4 4" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="surface p-4">
            <p className="mb-3 text-sm font-semibold">Calendar</p>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(22px,1fr))] gap-1.5">
              {cells.map((d) => { const e = byDate.get(d); return <span key={d} title={`${d}${e ? ` · mood ${e.mood}` : ""}`} className={cn("aspect-square rounded-md", moodBg[e?.mood ?? 0])} />; })}
            </div>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild><Button variant="ghost" className="text-muted-foreground"><Trash2 className="size-4" />Delete my history</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader><AlertDialogTitle>Delete your mood history?</AlertDialogTitle><AlertDialogDescription>All your check-ins will be removed. This can't be undone.</AlertDialogDescription></AlertDialogHeader>
              <AlertDialogFooter><AlertDialogCancel>Keep it</AlertDialogCancel><AlertDialogAction onClick={async () => { await del.mutateAsync(); toast("History deleted."); }}>Delete</AlertDialogAction></AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </>
      )}
    </div>
  );
}
