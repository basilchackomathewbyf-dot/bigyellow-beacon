import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowLeft, Check, CheckCircle2, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { useLearningAck, useLearnings } from "@/hooks/queries";
import { ListSkeleton } from "@/components/beacon/bits";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getLearningImageUrl, getFallbackImageForLearning } from "@/lib/learning-media";

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

  useEffect(() => {
    if (l && !l.acked) {
      ack.mutate({ id: l.id, body: { opened: true } });
    }
  }, [l?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!l) return <ListSkeleton />;
  const right = pick === l.check_question.answer_index;
  const isVideo = l.media?.kind === "video" && !!l.media?.url;
  const imgSrc = getLearningImageUrl(l.media, l.id);

  const handleUnderstood = async () => {
    if (l.acked) {
      toast.success("Lesson already acknowledged.");
      return;
    }
    if (!right) {
      toast.error("Please answer the quick check correctly to confirm your understanding.");
      return;
    }
    try {
      await ack.mutateAsync({ id: l.id, body: { acked: true, check_answer: pick! } });
      toast.success("Thanks — marked as understood.");
    } catch {
      toast.error("Could not record confirmation. Please try again.");
    }
  };

  return (
    <article className="mx-auto max-w-2xl space-y-6">
      <Link to="/learn" className="tap -ml-2 inline-flex items-center gap-1 px-2 text-sm text-muted-foreground"><ArrowLeft className="size-4" />Learn</Link>
      <div className="overflow-hidden rounded-3xl bg-muted">
        {isVideo ? (
          <video src={l.media?.url} autoPlay muted loop playsInline className="aspect-video w-full object-cover" />
        ) : (
          <img
            src={imgSrc}
            alt={l.title}
            onError={(e) => {
              const target = e.currentTarget;
              const fallback = getFallbackImageForLearning(l.id);
              if (target.src !== fallback) {
                target.src = fallback;
              }
            }}
            className="aspect-video w-full object-cover"
          />
        )}
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
            pick === i ? (right ? "border-secondary bg-secondary-soft font-medium" : "border-sev-mid bg-warn-soft") : "hover:bg-muted")}>{o}</button>
        ))}
        {pick !== null && <p className="text-sm text-muted-foreground">{right ? "That's right." : "Not quite — have another look above."}</p>}
      </div>
      <Button
        type="button"
        className={cn(
          "h-14 w-full rounded-2xl text-base font-semibold transition-all shadow-md active:scale-[0.99]",
          l.acked
            ? "bg-secondary text-secondary-foreground hover:bg-secondary/90 cursor-pointer"
            : right
              ? "bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
              : "bg-primary/80 text-primary-foreground hover:bg-primary/90 cursor-pointer"
        )}
        disabled={ack.isPending}
        onClick={handleUnderstood}
      >
        {ack.isPending ? (
          <span className="inline-flex items-center gap-2"><Loader2 className="size-5 animate-spin" />Saving...</span>
        ) : l.acked ? (
          <span className="inline-flex items-center gap-2"><CheckCircle2 className="size-5" />Understood</span>
        ) : (
          "Understood"
        )}
      </Button>
    </article>
  );
}
