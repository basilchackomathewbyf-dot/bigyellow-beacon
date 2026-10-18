import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({ to: "/tickets" });
  },
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Beacon Dashboard — Shore safety team" },
      { name: "description", content: "Review near-miss reports from the fleet, reply anonymously and publish microlearnings." },
      { property: "og:title", content: "Beacon Dashboard — Shore safety team" },
      { property: "og:description", content: "Review near-miss reports from the fleet, reply anonymously and publish microlearnings." },
    ],
  }),
});
