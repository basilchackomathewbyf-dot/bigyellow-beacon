import { useTranslation } from "react-i18next";
import { Check, Siren, X } from "lucide-react";
import type { LearningInput } from "@/api/types";
import { cn } from "@/lib/utils";

/** 360px frame mirroring how the crew app renders a microlearning card. */
export function PhonePreview({ value }: { value: LearningInput }) {
  const { t } = useTranslation();
  const primary = value.media.find((m) => m.primary) ?? value.media[0];
  return (
    <div className="mx-auto w-[360px] rounded-[44px] border-[10px] border-foreground bg-foreground shadow-[var(--shadow-lift)]">
      <div className="relative h-[700px] overflow-hidden rounded-[34px] bg-background">
        <div className="mx-auto mt-2 h-5 w-28 rounded-full bg-foreground" aria-hidden />
        <div className="h-full overflow-y-auto px-4 pb-16 pt-3">
          {value.priority === "urgent" && (
            <div className="mb-3 flex items-center gap-2 rounded-xl bg-severity-high-soft px-3 py-2 text-xs font-semibold text-severity-high">
              <Siren className="size-3.5" aria-hidden /> {t("learn.priority.urgent")} · {t("learn.urgentDesc")}
            </div>
          )}
          <div className="overflow-hidden rounded-2xl bg-card shadow-[var(--shadow-soft)]">
            {primary ? (
              primary.kind === "video" ? (
                <video src={primary.url} className="aspect-video w-full object-cover" autoPlay loop muted playsInline />
              ) : (
                <img src={primary.url} alt="" className="aspect-video w-full object-cover" />
              )
            ) : (
              <div className="grid aspect-video place-items-center sea-gradient text-sm text-primary-foreground/80">{t("learn.previewEmpty")}</div>
            )}
            <div className="space-y-3 p-4">
              <div className="flex flex-wrap gap-1">
                {Object.values(value.tags).filter(Boolean).map((tag) => (
                  <span key={tag} className="rounded-full bg-seaglass-soft px-2 py-0.5 text-[10px] font-medium capitalize text-seaglass-strong">{tag}</span>
                ))}
              </div>
              <h3 className="text-lg font-semibold leading-snug">{value.title || "—"}</h3>
              {value.context && <p className="text-xs text-muted-foreground">{value.context}</p>}
              {value.situation && <p className="text-sm">{value.situation}</p>}
              <div className="space-y-1.5">
                {value.do_points.filter(Boolean).map((d, i) => (
                  <div key={i} className="flex items-start gap-2 rounded-lg bg-severity-low-soft p-2 text-xs"><Check className="mt-0.5 size-3.5 shrink-0 text-severity-low" aria-hidden />{d}</div>
                ))}
                {value.dont_points.filter(Boolean).map((d, i) => (
                  <div key={i} className="flex items-start gap-2 rounded-lg bg-severity-high-soft p-2 text-xs"><X className="mt-0.5 size-3.5 shrink-0 text-severity-high" aria-hidden />{d}</div>
                ))}
              </div>
              {value.check_question.q && (
                <div className="rounded-xl border p-3">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{t("learn.checkKnowledge")}</div>
                  <p className="mb-2 text-sm font-medium">{value.check_question.q}</p>
                  <div className="space-y-1.5">
                    {value.check_question.options.map((o, i) => (
                      <div key={i} className={cn("rounded-lg border px-3 py-2 text-xs", i === value.check_question.answer_index && "border-seaglass bg-seaglass-soft")}>{o || "…"}</div>
                    ))}
                  </div>
                </div>
              )}
              <button type="button" className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-primary-foreground">{t("learn.acknowledge")}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
