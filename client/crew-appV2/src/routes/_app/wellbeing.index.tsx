import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { BarChart3, Check, HeartHandshake, Loader2, Minus, Phone, Plus, Send, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { useChatTurn, useCheckinToday, useQuickCheckin, useStartChat, useTranscribe, useWelfareRequest } from "@/hooks/queries";
import type { CheckinTag } from "@/api/types";
import { MOOD_LABEL, TAGS } from "@/lib/labels";
import { moodBg, moodIcon } from "@/lib/moods";
import { PageHeader } from "@/components/beacon/bits";
import { MicButton } from "@/media/MicButton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/wellbeing/")({
  head: () => ({ meta: [{ title: "Wellbeing — Beacon" }, { name: "description", content: "A private daily check-in on how you feel." }, { property: "og:title", content: "Wellbeing — Beacon" }, { property: "og:description", content: "A private daily check-in." }] }),
  component: Wellbeing,
});

type Mood = 1 | 2 | 3 | 4 | 5;

function MoodPicker({ value, onChange }: { value: Mood | null; onChange: (m: Mood) => void }) {
  return (
    <div role="radiogroup" aria-label="Mood" className="grid grid-cols-5 gap-2">
      {([1, 2, 3, 4, 5] as Mood[]).map((m) => {
        const I = moodIcon[m];
        const on = value === m;
        return (
          <button key={m} role="radio" aria-checked={on} aria-label={MOOD_LABEL[m]} onClick={() => onChange(m)}
            className={cn("flex aspect-square flex-col items-center justify-center gap-1.5 rounded-2xl transition", on ? `${moodBg[m]} scale-105 shadow-lift` : "bg-muted hover:bg-muted/70")}>
            <I className={cn("size-6", on ? "text-ink" : "text-muted-foreground")} />
            <span className={cn("text-[10px] font-semibold leading-tight", on ? "text-ink" : "text-muted-foreground")}>{MOOD_LABEL[m]}</span>
          </button>
        );
      })}
    </div>
  );
}

function Wellbeing() {
  const today = useCheckinToday();
  const [mode, setMode] = useState<"quick" | "chat">("quick");
  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="How are you today?" subtitle="Private to you. Takes 20 seconds."
        action={<Button asChild variant="ghost" className="rounded-xl"><Link to="/wellbeing/history"><BarChart3 className="size-4" />History</Link></Button>} />
      {today.isLoading ? <Skeleton className="h-80 rounded-3xl" /> : today.data ? (
        <div className="surface flex flex-col items-center gap-3 p-10 text-center">
          <span className="grid size-14 place-items-center rounded-full bg-secondary-soft text-secondary"><Check className="size-7" /></span>
          <p className="text-lg font-semibold">You've checked in today</p>
          <p className="text-sm text-muted-foreground">Thank you. See you tomorrow.</p>
          <Button asChild variant="secondary" className="mt-2 rounded-xl"><Link to="/wellbeing/history">See my mood history</Link></Button>
        </div>
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 rounded-2xl bg-muted p-1 text-sm">
            {(["quick", "chat"] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)} className={cn("tap rounded-xl font-medium", mode === m ? "bg-card shadow-soft" : "text-muted-foreground")}>
                {m === "quick" ? "Quick" : "Chat with Beacon"}
              </button>
            ))}
          </div>
          {mode === "quick" ? <Quick /> : <Chat />}
        </>
      )}
    </div>
  );
}

