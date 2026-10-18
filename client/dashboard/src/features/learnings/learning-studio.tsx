import { useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, Loader2, Rocket, Save, Siren, Sparkles, Undo2 } from "lucide-react";
import { toast } from "sonner";
import type { Learning, LearningInput, VesselType } from "@/api/types";
import { useDraftLearning, usePublishLearning, useRetractLearning, useSaveLearning, useVessels } from "@/hooks/use-content";
import { useTicket } from "@/hooks/use-tickets";
import { SHIP_BUDGET_BYTES, audienceCount, estimateDeliveryBytes } from "@/lib/rules";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { PageHeader, Pill, SeverityPill } from "@/components/beacon/chips";
import { PhonePreview } from "./phone-preview";
import { MediaUploader } from "./media-uploader";

const empty = (ticketId?: string, vesselId?: string): LearningInput => ({
  source_ticket_id: ticketId,
  title: "",
  context: "",
  situation: "",
  do_points: ["", "", ""],
  dont_points: ["", "", ""],
  check_question: { q: "", options: ["", "", ""], answer_index: 0 },
  tags: {},
  media: [],
  audience: { mode: ticketId ? "same_vessel" : "all", vessel_ids: vesselId ? [vesselId] : [] },
  rank_filter: "all",
  priority: "normal",
  ai_drafted_fields: [],
});

function toInput(l: Learning): LearningInput {
  const { id: _id, status: _s, stats: _st, published_at: _p, updated_at: _u, ...rest } = l;
  return rest;
}

function Card({ n, title, children, action }: { n: number; title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="surface-card p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="grid size-6 place-items-center rounded-full bg-primary-soft text-xs font-semibold text-primary">{n}</span>
        <h2 className="text-sm font-semibold">{title}</h2>
        <div className="ml-auto">{action}</div>
      </div>
      {children}
    </section>
  );
}

