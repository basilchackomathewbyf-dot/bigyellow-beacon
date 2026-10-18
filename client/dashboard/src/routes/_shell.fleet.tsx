import { createFileRoute } from "@tanstack/react-router";
import { FleetOverviewView } from "@/features/fleet/fleet-overview";

export const Route = createFileRoute("/_shell/fleet")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Fleet overview — Beacon Dashboard" },
      { name: "description", content: "Safety reporting KPIs, hazard clusters and crew wellbeing across the fleet." },
      { property: "og:title", content: "Fleet overview — Beacon Dashboard" },
      { property: "og:description", content: "Safety reporting KPIs, hazard clusters and crew wellbeing across the fleet." },
    ],
  }),
  component: FleetOverviewView,
});
