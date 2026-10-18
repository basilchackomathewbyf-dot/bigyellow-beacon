// Tiny shared store so the AI panel can push text into the reply box.
import { useSyncExternalStore } from "react";

const drafts = new Map<string, string>();
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

export function setReplyDraft(ticketId: string, body: string) {
  drafts.set(ticketId, body);
  emit();
}
export function appendToReply(ticketId: string, text: string) {
  const cur = drafts.get(ticketId) ?? "";
  setReplyDraft(ticketId, cur ? `${cur}\n${text}` : text);
}
export function useReplyDraft(ticketId: string): string {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => {
        listeners.delete(l);
      };
    },
    () => drafts.get(ticketId) ?? "",
    () => "",
  );
}
