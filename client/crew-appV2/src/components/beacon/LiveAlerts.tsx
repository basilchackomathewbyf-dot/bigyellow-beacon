import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { HeartHandshake, X } from "lucide-react";
import { events } from "@/api/events";
import type { Ticket, WelfareRequest } from "@/api/types";
import { useSession } from "@/lib/session";
import { severityTone } from "@/lib/rules";
import { cn } from "@/lib/utils";

function chime() {
  try {
    const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ac = new AC();
    [660, 880].forEach((f, i) => {
      const o = ac.createOscillator(), g = ac.createGain();
      o.frequency.value = f; o.type = "sine";
      g.gain.setValueAtTime(0.0001, ac.currentTime + i * 0.18);
      g.gain.exponentialRampToValueAtTime(0.12, ac.currentTime + i * 0.18 + 0.03);
      g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + i * 0.18 + 0.5);
      o.connect(g).connect(ac.destination);
      o.start(ac.currentTime + i * 0.18); o.stop(ac.currentTime + i * 0.18 + 0.55);
    });
    setTimeout(() => ac.close(), 1200);
  } catch { /* audio blocked */ }
}

const tone = { low: "border-sev-low bg-card", mid: "border-sev-mid bg-card", high: "border-sev-high bg-card" };

/** Global listener: invalidates caches on every live event; Master gets banners. */
export function LiveAlerts() {
  const { user } = useSession();
  const qc = useQueryClient();
  const nav = useNavigate();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [welfare, setWelfare] = useState<WelfareRequest | null>(null);
  const isMaster = user?.role === "master";

  useEffect(() => {
    const inv = () => qc.invalidateQueries();
    const offs = [
      events.on("ticket.updated", inv), events.on("message.new", inv), events.on("learning.new", inv), events.on("inbox.new", inv),
      events.on("ticket.new", (t) => {
        inv();
        if (!isMaster) return;
        setTicket(t);
        chime();
        navigator.vibrate?.([120, 60, 120]);
        if ("Notification" in window && Notification.permission === "granted")
          new Notification(`Near-miss · severity ${t.severity}`, { body: `${t.title_en} — ${t.location_on_board}` });
      }),
      events.on("welfare.request", (w) => { inv(); if (isMaster) setWelfare(w); }),
    ];
    return () => offs.forEach((o) => o());
  }, [qc, isMaster]);

  if (!ticket && !welfare) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-3">
      {ticket && (
        <div role="alert" className={cn("pointer-events-auto flex w-full max-w-lg items-center gap-3 rounded-2xl border-l-4 p-4 shadow-lift animate-in slide-in-from-top-4", tone[severityTone(ticket.severity)])}>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-muted-foreground">New near-miss · severity {ticket.severity}</p>
            <p className="truncate font-semibold">{ticket.title_en}</p>
            <p className="truncate text-sm text-muted-foreground">{ticket.location_on_board}</p>
          </div>
          <button className="tap rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground" onClick={() => { nav({ to: "/master/board", search: { t: ticket.id } }); setTicket(null); }}>View</button>
          <button aria-label="Dismiss" className="tap grid place-items-center text-muted-foreground" onClick={() => setTicket(null)}><X className="size-4" /></button>
        </div>
      )}
      {welfare && (
        <div role="status" className="pointer-events-auto flex w-full max-w-lg items-center gap-3 rounded-2xl bg-secondary-soft p-4 shadow-lift animate-in slide-in-from-top-4">
          <HeartHandshake className="size-5 text-secondary" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="font-semibold">A crew member asked to talk</p>
            <p className="text-sm text-muted-foreground">{welfare.name}</p>
          </div>
          <button className="tap rounded-xl bg-secondary px-4 text-sm font-semibold text-secondary-foreground" onClick={() => { nav({ to: "/master/welfare" }); setWelfare(null); }}>Open</button>
          <button aria-label="Dismiss" className="tap grid place-items-center text-muted-foreground" onClick={() => setWelfare(null)}><X className="size-4" /></button>
        </div>
      )}
    </div>
  );
}
