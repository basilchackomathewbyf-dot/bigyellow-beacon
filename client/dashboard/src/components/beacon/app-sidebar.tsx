import { Link } from "@tanstack/react-router";
import { Anchor, BookOpenCheck, Inbox, LayoutDashboard, Ship } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useTickets } from "@/hooks/use-tickets";
import { useAuth } from "@/lib/auth-store";

const linkCls =
  "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground";
const activeCls = "bg-sidebar-accent text-sidebar-accent-foreground shadow-[inset_3px_0_0_var(--color-sidebar-primary)]";

export function AppSidebar() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { data: newTickets } = useTickets({ status: "NEW" });

  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col bg-sidebar px-3 py-5 max-lg:w-16">
      <div className="mb-8 flex items-center gap-2.5 px-2">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl sea-gradient text-primary-foreground">
          <Anchor className="size-5" aria-hidden />
        </span>
        <div className="max-lg:hidden">
          <div className="font-semibold tracking-tight text-sidebar-accent-foreground">{t("app.name")}</div>
          <div className="text-[11px] text-sidebar-foreground/70">{t("app.tagline")}</div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1" aria-label="Main">
        <Link to="/tickets" className={linkCls} activeProps={{ className: activeCls }}>
          <Inbox className="size-4 shrink-0" aria-hidden />
          <span className="flex-1 max-lg:hidden">{t("nav.tickets")}</span>
          {!!newTickets?.length && (
            <span className="rounded-full bg-sidebar-primary px-1.5 text-[11px] font-semibold tabular-nums text-sidebar-primary-foreground animate-pulse-ring max-lg:hidden">
              {newTickets.length}
            </span>
          )}
        </Link>
        <Link to="/fleet" className={linkCls} activeProps={{ className: activeCls }}>
          <LayoutDashboard className="size-4 shrink-0" aria-hidden />
          <span className="max-lg:hidden">{t("nav.fleet")}</span>
        </Link>
        <Link to="/learnings" className={linkCls} activeProps={{ className: activeCls }}>
          <BookOpenCheck className="size-4 shrink-0" aria-hidden />
          <span className="max-lg:hidden">{t("nav.learnings")}</span>
        </Link>
        {user?.role === "admin" && (
          <>
            <div className="mt-6 mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/60 max-lg:hidden">{t("nav.settings")}</div>
            <Link to="/settings/vessels" className={linkCls} activeProps={{ className: activeCls }}>
              <Ship className="size-4 shrink-0" aria-hidden />
              <span className="max-lg:hidden">{t("nav.vessels")}</span>
            </Link>
          </>
        )}
      </nav>
    </aside>
  );
}
