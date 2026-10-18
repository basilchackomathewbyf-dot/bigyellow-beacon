import { useEffect, useState } from "react";
import { CloudOff, RadioTower, Satellite } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useSyncStatus, qk } from "@/hooks/queries";
import { events } from "@/api/events";
import { flushOutbox, onOutboxChange } from "@/lib/outbox";
import { cn } from "@/lib/utils";

export function useOutboxCount() {
  const [n, setN] = useState(0);
  useEffect(() => onOutboxChange(setN), []);
  return n;
}

export function ConnectivityBanner() {
  const qc = useQueryClient();
  const sync = useSyncStatus();
  const pending = useOutboxCount();
  const [online, setOnline] = useState(true);

  useEffect(() => {
    setOnline(navigator.onLine);
    const on = () => setOnline(true), off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    const un = events.on("sync.status", () => qc.invalidateQueries({ queryKey: qk.sync }));
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); un(); };
  }, [qc]);

  const reachable = online && !sync.isError;
  useEffect(() => {
    if (reachable && pending > 0) void flushOutbox().then((n) => { if (n) void qc.invalidateQueries(); });
  }, [reachable, pending, qc]);

  const state = !reachable ? "edge" : sync.data?.link === "DOWN" ? "shore" : "ok";
  const last = sync.data ? new Date(sync.data.last_pull_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
  const cfg = {
    ok: { icon: RadioTower, text: "Connected to ship server", cls: "bg-secondary-soft text-secondary" },
    edge: { icon: CloudOff, text: "Ship server unreachable, saving on this phone", cls: "bg-warn-soft text-warn" },
    shore: { icon: Satellite, text: `Ship offline from shore, last sync ${last}`, cls: "bg-primary-soft text-primary" },
  }[state];
  const Icon = cfg.icon;

  return (
    <div role="status" aria-live="polite" className={cn("flex items-center justify-center gap-2 px-4 py-1.5 text-xs font-medium", cfg.cls)}>
      <Icon className="size-3.5" aria-hidden />
      <span className="truncate">{cfg.text}</span>
      {pending > 0 && <span className="ml-1 rounded-full bg-card px-2 py-0.5 text-[11px] text-foreground shadow-soft">{pending} waiting to send</span>}
    </div>
  );
}
