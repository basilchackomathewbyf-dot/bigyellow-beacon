import { useTranslation } from "react-i18next";
import { CloudOff, Inbox } from "lucide-react";
import { useSyncStatus } from "@/hooks/queries";
import { useOutboxCount } from "@/components/beacon/ConnectivityBanner";
import { cn } from "@/lib/utils";

/** Tells the crew that what they just did is saved on the phone and will go out on its own. */
export function QueuedNotice({ className }: { className?: string }) {
  const { t } = useTranslation();
  const pending = useOutboxCount();
  const sync = useSyncStatus();
  if (pending === 0) return null;
  const waiting = sync.isError || sync.data?.link === "DOWN" || !navigator.onLine;
  return (
    <div role="status" aria-live="polite" className={cn("flex items-start gap-3 rounded-3xl border p-4 shadow-soft", waiting ? "border-warn/30 bg-warn-soft" : "border-secondary/25 bg-secondary-soft", className)}>
      <span className={cn("grid size-10 shrink-0 place-items-center rounded-2xl", waiting ? "bg-warn/15 text-warn" : "bg-secondary/15 text-secondary")}>
        {waiting ? <CloudOff className="size-5" /> : <Inbox className="size-5" />}
      </span>
      <div className="min-w-0">
        <p className={cn("font-display text-sm font-bold", waiting ? "text-warn" : "text-secondary")}>{t("home.queuedTitle")}</p>
        <p className="mt-0.5 text-sm text-foreground/75">{t("home.queuedBody", { n: pending })}</p>
      </div>
    </div>
  );
}
