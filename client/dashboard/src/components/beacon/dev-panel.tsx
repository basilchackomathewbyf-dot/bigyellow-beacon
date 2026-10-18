import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { MessageSquareReply, RefreshCw, RotateCcw, Settings2, ShipWheel } from "lucide-react";
import { toast } from "sonner";
import { devApi } from "@/api/endpoints/dev";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

export function DevPanel() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const run = async (fn: () => Promise<unknown> | void) => {
    await fn();
    await qc.invalidateQueries();
    toast(t("dev.done"));
  };
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button size="icon" variant="outline" aria-label={t("dev.title")} className="fixed bottom-5 left-5 z-40 size-11 rounded-full shadow-[var(--shadow-lift)]">
          <Settings2 />
        </Button>
      </PopoverTrigger>
      <PopoverContent side="top" align="start" className="w-72 space-y-1 p-2">
        <div className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("dev.title")}</div>
        <Button variant="ghost" className="w-full justify-start" onClick={() => run(devApi.simulateNewTickets)}>
          <ShipWheel /> {t("dev.newTicket")}
        </Button>
        <Button variant="ghost" className="w-full justify-start" onClick={() => run(devApi.simulateReporterReply)}>
          <MessageSquareReply /> {t("dev.reply")}
        </Button>
        <Button variant="ghost" className="w-full justify-start" onClick={() => run(devApi.simulateShipSync)}>
          <RefreshCw /> {t("dev.sync")}
        </Button>
        <Button variant="ghost" className="w-full justify-start text-destructive hover:text-destructive" onClick={() => run(devApi.reset)}>
          <RotateCcw /> {t("dev.reset")}
        </Button>
      </PopoverContent>
    </Popover>
  );
}
