import { useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { ChevronDown, X } from "lucide-react";
import type { HazardType, IsmCategory, Severity } from "@/api/types";
import { useVessels } from "@/hooks/use-content";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { QueueSearch } from "@/routes/_shell.tickets.index";

const HAZARDS: HazardType[] = ["slip_trip_fall", "mooring", "crane_lifting", "enclosed_space", "fire", "machinery", "electrical", "chemical", "other"];
const ISMS: IsmCategory[] = ["unsafe_act", "unsafe_condition", "equipment_failure", "procedure_gap"];
const SEVS: Severity[] = [5, 4, 3, 2, 1];

function MultiFilter<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value?: T[];
  onChange: (v: T[] | undefined) => void;
}) {
  const sel = value ?? [];
  const toggle = (v: T) => {
    const next = sel.includes(v) ? sel.filter((x) => x !== v) : [...sel, v];
    onChange(next.length ? next : undefined);
  };
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className={cn(
            "inline-flex h-8 items-center gap-1.5 rounded-lg border bg-card px-3 text-sm text-muted-foreground transition hover:border-primary/40 hover:text-foreground",
            sel.length && "border-primary/40 bg-primary-soft text-primary",
          )}
        >
          {label}
          {sel.length > 0 && <span className="rounded-full bg-primary px-1.5 text-[11px] text-primary-foreground">{sel.length}</span>}
          <ChevronDown className="size-3.5" aria-hidden />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-60 p-1.5">
        {options.map((o) => (
          <label key={String(o.value)} className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm hover:bg-accent">
            <Checkbox checked={sel.includes(o.value)} onCheckedChange={() => toggle(o.value)} />
            {o.label}
          </label>
        ))}
      </PopoverContent>
    </Popover>
  );
}

export function TicketFiltersBar({ search }: { search: QueueSearch }) {
  const { t } = useTranslation();
  const navigate = useNavigate({ from: "/tickets/" });
  const { data: vessels } = useVessels();
  const set = (patch: Partial<QueueSearch>) => navigate({ to: ".", search: (p) => ({ ...p, ...patch }), replace: true });
  const active = !!(search.vessel || search.severity || search.hazard || search.ism || search.days || search.q);

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <MultiFilter label={t("tickets.filter.vessel")} options={(vessels ?? []).map((v) => ({ value: v.id, label: v.name }))} value={search.vessel} onChange={(vessel) => set({ vessel })} />
      <MultiFilter label={t("tickets.filter.severity")} options={SEVS.map((s) => ({ value: s, label: `${t("severity.label")} ${s}` }))} value={search.severity} onChange={(severity) => set({ severity })} />
      <MultiFilter label={t("tickets.filter.hazard")} options={HAZARDS.map((h) => ({ value: h, label: t(`hazard.${h}`) }))} value={search.hazard} onChange={(hazard) => set({ hazard })} />
      <MultiFilter label={t("tickets.filter.ism")} options={ISMS.map((h) => ({ value: h, label: t(`ism.${h}`) }))} value={search.ism} onChange={(ism) => set({ ism })} />
      <div className="inline-flex h-8 items-center rounded-lg border bg-card p-0.5 text-sm">
        {[undefined, 7, 30].map((d) => (
          <button
            key={String(d)}
            onClick={() => set({ days: d })}
            className={cn("h-full rounded-md px-2.5 text-muted-foreground transition", search.days === d && "bg-primary-soft text-primary font-medium")}
          >
            {d === undefined ? t("tickets.filter.anytime") : d === 7 ? t("tickets.filter.last7") : t("tickets.filter.last30")}
          </button>
        ))}
      </div>
      {active && (
        <Button variant="ghost" size="sm" onClick={() => navigate({ to: ".", search: (p) => ({ status: p.status }) })}>
          <X /> {t("common.clear")}
        </Button>
      )}
    </div>
  );
}
