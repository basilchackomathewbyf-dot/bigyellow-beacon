import { createFileRoute } from "@tanstack/react-router";
import { useLearning } from "@/hooks/use-content";
import { Skeleton } from "@/components/ui/skeleton";
import { LearningStudio } from "@/features/learnings/learning-studio";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/_shell/learnings/$learningId")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Edit microlearning — Beacon Dashboard" },
      { name: "description", content: "Edit, publish or retract a crew microlearning." },
      { property: "og:title", content: "Edit microlearning — Beacon Dashboard" },
      { property: "og:description", content: "Edit, publish or retract a crew microlearning." },
    ],
  }),
  component: EditLearning,
});

function EditLearning() {
  const { learningId } = Route.useParams();
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch } = useLearning(learningId);
  if (isLoading) return <Skeleton className="h-[600px] w-full rounded-2xl" />;
  if (isError || !data) return (
    <div role="alert" className="space-y-3 py-10 text-center">
      <p className="text-muted-foreground">{t("common.error")}</p>
      <Button variant="outline" onClick={() => refetch()}>{t("common.retry")}</Button>
    </div>
  );
  return <LearningStudio key={data.id} existing={data} sourceTicketId={data.source_ticket_id} />;
}
