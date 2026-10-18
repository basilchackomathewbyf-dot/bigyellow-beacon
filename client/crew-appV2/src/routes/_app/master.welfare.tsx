import { createFileRoute } from "@tanstack/react-router";
import { HandHeart, Lock } from "lucide-react";
import { useWelfare, useWelfareAck } from "@/hooks/queries";
import { Chip, Empty, ListSkeleton, PageHeader } from "@/components/beacon/bits";
import { Button } from "@/components/ui/button";
import { timeAgo } from "@/lib/labels";

export const Route = createFileRoute("/_app/master/welfare")({
  head: () => ({ meta: [{ title: "Welfare — Beacon" }, { name: "description", content: "Crew who asked to talk." }, { property: "og:title", content: "Welfare — Beacon" }, { property: "og:description", content: "Crew who asked to talk." }] }),
  component: Welfare,
});

function Welfare() {
  const q = useWelfare();
  const ack = useWelfareAck();
  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Welfare" subtitle="Crew who asked you to check on them." />
      <p className="mb-4 flex items-center gap-2 text-sm text-muted-foreground"><Lock className="size-4" />Check-in answers and scores are never shown here.</p>
      {q.isLoading ? <ListSkeleton /> : !q.data?.length ? <Empty icon={<HandHeart className="size-5" />} text="No requests." /> : (
        <ul className="space-y-3">
          {q.data.map((w) => (
            <li key={w.id} className="surface flex flex-wrap items-center gap-3 p-4">
              <span className="grid size-10 place-items-center rounded-full bg-secondary-soft font-semibold text-secondary">{w.name[0]}</span>
              <div className="min-w-0 flex-1"><p className="font-semibold">{w.name}</p><p className="text-xs text-muted-foreground">{timeAgo(w.created_at)}</p></div>
              <Chip tone={w.status === "pending" ? "warn" : w.status === "contacted" ? "sea" : "primary"} className="capitalize">{w.status}</Chip>
              <div className="flex w-full gap-2 sm:w-auto">
                {w.status === "pending" && <Button variant="secondary" className="flex-1 rounded-xl" onClick={() => ack.mutate({ id: w.id, status: "acknowledged" })}>Acknowledge</Button>}
                {w.status !== "contacted" && <Button className="flex-1 rounded-xl" onClick={() => ack.mutate({ id: w.id, status: "contacted" })}>Mark contacted</Button>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
