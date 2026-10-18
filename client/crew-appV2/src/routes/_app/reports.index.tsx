import { createFileRoute, Link } from "@tanstack/react-router";
import { ClipboardList } from "lucide-react";
import { useMyReports } from "@/hooks/queries";
import { Empty, ListSkeleton, OnboardChip, PageHeader, SeverityPill, ShoreChip } from "@/components/beacon/bits";
import { timeAgo } from "@/lib/labels";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/_app/reports/")({
  head: () => ({ meta: [{ title: "My reports — Beacon" }, { name: "description", content: "Track your near-miss reports on board and with shore." }, { property: "og:title", content: "My reports — Beacon" }, { property: "og:description", content: "Track your near-miss reports." }] }),
  component: Mine,
});

function Mine() {
  const q = useMyReports();
  return (
    <div>
      <PageHeader title="My reports" subtitle="Every report helps someone go home safe." action={<Button asChild className="rounded-xl"><Link to="/report">New</Link></Button>} />
      {q.isLoading ? <ListSkeleton /> : !q.data?.length ? <Empty icon={<ClipboardList className="size-5" />} text="No reports yet." /> : (
        <ul className="space-y-3">
          {q.data.map((t) => (
            <li key={t.id}>
              <Link to="/reports/$id" params={{ id: t.id }} className="surface block space-y-3 p-4 transition hover:shadow-lift">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-mono">{t.ticket_no}</span><span>·</span><span>{timeAgo(t.created_at)}</span>
                  <span className="ml-auto"><SeverityPill s={t.severity} withLabel={false} /></span>
                </div>
                <p className="font-semibold leading-snug">{t.title_en}</p>
                <div className="flex flex-wrap gap-1.5"><OnboardChip s={t.onboard_status} /><ShoreChip s={t.shore_status} /></div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
