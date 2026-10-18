import { USE_MOCK } from "../config";
import { api } from "../client";
import { events } from "../events";
import { ApiError, type LearningStat, type MorningBrief, type OnboardStatus, type PairedDevice, type Ticket, type WelfareRequest } from "../types";
import { getDb } from "../mock/db";
import { CREW } from "../mock/seed";
import { id, latency, nowIso } from "../mock/util";
import { MIN_CREW_FOR_MOOD_TREND } from "@/lib/rules";

const findTicket = (tid: string) => {
  const t = getDb().tickets.find((x) => x.id === tid);
  if (!t) throw new ApiError(404, "Not found");
  return t;
};

// GET /master/tickets?onboard_status=&severity=
export async function masterTickets(f: { onboard_status?: OnboardStatus; severity?: number } = {}): Promise<Ticket[]> {
  if (!USE_MOCK) {
    const q = new URLSearchParams();
    if (f.onboard_status) q.set("onboard_status", f.onboard_status);
    if (f.severity) q.set("severity", String(f.severity));
    return api("GET", `/master/tickets?${q}`);
  }
  return latency(() =>
    getDb().tickets
      .filter((t) => (!f.onboard_status || t.onboard_status === f.onboard_status) && (!f.severity || t.severity === f.severity))
      .map((t) => ({ ...t, reporter_name: t.share_name_with_master ? t.reporter_name : undefined })),
  );
}

// POST /master/tickets/{id}/ack
export async function ackTicket(tid: string): Promise<Ticket> {
  if (!USE_MOCK) return api("POST", `/master/tickets/${tid}/ack`);
  const t = await latency(() => {
    const t = findTicket(tid);
    if (t.onboard_status === "SUBMITTED") t.onboard_status = "ACKNOWLEDGED";
    return t;
  });
  events.emit("ticket.updated", t);
  return t;
}

// POST /master/tickets/{id}/actions
export async function addAction(tid: string, a: { text: string; responsible_rank: string; due_at: string; resolve?: boolean; photo?: Blob }): Promise<Ticket> {
  if (!USE_MOCK) {
    if (a.photo) {
      const fd = new FormData();
      if (a.text) fd.append("text", a.text);
      if (a.responsible_rank) fd.append("responsible_rank", a.responsible_rank);
      if (a.due_at) fd.append("due_at", a.due_at);
      if (a.resolve !== undefined) fd.append("resolve", String(a.resolve));
      fd.append("photo", a.photo, "resolution.jpg");
      return api<Ticket>("POST", `/master/tickets/${tid}/actions`, fd);
    }
    return api<Ticket>("POST", `/master/tickets/${tid}/actions`, {
      text: a.text,
      responsible_rank: a.responsible_rank,
      due_at: a.due_at,
      resolve: a.resolve,
    });
  }
  const photo_url = a.photo ? URL.createObjectURL(a.photo) : undefined;
  const t = await latency(() => {
    const t = findTicket(tid);
    t.actions.push({ id: id("a"), text: a.text, responsible_rank: a.responsible_rank, due_at: a.due_at, photo_url, resolved: !!a.resolve, created_at: nowIso() });
    if (photo_url) t.photos.push(photo_url);
    t.onboard_status = a.resolve ? "RESOLVED_ON_BOARD" : "ACTION_IN_PROGRESS";
    return t;
  });
  events.emit("ticket.updated", t);
  return t;
}

const buildBrief = (): MorningBrief => {
  const db = getDb();
  const open = db.tickets.filter((t) => t.onboard_status !== "RESOLVED_ON_BOARD").sort((a, b) => b.severity - a.severity);
  const n = 6; // crew who checked in this week (mock)
  const variants = [
    "Steady night. One high-severity hazard still open on deck.",
    "Quiet watch overnight. Focus today on mooring gear before arrival.",
    "Crew mood is holding. Clear the enclosed-space finding first.",
  ];
  return {
    generated_at: nowIso(),
    headline: variants[db.briefVersion % variants.length],
    rest_hours_risk: { level: "medium", note: "2 crew are close to the 10-hour rest limit after cargo ops." },
    mood_trend: n >= MIN_CREW_FOR_MOOD_TREND
      ? { n, points: Array.from({ length: 7 }, (_, i) => ({ date: new Date(Date.now() - (6 - i) * 86_400_000).toISOString().slice(5, 10), mood: Math.round((3.2 + Math.sin(i + db.briefVersion) * 0.5) * 10) / 10 })) }
      : null,
    open_hazards: open.slice(0, 4).map((t) => ({ ticket_no: t.ticket_no, title: t.title_en, severity: t.severity })),
    recommended_action: "Hold a 5-minute toolbox talk on hydraulic leaks before deck work.",
    fleet_context: "3 sister vessels reported crane hydraulic leaks in the last 30 days.",
  };
};

