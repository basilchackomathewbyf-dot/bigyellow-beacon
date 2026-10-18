import { useTranslation } from "react-i18next";
import { Check } from "lucide-react";
import type { Ticket } from "@/api/types";
import { useMessages } from "@/hooks/use-tickets";
import { FLOW_STEPS, currentFlowStep } from "@/lib/rules";
import { cn } from "@/lib/utils";

export function FlowTracker({ ticket }: { ticket: Ticket }) {
  const { t } = useTranslation();
  const { data: messages } = useMessages(ticket.id);
  const hasReply = !!messages?.some((m) => m.sender === "shore");
  const step = currentFlowStep(ticket.shore_status, hasReply);
  const done = step >= FLOW_STEPS.length;

  return (
    <div className="surface-card p-4 animate-fade-up">
      <ol className="flex items-center gap-1 overflow-x-auto">
        {FLOW_STEPS.map((s, i) => {
          const complete = i < step;
          const active = i === step || (i === 2 && step === 1);
          return (
            <li key={s} className="flex flex-1 items-center gap-2 min-w-fit">
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-all",
                  complete ? "bg-primary text-primary-foreground" : active ? "bg-primary-soft text-primary ring-2 ring-primary" : "bg-muted text-muted-foreground",
                )}
              >
                {complete ? <Check className="size-3.5" aria-hidden /> : i + 1}
              </span>
              <span className={cn("whitespace-nowrap text-sm", complete || active ? "font-medium text-foreground" : "text-muted-foreground")}>{t(`flow.${s}`)}</span>
              {i < FLOW_STEPS.length - 1 && <span className={cn("mx-2 h-0.5 flex-1 min-w-4 rounded-full", complete ? "bg-primary" : "bg-border")} aria-hidden />}
            </li>
          );
        })}
      </ol>
      <p className={cn("mt-3 rounded-lg px-3 py-2 text-sm", done ? "bg-severity-low-soft text-severity-low" : "bg-primary-soft text-foreground")}>
        {done ? `${t("flow.done")} · ` : ""}
        {t(`flow.hint.${Math.min(step, 5)}`)}
      </p>
    </div>
  );
}
