import { createFileRoute, Link } from "@tanstack/react-router";
import { Check, Pin } from "lucide-react";
import { useLearnings } from "@/hooks/queries";
import { ListSkeleton, PageHeader, Chip } from "@/components/beacon/bits";
import { getLearningImageUrl, getFallbackImageForLearning } from "@/lib/learning-media";

export const Route = createFileRoute("/_app/learn/")({
  head: () => ({ meta: [{ title: "Learn — Beacon" }, { name: "description", content: "Short safety lessons from across the fleet." }, { property: "og:title", content: "Learn — Beacon" }, { property: "og:description", content: "Short safety lessons from the fleet." }] }),
  component: Learn,
});

function Learn() {
  const q = useLearnings();
  return (
    <div>
      <PageHeader title="Learn" subtitle="Two minutes. Lessons from real ships." />
      {q.isLoading ? <ListSkeleton /> : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {q.data?.map((l) => {
            const imgSrc = getLearningImageUrl(l.media, l.id);
            return (
              <Link key={l.id} to="/learn/$id" params={{ id: l.id }} className="surface group flex h-72 flex-col overflow-hidden p-0 transition hover:shadow-lift">
                <div className="relative overflow-hidden bg-muted">
                  <img
                    src={imgSrc}
                    alt={l.title}
                    loading="lazy"
                    onError={(e) => {
                      const target = e.currentTarget;
                      const fallback = getFallbackImageForLearning(l.id);
                      if (target.src !== fallback) {
                        target.src = fallback;
                      }
                    }}
                    className="h-36 w-full object-cover transition duration-500 group-hover:scale-105"
                  />
                  <div className="absolute left-3 top-3 flex gap-1.5">
                    {l.priority === "urgent" && <Chip tone="warn" className="bg-card"><Pin className="size-3" />Urgent</Chip>}
                    {l.acked && <Chip tone="sea" className="bg-card"><Check className="size-3" />Done</Chip>}
                  </div>
                </div>
                <div className="min-h-0 flex-1 p-4">
                  <p className="line-clamp-2 font-semibold leading-snug">{l.title}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{l.context}</p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
