import type { ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { BookOpen, ClipboardList, Heart, Home, LayoutGrid, LogOut, Mic, Newspaper, UserRound, Users, HandHeart, ArrowLeftRight } from "lucide-react";
import { useSession } from "@/lib/session";
import { cn } from "@/lib/utils";
import { ConnectivityBanner } from "./ConnectivityBanner";
import { LiveAlerts } from "./LiveAlerts";
import { DevPanel } from "./DevPanel";
import { Logo } from "./Logo";
import { SessionRoleSwitchDialog } from "./SessionRoleSwitchDialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useState } from "react";

type To = "/home" | "/report" | "/reports" | "/wellbeing" | "/learn" | "/master/board" | "/master/brief" | "/master/welfare" | "/master/crew";
type Tone = "sun" | "coral" | "primary" | "sea" | "lavender" | "ink";
type Item = { to: To; label: string; icon: typeof Home; tone: Tone };

const toneActive: Record<Tone, string> = {
  sun: "bg-sun-soft text-accent-foreground",
  coral: "bg-coral-soft text-coral",
  primary: "bg-primary-soft text-primary",
  sea: "bg-secondary-soft text-secondary",
  lavender: "bg-lavender-soft text-lavender",
  ink: "bg-ink text-sun",
};
const toneIcon: Record<Tone, string> = {
  sun: "text-sun", coral: "text-coral", primary: "text-primary", sea: "text-secondary", lavender: "text-lavender", ink: "text-ink",
};

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { user, signOut } = useSession();
  const [roleSwitchOpen, setRoleSwitchOpen] = useState(false);
  const nav = useNavigate();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const crew: Item[] = [
    { to: "/home", label: t("nav.home"), icon: Home, tone: "sun" },
    { to: "/report", label: t("nav.report"), icon: Mic, tone: "coral" },
    { to: "/reports", label: t("nav.reports"), icon: ClipboardList, tone: "primary" },
    { to: "/wellbeing", label: t("nav.wellbeing"), icon: Heart, tone: "sea" },
    { to: "/learn", label: t("nav.learn"), icon: BookOpen, tone: "lavender" },
  ];
  const master: Item[] = [
    { to: "/master/board", label: t("nav.board"), icon: LayoutGrid, tone: "ink" },
    { to: "/master/brief", label: t("nav.brief"), icon: Newspaper, tone: "ink" },
    { to: "/master/welfare", label: t("nav.welfare"), icon: HandHeart, tone: "ink" },
    { to: "/master/crew", label: t("nav.crew"), icon: Users, tone: "ink" },
  ];
  const isMaster = user?.role === "master";
  const mobile = isMaster ? [master[0], master[1], master[3], master[2], crew[0]] : crew;
  const active = (to: string) => path === to || path.startsWith(to + "/");
  const initials = user?.name.replace("Capt. ", "").split(" ").map((p) => p[0]).slice(0, 2).join("");
  const logout = () => { signOut(); nav({ to: "/login", replace: true }); };

  return (
    <div className="min-h-dvh lg:pl-72">
      <LiveAlerts />
      <aside className="fixed inset-y-3 left-3 z-30 hidden w-66 flex-col rounded-3xl border border-card bg-card/70 px-4 py-6 shadow-soft backdrop-blur-xl lg:flex">
        <Logo className="mb-8 px-2" />
        <nav className="flex flex-col gap-1" aria-label="Main">
          {isMaster && <p className="px-3 pb-1 pt-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Master</p>}
          {isMaster && master.map((i) => <SideLink key={i.to} i={i} active={active(i.to)} />)}
          {isMaster && <p className="px-3 pb-1 pt-5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">My space</p>}
          {crew.map((i) => <SideLink key={i.to} i={i} active={active(i.to)} />)}
        </nav>
        <div className="mt-auto space-y-1">
          <button
            type="button"
            onClick={() => setRoleSwitchOpen(true)}
            className="tap flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-xs font-semibold text-ocean bg-ocean/10 hover:bg-ocean/20 transition-colors cursor-pointer"
          >
            <ArrowLeftRight className="size-4 shrink-0" />
            <span>Switch Role / PIN</span>
          </button>
          <Link to="/profile" className="tap flex items-center gap-3 rounded-2xl px-2 py-2 hover:bg-muted">
            <span className="grid size-10 place-items-center rounded-full bg-sunrise text-sm font-bold text-primary-foreground">{initials}</span>
            <span className="min-w-0 text-sm">
              <span className="block truncate font-semibold">{user?.name}</span>
              <span className="block truncate text-xs text-muted-foreground">{user?.rank}</span>
            </span>
          </Link>
          <button onClick={logout} className="tap flex w-full items-center gap-3 rounded-2xl px-3 text-sm font-medium text-muted-foreground hover:bg-coral-soft hover:text-coral cursor-pointer">
            <LogOut className="size-[18px]" />Log out
          </button>
        </div>
      </aside>

      <div className="sticky top-0 z-20 border-b border-border/40 bg-background/80 backdrop-blur-xl">
        <ConnectivityBanner />
        <div className="flex items-center justify-between px-4 py-2.5 sm:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <div className="lg:hidden shrink-0">
              <Logo size={32} />
            </div>

            {/* Top Navigation Bar Tabs for Master */}
            {isMaster && (
              <nav aria-label="Master Navigation" className="flex items-center gap-1.5 overflow-x-auto py-0.5 no-scrollbar">
                {master.map((i) => {
                  const a = active(i.to);
                  return (
                    <Link
                      key={i.to}
                      to={i.to}
                      className={cn(
                        "tap flex shrink-0 items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold transition-all",
                        a
                          ? "bg-ocean text-white shadow-soft"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      <i.icon className="size-3.5" />
                      <span>{i.label}</span>
                    </Link>
                  );
                })}
              </nav>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <DropdownMenu>
              <DropdownMenuTrigger aria-label="Account menu" className="tap grid place-items-center">
                <span className="grid size-9 place-items-center rounded-full bg-sunrise text-xs font-bold text-primary-foreground shadow-soft">
                  {initials}
                </span>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 rounded-2xl">
                <DropdownMenuLabel>
                  <span className="block truncate font-semibold">{user?.name}</span>
                  <span className="block text-xs font-normal text-muted-foreground">{user?.rank}</span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {isMaster && (
                  <DropdownMenuItem onSelect={() => nav({ to: "/master/crew" })} className="h-10 cursor-pointer">
                    <Users className="size-4 mr-2 text-ocean" />
                    Crew & Accounts
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onSelect={() => setRoleSwitchOpen(true)} className="h-10 cursor-pointer">
                  <ArrowLeftRight className="size-4 mr-2 text-ocean" />
                  Switch Role / PIN
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => nav({ to: "/profile" })} className="h-10 cursor-pointer">
                  <UserRound className="size-4 mr-2" />
                  Profile
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={logout} className="h-10 text-coral focus:text-coral cursor-pointer">
                  <LogOut className="size-4 mr-2" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      <main className="mx-auto w-full max-w-5xl px-4 pb-32 pt-4 sm:px-6 lg:pb-12 lg:pt-8">{children}</main>

      <nav aria-label="Main" className="fixed inset-x-3 bottom-[max(env(safe-area-inset-bottom),0.75rem)] z-30 flex gap-1 rounded-full border border-card bg-card/95 p-1.5 shadow-lift backdrop-blur-xl lg:hidden">
        {mobile.map((i) => {
          const a = active(i.to);
          return (
            <Link key={i.to} to={i.to} aria-label={i.label}
              className={cn("tap flex flex-1 flex-col items-center justify-center gap-0.5 rounded-full text-[10px] font-semibold transition-colors", a ? toneActive[i.tone] : "text-muted-foreground")}>
              <i.icon className="size-5" aria-hidden />
              <span className="max-w-full truncate">{i.label}</span>
            </Link>
          );
        })}
      </nav>
      <SessionRoleSwitchDialog open={roleSwitchOpen} onOpenChange={setRoleSwitchOpen} />
      <DevPanel />
    </div>
  );
}

function SideLink({ i, active }: { i: Item; active: boolean }) {
  return (
    <Link to={i.to} className={cn("tap flex items-center gap-3 rounded-2xl px-3 text-sm font-semibold transition-colors", active ? toneActive[i.tone] : "text-muted-foreground hover:bg-muted hover:text-foreground")}>
      <i.icon className={cn("size-[18px]", !active && toneIcon[i.tone])} aria-hidden />
      {i.label}
    </Link>
  );
}
