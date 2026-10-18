import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ArrowRight, BookOpen, Check, ExternalLink, Lightbulb, Loader2, MessageSquarePlus, RefreshCw, ShieldCheck, Sparkles, Wrench } from "lucide-react";
import type { Analysis, Ticket } from "@/api/types";
import { useAnalysis, useApplySuggestion, useRerunAnalysis } from "@/hooks/use-tickets";
import { appendToReply } from "@/lib/reply-draft";
import { relTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AiBadge, SeverityPill } from "@/components/beacon/chips";

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="relative pl-9 animate-fade-up" style={{ animationDelay: `${n * 60}ms` }}>
      <span className="absolute left-0 top-0 flex size-6 items-center justify-center rounded-full bg-ai-foreground text-[11px] font-bold text-ai">{n}</span>
      <span className="absolute left-3 top-7 bottom-[-1.25rem] w-px bg-ai-border" aria-hidden />
      <h3 className="mb-2.5 pt-0.5 text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function CheckCard({
  title,
  current,
  suggested,
  reason,
  same,
  onApply,
  pending,
}: {
  title: string;
  current: React.ReactNode;
  suggested: React.ReactNode;
  reason: string;
  same: boolean;
  onApply: () => void;
  pending: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className={cn("rounded-xl border bg-card p-3.5 transition", same ? "border-border" : "border-ai-border shadow-[var(--shadow-soft)]")}>
      <div className="mb-2.5 text-xs font-semibold text-muted-foreground">{title}</div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-sm">
        <div className="rounded-lg bg-muted px-2.5 py-2">
          <div className="text-[11px] text-muted-foreground">{t("analysis.current")}</div>
          {current}
        </div>
        <ArrowRight className="size-4 text-muted-foreground" aria-hidden />
        <div className="rounded-lg bg-ai px-2.5 py-2">
          <div className="text-[11px] text-ai-foreground">{t("analysis.suggested")}</div>
          {suggested}
        </div>
      </div>
      <p className="mt-2.5 text-xs leading-relaxed text-muted-foreground">{reason}</p>
      <div className="mt-2.5 flex justify-end">
        {same ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-severity-low">
            <ShieldCheck className="size-3.5" aria-hidden />
            {t("analysis.agrees")}
          </span>
        ) : (
          <Button size="sm" onClick={onApply} disabled={pending}>
            {pending ? <Loader2 className="animate-spin" /> : <Check />}
            {t("analysis.apply")}
          </Button>
        )}
      </div>
    </div>
  );
}

