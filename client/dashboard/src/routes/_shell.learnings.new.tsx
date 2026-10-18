import { createFileRoute } from "@tanstack/react-router";
import { LearningStudio } from "@/features/learnings/learning-studio";

export const Route = createFileRoute("/_shell/learnings/new")({
  validateSearch: (s: Record<string, unknown>): { ticketId?: string } => ({
    ticketId: typeof s.ticketId === "string" ? s.ticketId : undefined,
  }),
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "New microlearning — Beacon Dashboard" },
      { name: "description", content: "Create a microlearning card for crew with a live phone preview." },
      { property: "og:title", content: "New microlearning — Beacon Dashboard" },
      { property: "og:description", content: "Create a microlearning card for crew with a live phone preview." },
    ],
  }),
  component: NewLearning,
});

function NewLearning() {
  const { ticketId } = Route.useSearch();
  return <LearningStudio key={ticketId ?? "blank"} sourceTicketId={ticketId} />;
}
