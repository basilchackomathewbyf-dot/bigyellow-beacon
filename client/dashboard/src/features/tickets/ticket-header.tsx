import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BookPlus, Check, Loader2, Ship, X } from "lucide-react";
import type { RejectReason, Ticket } from "@/api/types";
import { useAcceptTicket, useCloseTicket, useRejectTicket } from "@/hooks/use-tickets";
import { REJECT_REASONS, validateReject } from "@/lib/rules";
import { relTime } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { OnboardChip, Pill, SeverityPill, ShoreChip } from "@/components/beacon/chips";

export function TicketHeader({ ticket }: { ticket: Ticket }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const accept = useAcceptTicket();
  const reject = useRejectTicket();
  const close = useCloseTicket();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const [reason, setReason] = useState<RejectReason | undefined>();
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");

  return (
    <div className="surface-card p-6 animate-fade-up">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">{ticket.ticket_no}</span>
            <SeverityPill value={ticket.severity} />
            <ShoreChip value={ticket.shore_status} />
            <OnboardChip value={ticket.onboard_status} />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{ticket.title_en}</h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <Ship className="size-4" aria-hidden /> <span className="font-medium text-foreground">{ticket.vessel.name}</span> · {ticket.vessel.type}
            </span>
            <span>{t("detail.rank")}: {ticket.rank_band}</span>
            <span>{t("detail.received", { time: relTime(ticket.received_at) })}</span>
            {ticket.assigned_to && <Pill tone="IN_REVIEW">{t("detail.assigned", { name: ticket.assigned_to })}</Pill>}
            {ticket.reject_reason && <Pill tone="REJECTED">{t("detail.rejectedBecause", { reason: t(`reject.${ticket.reject_reason}`) })}</Pill>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={() => navigate({ to: "/learnings/new", search: { ticketId: ticket.id } })}>
            <BookPlus /> {t("detail.createLearning")}
          </Button>
          {ticket.shore_status === "NEW" && (
            <>
              <Button variant="outline" onClick={() => setRejectOpen(true)}>
                <X /> {t("detail.reject")}
              </Button>
              <Button onClick={() => accept.mutate(ticket.id)} disabled={accept.isPending}>
                {accept.isPending ? <Loader2 className="animate-spin" /> : <Check />}
                {t("detail.accept")}
              </Button>
            </>
          )}
          {ticket.shore_status === "IN_REVIEW" && (
            <Button onClick={() => setCloseOpen(true)}>
              <Check /> {t("detail.close")}
            </Button>
          )}
        </div>
      </div>

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("detail.rejectTitle")}</DialogTitle>
            <DialogDescription>{t("detail.rejectDesc")}</DialogDescription>
          </DialogHeader>
          <RadioGroup value={reason} onValueChange={(v) => setReason(v as RejectReason)} className="gap-2">
            {REJECT_REASONS.map((r) => (
              <Label key={r} className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 font-normal has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary-soft">
                <RadioGroupItem value={r} /> {t(`reject.${r}`)}
              </Label>
            ))}
          </RadioGroup>
          <div className="space-y-1.5">
            <Label htmlFor="reject-note">{t("detail.note")}</Label>
            <Textarea id="reject-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder={t("detail.notePlaceholder")} />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRejectOpen(false)}>{t("common.cancel")}</Button>
            <Button
              variant="destructive"
              disabled={!validateReject(reason, note) || reject.isPending}
              onClick={() => reason && reject.mutate({ id: ticket.id, reason, note }, { onSuccess: () => setRejectOpen(false) })}
            >
              {reject.isPending && <Loader2 className="animate-spin" />}
              {t("detail.reject")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={closeOpen} onOpenChange={setCloseOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("detail.closeTitle")}</DialogTitle>
            <DialogDescription>{t("detail.closeDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="resolution">{t("detail.resolution")}</Label>
            <Textarea id="resolution" rows={4} value={resolution} onChange={(e) => setResolution(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setCloseOpen(false)}>{t("common.cancel")}</Button>
            <Button disabled={!resolution.trim() || close.isPending} onClick={() => close.mutate({ id: ticket.id, note: resolution }, { onSuccess: () => setCloseOpen(false) })}>
              {close.isPending && <Loader2 className="animate-spin" />}
              {t("detail.close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
