import type { Ticket } from "@/api/types";
import { HAZARDS, ISM, ONBOARD, timeAgo } from "@/lib/labels";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown } from "lucide-react";

export function TicketBody({ t }: { t: Ticket }) {
  const timeline = [
    { at: t.created_at, text: "Reported" },
    ...(t.onboard_status !== "SUBMITTED" ? [{ at: t.created_at, text: "Acknowledged by Master" }] : []),
    ...t.actions.map((a) => ({ at: a.created_at, text: `${a.resolved ? "Resolved" : "Action"}: ${a.text} · ${a.responsible_rank}`, photo: a.photo_url })),
  ];
  return (
    <div className="space-y-5">
      <p className="text-foreground/80">{t.description_en}</p>
      {t.description_original !== t.description_en && (
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-sm font-medium text-primary">Original ({t.original_language.toUpperCase()}) <ChevronDown className="size-4" /></CollapsibleTrigger>
          <CollapsibleContent className="mt-2 rounded-xl bg-muted p-3 text-sm">{t.description_original}</CollapsibleContent>
        </Collapsible>
      )}
      <dl className="grid grid-cols-2 gap-3 text-sm">
        {[["Location", t.location_on_board], ["Hazard", HAZARDS[t.hazard_type]], ["ISM", ISM[t.ism_category]], ["Immediate action", t.immediate_action || "—"]].map(([k, v]) => (
          <div key={k} className="rounded-xl bg-muted/60 p-3"><dt className="text-xs text-muted-foreground">{k}</dt><dd className="mt-0.5 font-medium">{v}</dd></div>
        ))}
      </dl>
      {t.audio_url && <audio src={t.audio_url} controls className="w-full" />}
      {t.photos.length > 0 && (
        <div className="grid grid-cols-3 gap-2">{t.photos.map((p, i) => <img key={i} src={p} alt={`Report photo ${i + 1}`} className="aspect-square rounded-xl object-cover" />)}</div>
      )}
      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Timeline · {ONBOARD[t.onboard_status]}</h3>
        <ol className="space-y-3 border-l-2 border-border pl-4">
          {timeline.map((e, i) => (
            <li key={i} className="relative text-sm">
              <span className="absolute -left-[21px] top-1.5 size-2.5 rounded-full bg-primary" />
              <p>{e.text}</p>
              <p className="text-xs text-muted-foreground">{timeAgo(e.at)}</p>
              {"photo" in e && e.photo && <img src={e.photo} alt="Fix photo" className="mt-2 h-24 rounded-lg object-cover" />}
            </li>
          ))}
        </ol>
      </div>
      {t.reject_reason && <p className="rounded-xl bg-accent p-3 text-sm text-accent-foreground">Shore note: {t.reject_reason}</p>}
    </div>
  );
}
