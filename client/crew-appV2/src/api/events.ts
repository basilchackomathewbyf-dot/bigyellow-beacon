import type { InboxItem, Learning, Message, SyncStatus, Ticket, AnchorCard, WelfareRequest } from "./types";

export interface BeaconEvents {
  "ticket.new": Ticket;
  "ticket.updated": Ticket;
  "message.new": Message;
  "learning.new": Learning;
  "anchor.new": AnchorCard;
  "checkin.reminder": { at: string };
  "welfare.request": WelfareRequest;
  "sync.status": SyncStatus;
  "inbox.new": InboxItem;
}
type Handler<K extends keyof BeaconEvents> = (payload: BeaconEvents[K]) => void;

const handlers = new Map<keyof BeaconEvents, Set<Handler<never>>>();

import { API_BASE_URL, USE_MOCK } from "./config";
import { getAuthToken } from "./client";

let eventSource: EventSource | null = null;

function ensureEventSource() {
  if (USE_MOCK || typeof window === "undefined" || typeof EventSource === "undefined") return;
  const token = getAuthToken();
  if (!token || eventSource) return;

  try {
    const url = `${API_BASE_URL}/events?token=${encodeURIComponent(token)}`;
    eventSource = new EventSource(url);

    const eventNames: (keyof BeaconEvents)[] = [
      "ticket.new",
      "ticket.updated",
      "message.new",
      "learning.new",
      "anchor.new",
      "checkin.reminder",
      "welfare.request",
      "sync.status",
      "inbox.new",
    ];

    eventNames.forEach((evt) => {
      eventSource?.addEventListener(evt, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          events.emit(evt, data);
        } catch (err) {
          console.error(`Failed to parse SSE event ${evt}:`, err);
        }
      });
    });

    eventSource.onerror = () => {
      // EventSource auto-reconnects, but if disconnected or 401, clean up if closed
      if (eventSource?.readyState === EventSource.CLOSED) {
        eventSource.close();
        eventSource = null;
      }
    };
  } catch (err) {
    console.error("Failed to initialize EventSource:", err);
  }
}

/** Live / simulated event stream. Connects to SSE when USE_MOCK is false. */
export const events = {
  on<K extends keyof BeaconEvents>(name: K, fn: Handler<K>) {
    ensureEventSource();
    if (!handlers.has(name)) handlers.set(name, new Set());
    handlers.get(name)!.add(fn as Handler<never>);
    return () => { handlers.get(name)?.delete(fn as Handler<never>); };
  },
  emit<K extends keyof BeaconEvents>(name: K, payload: BeaconEvents[K]) {
    handlers.get(name)?.forEach((fn) => (fn as Handler<K>)(payload));
  },
  close() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  },
};