function Quick() {
  const [mood, setMood] = useState<Mood | null>(null);
  const [sleep, setSleep] = useState(7);
  const [fatigue, setFatigue] = useState(3);
  const [tags, setTags] = useState<CheckinTag[]>([]);
  const m = useQuickCheckin();
  const submit = async () => {
    try {
      const r = await m.mutateAsync({ mode: "quick", mood: mood!, sleep_hours: sleep, fatigue: fatigue as Mood, tags });
      toast.success(r.queued ? "Saved on this phone — it will send soon." : "Thanks for checking in.");
    } catch { toast("You've already checked in today."); }
  };
  return (
    <div className="surface space-y-6 p-5">
      <MoodPicker value={mood} onChange={setMood} />
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Sleep last night</span>
        <div className="flex items-center gap-3">
          <Button size="icon" variant="secondary" className="size-11 rounded-xl" aria-label="Less sleep" onClick={() => setSleep((s) => Math.max(0, s - 0.5))}><Minus className="size-4" /></Button>
          <span className="w-14 text-center text-lg font-semibold tabular-nums">{sleep}h</span>
          <Button size="icon" variant="secondary" className="size-11 rounded-xl" aria-label="More sleep" onClick={() => setSleep((s) => Math.min(14, s + 0.5))}><Plus className="size-4" /></Button>
        </div>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm"><span className="font-medium">Tiredness</span><span className="text-muted-foreground">{["", "Fresh", "A little", "Some", "Tired", "Very tired"][fatigue]}</span></div>
        <Slider min={1} max={5} step={1} value={[fatigue]} onValueChange={([v]) => setFatigue(v)} aria-label="Tiredness" />
      </div>
      <div className="flex flex-wrap gap-2">
        {TAGS.map((t) => (
          <button key={t} aria-pressed={tags.includes(t)} onClick={() => setTags((x) => (x.includes(t) ? x.filter((y) => y !== t) : [...x, t]))}
            className={cn("tap rounded-full px-4 text-sm font-medium capitalize transition", tags.includes(t) ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground")}>{t}</button>
        ))}
      </div>
      <Button className="h-14 w-full rounded-2xl text-base" disabled={!mood || m.isPending} onClick={submit}>{m.isPending ? <Loader2 className="size-5 animate-spin" /> : "Check in"}</Button>
    </div>
  );
}

type Bubble = { from: "me" | "beacon"; text: string };

function Chat() {
  const [mood, setMood] = useState<Mood | null>(null);
  const [cid, setCid] = useState<string | null>(null);
  const [log, setLog] = useState<Bubble[]>([]);
  const [text, setText] = useState("");
  const [done, setDone] = useState(false);
  const [rail, setRail] = useState(false);
  const [asked, setAsked] = useState<"none" | "yes" | "no">("none");
  const start = useStartChat();
  const turn = useChatTurn();
  const tr = useTranscribe();
  const wr = useWelfareRequest();

  const begin = async (m: Mood) => {
    setMood(m);
    try {
      const r = await start.mutateAsync({ mode: "chat", mood: m });
      setCid(r.id);
      setLog([{ from: "beacon", text: r.prompt ?? "How are things?" }]);
    } catch { toast("You've already checked in today."); }
  };
  const say = async (msg: string) => {
    if (!cid || !msg.trim()) return;
    setLog((l) => [...l, { from: "me", text: msg }]);
    setText("");
    const r = await turn.mutateAsync({ id: cid, text: msg });
    if (r.rail_hit || r.safety_rail_triggered || r.offer_welfare_check) {
      setRail(true);
      setDone(true);
      return;
    }
    setLog((l) => [...l, { from: "beacon", text: r.reply }]);
    if (r.done) setDone(true);
  };
  const voice = async (b: Blob) => { if (cid) say((await tr.mutateAsync({ id: cid, audio: b })).text); };

  if (!mood) return <div className="surface space-y-4 p-5"><p className="text-sm text-muted-foreground">Pick how you feel to start.</p><MoodPicker value={null} onChange={begin} /></div>;

  return (
    <div className="surface flex flex-col p-0">
      <div className="space-y-3 p-5">
        {log.map((b, i) => (
          <div key={i} className={cn("flex gap-2", b.from === "me" && "justify-end")}>
            {b.from === "beacon" && <span className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary text-secondary-foreground"><Sparkles className="size-4" /></span>}
            <p className={cn("max-w-[80%] rounded-2xl px-4 py-2.5 text-sm", b.from === "me" ? "rounded-tr-sm bg-primary text-primary-foreground" : "rounded-tl-sm bg-secondary-soft")}>{b.text}</p>
          </div>
        ))}
        {(turn.isPending || tr.isPending || start.isPending) && <p className="pl-10 text-sm text-muted-foreground">Beacon is thinking…</p>}
        {rail && (
          <div className="space-y-4 rounded-2xl bg-secondary-soft p-5 border border-secondary/20">
            <p className="font-semibold text-foreground">You're not alone. Talking to someone can really help.</p>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2"><Phone className="size-4 text-secondary" />Master — Capt. Kundan, bridge ext. 201</li>
              <li className="flex items-center gap-2"><Phone className="size-4 text-secondary" />Medical officer — hospital ext. 310</li>
              <li className="flex items-center gap-2"><Phone className="size-4 text-secondary" />24/7 seafarer helpline — ISWAN +44 20 7323 2737</li>
            </ul>
            {asked === "none" ? (
              <div className="space-y-2 pt-2 border-t border-border/40">
                <p className="text-sm font-medium">Would you like Master to check on you?</p>
                <p className="text-xs text-muted-foreground">
                  Consented escalation only shares your name and request timestamp. Check-in scores and conversation text are never shared.
                </p>
                <div className="flex gap-2 pt-1">
                  <Button
                    className="rounded-xl bg-secondary text-secondary-foreground hover:bg-secondary/90 font-semibold"
                    onClick={async () => {
                      try {
                        await wr.mutateAsync(cid!);
                        setAsked("yes");
                        toast.success("The Master has been notified to check on you discreetly.");
                      } catch {
                        toast.error("Could not send welfare notification. Please reach out to the bridge directly.");
                      }
                    }}
                    disabled={wr.isPending}
                  >
                    Yes, notify Master
                  </Button>
                  <Button variant="ghost" className="rounded-xl" onClick={() => setAsked("no")}>No thanks</Button>
                </div>
              </div>
            ) : (
              <p className="flex items-center gap-2 text-sm text-foreground">
                <HeartHandshake className="size-4 text-secondary" />
                {asked === "yes"
                  ? "The Master has been discreetly alerted and will come check on you. Your check-in text remains private."
                  : "That's okay. These contacts and support are available anytime."}
              </p>
            )}
          </div>
        )}
      </div>
      {!done && (
        <form className="relative flex gap-2 border-t p-3" onSubmit={(e) => { e.preventDefault(); void say(text); }}>
          <MicButton onRecorded={voice} />
          <Input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type or tap the mic" className="h-11 rounded-xl" aria-label="Your reply" />
          <Button type="submit" size="icon" className="size-11 shrink-0 rounded-xl" aria-label="Send"><Send className="size-4" /></Button>
        </form>
      )}
    </div>
  );
}
