import { useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Link2, Inbox } from "lucide-react";
import type { Severity, Ticket, TicketFilters } from "@/api/types";
import { useTickets } from "@/hooks/use-tickets";
import { relTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { OnboardChip, PageHeader, SeverityPill, ShoreChip } from "@/components/beacon/chips";
import { Skeleton } from "@/components/ui/skeleton";
import type { QueueSearch } from "@/routes/_shell.tickets.index";
import { TicketFiltersBar } from "./ticket-filters";

const TABS = ["NEW", "IN_REVIEW", "REJECTED", "CLOSED", "ALL"] as const;
const col = createColumnHelper<Ticket>();

export function TicketQueue({ search }: { search: QueueSearch }) {
  const { t } = useTranslation();
  const navigate = useNavigate({ from: "/tickets/" });
  const status = search.status ?? "NEW";

  const baseFilters: TicketFilters = useMemo(
    () => ({
      vessel_id: search.vessel,
      severity: search.severity,
      hazard_type: search.hazard,
      ism_category: search.ism,
      q: search.q,
      from: search.days ? new Date(Date.now() - search.days * 86400_000).toISOString() : undefined,
    }),
    [search.vessel, search.severity, search.hazard, search.ism, search.q, search.days],
  );
  const { data: all, isLoading, isError, refetch } = useTickets(baseFilters);
  const rows = useMemo(() => (all ?? []).filter((r) => status === "ALL" || r.shore_status === status), [all, status]);
  const counts = useMemo(() => {
    const c: Record<string, number> = { ALL: all?.length ?? 0 };
    all?.forEach((r) => (c[r.shore_status] = (c[r.shore_status] ?? 0) + 1));
    return c;
  }, [all]);

  const sevGroups = useMemo(() => {
    const inTab = (all ?? []).filter((r) => status === "ALL" || r.shore_status === status);
    const n = (vs: number[]) => inTab.filter((r) => vs.includes(r.severity)).length;
    return [
      { key: "high", values: [4, 5] as Severity[], bar: "bg-severity-high", count: n([4, 5]) },
      { key: "mid", values: [3] as Severity[], bar: "bg-severity-mid", count: n([3]) },
      { key: "low", values: [1, 2] as Severity[], bar: "bg-severity-low", count: n([1, 2]) },
    ];
  }, [all, status]);

  const columns = useMemo(
    () => [
      col.accessor("severity", { header: t("tickets.col.severity"), cell: (c) => <SeverityPill value={c.getValue()} />, size: 64 }),
      col.accessor("ticket_no", { header: t("tickets.col.no"), cell: (c) => <span className="font-mono text-xs text-muted-foreground">{c.getValue()}</span>, size: 130 }),
      col.accessor("title_en", {
        header: t("tickets.col.title"),
        cell: (c) => <span className="line-clamp-1 font-medium text-foreground">{c.getValue()}</span>,
      }),
      col.accessor((r) => r.vessel.name, { id: "vessel", header: t("tickets.col.vessel"), cell: (c) => <span className="whitespace-nowrap">{c.getValue()}</span>, size: 150 }),
      col.accessor("hazard_type", { header: t("tickets.col.hazard"), cell: (c) => <span className="whitespace-nowrap text-muted-foreground">{t(`hazard.${c.getValue()}`)}</span>, size: 140 }),
      col.accessor("onboard_status", { header: t("tickets.col.onboard"), cell: (c) => <OnboardChip value={c.getValue()} />, size: 160 }),
      col.accessor("shore_status", { header: t("tickets.col.shore"), cell: (c) => <ShoreChip value={c.getValue()} />, size: 100 }),
      col.accessor("received_at", { header: t("tickets.col.received"), cell: (c) => <span className="whitespace-nowrap text-muted-foreground">{relTime(c.getValue())}</span>, size: 110 }),
      col.accessor("similar_count", {
        header: t("tickets.col.similar"),
        cell: (c) =>
          c.getValue() > 0 ? (
            <span className="inline-flex items-center gap-1 text-primary" aria-label={t("tickets.similarAria", { count: c.getValue() })}>
              <Link2 className="size-3.5" aria-hidden />
              <span className="text-xs font-semibold tabular-nums">{c.getValue()}</span>
            </span>
          ) : (
            <span className="text-muted-foreground/50">—</span>
          ),
        size: 70,
      }),
    ],
    [t],
  );
  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel(), getRowId: (r) => r.id });

  // j/k keyboard navigation
  const [cursor, setCursor] = useState(0);
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);
  useEffect(() => {
    setCursor(0);
  }, [status, rows.length]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable) return;
      if (e.metaKey || e.ctrlKey || e.altKey || document.querySelector('[role="dialog"]')) return;
      if (e.key === "j") setCursor((c) => Math.min(rows.length - 1, c + 1));
      else if (e.key === "k") setCursor((c) => Math.max(0, c - 1));
      else if (e.key === "Enter" && rows[cursor]) navigate({ to: "/tickets/$ticketId", params: { ticketId: rows[cursor].id } });
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rows, cursor, navigate]);
  useEffect(() => {
    rowRefs.current[cursor]?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  return (
    <div>
      <PageHeader title={t("tickets.title")} subtitle={t("tickets.subtitle")} actions={<span className="text-xs text-muted-foreground">{t("tickets.keyboardHint")}</span>} />

      <div role="tablist" className="mb-4 flex gap-1 border-b">
        {TABS.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={status === s}
            onClick={() => navigate({ to: ".", search: (p) => ({ ...p, status: s }) })}
            className={cn(
              "relative -mb-px flex items-center gap-2 border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground",
              status === s && "border-primary text-foreground",
            )}
          >
            {t(`status.${s}`)}
            <span className={cn("rounded-full px-1.5 text-[11px] tabular-nums", status === s ? "bg-primary text-primary-foreground" : "bg-muted")}>{counts[s] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        {sevGroups.map((g) => {
          const active = JSON.stringify(search.severity ?? []) === JSON.stringify(g.values);
          return (
            <button
              key={g.key}
              onClick={() => navigate({ to: ".", search: (p) => ({ ...p, severity: active ? undefined : g.values }) })}
              aria-pressed={active}
              className={cn(
                "surface-card flex items-center gap-3 p-4 text-left transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-lift)]",
                active && "ring-2 ring-primary",
              )}
            >
              <span className={cn("h-10 w-1.5 rounded-full", g.bar)} aria-hidden />
              <div>
                <div className="text-2xl font-semibold tabular-nums">{g.count}</div>
                <div className="text-xs text-muted-foreground">{t(`tickets.sevSummary.${g.key}`)}</div>
              </div>
            </button>
          );
        })}
      </div>

      <TicketFiltersBar search={search} />

      <div className="surface-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} style={{ width: h.id === "title_en" ? undefined : h.getSize() }} className="h-10 px-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td colSpan={columns.length} className="h-10 px-3">
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              ))}
            {isError && (
              <tr>
                <td colSpan={columns.length} className="p-8 text-center text-sm text-muted-foreground">
                  {t("common.error")}{" "}
                  <button className="font-medium text-primary underline" onClick={() => refetch()}>
                    {t("common.retry")}
                  </button>
                </td>
              </tr>
            )}
            {!isLoading && rows.length === 0 && !isError && (
              <tr>
                <td colSpan={columns.length} className="p-14 text-center">
                  <Inbox className="mx-auto mb-2 size-8 text-muted-foreground/50" aria-hidden />
                  <p className="text-sm text-muted-foreground">{t("tickets.empty")}</p>
                </td>
              </tr>
            )}
            {table.getRowModel().rows.map((row, i) => (
              <tr
                key={row.id}
                ref={(el) => {
                  rowRefs.current[i] = el;
                }}
                tabIndex={0}
                aria-selected={cursor === i}
                onClick={() => navigate({ to: "/tickets/$ticketId", params: { ticketId: row.id } })}
                onKeyDown={(e) => e.key === "Enter" && navigate({ to: "/tickets/$ticketId", params: { ticketId: row.id } })}
                onFocus={() => setCursor(i)}
                className={cn(
                  "h-10 cursor-pointer border-b transition-colors last:border-0 hover:bg-primary-soft/60",
                  cursor === i && "bg-primary-soft/70 shadow-[inset_3px_0_0_var(--color-primary)]",
                  row.original.shore_status === "NEW" && "font-medium",
                  row.original.severity >= 4 ? "shadow-[inset_3px_0_0_var(--color-severity-high)]" : row.original.severity === 3 ? "shadow-[inset_3px_0_0_var(--color-severity-mid)]" : "",
                )}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-1.5">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