// GET /master/brief
export async function getBrief(): Promise<MorningBrief> {
  if (!USE_MOCK) return api("GET", "/master/brief");
  return latency(buildBrief);
}

// POST /master/brief/regenerate
export async function regenerateBrief(): Promise<MorningBrief> {
  if (!USE_MOCK) return api("POST", "/master/brief/regenerate");
  await new Promise((r) => setTimeout(r, 200));
  return latency(() => { getDb().briefVersion++; return buildBrief(); });
}

// GET /master/learnings/stats
export async function learningStats(): Promise<LearningStat[]> {
  if (!USE_MOCK) return api("GET", "/master/learnings/stats");
  return latency(() => getDb().learnings.map((l) => ({ learning_id: l.id, title: l.title, acked: getDb().learningAcks[l.id] ?? 0, total: 8 })));
}

// GET /master/welfare
export async function welfareList(): Promise<WelfareRequest[]> {
  if (!USE_MOCK) return api("GET", "/master/welfare");
  return latency(() => [...getDb().welfare].sort((a, b) => b.created_at.localeCompare(a.created_at)));
}

// POST /master/welfare/{id}/ack
export async function welfareAck(wid: string, status: "acknowledged" | "contacted"): Promise<WelfareRequest> {
  if (!USE_MOCK) return api("POST", `/master/welfare/${wid}/ack`, { status });
  return latency(() => {
    const w = getDb().welfare.find((x) => x.id === wid);
    if (!w) throw new ApiError(404, "Not found");
    w.status = status;
    return w;
  });
}

/** GET /master/devices */
export async function pairedDevices(): Promise<PairedDevice[]> {
  if (!USE_MOCK) return api("GET", "/master/devices");
  return latency(() => getDb().devices);
}

/** DELETE /master/devices/{id} */
export async function revokeDevice(did: string): Promise<void> {
  if (!USE_MOCK) return api("DELETE", `/master/devices/${did}`);
  return latency(() => { const db = getDb(); db.devices = db.devices.filter((d) => d.id !== did); });
}

export interface CrewMember {
  id: string;
  name: string;
  username: string;
  rank: string;
  rank_band: "officer" | "rating";
  role: "crew" | "master";
  language: string;
  created_at: string;
}

export interface CreateCrewInput {
  name: string;
  username: string;
  password: string;
  rank: string;
  rank_band?: "officer" | "rating";
  language?: string;
}

/** GET /master/crew */
export async function getCrewList(): Promise<CrewMember[]> {
  if (!USE_MOCK) return api("GET", "/master/crew");
  return latency(() =>
    CREW.map((c) => ({
      id: c.id,
      name: c.name,
      username: c.id.replace(/^u-/, ""),
      rank: c.rank,
      rank_band: (c.rank_band?.toLowerCase() === "officer" ? "officer" : "rating") as "officer" | "rating",
      role: c.role,
      language: c.language || "en",
      created_at: nowIso(),
    }))
  );
}

/** POST /master/crew */
export async function createCrewMember(input: CreateCrewInput): Promise<CrewMember> {
  if (!USE_MOCK) return api("POST", "/master/crew", input);
  return latency(() => {
    return {
      id: id("u"),
      name: input.name,
      username: input.username,
      rank: input.rank,
      rank_band: input.rank_band || "rating",
      role: "crew" as const,
      language: input.language || "en",
      created_at: nowIso(),
    };
  });
}

/** DELETE /master/crew/{id} */
export async function deleteCrewMember(crewId: string): Promise<void> {
  if (!USE_MOCK) return api("DELETE", `/master/crew/${crewId}`);
  return latency(() => {});
}

