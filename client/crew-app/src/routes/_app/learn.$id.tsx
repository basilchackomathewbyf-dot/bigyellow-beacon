import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowLeft, Check, X } from "lucide-react";
import { toast } from "sonner";
import { useLearningAck, useLearnings } from "@/hooks/queries";
import { ListSkeleton } from "@/components/beacon/bits";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/learn/$id")({
  head: () => ({ meta: [{ title: "Lesson — Beacon" }, { name: "description", content: "A short safety lesson." }, { property: "og:title", content: "Lesson — Beacon" }, { property: "og:description", content: "A short safety lesson." }] }),
  component: Lesson,
});

function Lesson() {
  const { id } = Route.useParams();
  const q = useLearnings();
  const ack = useLearningAck();
  const l = q.data?.find((x) => x.id === id);
  const [pick, setPick] = useState<number | null>(null);
  useEffect(() => { if (l) ack.mutate({ id: l.id, body: { opened: true } }); }, [l?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!l) return <ListSkeleton />;
  const right = pick === l.check_question.answer_index;

  return (
    <article className="mx-auto max-w-2xl space-y-6">
      <Link to="/learn" className="tap -ml-2 inline-flex items-center gap-1 px-2 text-sm text-muted-foreground"><ArrowLeft className="size-4" />Learn</Link>
      <div className="overflow-hidden rounded-3xl bg-muted">
        {l.media.kind === "video" ? <video src={l.media.url} autoPlay muted loop playsInline className="aspect-video w-full object-cover" /> : <img src={l.media.url} alt="" className="aspect-video w-full object-cover" />}
      </div>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{l.title}</h1>
      <div className="space-y-3 text-foreground/80"><p>{l.context}</p><p>{l.situation}</p></div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-2xl bg-secondary-soft p-5"><p className="mb-3 text-sm font-semibold text-secondary">Do</p><ul className="space-y-2">{l.do_points.map((d) => <li key={d} className="flex gap-2 text-sm"><Check className="mt-0.5 size-4 shrink-0 text-secondary" />{d}</li>)}</ul></div>
        <div className="rounded-2xl bg-accent p-5"><p className="mb-3 text-sm font-semibold text-accent-foreground">Don't</p><ul className="space-y-2">{l.dont_points.map((d) => <li key={d} className="flex gap-2 text-sm"><X className="mt-0.5 size-4 shrink-0 text-accent-foreground" />{d}</li>)}</ul></div>
      </div>
      <div className="surface space-y-3 p-5">
        <p className="font-semibold">Quick check: {l.check_question.q}</p>
        {l.check_question.options.map((o, i) => (
          <button key={o} onClick={() => setPick(i)} className={cn("tap flex w-full items-center rounded-xl border px-4 text-left text-sm transition",
            pick === i ? (right ? "border-secondary bg-secondary-soft" : "border-sev-mid bg-warn-soft") : "hover:bg-muted")}>{o}</button>
        ))}
        {pick !== null && <p className="text-sm text-muted-foreground">{right ? "That's right." : "Not quite — have another look above."}</p>}
      </div>
      <Button className="h-14 w-full rounded-2xl text-base" disabled={l.acked || !right}
        onClick={async () => { await ack.mutateAsync({ id: l.id, body: { acked: true, check_answer: pick! } }); toast.success("Thanks — marked as understood."); }}>
        {l.acked ? "Understood" : "I understood"}
      </Button>
    </article>
  );
}
