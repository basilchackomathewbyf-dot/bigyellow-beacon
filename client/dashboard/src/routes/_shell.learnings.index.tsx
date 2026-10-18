import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { Plus, Siren } from "lucide-react";
import { useLearnings } from "@/hooks/use-content";
import { useTickets } from "@/hooks/use-tickets";
import { shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, Pill } from "@/components/beacon/chips";

export const Route = createFileRoute("/_shell/learnings/")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Microlearnings — Beacon Dashboard" },
      { name: "description", content: "Short safety cards delivered to crew phones across the fleet." },
      { property: "og:title", content: "Microlearnings — Beacon Dashboard" },
      { property: "og:description", content: "Short safety cards delivered to crew phones across the fleet." },
    ],
  }),
  component: LearningsPage,
});

function LearningsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useLearnings();
  const { data: tickets } = useTickets();
  const ticketNo = (id?: string) => tickets?.find((x) => x.id === id)?.ticket_no;

  return (
    <div>
      <PageHeader
        title={t("learn.title")}
        subtitle={t("learn.subtitle")}
        actions={
          <Button onClick={() => navigate({ to: "/learnings/new", search: {} })}>
            <Plus /> {t("learn.new")}
          </Button>
        }
      />
      <div className="surface-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              {(["title", "source", "audience", "priority", "status", "published", "delivery", "ack"] as const).map((k) => (
                <th key={k} className="h-10 px-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t(`learn.col.${k}`)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={8} className="p-3"><Skeleton className="h-24 w-full" /></td></tr>
            )}
            {isError && (
              <tr><td colSpan={8} className="p-8 text-center" role="alert">
                <p className="mb-3 text-muted-foreground">{t("common.error")}</p>
                <Button variant="outline" onClick={() => refetch()}>{t("common.retry")}</Button>
              </td></tr>
            )}
            {data?.map((l) => {
              const ack = l.stats.opened ? l.stats.acknowledged / l.stats.opened : 0;
              return (
                <tr key={l.id} onClick={() => navigate({ to: "/learnings/$learningId", params: { learningId: l.id } })} className="h-12 cursor-pointer border-b last:border-0 hover:bg-primary-soft/60">
                  <td className="px-3 font-medium">{l.title}</td>
                  <td className="px-3">
                    {l.source_ticket_id ? (
                      <Link to="/tickets/$ticketId" params={{ ticketId: l.source_ticket_id }} onClick={(e) => e.stopPropagation()} className="font-mono text-xs text-primary hover:underline">
                        {ticketNo(l.source_ticket_id) ?? l.source_ticket_id}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground/50">—</span>
                    )}
                  </td>
                  <td className="px-3 text-muted-foreground">{t(`learn.audience.${l.audience.mode}`)}</td>
                  <td className="px-3">
                    {l.priority === "urgent" ? <Pill tone="high"><Siren className="size-3" aria-hidden />{t("learn.priority.urgent")}</Pill> : <Pill>{t("learn.priority.normal")}</Pill>}
                  </td>
                  <td className="px-3">
                    <Pill tone={l.status === "published" ? "IN_REVIEW" : l.status === "draft" ? "NEW" : "CLOSED"}>{t(`learn.status.${l.status}`)}</Pill>
                  </td>
                  <td className="px-3 text-muted-foreground">{l.published_at ? shortDate(l.published_at) : "—"}</td>
                  <td className="px-3 tabular-nums">{t("learn.deliveryOf", { a: l.stats.vessels_delivered, b: l.stats.vessels_total })}</td>
                  <td className="w-44 px-3">
                    <div className="flex items-center gap-2">
                      <Progress value={ack * 100} className="h-1.5" aria-label={t("learn.col.ack")} />
                      <span className="w-9 text-xs tabular-nums text-muted-foreground">{Math.round(ack * 100)}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
