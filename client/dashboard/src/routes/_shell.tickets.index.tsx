import { createFileRoute } from "@tanstack/react-router";
import { TicketQueue } from "@/features/tickets/ticket-queue";
import type { HazardType, IsmCategory, Severity, ShoreStatus } from "@/api/types";

export type QueueSearch = {
  status?: ShoreStatus | "ALL";
  vessel?: string[];
  severity?: Severity[];
  hazard?: HazardType[];
  ism?: IsmCategory[];
  days?: number;
  q?: string;
};

const arr = <T,>(v: unknown): T[] | undefined => (Array.isArray(v) ? (v as T[]) : v ? [v as T] : undefined);

export const Route = createFileRoute("/_shell/tickets/")({
  validateSearch: (s: Record<string, unknown>): QueueSearch => ({
    status: (s.status as QueueSearch["status"]) ?? undefined,
    vessel: arr<string>(s.vessel),
    severity: arr<number>(s.severity)?.map(Number) as Severity[] | undefined,
    hazard: arr<HazardType>(s.hazard),
    ism: arr<IsmCategory>(s.ism),
    days: s.days ? Number(s.days) : undefined,
    q: typeof s.q === "string" ? s.q : undefined,
  }),
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Ticket queue — Beacon Dashboard" },
      { name: "description", content: "Near-miss tickets synced from the fleet, sorted by severity." },
      { property: "og:title", content: "Ticket queue — Beacon Dashboard" },
      { property: "og:description", content: "Near-miss tickets synced from the fleet, sorted by severity." },
    ],
  }),
  component: TicketsPage,
});

function TicketsPage() {
  return <TicketQueue search={Route.useSearch()} />;
}
