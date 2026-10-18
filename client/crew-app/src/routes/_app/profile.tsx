import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { Bell, CalendarCheck, ChevronRight, Flame, Lightbulb, LogOut, ArrowLeftRight, Ship, ShieldCheck, Crown, Users } from "lucide-react";
import { toast } from "sonner";
import { useSession } from "@/lib/session";
import { useUpdatePrefs, useHistory } from "@/hooks/queries";
import { LANGUAGES } from "@/i18n";
import type { Language } from "@/api/types";
import { MOOD_LABEL } from "@/lib/labels";
import { moodBg, moodIcon } from "@/lib/moods";
import { PageHeader, Empty } from "@/components/beacon/bits";
import { SessionRoleSwitchDialog } from "@/components/beacon/SessionRoleSwitchDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/profile")({
  head: () => ({ meta: [{ title: "Profile — Beacon" }, { name: "description", content: "Language, app settings and your check-in journey." }, { property: "og:title", content: "Profile — Beacon" }, { property: "og:description", content: "Your settings and daily check-in journey." }] }),
  component: Profile,
});


function CheckinJourney() {
  const { t } = useTranslation();
  const q = useHistory("30d");
  const days = 14;
  const cells = Array.from({ length: days }, (_, i) => new Date(Date.now() - (days - 1 - i) * 86_400_000).toISOString().slice(0, 10));

  if (q.isLoading) return <Skeleton className="h-52 rounded-3xl" />;
  const data = q.data;
  if (!data || data.entries.length === 0) {
    return (
      <div className="surface p-5">
        <p className="mb-3 font-display text-base font-bold">{t("home.journey")}</p>
        <Empty icon={<CalendarCheck className="size-5" />} text={t("home.checkinCta")} />
      </div>
    );
  }

  const byDate = new Map(data.entries.map((e) => [e.date, e]));
  const done = cells.filter((d) => byDate.has(d)).length;

  return (
    <div className="surface space-y-4 p-5">
      <div className="flex items-center gap-3">
        <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sun-soft text-warn"><CalendarCheck className="size-6" /></span>
        <div className="min-w-0 flex-1">
          <p className="font-display text-base font-bold">{t("home.journey")}</p>
          <p className="truncate text-xs text-muted-foreground">{t("home.privateNote")}</p>
        </div>
        <Link to="/wellbeing/history" className="tap inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted/70">
          {t("home.viewHistory")}<ChevronRight className="size-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-2xl bg-coral-soft p-3">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-coral"><Flame className="size-3.5" />{t("home.streakLabel")}</p>
          <p className="mt-1 font-display text-2xl font-extrabold text-foreground">{data.streak}</p>
        </div>
        <div className="rounded-2xl bg-secondary-soft p-3">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-secondary"><CalendarCheck className="size-3.5" />{t("home.checkinsLabel")}</p>
          <p className="mt-1 font-display text-2xl font-extrabold text-foreground">{done}<span className="text-sm font-semibold text-muted-foreground">/{days}</span></p>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1.5">
        {cells.map((d, i) => {
          const e = byDate.get(d);
          const I = e ? moodIcon[e.mood] : null;
          return (
            <div key={d} className="flex flex-col items-center gap-1">
              <span title={`${d}${e ? ` · ${MOOD_LABEL[e.mood]}` : ""}`} className={cn("grid aspect-square w-full place-items-center rounded-2xl shadow-soft transition", e ? moodBg[e.mood] : "bg-muted")}>
                {I ? <I className="size-4 text-ink/75" /> : <span className="text-muted-foreground">·</span>}
              </span>
              <span className={cn("text-[10px] font-semibold tabular-nums", i === cells.length - 1 ? "text-foreground" : "text-muted-foreground")}>{new Date(d).getDate()}</span>
            </div>
          );
        })}
      </div>

      {data.top_tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {data.top_tags.slice(0, 4).map((x) => <span key={x.tag} className="rounded-full bg-lavender-soft px-3 py-1 text-xs font-semibold capitalize text-lavender">{x.tag} · {x.count}</span>)}
        </div>
      )}

      <p className="flex items-start gap-2 rounded-2xl bg-accent p-3 text-sm text-foreground"><Lightbulb className="mt-0.5 size-4 shrink-0 text-accent-foreground" />{data.insight}</p>
    </div>
  );
}

