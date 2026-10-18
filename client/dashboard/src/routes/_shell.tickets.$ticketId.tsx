import { createFileRoute, Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { ArrowLeft } from "lucide-react";
import { useTicket } from "@/hooks/use-tickets";
import { Skeleton } from "@/components/ui/skeleton";
import { TicketHeader } from "@/features/tickets/ticket-header";
import { AsReported } from "@/features/tickets/as-reported";
import { Conversation } from "@/features/tickets/conversation";
import { FlowTracker } from "@/features/tickets/flow-tracker";
import { AnalysisPanel } from "@/features/analysis/analysis-panel";

export const Route = createFileRoute("/_shell/tickets/$ticketId")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Ticket — Beacon Dashboard" },
      { name: "description", content: "Review a near-miss report with AI analysis and reply anonymously." },
      { property: "og:title", content: "Ticket — Beacon Dashboard" },
      { property: "og:description", content: "Review a near-miss report with AI analysis and reply anonymously." },
    ],
  }),
  component: TicketDetailPage,
});

function TicketDetailPage() {
  const { ticketId } = Route.useParams();
  const { t } = useTranslation();
  const { data: ticket, isLoading, isError } = useTicket(ticketId);

  return (
    <div className="space-y-5">
      <Link to="/tickets" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" aria-hidden /> {t("tickets.title")}
      </Link>
      {isLoading && <Skeleton className="h-28 w-full rounded-2xl" />}
      {isError && <div className="surface-card p-10 text-center text-muted-foreground">{t("detail.notFound")}</div>}
      {ticket && (
        <>
          <TicketHeader ticket={ticket} />
          <FlowTracker ticket={ticket} />
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
            <div className="space-y-5">
              <AsReported ticket={ticket} />
              <Conversation ticketId={ticket.id} />
            </div>
            <AnalysisPanel ticket={ticket} />
          </div>
        </>
      )}
    </div>
  );
}
