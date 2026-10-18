import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, ArrowUp, Check, ChevronDown, Loader2, Mic, PartyPopper, ShieldCheck, Sparkles, Square, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { useAnswerDraft, useCreateDraft, useStructure, useSubmitReport } from "@/hooks/queries";
import type { ReportFields, StructureResult, Ticket } from "@/api/types";
import { HAZARDS, ISM, SEVERITY } from "@/lib/labels";
import { MAX_PHOTOS, addPhotos, severityTone } from "@/lib/rules";
import { useMicRecorder } from "@/media/useMicRecorder";
import { Waveform } from "@/media/Waveform";
import { MediaErrorNote } from "@/media/MediaErrorNote";
import { AttachMenu } from "@/components/beacon/AttachMenu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/report")({
  head: () => ({ meta: [{ title: "Report a near-miss — Beacon" }, { name: "description", content: "Report a near-miss by voice, photo or text in one quick flow." }, { property: "og:title", content: "Report a near-miss — Beacon" }, { property: "og:description", content: "Speak, type or attach — in one flow." }] }),
  validateSearch: (s: Record<string, unknown>): { start?: "voice" | "text" | "photo" } =>
    s.start === "voice" || s.start === "text" || s.start === "photo" ? { start: s.start } : {},
  component: Report,
});

type Phase = "compose" | "thinking" | "review" | "privacy" | "done";
const fmt = (s: number) => `0:${String(Math.floor(s)).padStart(2, "0")}`;

function BeaconSays({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-2.5 rise">
      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-sunrise text-primary-foreground shadow-glow"><Sparkles className="size-4" /></span>
      <div className="min-w-0 max-w-[88%] space-y-2">{children}</div>
    </div>
  );
}
const bubble = "rounded-3xl rounded-tl-md bg-card px-4 py-3 text-[15px] shadow-soft";

