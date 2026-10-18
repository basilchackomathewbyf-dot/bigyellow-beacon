import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { LogOut, RadioTower, Search } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useFleetOverview } from "@/hooks/use-content";
import { useTickets } from "@/hooks/use-tickets";
import { authStore, useAuth } from "@/lib/auth-store";
import { relTime } from "@/lib/format";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { SeverityPill } from "./chips";

export function TopBar() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setSearch(q.trim()), 200);
    return () => clearTimeout(timer);
  }, [q]);
  const [open, setOpen] = useState(false);
  const { data: fleet } = useFleetOverview();
  const { data: results } = useTickets({ q: search }, search.length >= 2 && search === q.trim());

  const go = (id: string) => {
    setOpen(false);
    setQ("");
    navigate({ to: "/tickets/$ticketId", params: { ticketId: id } });
  };
  const initials = user?.name.split(" ").map((p) => p[0]).join("") ?? "";

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b bg-card/85 px-6 backdrop-blur xl:px-8">
      <Popover open={open && q.trim().length >= 2} onOpenChange={setOpen}>
        <PopoverAnchor asChild>
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <input
              aria-label={t("top.search")}
              placeholder={t("top.search")}
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setOpen(true);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && results?.[0]) go(results[0].id);
                if (e.key === "Escape") setOpen(false);
              }}
              className="h-10 w-full rounded-lg border bg-background pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:bg-card focus:ring-2 focus:ring-primary/15"
            />
          </div>
        </PopoverAnchor>
        <PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] min-w-96 p-1" onOpenAutoFocus={(e) => e.preventDefault()}>
          {results?.length ? (
            results.slice(0, 8).map((r) => (
              <button key={r.id} onClick={() => go(r.id)} className="flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-left text-sm hover:bg-accent">
                <SeverityPill value={r.severity} />
                <span className="font-mono text-xs text-muted-foreground">{r.ticket_no}</span>
                <span className="truncate">{r.title_en}</span>
              </button>
            ))
          ) : (
            <div className="px-3 py-4 text-sm text-muted-foreground">{t("top.noResults")}</div>
          )}
        </PopoverContent>
      </Popover>

      <div className="ml-auto flex items-center gap-4">
        {fleet && (
          <div className="flex items-center gap-2 rounded-full border bg-background px-3 py-1.5 text-xs text-muted-foreground">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-seaglass opacity-60" />
              <span className="relative inline-flex size-2 rounded-full bg-seaglass" />
            </span>
            <RadioTower className="size-3.5" aria-hidden />
            {t("top.lastSync")} <span className="font-medium text-foreground">{relTime(fleet.last_ship_sync_at)}</span>
          </div>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger aria-label={user?.name} className="flex items-center gap-2 rounded-full p-0.5 pr-3 hover:bg-accent">
            <span className="grid size-8 place-items-center rounded-full bg-primary-soft text-xs font-semibold text-primary">{initials}</span>
            <span className="text-sm font-medium max-xl:hidden">{user?.name}</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="font-medium">{user?.name}</div>
              <div className="text-xs font-normal text-muted-foreground">{user?.email} · {user?.role}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => {
                authStore.clear();
                qc.clear();
                navigate({ to: "/login" });
              }}
            >
              <LogOut /> {t("nav.signOut")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