function Body({ a, ticket }: { a: Analysis; ticket: Ticket }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const apply = useApplySuggestion();
  const [added, setAdded] = useState<Set<string>>(new Set());

  const addReply = (text: string) => {
    appendToReply(ticket.id, text);
    setAdded((s) => new Set(s).add(text));
    toast.success(t("analysis.addedToReply"));
    document.getElementById("reply")?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <div className="space-y-5">
      <Step n={1} title={t("analysis.s1")}>
        <ul className="space-y-1.5 rounded-xl bg-card p-3.5 text-sm leading-relaxed">
          {a.summary.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </Step>

      <Step n={2} title={t("analysis.s2")}>
        <div className="flex flex-wrap gap-1.5">
          {a.contributing_factors.map((f) => (
            <span key={f} className="rounded-full border border-ai-border bg-card px-2.5 py-1 text-xs font-medium">
              {f}
            </span>
          ))}
        </div>
      </Step>

      <Step n={3} title={t("analysis.s3")}>
        <div className="space-y-2.5">
          <CheckCard
            title={t("analysis.ismCheck")}
            current={<span className="font-medium">{t(`ism.${ticket.ism_category}`)}</span>}
            suggested={<span className="font-medium text-ai-foreground">{t(`ism.${a.ism_check.suggested}`)}</span>}
            reason={a.ism_check.reason}
            same={ticket.ism_category === a.ism_check.suggested}
            pending={apply.isPending}
            onApply={() => apply.mutate({ id: ticket.id, ism_category: a.ism_check.suggested })}
          />
          <CheckCard
            title={t("analysis.sevCheck")}
            current={<SeverityPill value={ticket.severity} />}
            suggested={<SeverityPill value={a.severity_check.suggested} />}
            reason={a.severity_check.reason}
            same={ticket.severity === a.severity_check.suggested}
            pending={apply.isPending}
            onApply={() => apply.mutate({ id: ticket.id, severity: a.severity_check.suggested })}
          />
        </div>
      </Step>

      {(a.similar_tickets.length > 0 || a.corpus_matches.length > 0) && (
        <Step n={4} title={t("analysis.s4")}>
          <div className="space-y-1.5">
            {a.similar_tickets.map((s) => (
              <Link
                key={s.ticket_id}
                to="/tickets/$ticketId"
                params={{ ticketId: s.ticket_id }}
                className="block rounded-lg bg-card px-3 py-2 text-sm transition hover:-translate-y-px hover:shadow-[var(--shadow-soft)]"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">{s.ticket_no}</span>
                  <span className="min-w-0 flex-1 truncate">{s.title}</span>
                  <span className="text-xs text-muted-foreground">{s.vessel}</span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-ai-foreground" style={{ width: `${Math.round(s.score * 100)}%` }} />
                  </div>
                  <span className="text-[11px] font-semibold tabular-nums text-ai-foreground">
                    {Math.round(s.score * 100)}% {t("analysis.match")}
                  </span>
                </div>
              </Link>
            ))}
            {a.corpus_matches.map((c) => (
              <a key={c.title} href={c.url} target="_blank" rel="noreferrer" className="block rounded-lg bg-card p-3 transition hover:shadow-[var(--shadow-soft)]">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <BookOpen className="size-3.5 text-muted-foreground" aria-hidden />
                  <span className="rounded bg-muted px-1.5 text-[11px] font-semibold text-muted-foreground">{c.source}</span>
                  <span className="min-w-0 flex-1 truncate">{c.title}</span>
                  <ExternalLink className="size-3.5 text-muted-foreground" aria-hidden />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{c.why_relevant}</p>
              </a>
            ))}
          </div>
        </Step>
      )}

      <Step n={5} title={t("analysis.s5")}>
        <div className="space-y-2">
          {a.recommendations.map((r) => (
            <div key={r.text} className="flex items-start gap-2.5 rounded-lg bg-card p-3">
              {r.type === "corrective" ? <Wrench className="mt-0.5 size-4 shrink-0 text-severity-mid" aria-hidden /> : <ShieldCheck className="mt-0.5 size-4 shrink-0 text-seaglass-strong" aria-hidden />}
              <div className="min-w-0 flex-1">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{t(`analysis.${r.type}`)}</div>
                <div className="text-sm">{r.text}</div>
              </div>
              <Button size="sm" variant="ghost" className="shrink-0" onClick={() => addReply(r.text)} disabled={added.has(r.text)}>
                {added.has(r.text) ? <Check /> : <MessageSquarePlus />}
                <span className="sr-only sm:not-sr-only">{t("analysis.addToReply")}</span>
              </Button>
            </div>
          ))}
        </div>
      </Step>

      {a.suggest_learning && (
        <div className="flex flex-wrap items-center gap-4 rounded-xl sea-gradient p-4 text-primary-foreground shadow-[var(--shadow-lift)] animate-fade-up">
          <Lightbulb className="size-6 shrink-0" aria-hidden />
          <div className="min-w-48 flex-1">
            <div className="font-semibold">{t("analysis.learningCallout")}</div>
            <div className="text-sm opacity-90">{t("analysis.learningCalloutSub")}</div>
          </div>
          <Button variant="secondary" onClick={() => navigate({ to: "/learnings/new", search: { ticketId: ticket.id } })}>
            {t("detail.createLearning")}
          </Button>
        </div>
      )}
    </div>
  );
}

function Thinking() {
  const { t } = useTranslation();
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setStage((s) => Math.min(4, s + 1)), 450);
    return () => window.clearInterval(id);
  }, []);
  return (
    <ol className="space-y-2.5" aria-busy aria-live="polite">
      {[0, 1, 2, 3, 4].map((i) => (
        <li key={i} className={cn("flex items-center gap-2.5 text-sm transition-opacity", i > stage ? "opacity-35" : "opacity-100")}>
          {i < stage ? <Check className="size-4 text-severity-low" aria-hidden /> : i === stage ? <Loader2 className="size-4 animate-spin text-ai-foreground" aria-hidden /> : <span className="size-4 rounded-full border" aria-hidden />}
          {t(`analysis.stages.${i}`)}
        </li>
      ))}
    </ol>
  );
}

export function AnalysisPanel({ ticket }: { ticket: Ticket }) {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch } = useAnalysis(ticket.id);
  const rerun = useRerunAnalysis(ticket.id);
  const loading = isLoading || rerun.isPending || !data;

  return (
    <aside className="ai-panel h-fit overflow-hidden p-0 xl:sticky xl:top-22" aria-labelledby="ai-title">
      <div className="border-b border-ai-border bg-card/60 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg sea-gradient text-primary-foreground">
            <Sparkles className="size-4" aria-hidden />
          </span>
          <h2 id="ai-title" className="text-base font-semibold">
            {t("analysis.title")}
          </h2>
          <Button size="sm" variant="outline" className="ml-auto" onClick={() => rerun.mutate()} disabled={rerun.isPending}>
            <RefreshCw className={rerun.isPending ? "animate-spin" : ""} /> {t("detail.rerun")}
          </Button>
        </div>
        <div className="mt-2.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {data && !rerun.isPending && <AiBadge>{t("analysis.badge", { model: data.model, time: relTime(data.created_at) })}</AiBadge>}
          <span>{t("analysis.review")}</span>
        </div>
      </div>
      <div className="p-5">{isError ? <div role="alert" className="space-y-3">
        <p className="text-sm text-muted-foreground">{t("common.error")}</p>
        <Button variant="outline" onClick={() => refetch()}>{t("common.retry")}</Button>
      </div> : loading ? <Thinking /> : <Body a={data} ticket={ticket} />}</div>
    </aside>
  );
}
