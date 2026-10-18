import { useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import { useMessages, usePostMessage } from "@/hooks/queries";
import { timeAgo } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

/** Anonymous ticket thread. `me` decides which side is "mine". */
export function Thread({ ticketId, me }: { ticketId: string; me: "reporter" | "master" }) {
  const msgs = useMessages(ticketId);
  const post = usePostMessage(ticketId);
  const [body, setBody] = useState("");
  const label = { reporter: me === "reporter" ? "You" : "Reporter", master: "Master", shore: "Shore safety team" };
  const send = async () => {
    const r = await post.mutateAsync(body);
    setBody("");
    if (r.queued) toast("Saved on this phone. It will send when the ship server is back.");
  };
  return (
    <div className="space-y-3">
      {msgs.data?.length === 0 && <p className="text-sm text-muted-foreground">No messages yet.</p>}
      {msgs.data?.map((m) => {
        const mine = m.sender === me;
        return (
          <div key={m.id} className={cn("flex flex-col", mine ? "items-end" : "items-start")}>
            <span className="mb-1 text-[11px] text-muted-foreground">{label[m.sender]} · {timeAgo(m.created_at)}</span>
            <p className={cn("max-w-[85%] rounded-2xl px-4 py-2.5 text-sm", mine ? "rounded-tr-sm bg-primary text-primary-foreground" : m.sender === "shore" ? "rounded-tl-sm bg-secondary-soft" : "rounded-tl-sm bg-muted")}>{m.body}</p>
          </div>
        );
      })}
      <form className="flex gap-2 pt-2" onSubmit={(e) => { e.preventDefault(); if (body.trim()) void send(); }}>
        <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a reply" className="h-11 rounded-xl bg-card" aria-label="Reply" />
        <Button type="submit" size="icon" className="size-11 rounded-xl" disabled={post.isPending} aria-label="Send"><Send className="size-4" /></Button>
      </form>
    </div>
  );
}
