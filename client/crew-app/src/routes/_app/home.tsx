import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Anchor, ArrowRight, Camera, Clock, Cloud, GraduationCap, Keyboard, Lightbulb, Mic, ShieldAlert, Sun, BookOpen, Check, ChevronRight, Heart, HeartHandshake, Home as HomeIcon, Inbox, Lock, MessageSquare, Minus, Moon, Plus, RefreshCcw, Sparkles, Stethoscope, Users } from "lucide-react";
import { toast } from "sonner";
import { useCheckinToday, useHistory, useInbox, useInboxRead, useLearnings, useMyReports, useQuickCheckin } from "@/hooks/queries";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerTrigger } from "@/components/ui/drawer";
import { useSession } from "@/lib/session";
import { Empty, ListSkeleton, Section } from "@/components/beacon/bits";
import { QueuedNotice } from "@/components/beacon/QueuedNotice";
import { Skeleton } from "@/components/ui/skeleton";
import { MOOD_LABEL, TAGS, timeAgo } from "@/lib/labels";
import { moodBg, moodIcon } from "@/lib/moods";
import type { CheckinTag } from "@/api/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/home")({
  head: () => ({ meta: [{ title: "Home — Beacon" }, { name: "description", content: "Your day on board at a glance." }, { property: "og:title", content: "Home — Beacon" }, { property: "og:description", content: "Your day on board at a glance." }] }),
  component: Home,
});

type Mood = 1 | 2 | 3 | 4 | 5;
const tagIcon: Record<CheckinTag, typeof Moon> = { rest: Moon, workload: Anchor, home: HomeIcon, family: Heart, health: Stethoscope, team: Users };

