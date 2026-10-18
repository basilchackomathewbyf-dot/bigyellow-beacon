import Dexie, { type Table } from "dexie";
import { ApiError } from "@/api/types";
import { postMessage } from "@/api/endpoints/reports";
import { startCheckin } from "@/api/endpoints/checkins";
import { anchorReact, learningAck } from "@/api/endpoints/content";

/** Offline writes are queued here (IndexedDB) and flushed when the ship server is reachable. */
export type OutboxKind = "message" | "checkin_quick" | "anchor_react" | "learning_ack";
export interface OutboxRow { id?: number; kind: OutboxKind; payload: unknown; created_at: string }

class BeaconDb extends Dexie {
  outbox!: Table<OutboxRow, number>;
  constructor() {
    super("beacon");
    this.version(1).stores({ outbox: "++id, kind, created_at" });
  }
}

let _db: BeaconDb | null = null;
const db = () => (_db ??= new BeaconDb());
const listeners = new Set<(n: number) => void>();
const notify = async () => { const n = await db().outbox.count(); listeners.forEach((l) => l(n)); };

export const onOutboxChange = (fn: (n: number) => void) => {
  listeners.add(fn);
  void notify();
  return () => { listeners.delete(fn); };
};

const isUnreachable = (e: unknown) =>
  (e instanceof ApiError && e.status === 0) || (typeof navigator !== "undefined" && !navigator.onLine);

const runners: Record<OutboxKind, (p: any) => Promise<unknown>> = {
  message: (p) => postMessage(p.ticketId, p.body),
  checkin_quick: (p) => startCheckin(p),
  anchor_react: (p) => anchorReact(p.id, p.r),
  learning_ack: (p) => learningAck(p.id, p.body),
};

/** Try the write; if the ship server is unreachable, queue it and return { queued: true }. */
export async function sendOrQueue<T>(kind: OutboxKind, payload: unknown): Promise<{ queued: false; result: T } | { queued: true }> {
  try {
    return { queued: false, result: (await runners[kind](payload)) as T };
  } catch (e) {
    if (!isUnreachable(e)) throw e;
    await db().outbox.add({ kind, payload, created_at: new Date().toISOString() });
    await notify();
    return { queued: true };
  }
}

let flushing = false;
export async function flushOutbox(): Promise<number> {
  if (flushing) return 0;
  flushing = true;
  let sent = 0;
  try {
    const rows = await db().outbox.orderBy("id").toArray();
    for (const r of rows) {
      try { await runners[r.kind](r.payload); }
      catch (e) { if (isUnreachable(e)) break; /* drop permanent failures, e.g. 409 */ }
      await db().outbox.delete(r.id!);
      sent++;
    }
  } finally {
    flushing = false;
    await notify();
  }
  return sent;
}