function Profile() {
  const { t, i18n } = useTranslation();
  const { user, update, signOut } = useSession();
  const [roleSwitchOpen, setRoleSwitchOpen] = useState(false);
  const prefs = useUpdatePrefs();
  const nav = useNavigate();
  const setLang = async (l: Language) => { await i18n.changeLanguage(l); update(await prefs.mutateAsync({ language: l })); };

  const isMaster = user?.role === "master";
  const rankBand = user?.rank_band || (isMaster ? "Officer" : "Rating");

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="space-y-2">
        <PageHeader title={user!.name} subtitle={`${user!.rank} · ${user!.vessel}`} />
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-ocean/10 px-3 py-1 text-xs font-bold text-ocean">
            <ShieldCheck className="size-3.5" />
            Rank Band: {rankBand}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs font-semibold text-muted-foreground">
            <Ship className="size-3.5" />
            {user?.vessel || "MV-PACIFIC-STAR"}
          </span>
        </div>
      </div>

      {/* Terminal Watch Session & Role Switcher */}
      <div className="surface space-y-3 p-5 border border-border/80">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Active Watch Station</p>
            <div className="flex items-center gap-2 mt-0.5">
              {isMaster ? <Crown className="size-4 text-amber-600" /> : <Users className="size-4 text-ocean" />}
              <span className="text-sm font-bold text-foreground">
                {isMaster ? "Master Command (Bridge)" : "Crew Watch (Deck/Engine)"}
              </span>
            </div>
          </div>
          <span className="rounded-xl bg-muted px-2.5 py-1 text-[11px] font-semibold text-muted-foreground">
            {isMaster ? "6-digit PIN" : "4-digit PIN"}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Switch active watch role or authenticate another crew member on this shipboard terminal.
        </p>
        <Button
          type="button"
          variant="outline"
          className="w-full gap-2 rounded-xl text-xs font-bold text-ocean border-ocean/30 bg-ocean/5 hover:bg-ocean/10 cursor-pointer"
          onClick={() => setRoleSwitchOpen(true)}
        >
          <ArrowLeftRight className="size-4" />
          Switch Role / User PIN
        </Button>
      </div>

      <CheckinJourney />

      <div className="surface space-y-3 p-5">
        <p className="text-sm font-semibold">{t("common.language")}</p>
        <div className="grid grid-cols-2 gap-2">
          {LANGUAGES.map((l) => (
            <button key={l.code} onClick={() => setLang(l.code)} className={cn("tap rounded-xl border font-medium", i18n.language === l.code ? "border-primary bg-primary-soft text-primary" : "")}>{l.label}</button>
          ))}
        </div>
      </div>
      {user!.role === "master" && (
        <Button variant="secondary" className="h-12 w-full rounded-xl" onClick={async () => {
          if (!("Notification" in window)) { toast("This browser can't show alerts."); return; }
          const p = await Notification.requestPermission();
          toast(p === "granted" ? "Alerts are on." : "Alerts stay off.");
        }}><Bell className="size-4" />Allow near-miss alerts</Button>
      )}
      <Button variant="ghost" className="h-12 w-full rounded-xl text-muted-foreground" onClick={() => { signOut(); nav({ to: "/login", replace: true }); }}><LogOut className="size-4" />{t("common.signOut")}</Button>

      <SessionRoleSwitchDialog open={roleSwitchOpen} onOpenChange={setRoleSwitchOpen} />
    </div>
  );
}