function CheckinForm({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const m = useQuickCheckin();
  const [mood, setMood] = useState<Mood | null>(null);
  const [sleep, setSleep] = useState(7);
  const [tags, setTags] = useState<CheckinTag[]>([]);

  const send = async () => {
    if (!mood) return;
    try {
      const r = await m.mutateAsync({ mode: "quick", mood, sleep_hours: sleep, fatigue: 3 as Mood, tags });
      toast.success(r.queued ? t("home.queuedTitle") : t("home.doneToday"));
      onDone();
    } catch { toast(t("home.doneToday")); }
  };

  return (
    <div className="flex flex-col gap-4 px-5 pb-6">
      <div className="flex items-center gap-3">
        <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-coral-soft text-coral"><HeartHandshake className="size-6" /></span>
        <div className="min-w-0">
          <p className="font-display text-base font-bold">{t("home.howAreYou")}</p>
          <p className="flex items-center gap-1 text-xs text-muted-foreground"><Lock className="size-3" />{t("home.privateNote")}</p>
        </div>
      </div>

      <div role="radiogroup" aria-label={t("home.moodPrompt")} className="grid grid-cols-5 gap-1.5 sm:gap-2">
        {([1, 2, 3, 4, 5] as Mood[]).map((v) => {
          const I = moodIcon[v];
          const on = mood === v;
          return (
            <button key={v} type="button" role="radio" aria-checked={on} aria-label={MOOD_LABEL[v]} onClick={() => setMood(v)}
              className={cn("flex flex-col items-center gap-1.5 rounded-2xl px-1 py-3 transition", on ? cn(moodBg[v], "scale-[1.05] shadow-lift") : "bg-muted/60 hover:bg-muted")}>
              <I className={cn("size-6", on ? "text-ink" : "text-muted-foreground")} />
              <span className={cn("text-[10px] font-semibold leading-tight", on ? "text-ink" : "text-muted-foreground")}>{MOOD_LABEL[v]}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-3 rounded-2xl bg-muted/50 p-2.5">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-lavender-soft text-lavender"><Moon className="size-4" /></span>
        <span className="min-w-0 flex-1 text-sm font-semibold">{t("home.slept")}</span>
        <button type="button" aria-label="Less sleep" onClick={() => setSleep((s) => Math.max(0, s - 0.5))} className="grid size-8 place-items-center rounded-full bg-card text-muted-foreground shadow-soft"><Minus className="size-3.5" /></button>
        <span className="w-12 text-center font-display text-base font-bold tabular-nums">{sleep}h</span>
        <button type="button" aria-label="More sleep" onClick={() => setSleep((s) => Math.min(14, s + 0.5))} className="grid size-8 place-items-center rounded-full bg-card text-muted-foreground shadow-soft"><Plus className="size-3.5" /></button>
      </div>

      <div className="min-w-0">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{t("home.tagsPrompt")}</p>
        <div className="flex flex-wrap gap-1.5">
          {TAGS.map((tg) => {
            const I = tagIcon[tg];
            const on = tags.includes(tg);
            return (
              <button key={tg} type="button" aria-pressed={on} onClick={() => setTags((x) => (on ? x.filter((y) => y !== tg) : [...x, tg]))}
                className={cn("tap inline-flex items-center gap-1.5 rounded-full px-3 text-sm font-medium capitalize transition", on ? "bg-secondary text-secondary-foreground shadow-soft" : "bg-muted text-muted-foreground hover:bg-muted/70")}>
                <I className="size-3.5" />{tg}
              </button>
            );
          })}
        </div>
      </div>

      <button type="button" disabled={!mood || m.isPending} onClick={() => void send()}
        className="mt-auto inline-flex h-13 w-full items-center justify-center gap-2 rounded-2xl bg-sunrise font-display text-base font-bold text-primary-foreground shadow-glow transition disabled:opacity-40 disabled:shadow-none">
        {t("home.checkinBtn")}<ArrowRight className="size-4" />
      </button>
    </div>
  );
}

function CheckinTile() {
  const { t } = useTranslation();
  const today = useCheckinToday();
  const hist = useHistory("7d");
  const [open, setOpen] = useState(false);
  const [burst, setBurst] = useState(false);
  if (today.isLoading) return <Skeleton className="h-24 rounded-3xl" />;
  const last = hist.data?.entries.at(-1);
  if (today.data) {
    const I = last ? moodIcon[last.mood] : Sun;
    return (
      <div className="surface flex items-center gap-3 p-4">
        <span className={cn("grid size-12 shrink-0 place-items-center rounded-2xl text-ink", last ? moodBg[last.mood] : "bg-sun", burst && "sun-burst")}><I className="size-6" /></span>
        <div className="min-w-0 flex-1">
          <p className="font-display text-base font-bold">Checked in today</p>
          {hist.data && <p className="flex items-center gap-1 text-sm text-muted-foreground"><Sparkles className="size-3.5 text-warn" />{t("home.streak", { n: hist.data.streak })}</p>}
        </div>
        <ButtonLink to="/wellbeing" label={t("home.talk")} />
      </div>
    );
  }
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>
        <button type="button" className="surface flex w-full items-center gap-3 p-4 text-left transition hover:shadow-lift">
          <span className="relative grid size-12 shrink-0 place-items-center overflow-hidden rounded-2xl bg-sun-soft">
            <Sun className="absolute size-7 text-warn" />
            <Cloud className="sky-drift absolute bottom-1.5 left-1.5 size-6 fill-card text-lavender" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-display text-base font-bold">{t("home.howAreYou")}</p>
            <p className="flex items-center gap-1 text-sm text-muted-foreground"><Lock className="size-3" />10-second private check-in</p>
          </div>
          <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
        </button>
      </DrawerTrigger>
      <DrawerContent className="mx-auto max-w-lg">
        <DrawerHeader><DrawerTitle className="font-display text-xl">{t("home.howAreYou")}</DrawerTitle></DrawerHeader>
        <CheckinForm onDone={() => { setOpen(false); setBurst(true); }} />
      </DrawerContent>
    </Drawer>
  );
}

function ReportHero() {
  const mine = useMyReports();
  const now = new Date();
  const n = mine.data?.filter((r) => { const d = new Date(r.created_at); return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear(); }).length ?? 0;
  const opts = [
    { start: "voice" as const, label: "Speak", icon: Mic, pulse: true },
    { start: "text" as const, label: "Type", icon: Keyboard, pulse: false },
    { start: "photo" as const, label: "Photo", icon: Camera, pulse: false },
  ];
  return (
    <section className="relative overflow-hidden rounded-3xl bg-sunrise p-5 text-primary-foreground shadow-glow">
      <div aria-hidden className="pointer-events-none absolute -right-10 -top-10 size-40 rounded-full bg-card/15" />
      <div className="relative flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em]"><ShieldAlert className="size-4" />Near-miss</div>
      <h2 className="relative mt-1.5 font-display text-2xl font-extrabold leading-tight">Seen something unsafe?</h2>
      <p className="relative text-sm opacity-90">Report it in 30 seconds. Every report keeps the crew safer.</p>
      <div className="relative mt-4 grid grid-cols-3 gap-2">
        {opts.map((o) => (
          <Link key={o.start} to="/report" search={{ start: o.start }} className="flex flex-col items-center gap-1.5 rounded-2xl bg-card py-3 text-foreground shadow-soft transition active:scale-95">
            <span className={cn("grid size-10 place-items-center rounded-full bg-coral-soft text-coral", o.pulse && "soft-pulse")}><o.icon className="size-5" /></span>
            <span className="text-sm font-bold">{o.label}</span>
          </Link>
        ))}
      </div>
      <div className="relative mt-3 flex items-center justify-between text-sm">
        <span className="opacity-90">Your reports this month: <b>{n}</b></span>
        <Link to="/reports" className="inline-flex items-center gap-0.5 font-semibold underline-offset-2 hover:underline">My reports<ChevronRight className="size-4" /></Link>
      </div>
    </section>
  );
}

const forYouTint = ["from-lavender-soft to-primary-soft text-lavender", "from-secondary-soft to-sun-soft text-secondary", "from-coral-soft to-sun-soft text-coral"];
const forYouIcon = [Lightbulb, GraduationCap, BookOpen];

function ForYou() {
  const today = useCheckinToday();
  const ls = useLearnings();
  if (!today.data) {
    return <div className="surface flex items-center gap-3 p-4 text-sm text-muted-foreground"><Sparkles className="size-5 text-lavender" />Check in to see what's for you today.</div>;
  }
  if (ls.isLoading) return <ListSkeleton n={2} />;
  const todo = (ls.data ?? []).filter((l) => !l.acked);
  if (todo.length === 0) {
    return (
      <Link to="/learn" className="surface flex items-center gap-3 p-4">
        <span className="grid size-11 place-items-center rounded-2xl bg-secondary-soft text-secondary"><Check className="size-5" /></span>
        <span className="min-w-0 flex-1"><span className="block font-display font-bold">All caught up</span><span className="block text-sm text-muted-foreground">Browse past learnings</span></span>
        <ChevronRight className="size-5 text-muted-foreground" />
      </Link>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {todo.map((l, i) => {
        const I = forYouIcon[i % 3];
        return (
          <Link key={l.id} to="/learn/$id" params={{ id: l.id }} className="surface rise flex flex-col overflow-hidden p-0 transition hover:shadow-lift">
            <div className={cn("relative flex h-24 items-center justify-center bg-gradient-to-br", forYouTint[i % 3])}>
              <I className="size-10" />
              {l.priority === "urgent" && <span className="absolute left-3 top-3 rounded-full bg-coral px-2 py-0.5 text-[10px] font-bold uppercase text-primary-foreground">Urgent</span>}
              <span className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-full bg-card/90 px-2 py-0.5 text-[11px] font-semibold text-foreground"><Clock className="size-3" />{2 + l.do_points.length} min</span>
            </div>
            <div className="flex flex-1 items-center gap-3 p-4">
              <span className="size-2.5 shrink-0 rounded-full bg-sun" aria-label="Not finished" />
              <span className="min-w-0 flex-1"><span className="block truncate font-display font-bold">{l.title}</span><span className="block truncate text-sm text-muted-foreground">{l.context}</span></span>
              <ArrowRight className="size-4 shrink-0 text-primary" />
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function ButtonLink({ to, label }: { to: "/wellbeing"; label: string }) {
  return (
    <Link to={to} className="tap inline-flex items-center gap-1.5 rounded-full bg-secondary-soft px-3 py-1.5 text-sm font-semibold text-secondary">
      {label}<ChevronRight className="size-4" />
    </Link>
  );
}

function Home() {
  const { t } = useTranslation();
  const { user } = useSession();
  const inbox = useInbox();
  const read = useInboxRead();
  const h = new Date().getHours();
  const greet = t(h < 12 ? "home.greeting_morning" : h < 18 ? "home.greeting_afternoon" : "home.greeting_evening");
  const unread = inbox.data?.filter((i) => !i.read) ?? [];
  const icon = { shore_reply: MessageSquare, master_reply: MessageSquare, status_change: RefreshCcw, learning: BookOpen };

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-sunrise font-display text-lg font-extrabold text-primary-foreground shadow-glow">
          {(user?.name ?? "?").slice(0, 1)}
        </span>
        <div className="min-w-0">
          <p className="truncate text-xs text-muted-foreground">
            {new Date().toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })} · {user?.vessel}
          </p>
          <h1 className="truncate font-display text-2xl font-extrabold tracking-tight">{greet}, {user?.role === "master" ? "Captain" : user?.name.split(" ")[0]}</h1>
        </div>
      </header>

      <QueuedNotice />

      <ReportHero />

      <Section title="Daily check-in"><CheckinTile /></Section>

      <Section title="For you"><ForYou /></Section>

      <div className="grid grid-cols-1 items-stretch gap-6">

        <Section title="Inbox">
          <div className="surface flex h-full min-h-64 flex-col overflow-hidden p-0">
            {inbox.isLoading ? (
              <div className="p-4"><ListSkeleton n={3} /></div>
            ) : unread.length === 0 ? (
              <div className="flex flex-1 items-center justify-center p-6"><Empty icon={<Inbox className="size-5" />} text={t("home.noInbox")} /></div>
            ) : (
              <ul className="divide-y overflow-y-auto">
                {unread.map((i) => {
                  const I = icon[i.kind];
                  const inner = (
                    <>
                      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary"><I className="size-[18px]" /></span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold">{i.title}</span>
                        <span className="block truncate text-sm text-muted-foreground">{i.body}</span>
                      </span>
                      <span className="shrink-0 text-xs text-muted-foreground">{timeAgo(i.created_at)}</span>
                    </>
                  );
                  const cls = "flex w-full items-center gap-3 p-4 text-left hover:bg-muted/50";
                  return (
                    <li key={i.id}>
                      {i.link?.to === "/learn/$id" ? (
                        <Link to="/learn/$id" params={{ id: i.link.id! }} className={cls} onClick={() => read.mutate(i.id)}>{inner}</Link>
                      ) : i.link?.to === "/reports/$id" ? (
                        <Link to="/reports/$id" params={{ id: i.link.id! }} className={cls} onClick={() => read.mutate(i.id)}>{inner}</Link>
                      ) : <button className={cls} onClick={() => read.mutate(i.id)}>{inner}</button>}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Section>
      </div>

    </div>
  );
}
