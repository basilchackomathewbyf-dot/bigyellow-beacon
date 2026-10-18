import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useTicket } from "@/hooks/queries";
import { ListSkeleton, OnboardChip, SeverityPill, ShoreChip, Section } from "@/components/beacon/bits";
import { TicketBody } from "@/components/beacon/TicketBody";
import { Thread } from "@/components/beacon/Thread";

export const Route = createFileRoute("/_app/reports/$id")({
  head: () => ({ meta: [{ title: "Report — Beacon" }, { name: "description", content: "Report details, timeline and messages." }, { property: "og:title", content: "Report — Beacon" }, { property: "og:description", content: "Report details and messages." }] }),
  component: Detail,
});

function Detail() {
  const { id } = Route.useParams();
  const q = useTicket(id);
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link to="/reports" className="tap -ml-2 inline-flex items-center gap-1 px-2 text-sm text-muted-foreground"><ArrowLeft className="size-4" />My reports</Link>
      {!q.data ? <ListSkeleton /> : (
        <>
          <header className="space-y-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="font-mono">{q.data.ticket_no}</span><SeverityPill s={q.data.severity} /></div>
            <h1 className="text-2xl font-semibold tracking-tight">{q.data.title_en}</h1>
            <div className="flex flex-wrap gap-1.5"><OnboardChip s={q.data.onboard_status} /><ShoreChip s={q.data.shore_status} /></div>
          </header>
          <div className="surface p-5"><TicketBody t={q.data} /></div>
          <Section title="Messages · anonymous"><div className="surface p-5"><Thread ticketId={id} me="reporter" /></div></Section>
        </>
      )}
    </div>
  );
}
