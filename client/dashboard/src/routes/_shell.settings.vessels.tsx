import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { ShieldAlert } from "lucide-react";
import { useVessels } from "@/hooks/use-content";
import { useAuth } from "@/lib/auth-store";
import { relTime } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/beacon/chips";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/_shell/settings/vessels")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Vessels — Beacon Dashboard" },
      { name: "description", content: "Ships connected to Beacon and their last sync." },
      { property: "og:title", content: "Vessels — Beacon Dashboard" },
      { property: "og:description", content: "Ships connected to Beacon and their last sync." },
    ],
  }),
  component: VesselsPage,
});

function VesselsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { data, isLoading, isError, refetch } = useVessels();
  if (user?.role !== "admin")
    return (
      <div className="surface-card flex items-center gap-3 p-8 text-muted-foreground">
        <ShieldAlert className="size-5" aria-hidden /> {t("vessels.adminOnly")}
      </div>
    );
  return (
    <div>
      <PageHeader title={t("vessels.title")} subtitle={t("vessels.subtitle")} />
      <div className="surface-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              {(["name", "type", "imo", "flag", "crew", "sync"] as const).map((k) => (
                <th key={k} className="h-10 px-4 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t(`vessels.${k}`)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="p-4"><Skeleton className="h-20" /></td></tr>}
            {isError && <tr><td colSpan={6} role="alert" className="space-y-3 p-8 text-center">
              <p className="text-muted-foreground">{t("common.error")}</p>
              <Button variant="outline" onClick={() => refetch()}>{t("common.retry")}</Button>
            </td></tr>}
            {data?.map((v) => (
              <tr key={v.id} className="h-11 border-b last:border-0">
                <td className="px-4 font-medium">{v.name}</td>
                <td className="px-4 text-muted-foreground">{v.type}</td>
                <td className="px-4 font-mono text-xs">{v.imo}</td>
                <td className="px-4 text-muted-foreground">{v.flag}</td>
                <td className="px-4 tabular-nums">{v.crew_count}</td>
                <td className="px-4 text-muted-foreground">{relTime(v.last_sync_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
