import { useTranslation } from "react-i18next";
import { Check, Clock, Lock, Send } from "lucide-react";
import { useMessages, useSendMessage } from "@/hooks/use-tickets";
import { setReplyDraft, useReplyDraft } from "@/lib/reply-draft";
import { useAuth } from "@/lib/auth-store";
import { dateTime, relTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";

export function Conversation({ ticketId }: { ticketId: string }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { data: messages, isLoading, isError, refetch } = useMessages(ticketId);
  const send = useSendMessage(ticketId, user?.name ?? "");
  const body = useReplyDraft(ticketId);
  const setBody = (v: string) => setReplyDraft(ticketId, v);

  const submit = () => {
    if (!body.trim() || send.isPending) return;
    send.mutate(body.trim(), { onSuccess: () => setBody("") });
  };

  return (
    <section id="reply" className="surface-card p-6 scroll-mt-24" aria-labelledby="conv">
      <h2 id="conv" className="mb-4 text-base font-semibold">{t("detail.conversation")}</h2>
      <div className="space-y-3">
        {isLoading && <Skeleton className="h-16 w-2/3" />}
        {isError && <div role="alert" className="space-y-2">
          <p className="text-sm text-muted-foreground">{t("common.error")}</p>
          <Button variant="outline" onClick={() => refetch()}>{t("common.retry")}</Button>
        </div>}
        {messages?.map((m) => {
          const shore = m.sender === "shore";
          const label = m.sender === "reporter" ? t("detail.reporter") : m.sender === "master" ? t("detail.master") : t("detail.shore", { name: m.shore_user_name });
          return (
            <div key={m.id} className={cn("flex flex-col animate-fade-up", shore ? "items-end" : "items-start")}>
              <div className="mb-1 text-xs font-medium text-muted-foreground">{label} · {relTime(m.created_at)}</div>
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                  shore ? "rounded-br-sm bg-primary text-primary-foreground" : m.sender === "master" ? "rounded-bl-sm bg-seaglass-soft" : "rounded-bl-sm bg-muted",
                )}
              >
                {m.body}
              </div>
              {shore && (
                <div className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground">
                  {m.delivered_at ? (
                    <>
                      <Check className="size-3 text-seaglass-strong" aria-hidden /> {t("detail.delivered", { time: dateTime(m.delivered_at) })}
                    </>
                  ) : (
                    <>
                      <Clock className="size-3" aria-hidden /> {t("detail.queued")}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-5 border-t pt-4">
        <p className="mb-2 flex items-start gap-2 rounded-lg bg-seaglass-soft p-2.5 text-xs text-seaglass-strong">
          <Lock className="mt-0.5 size-3.5 shrink-0" aria-hidden />
          {t("detail.privacy")}
        </p>
        <div className="flex items-end gap-2">
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
            }}
            placeholder={t("detail.replyPlaceholder")}
            aria-label={t("detail.replyPlaceholder")}
            rows={2}
            disabled={send.isPending}
            className="resize-none"
          />
          <Button onClick={submit} disabled={!body.trim() || send.isPending} aria-label={t("detail.send")}>
            <Send /> {t("detail.send")}
          </Button>
        </div>
      </div>
    </section>
  );
}