function Report() {
  const [phase, setPhase] = useState<Phase>("compose");
  const [text, setText] = useState("");
  const [photos, setPhotos] = useState<Blob[]>([]);
  const [audio, setAudio] = useState<Blob | null>(null);
  const [sentText, setSentText] = useState("");
  const [draftId, setDraftId] = useState("");
  const [structure, setStructure] = useState<StructureResult | null>(null);
  const [fields, setFields] = useState<ReportFields | null>(null);
  const [answers, setAnswers] = useState<{ q: string; a: string }[]>([]);
  const [share, setShare] = useState(false);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const mic = useMicRecorder();
  const { start } = Route.useSearch();
  const taRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (start === "voice") void mic.start();
    if (start === "text") taRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { if (mic.blob) setAudio(mic.blob); }, [mic.blob]);
  const audioUrl = mic.url;
  const photoUrls = useMemo(() => photos.map((p) => URL.createObjectURL(p)), [photos]);
  useEffect(() => () => photoUrls.forEach((u) => URL.revokeObjectURL(u)), [photoUrls]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [phase, answers.length, structure?.clarifying_question]);

  const draft = useCreateDraft();
  const struct = useStructure();
  const ans = useAnswerDraft();
  const submit = useSubmitReport();

  const hasInput = !!audio || photos.length > 0 || text.trim().length > 0;
  const question = phase === "review" ? structure?.clarifying_question : undefined;
  const step = phase === "compose" ? 0 : phase === "thinking" || phase === "review" ? 1 : 2;

  const sendCapture = async () => {
    setSentText(text.trim());
    setText("");
    setPhase("thinking");
    try {
      const d = await draft.mutateAsync({
        audio: audio ?? undefined,
        photos,
        text: text.trim() || undefined,
        duration: mic.elapsed > 0 ? mic.elapsed : undefined,
      });
      setDraftId(d.draft_id);
      const s = await struct.mutateAsync(d.draft_id);
      setStructure(s);
      setFields(s.fields);
      setPhase("review");
    } catch (ex: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const errObj = ex as any;
      const msg = errObj?.detail?.error || errObj?.error || (ex instanceof Error ? ex.message : "Couldn't reach the ship server. Please try again.");
      toast.error(msg);
      setText(sentText);
      setPhase("compose");
    }
  };
  const sendAnswer = async () => {
    const a = text.trim();
    if (!a || !question) return;
    setText("");
    setAnswers((x) => [...x, { q: question, a }]);
    const f = await ans.mutateAsync({ id: draftId, answer: a });
    setFields((old) => ({ ...old!, location_on_board: f.location_on_board }));
    setStructure((s) => s && { ...s, clarifying_question: undefined });
  };
  const send = async () => {
    try {
      setTicket(await submit.mutateAsync({ draft_id: draftId, fields: fields!, share }));
      setPhase("done");
    } catch { toast.error("Couldn't send. Please try again."); }
  };
  const restart = () => {
    setPhase("compose"); setText(""); setPhotos([]); setAudio(null); mic.discard(); setSentText("");
    setStructure(null); setFields(null); setAnswers([]); setShare(false); setTicket(null);
  };
  const set = <K extends keyof ReportFields>(k: K, v: ReportFields[K]) => setFields((f) => ({ ...f!, [k]: v }));

  const holdDown = (e: React.PointerEvent) => { e.preventDefault(); (e.target as HTMLElement).setPointerCapture?.(e.pointerId); if (!mic.recording) void mic.start(); };
  const holdUp = () => mic.recording && mic.stop();

  const composerOn = phase === "compose" || !!question;

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-11rem)] max-w-2xl flex-col">
      <header className="mb-5">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-coral-soft px-3 py-1 text-xs font-bold text-coral">Near-miss</span>
          <div className="ml-auto flex w-36 gap-1" aria-label={`Step ${step + 1} of 3`}>
            {["Capture", "Review", "Send"].map((s, i) => <span key={s} title={s} className={cn("h-1.5 flex-1 rounded-full transition-colors", i <= step ? "bg-sunrise" : "bg-border")} />)}
          </div>
        </div>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight">What happened?</h1>
        <p className="mt-1 text-muted-foreground">Speak, type or attach — any mix works.</p>
      </header>

      <div className="flex-1 space-y-4 pb-28 lg:pb-6">
        <BeaconSays><p className={bubble}>Hi — tell me what you saw. Tap the <b>mic</b> to talk, or tap the <b>paperclip</b> for photos.</p></BeaconSays>

        {phase !== "compose" && (
          <div className="flex justify-end rise">
            <div className="max-w-[85%] space-y-2 rounded-3xl rounded-tr-md bg-ocean p-3 text-primary-foreground shadow-lift">
              {audioUrl && <audio src={audioUrl} controls className="h-10 w-64 max-w-full" />}
              {photoUrls.length > 0 && <div className="flex gap-1.5">{photoUrls.map((u, i) => <img key={u} src={u} alt={`Photo ${i + 1}`} className="size-20 rounded-2xl object-cover" />)}</div>}
              {sentText && <p className="px-1 text-[15px]">{sentText}</p>}
            </div>
          </div>
        )}

        {phase === "thinking" && (
          <BeaconSays><p className={cn(bubble, "flex items-center gap-2")}><Loader2 className="size-4 animate-spin text-coral" />Understanding your report…</p></BeaconSays>
        )}

        {fields && phase !== "compose" && phase !== "thinking" && (
          <BeaconSays>
            <p className={bubble}>Here's what I understood. Tap anything to fix it.</p>
            <div className="space-y-3 rounded-3xl bg-card p-4 shadow-soft">
              <Input value={fields.title_en} onChange={(e) => set("title_en", e.target.value)} aria-label="Title" className="h-auto border-0 bg-transparent p-0 font-display text-lg font-bold shadow-none focus-visible:ring-0" />
              <Input value={fields.location_on_board} onChange={(e) => set("location_on_board", e.target.value)} placeholder="Location on board" aria-label="Location" className="h-10 rounded-xl bg-muted/60" />
              <div className="grid grid-cols-2 gap-2">
                <Select value={fields.hazard_type} onValueChange={(v) => set("hazard_type", v as ReportFields["hazard_type"])}>
                  <SelectTrigger className="h-10 rounded-xl bg-muted/60" aria-label="Hazard type"><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(HAZARDS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
                <Select value={fields.ism_category} onValueChange={(v) => set("ism_category", v as ReportFields["ism_category"])}>
                  <SelectTrigger className="h-10 rounded-xl bg-muted/60" aria-label="ISM category"><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(ISM).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="rounded-xl bg-muted/60 p-3">
                <div className="mb-2 flex justify-between text-xs font-semibold"><span>Severity</span>
                  <span className={{ low: "text-sev-low", mid: "text-warn", high: "text-sev-high" }[severityTone(fields.severity)]}>{fields.severity} · {SEVERITY[fields.severity]}</span></div>
                <Slider min={1} max={5} step={1} value={[fields.severity]} onValueChange={([v]) => set("severity", v as ReportFields["severity"])} aria-label="Severity" />
              </div>
              <Textarea value={fields.immediate_action} onChange={(e) => set("immediate_action", e.target.value)} placeholder="What did you do straight away?" aria-label="Immediate action" className="min-h-16 rounded-xl bg-muted/60" />
              {structure && structure.transcript_original !== fields.description_en && (
                <Collapsible>
                  <CollapsibleTrigger className="flex items-center gap-1 text-xs font-semibold text-primary">Original ({structure.original_language.toUpperCase()}) <ChevronDown className="size-3.5" /></CollapsibleTrigger>
                  <CollapsibleContent className="mt-1.5 text-sm text-muted-foreground">{structure.transcript_original}</CollapsibleContent>
                </Collapsible>
              )}
            </div>
          </BeaconSays>
        )}

        {answers.map((x, i) => (
          <div key={i} className="space-y-3">
            <BeaconSays><p className={bubble}>{x.q}</p></BeaconSays>
            <div className="flex justify-end"><p className="max-w-[80%] rounded-3xl rounded-tr-md bg-ocean px-4 py-3 text-primary-foreground">{x.a}</p></div>
          </div>
        ))}
        {question && <BeaconSays><p className={cn(bubble, "ring-2 ring-sun")}>{question}</p></BeaconSays>}

        {phase === "review" && !question && (
          <div className="flex flex-col items-end gap-1.5 rise">
            <button type="button" disabled={!fields?.title_en} onClick={() => setPhase("privacy")}
              className="inline-flex items-center gap-2 rounded-2xl border-2 border-ink/25 bg-sun px-5 py-3 font-display text-[15px] font-extrabold tracking-tight text-ink shadow-press transition active:translate-y-[3px] active:shadow-press-sm disabled:opacity-40 disabled:shadow-none">
              <Check className="size-5" strokeWidth={3} />Looks right<ArrowRight className="size-4" strokeWidth={2.5} />
            </button>
            <p className="pr-1 text-[11px] font-medium text-muted-foreground">Tap the yellow button to continue</p>
          </div>
        )}

        {(phase === "privacy" || phase === "done") && (
          <BeaconSays>
            <p className={bubble}>Last thing — who should see your name?</p>
            <div className="grid grid-cols-2 gap-2 rounded-3xl bg-card p-2 shadow-soft" role="radiogroup">
              {[false, true].map((v) => (
                <button key={String(v)} role="radio" aria-checked={share === v} disabled={phase === "done"} onClick={() => setShare(v)}
                  className={cn("rounded-2xl px-3 py-3 text-sm font-semibold transition", share === v ? "bg-ocean text-primary-foreground shadow-soft" : "text-muted-foreground hover:bg-muted")}>
                  {v ? "Share my name with the Master" : "Anonymous (recommended)"}
                </button>
              ))}
            </div>
            <p className="flex items-center gap-1.5 px-1 text-xs text-muted-foreground"><ShieldCheck className="size-3.5 text-secondary" />Shore never sees names.</p>
            {phase === "privacy" && (
              <Button className="h-14 w-full rounded-2xl bg-sunrise text-base font-bold shadow-glow" disabled={submit.isPending} onClick={send}>
                {submit.isPending ? <Loader2 className="size-5 animate-spin" /> : "Send report"}
              </Button>
            )}
          </BeaconSays>
        )}

        {phase === "done" && ticket && (
          <BeaconSays>
            <div className="rounded-3xl bg-secondary-soft p-5 shadow-soft">
              <p className="flex items-center gap-2 font-display text-lg font-bold"><PartyPopper className="size-5 text-secondary" />Thank you</p>
              <p className="mt-1 text-sm">Your Master has been alerted. Shore will receive it when the ship is online.</p>
              <p className="mt-3 inline-block rounded-full bg-card px-3 py-1 font-mono text-xs">{ticket.ticket_no}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button asChild className="rounded-full"><Link to="/reports/$id" params={{ id: ticket.id }}>View report</Link></Button>
                <Button variant="ghost" className="rounded-full" onClick={restart}>Report another</Button>
              </div>
            </div>
          </BeaconSays>
        )}
        <div ref={endRef} style={{ scrollMarginBottom: composerOn ? 176 : 104 }} />
      </div>

      {composerOn && (
        <div className="sticky bottom-24 z-10 lg:bottom-4">
          {mic.error && <div className="mb-2"><MediaErrorNote error={mic.error} kind="mic" onRetry={mic.start} fallback="You can type or attach photos instead." /></div>}
          {phase === "compose" && (audioUrl || photoUrls.length > 0) && !mic.recording && (
            <div className="mb-2 flex flex-wrap items-center gap-2 rounded-3xl bg-card/90 p-2 shadow-soft backdrop-blur">
              {audioUrl && (
                <div className="flex items-center gap-1 rounded-full bg-coral-soft py-1 pl-1 pr-2">
                  <audio src={audioUrl} controls className="h-8 w-48" />
                  <span className="text-xs tabular-nums">{fmt(mic.elapsed)}</span>
                  <button aria-label="Delete recording" onClick={() => { mic.discard(); setAudio(null); }} className="grid size-7 place-items-center rounded-full hover:bg-card"><Trash2 className="size-3.5" /></button>
                </div>
              )}
              {photoUrls.map((u, i) => (
                <div key={u} className="relative">
                  <img src={u} alt={`Photo ${i + 1}`} className="size-14 rounded-2xl object-cover" />
                  <button aria-label={`Remove photo ${i + 1}`} onClick={() => setPhotos((p) => p.filter((_, j) => j !== i))} className="absolute -right-1 -top-1 grid size-6 place-items-center rounded-full bg-ink text-ink-foreground"><X className="size-3" /></button>
                </div>
              ))}
            </div>
          )}
          <form onSubmit={(e) => { e.preventDefault(); if (question) void sendAnswer(); else if (hasInput) void sendCapture(); }}
            className="flex items-end gap-1.5 rounded-[28px] border border-card bg-card/95 p-1.5 shadow-lift backdrop-blur-xl">
            {phase === "compose" && <AttachMenu defaultOpen={start === "photo"} remaining={MAX_PHOTOS - photos.length} onAdd={(b) => setPhotos((p) => addPhotos(p, b))} />}
            {mic.recording ? (
              <div className="flex min-h-11 min-w-0 flex-1 items-center gap-2 px-2">
                <span className="size-2 shrink-0 animate-pulse rounded-full bg-coral" />
                <div className="min-w-0 flex-1 overflow-hidden"><Waveform levels={mic.levels} active /></div>
                <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{fmt(mic.elapsed)}</span>
              </div>
            ) : (
              <Textarea ref={taRef} rows={1} value={text} onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }}
                placeholder={question ? "Type your answer" : "Describe what happened…"} aria-label="Message"
                className="max-h-32 min-h-11 min-w-0 flex-1 resize-none border-0 bg-transparent py-3 text-[15px] shadow-none focus-visible:ring-0" />
            )}
            {phase === "compose" && (
              <button
                type="button"
                aria-label={mic.recording ? "Stop recording" : "Hold or tap to record voice (max 60s)"}
                onPointerDown={holdDown}
                onPointerUp={holdUp}
                onPointerCancel={holdUp}
                onClick={() => {
                  if (!mic.recording && !audio) void mic.start();
                  else if (mic.recording) mic.stop();
                }}
                className={cn(
                  "relative grid size-11 shrink-0 select-none place-items-center rounded-full transition cursor-pointer touch-none",
                  mic.recording ? "bg-coral text-primary-foreground" : "bg-coral-soft text-coral hover:bg-coral-soft/80"
                )}
              >
                {mic.recording && <span className="pulse-ring absolute inset-0 rounded-full bg-coral" />}
                {mic.recording ? <Square className="relative size-4 fill-current" /> : <Mic className="relative size-5" />}
              </button>
            )}
            <button type="submit" aria-label="Send" disabled={question ? !text.trim() || ans.isPending : !hasInput || mic.recording}
              className="grid size-11 shrink-0 place-items-center rounded-full bg-sunrise text-primary-foreground shadow-glow transition disabled:opacity-30 disabled:shadow-none cursor-pointer">
              <ArrowUp className="size-5" />
            </button>
          </form>
          {phase === "compose" && (
            <p className="mt-1.5 text-center text-[11px] text-muted-foreground">
              Hold or tap mic to record · max 60s · up to 3 photos (EXIF stripped)
            </p>
          )}
        </div>
      )}
    </div>
  );
}
