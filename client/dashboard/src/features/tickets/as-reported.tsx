import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Languages, MapPin, ShieldAlert, Tag, Zap } from "lucide-react";
import type { Ticket } from "@/api/types";
import { dateTime } from "@/lib/format";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { SectionTitle } from "@/components/beacon/chips";

export function AsReported({ ticket }: { ticket: Ticket }) {
  const { t } = useTranslation();
  const [original, setOriginal] = useState(false);
  const [lightbox, setLightbox] = useState<string | null>(null);
  const translated = ticket.original_language !== "English";

  const fields = [
    { icon: MapPin, label: t("detail.location"), value: ticket.location_on_board },
    { icon: Tag, label: t("detail.hazard"), value: t(`hazard.${ticket.hazard_type}`) },
    { icon: ShieldAlert, label: t("detail.ism"), value: t(`ism.${ticket.ism_category}`) },
    { icon: Zap, label: t("detail.immediate"), value: ticket.immediate_action },
  ];

  return (
    <section className="surface-card p-6" aria-labelledby="as-reported">
      <div className="mb-4 flex items-center justify-between">
        <h2 id="as-reported" className="text-base font-semibold">{t("detail.asReported")}</h2>
        {translated && (
          <Button variant="outline" size="sm" onClick={() => setOriginal((v) => !v)}>
            <Languages /> {original ? t("detail.showEnglish") : t("detail.showOriginal", { lang: ticket.original_language })}
          </Button>
        )}
      </div>
      <p className="text-[15px] leading-relaxed text-foreground" lang={original ? "hi" : "en"}>
        {original ? ticket.description_original : ticket.description_en}
      </p>
      <p className="mt-2 text-xs text-muted-foreground">{t("detail.occurred")}: {dateTime(ticket.occurred_at)}</p>

      {ticket.photos.length > 0 && (
        <div className="mt-5">
          <SectionTitle>{t("detail.photos")}</SectionTitle>
          <div className="flex gap-3">
            {ticket.photos.map((p, i) => (
              <button key={p} onClick={() => setLightbox(p)} className="group overflow-hidden rounded-xl border" aria-label={`${t("detail.photos")} ${i + 1}`}>
                <img src={p} alt="" loading="lazy" width={1024} height={768} className="h-28 w-40 object-cover transition group-hover:scale-105" />
              </button>
            ))}
          </div>
        </div>
      )}

      <dl className="mt-6 grid gap-3 sm:grid-cols-2">
        {fields.map((f) => (
          <div key={f.label} className="rounded-xl bg-muted/60 p-3">
            <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <f.icon className="size-3.5" aria-hidden /> {f.label}
            </dt>
            <dd className="mt-1 text-sm font-medium">{f.value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-6">
        <SectionTitle>{t("detail.timeline")}</SectionTitle>
        <ol className="relative ml-2 space-y-4 border-l pl-5">
          <li className="relative">
            <span className="absolute -left-[27px] top-1 size-3 rounded-full border-2 border-card bg-primary" aria-hidden />
            <div className="text-sm font-medium">{t("onboard.SUBMITTED")}</div>
            <div className="text-xs text-muted-foreground">{dateTime(ticket.received_at)}</div>
          </li>
          {ticket.onboard_actions.map((a, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[27px] top-1 size-3 rounded-full border-2 border-card bg-seaglass" aria-hidden />
              <div className="text-sm"><span className="font-medium">{a.responsible_rank}:</span> {a.text}</div>
              <div className="text-xs text-muted-foreground">{dateTime(a.created_at)} · {t("detail.due", { time: dateTime(a.due_at) })}</div>
            </li>
          ))}
          {ticket.onboard_status === "RESOLVED_ON_BOARD" && (
            <li className="relative">
              <span className="absolute -left-[27px] top-1 size-3 rounded-full border-2 border-card bg-severity-low" aria-hidden />
              <div className="text-sm font-medium text-severity-low">{t("onboard.RESOLVED_ON_BOARD")}</div>
            </li>
          )}
          {ticket.onboard_actions.length === 0 && <li className="text-sm text-muted-foreground">{t("detail.timelineEmpty")}</li>}
        </ol>
      </div>

      <Dialog open={!!lightbox} onOpenChange={(o) => !o && setLightbox(null)}>
        <DialogContent className="max-w-4xl p-2">
          <DialogTitle className="sr-only">{t("detail.photos")}</DialogTitle>
          {lightbox && <img src={lightbox} alt="" className="w-full rounded-lg" />}
        </DialogContent>
      </Dialog>
    </section>
  );
}
