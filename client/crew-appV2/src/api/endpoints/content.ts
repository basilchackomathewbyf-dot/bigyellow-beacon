// Anchor, learnings, inbox and sync endpoints.
import { USE_MOCK } from "../config";
import { api } from "../client";
import { ApiError, type AnchorCard, type InboxItem, type Learning, type SyncStatus } from "../types";
import { getDb } from "../mock/db";
import { latency, nowIso, todayKey } from "../mock/util";

/* ---------- DAILY ANCHOR ---------- */

// GET /anchor/today
export async function anchorToday(): Promise<AnchorCard> {
  if (!USE_MOCK) return api("GET", "/anchor/today");
  return latency(() => getDb().anchors.find((a) => a.date === todayKey()) ?? getDb().anchors[0]);
}

// GET /anchor?days=14&saved=bool
export async function anchorList(opts: { days?: number; saved?: boolean } = {}): Promise<AnchorCard[]> {
  if (!USE_MOCK) return api("GET", `/anchor?days=${opts.days ?? 14}${opts.saved !== undefined ? `&saved=${opts.saved}` : ""}`);
  return latency(() => getDb().anchors.slice(0, opts.days ?? 14).filter((a) => (opts.saved ? a.saved : true)));
}

// POST /anchor/{id}/react
export async function anchorReact(aid: string, r: { viewed?: boolean; helpful?: boolean; saved?: boolean }): Promise<AnchorCard> {
  if (!USE_MOCK) return api("POST", `/anchor/${aid}/react`, r);
  return latency(() => {
    const a = getDb().anchors.find((x) => x.id === aid);
    if (!a) throw new ApiError(404, "Not found");
    Object.assign(a, r);
    return a;
  });
}

/* ---------- LEARNINGS ---------- */

// GET /learnings
export async function learnings(): Promise<Learning[]> {
  if (!USE_MOCK) return api("GET", "/learnings");
  return latency(() => [...getDb().learnings].sort((a, b) =>
    a.priority === b.priority ? b.created_at.localeCompare(a.created_at) : a.priority === "urgent" ? -1 : 1));
}

// POST /learnings/{id}/ack
export async function learningAck(lid: string, body: { opened?: boolean; acked?: boolean; check_answer?: number }): Promise<Learning> {
  if (!USE_MOCK) return api("POST", `/learnings/${lid}/ack`, body);
  return latency(() => {
    const db = getDb();
    const l = db.learnings.find((x) => x.id === lid);
    if (!l) throw new ApiError(404, "Not found");
    if (body.acked && !l.acked) { l.acked = true; db.learningAcks[lid] = (db.learningAcks[lid] ?? 0) + 1; }
    return l;
  });
}

/* ---------- INBOX ---------- */

// GET /inbox
export async function inbox(): Promise<InboxItem[]> {
  if (!USE_MOCK) return api("GET", "/inbox");
  return latency(() => [...getDb().inbox].sort((a, b) => b.created_at.localeCompare(a.created_at)));
}

// POST /inbox/{id}/read
export async function inboxRead(iid: string): Promise<void> {
  if (!USE_MOCK) return api("POST", `/inbox/${iid}/read`);
  return latency(() => { const i = getDb().inbox.find((x) => x.id === iid); if (i) i.read = true; });
}

/* ---------- SYNC ---------- */

// GET /sync/status
export async function syncStatus(): Promise<SyncStatus> {
  if (!USE_MOCK) return api("GET", "/sync/status");
  return latency(() => getDb().sync);
}

// POST /sync/now
export async function syncNow(): Promise<SyncStatus> {
  if (!USE_MOCK) return api("POST", "/sync/now");
  return latency(() => {
    const db = getDb();
    if (db.sync.link === "UP") {
      db.sync.last_push_at = db.sync.last_pull_at = nowIso();
      db.tickets.forEach((t) => { if (t.shore_status === "QUEUED") t.shore_status = "NEW"; });
    }
    return db.sync;
  });
}