export function LearningStudio({ existing, sourceTicketId }: { existing?: Learning; sourceTicketId?: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: ticket } = useTicket(sourceTicketId ?? "");
  const { data: vessels = [] } = useVessels();
  const [form, setForm] = useState<LearningInput>(() => (existing ? toInput(existing) : empty(sourceTicketId)));
  const [typeFilter, setTypeFilter] = useState<VesselType | "all">("all");
  const [confirm, setConfirm] = useState(false);
  const draft = useDraftLearning();
  const save = useSaveLearning();
  const publish = usePublishLearning();
  const retract = useRetractLearning();
  const status = existing?.status ?? "draft";

  const vesselId = ticket?.vessel.id;
  const ai = new Set(form.ai_drafted_fields);
  const set = <K extends keyof LearningInput>(k: K, v: LearningInput[K]) =>
    setForm((f) => ({ ...f, [k]: v, ai_drafted_fields: f.ai_drafted_fields.filter((x) => x !== k) }));
  const AiMark = ({ field }: { field: string }) =>
    ai.has(field) ? (
      <span title={t("learn.aiFilled")} aria-label={t("learn.aiFilled")} className="inline-flex text-ai-foreground">
        <Sparkles className="size-3.5" />
      </span>
    ) : null;

  const count = audienceCount(form.audience.mode, form.audience.vessel_ids, vessels.length);
  const overBudget = estimateDeliveryBytes(form.media) > SHIP_BUDGET_BYTES;
  const valid = form.title.trim() && form.situation.trim() && !overBudget && count > 0;

  const effectiveInput = (): LearningInput => ({
    ...form,
    audience: form.audience.mode === "same_vessel" ? { mode: "same_vessel", vessel_ids: vesselId ? [vesselId] : form.audience.vessel_ids } : form.audience,
  });

  const runDraft = () =>
    draft.mutate(sourceTicketId, {
      onSuccess: (d) => setForm((f) => ({ ...f, ...d, tags: { ...f.tags, ...d.tags } })),
    });

  const doSave = async () => {
    try {
    const l = await save.mutateAsync({ id: existing?.id, input: effectiveInput() });
    toast.success(t("learn.saved"));
    if (!existing) navigate({ to: "/learnings/$learningId", params: { learningId: l.id }, replace: true });
    } catch { /* The mutation displays the error; retain the draft. */ }
  };
  const doPublish = async () => {
    try {
    const l = await save.mutateAsync({ id: existing?.id, input: effectiveInput() });
    await publish.mutateAsync(l.id);
    toast.success(t("learn.published"));
    navigate({ to: "/learnings" });
    } catch { /* The mutation displays the error; retain the draft. */ }
  };

  const filteredVessels = useMemo(() => vessels.filter((v) => typeFilter === "all" || v.type === typeFilter), [vessels, typeFilter]);

  return (
    <div>
      <PageHeader
        title={t("learn.studio")}
        subtitle={existing ? existing.title : undefined}
        actions={
          <>
            {existing && <Pill tone={status === "published" ? "IN_REVIEW" : status === "draft" ? "NEW" : "CLOSED"}>{t(`learn.status.${status}`)}</Pill>}
            {status === "published" && existing && (
              <Button variant="outline" onClick={() => retract.mutate(existing.id, { onSuccess: () => toast(t("learn.retracted")) })}>
                <Undo2 /> {t("learn.retract")}
              </Button>
            )}
            <Button variant="outline" onClick={doSave} disabled={save.isPending || !form.title.trim()}>
              {save.isPending ? <Loader2 className="animate-spin" /> : <Save />} {t("learn.saveDraft")}
            </Button>
            <Button onClick={() => setConfirm(true)} disabled={!valid || status === "published" || save.isPending || publish.isPending}>
              <Rocket /> {t("learn.publish")}
            </Button>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-4">
          {ticket && (
            <Collapsible className="surface-card p-5">
              <CollapsibleTrigger className="flex w-full items-center gap-3 text-left">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("learn.source")}</span>
                <span className="font-mono text-xs text-muted-foreground">{ticket.ticket_no}</span>
                <SeverityPill value={ticket.severity} />
                <span className="truncate text-sm font-medium">{ticket.title_en}</span>
                <ChevronDown className="ml-auto size-4 text-muted-foreground" aria-hidden />
              </CollapsibleTrigger>
              <CollapsibleContent className="pt-3 text-sm text-muted-foreground">
                {ticket.vessel.name} · {t(`hazard.${ticket.hazard_type}`)} · {ticket.location_on_board}
                <p className="mt-2 text-foreground">{ticket.description_en}</p>
              </CollapsibleContent>
            </Collapsible>
          )}

          <Card
            n={1}
            title={t("learn.fSituation")}
            action={
              <Button size="sm" variant="outline" className="border-ai-border bg-ai text-ai-foreground hover:bg-ai/70" onClick={runDraft} disabled={draft.isPending}>
                {draft.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />} {draft.isPending ? t("learn.drafting") : t("learn.draftAi")}
              </Button>
            }
          >
            <div className={cn("space-y-4 transition", draft.isPending && "opacity-50")}>
              <div className="space-y-1.5">
                <Label htmlFor="l-title" className="flex items-center gap-1.5">{t("learn.fTitle")} <AiMark field="title" /></Label>
                <Input id="l-title" maxLength={80} value={form.title} onChange={(e) => set("title", e.target.value)} />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="l-ctx" className="flex items-center gap-1.5">{t("learn.fContext")} <AiMark field="context" /></Label>
                  <Textarea id="l-ctx" rows={3} value={form.context} onChange={(e) => set("context", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="l-sit" className="flex items-center gap-1.5">{t("learn.fSituation")} <AiMark field="situation" /></Label>
                  <Textarea id="l-sit" rows={3} value={form.situation} onChange={(e) => set("situation", e.target.value)} />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {(["do_points", "dont_points"] as const).map((k) => (
                  <div key={k} className="space-y-1.5">
                    <Label className="flex items-center gap-1.5">{k === "do_points" ? t("learn.fDo") : t("learn.fDont")} <AiMark field={k} /></Label>
                    {form[k].map((p, i) => (
                      <Input
                        key={i}
                        aria-label={`${k === "do_points" ? t("learn.fDo") : t("learn.fDont")} ${i + 1}`}
                        value={p}
                        className={k === "do_points" ? "border-l-4 border-l-severity-low" : "border-l-4 border-l-severity-high"}
                        onChange={(e) => set(k, form[k].map((x, j) => (j === i ? e.target.value : x)))}
                      />
                    ))}
                  </div>
                ))}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="l-q" className="flex items-center gap-1.5">{t("learn.fCheck")} <AiMark field="check_question" /></Label>
                <Input id="l-q" value={form.check_question.q} onChange={(e) => set("check_question", { ...form.check_question, q: e.target.value })} />
                <div className="grid gap-2 md:grid-cols-3">
                  {form.check_question.options.map((o, i) => (
                    <label key={i} className={cn("flex items-center gap-2 rounded-lg border p-1.5 pl-2.5", form.check_question.answer_index === i && "border-seaglass bg-seaglass-soft")}>
                      <input
                        type="radio"
                        name="answer"
                        aria-label={`${t("learn.fCorrect")} ${i + 1}`}
                        checked={form.check_question.answer_index === i}
                        onChange={() => set("check_question", { ...form.check_question, answer_index: i })}
                        className="accent-[var(--color-seaglass)]"
                      />
                      <input
                        aria-label={t("learn.fOption", { n: i + 1 })}
                        placeholder={t("learn.fOption", { n: i + 1 })}
                        value={o}
                        onChange={(e) => set("check_question", { ...form.check_question, options: form.check_question.options.map((x, j) => (j === i ? e.target.value : x)) })}
                        className="w-full bg-transparent text-sm outline-none"
                      />
                    </label>
                  ))}
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="flex items-center gap-1.5">{t("learn.fTags")} <AiMark field="tags" /></Label>
                <div className="grid gap-2 md:grid-cols-3">
                  {(["tool", "area", "situation"] as const).map((k) => (
                    <Input key={k} aria-label={t(`learn.tag${k[0].toUpperCase()}${k.slice(1)}`)} placeholder={t(`learn.tag${k[0].toUpperCase()}${k.slice(1)}`)} value={form.tags[k] ?? ""} onChange={(e) => set("tags", { ...form.tags, [k]: e.target.value })} />
                  ))}
                </div>
              </div>
            </div>
          </Card>

          <Card n={2} title={t("learn.media")}>
            <MediaUploader value={form.media} onChange={(m) => set("media", m)} ticketPhotos={ticket?.photos ?? []} />
          </Card>

          <Card n={3} title={t("learn.audienceLabel")}>
            <div className="grid gap-2 md:grid-cols-3">
              {(["same_vessel", "selected", "all"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  disabled={m === "same_vessel" && !vesselId}
                  onClick={() => set("audience", { mode: m, vessel_ids: m === "same_vessel" && vesselId ? [vesselId] : m === "selected" ? form.audience.vessel_ids : [] })}
                  className={cn("rounded-xl border p-3 text-left text-sm transition disabled:opacity-40", form.audience.mode === m ? "border-primary bg-primary-soft" : "hover:border-primary/40")}
                >
                  <div className="font-medium">{t(`learn.audience.${m}`)}</div>
                  <div className="text-xs text-muted-foreground">
                    {m === "same_vessel" ? ticket?.vessel.name ?? "—" : m === "all" ? `${vessels.length} ${t("common.vessels")}` : `${form.audience.vessel_ids.length} ${t("common.vessels")}`}
                  </div>
                </button>
              ))}
            </div>
            {form.audience.mode === "selected" && (
              <div className="mt-3 rounded-xl border p-3">
                <div className="mb-2 flex flex-wrap items-center gap-1.5 text-xs">
                  <span className="text-muted-foreground">{t("learn.vesselType")}:</span>
                  {(["all", "Bulk carrier", "Tanker", "Container"] as const).map((vt) => (
                    <button key={vt} type="button" onClick={() => setTypeFilter(vt)} className={cn("rounded-full border px-2 py-0.5", typeFilter === vt && "border-primary bg-primary-soft text-primary")}>
                      {vt === "all" ? t("common.all") : vt}
                    </button>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-1">
                  {filteredVessels.map((v) => (
                    <label key={v.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent">
                      <Checkbox
                        checked={form.audience.vessel_ids.includes(v.id)}
                        onCheckedChange={(c) =>
                          set("audience", { mode: "selected", vessel_ids: c ? [...form.audience.vessel_ids, v.id] : form.audience.vessel_ids.filter((x) => x !== v.id) })
                        }
                      />
                      {v.name}
                    </label>
                  ))}
                </div>
              </div>
            )}
            <div className="mt-4 flex items-center gap-3 text-sm">
              <span className="text-muted-foreground">{t("learn.rankFilter")}</span>
              <div className="inline-flex rounded-lg border p-0.5">
                {(["all", "officers", "ratings"] as const).map((r) => (
                  <button key={r} type="button" onClick={() => set("rank_filter", r)} className={cn("rounded-md px-3 py-1", form.rank_filter === r && "bg-primary-soft font-medium text-primary")}>
                    {t(`learn.rank.${r}`)}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          <Card n={4} title={t("learn.priorityLabel")}>
            <div className="grid gap-2 md:grid-cols-2">
              {(["normal", "urgent"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => set("priority", p)}
                  className={cn(
                    "flex items-start gap-3 rounded-xl border p-3 text-left text-sm transition",
                    form.priority === p ? (p === "urgent" ? "border-severity-high bg-severity-high-soft" : "border-primary bg-primary-soft") : "hover:border-primary/40",
                  )}
                >
                  {p === "urgent" && <Siren className="mt-0.5 size-4 text-severity-high" aria-hidden />}
                  <div>
                    <div className="font-medium">{t(`learn.priority.${p}`)}</div>
                    <div className="text-xs text-muted-foreground">{p === "urgent" ? t("learn.urgentDesc") : t("learn.normalDesc")}</div>
                  </div>
                </button>
              ))}
            </div>
          </Card>

          {existing && existing.status !== "draft" && (
            <section className="surface-card grid grid-cols-4 gap-4 p-5 text-center">
              {[
                [t("learn.stats"), `${existing.stats.vessels_delivered}/${existing.stats.vessels_total}`],
                [t("learn.opened"), existing.stats.opened],
                [t("learn.acked"), existing.stats.acknowledged],
                [t("learn.correct"), existing.stats.check_correct],
              ].map(([k, v]) => (
                <div key={String(k)}>
                  <div className="text-2xl font-semibold tabular-nums">{v}</div>
                  <div className="text-xs text-muted-foreground">{k}</div>
                </div>
              ))}
            </section>
          )}
        </div>

        <div className="xl:sticky xl:top-22 h-fit">
          <div className="mb-3 text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("learn.preview")}</div>
          <PhonePreview value={form} />
        </div>
      </div>

      <AlertDialog open={confirm} onOpenChange={setConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("learn.publishTitle", { count })}</AlertDialogTitle>
            <AlertDialogDescription>{t("learn.publishDesc")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={doPublish}>{t("learn.publish")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
