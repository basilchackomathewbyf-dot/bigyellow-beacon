import { useState } from "react";
import { Settings2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { USE_MOCK } from "@/api/config";
import * as sim from "@/api/mock/simulate";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

export function DevPanel() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  if (!USE_MOCK) return null;
  const run = (label: string, fn: () => unknown) => () => { const r = fn(); qc.invalidateQueries(); toast(typeof r === "boolean" ? `${label}: ${r ? "reachable" : "unreachable"}` : label); };
  const items: [string, () => unknown][] = [
    ["Simulate new near-miss alert", sim.simulateNearMiss],
    ["Simulate shore reply", sim.simulateShoreReply],
    ["Simulate urgent learning", sim.simulateUrgentLearning],
    ["Simulate welfare request", sim.simulateWelfare],
    ["Toggle ship link UP/DOWN", sim.toggleLink],
    ["Toggle edge reachable", sim.toggleEdge],
    ["Reset demo data", sim.resetDemo],
  ];
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button aria-label="Demo controls" className="tap fixed bottom-44 right-3 z-40 size-10 grid place-items-center rounded-full bg-ink text-ink-foreground shadow-lift lg:bottom-6">
          <Settings2 className="size-5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 space-y-1 rounded-2xl p-2">
        <p className="px-2 pb-1 pt-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Demo controls</p>
        {items.map(([l, f]) => (
          <Button key={l} variant="ghost" className="h-11 w-full justify-start" onClick={run(l, f)}>{l}</Button>
        ))}
      </PopoverContent>
    </Popover>
  );
}
