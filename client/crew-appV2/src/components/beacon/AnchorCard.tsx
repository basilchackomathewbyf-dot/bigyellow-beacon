import { ExternalLink, ThumbsUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { AnchorCard as A } from "@/api/types";
import { useAnchorReact } from "@/hooks/queries";
import { cn } from "@/lib/utils";

const tone: Record<string, string> = {
  safety: "bg-coral-soft text-coral",
  news: "bg-lavender-soft text-lavender",
  motivation: "bg-sun-soft text-warn",
};

export function AnchorCard({ a, compact }: { a: A; compact?: boolean }) {
  const { t } = useTranslation();
  const react = useAnchorReact();
  const dot = tone[a.type] ?? "bg-muted text-muted-foreground";
  return (
    <article className={cn("relative flex h-full flex-col overflow-hidden rounded-3xl bg-accent shadow-soft", compact ? "p-4" : "p-6 sm:p-8")}>
      <div aria-hidden className={cn("pointer-events-none absolute -right-14 -top-14 rounded-full bg-card/45", compact ? "size-32" : "size-56")} />
      <div className="relative flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em]">
        <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1", dot)}>
          <span className="size-1.5 rounded-full bg-current" />
          {t(`anchor.${a.type}`)}
        </span>
        {compact && <span className="ml-auto text-[11px] font-medium normal-case tracking-normal text-accent-foreground/80">{new Date(a.date).toLocaleDateString([], { day: "numeric", month: "short" })}</span>}
      </div>
      <h3 className={cn("relative mt-3 font-display font-bold tracking-tight text-foreground", compact ? "line-clamp-2 text-base" : "text-xl sm:text-2xl")}>{a.title}</h3>
      <p className={cn("relative mt-2 text-foreground/75", compact ? "line-clamp-2 text-sm" : "line-clamp-3")}>{a.body}</p>
      {a.source_name && !compact && (
        <a href={a.source_url} target="_blank" rel="noreferrer" className="relative mt-2 inline-flex items-center gap-1 text-xs font-semibold text-accent-foreground underline-offset-2 hover:underline">
          {a.source_name}{a.source_url && <ExternalLink className="size-3" />}
        </a>
      )}
      <div className="relative mt-auto flex pt-4">
        <button aria-pressed={a.helpful} onClick={() => react.mutate({ id: a.id, r: { helpful: !a.helpful } })}
          className={cn("tap inline-flex items-center gap-1.5 rounded-full px-4 text-sm font-semibold transition", a.helpful ? "bg-accent-foreground text-accent shadow-soft" : "bg-card/70 text-accent-foreground hover:bg-card")}>
          <ThumbsUp className={cn("size-4", a.helpful && "fill-current")} />{t("anchor.helpful")}
        </button>
      </div>
    </article>
  );
}
