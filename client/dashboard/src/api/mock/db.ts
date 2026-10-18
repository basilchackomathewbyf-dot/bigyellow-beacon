// In-memory mock backend. State persists in sessionStorage for the session.
import type {
  Analysis,
  FleetOverview,
  HazardCluster,
  Learning,
  LearningDraft,
  LearningInput,
  LoginResponse,
  Message,
  RejectReason,
  Severity,
  Ticket,
  TicketFilters,
  User,
  Vessel,
} from "../types";
import {
  NEW_TICKET_TEMPLATES,
  dayStr,
  seedAnalysis,
  seedLearnings,
  seedMessages,
  seedTickets,
  seedVessels,
} from "./seed";
import { audienceCount, canShowWellbeing, canTransition, validateReject } from "@/lib/rules";
import { authStore } from "@/lib/auth-store";

const KEY = "beacon.mockdb.v1";

interface DB {
  vessels: Vessel[];
  tickets: Ticket[];
  analyses: Record<string, Analysis>;
  messages: Message[];
  learnings: Learning[];
  seq: number;
}

function fresh(): DB {
  const now = Date.now();
  const vessels = seedVessels(now);
  const tickets = seedTickets(now, vessels);
  const analyses: Record<string, Analysis> = {};
  tickets.forEach((t) => (analyses[t.id] = seedAnalysis(t, tickets, now)));
  return { vessels, tickets, analyses, messages: seedMessages(tickets, now), learnings: seedLearnings(now), seq: 100 };
}

let db: DB | null = null;
function get(): DB {
  if (db) return db;
  if (typeof window !== "undefined") {
    const raw = sessionStorage.getItem(KEY);
    if (raw) {
      try {
        db = JSON.parse(raw) as DB;
        return db;
      } catch {
        /* fall through */
      }
    }
  }
  db = fresh();
  save();
  return db;
}
function save() {
  if (typeof window !== "undefined" && db) sessionStorage.setItem(KEY, JSON.stringify(db));
}

const latency = () => new Promise((r) => setTimeout(r, 30));
const clone = <T,>(v: T): T => structuredClone(v);
async function respond<T>(fn: () => T): Promise<T> {
  await latency();
  const out = fn();
  save();
  return clone(out);
}
const notFound = (what: string) => new Error(`${what} not found`);
const me = (): User => authStore.getUser() ?? { id: "u0", name: "Shore team", email: "", role: "reviewer" };
const nowIso = () => new Date().toISOString();
const uid = (p: string) => `${p}${++get().seq}`;

export const mock = {
  // ---- auth ----
  login: (email: string, _password: string) =>
    respond<LoginResponse>(() => {
      const admin = email.toLowerCase().startsWith("admin");
      return {
        token: `mock.${btoa(email)}.${Date.now()}`,
        user: { id: admin ? "u2" : "u1", name: admin ? "Marcus Lee" : "Anita Rao", email, role: admin ? "admin" : "reviewer" },
      };
    }),

  // ---- tickets ----
  listTickets: (f: TicketFilters) =>
    respond(() => {
      const q = f.q?.toLowerCase();
      return get()
        .tickets.filter((t) => {
          if (f.status && t.shore_status !== f.status) return false;
          if (f.vessel_id?.length && !f.vessel_id.includes(t.vessel.id)) return false;
          if (f.severity?.length && !f.severity.includes(t.severity)) return false;
          if (f.hazard_type?.length && !f.hazard_type.includes(t.hazard_type)) return false;
          if (f.ism_category?.length && !f.ism_category.includes(t.ism_category)) return false;
          if (f.from && t.received_at < f.from) return false;
          if (f.to && t.received_at > f.to) return false;
          if (f.updated_since && t.updated_at <= f.updated_since) return false;
          if (q && !`${t.ticket_no} ${t.title_en}`.toLowerCase().includes(q)) return false;
          return true;
        })
        .sort((a, b) => b.severity - a.severity || a.received_at.localeCompare(b.received_at));
    }),
  getTicket: (id: string) =>
    respond(() => {
      const t = get().tickets.find((x) => x.id === id);
      if (!t) throw notFound("Ticket");
      return t;
    }),
  patchTicket(id: string, fn: (t: Ticket) => void) {
    return respond(() => {
      const t = get().tickets.find((x) => x.id === id);
      if (!t) throw notFound("Ticket");
      fn(t);
      t.updated_at = nowIso();
      return t;
    });
  },
  accept: (id: string) =>
    mock.patchTicket(id, (t) => {
      if (!canTransition("accept", t.shore_status)) throw new Error("Only NEW tickets can be accepted");
      t.shore_status = "IN_REVIEW";
      t.assigned_to = me().name;
    }),
  reject: (id: string, reason: RejectReason, note: string) =>
    mock.patchTicket(id, (t) => {
      if (!canTransition("reject", t.shore_status)) throw new Error("Only NEW tickets can be rejected");
      if (!validateReject(reason, note)) throw new Error("Reason and note are required");
      t.shore_status = "REJECTED";
      t.reject_reason = reason;
      t.reject_note = note;
    }),
  close: (id: string, resolution_note: string) =>
    mock.patchTicket(id, (t) => {
      if (!canTransition("close", t.shore_status)) throw new Error("Only IN_REVIEW tickets can be closed");
      t.shore_status = "CLOSED";
      t.resolution_note = resolution_note;
    }),
  updateFields: (id: string, patch: Partial<Pick<Ticket, "severity" | "ism_category">>) =>
    mock.patchTicket(id, (t) => Object.assign(t, patch)),
  similar: (id: string) =>
    respond(() => {
      const t = get().tickets.find((x) => x.id === id);
      if (!t) throw notFound("Ticket");
      return get().tickets.filter((o) => o.id !== id && o.hazard_type === t.hazard_type).slice(0, 5);
    }),

  // ---- messages ----
  listMessages: (ticketId: string) =>
    respond(() => {
      // Simulated ship sync: queued shore messages older than 45s get delivered.
      const cutoff = Date.now() - 45_000;
      get().messages.forEach((m) => {
        if (!m.delivered_at && new Date(m.created_at).getTime() < cutoff) m.delivered_at = nowIso();
      });
      return get().messages.filter((m) => m.ticket_id === ticketId).sort((a, b) => a.created_at.localeCompare(b.created_at));
    }),
  sendMessage: (ticketId: string, body: string) =>
    respond(() => {
      const m: Message = { id: uid("m"), ticket_id: ticketId, sender: "shore", shore_user_name: me().name, body, created_at: nowIso() };
      get().messages.push(m);
      return m;
    }),

  // ---- analysis ----
  getAnalysis: (ticketId: string) =>
    respond(() => {
      const a = get().analyses[ticketId];
      if (!a) throw notFound("Analysis");
      return a;
    }),
  rerunAnalysis: async (ticketId: string) => {
    await latency();
    return respond(() => {
      const d = get();
      const t = d.tickets.find((x) => x.id === ticketId);
      if (!t) throw notFound("Ticket");
      d.analyses[ticketId] = { ...seedAnalysis(t, d.tickets, Date.now()), created_at: nowIso() };
      return d.analyses[ticketId];
    });
  },

  // ---- learnings ----
  listLearnings: () => respond(() => [...get().learnings].sort((a, b) => b.updated_at.localeCompare(a.updated_at))),
  getLearning: (id: string) =>
    respond(() => {
      const l = get().learnings.find((x) => x.id === id);
      if (!l) throw notFound("Learning");
      return l;
    }),
  draftLearning: async (ticketId?: string) => {
    await latency();
    return respond<LearningDraft>(() => {
      const t = ticketId ? get().tickets.find((x) => x.id === ticketId) : undefined;
      const topic = t?.title_en ?? "Stop, think, report";
      return {
        title: t ? `Lesson: ${topic}`.slice(0, 60) : "Stop, think, report",
        context: t ? `Reported on ${t.vessel.name}. Similar reports seen on ${t.similar_count} other vessels.` : "A fleet-wide reminder.",
        situation: t?.description_en ?? "A hazard noticed during routine work.",
        do_points: ["Stop the job when something looks wrong", "Make the area safe and report", "Share what you saw at the toolbox talk"],
        dont_points: ["Don't continue to 'just finish'", "Don't fix it alone without a permit", "Don't assume someone else reported it"],
        check_question: { q: "You notice the hazard mid-task. What comes first?", options: ["Finish the task", "Stop and make safe", "Tell someone after shift"], answer_index: 1 },
        tags: { tool: t?.hazard_type.replace(/_/g, " "), area: t?.location_on_board, situation: "Routine work" },
        ai_drafted_fields: ["title", "context", "situation", "do_points", "dont_points", "check_question", "tags"],
      };
    });
  },
  createLearning: (input: LearningInput) =>
    respond(() => {
      const l: Learning = {
        ...input,
        id: uid("l"),
        status: "draft",
        stats: { vessels_delivered: 0, vessels_total: audienceCount(input.audience.mode, input.audience.vessel_ids, get().vessels.length), opened: 0, acknowledged: 0, check_correct: 0 },
        updated_at: nowIso(),
      };
      get().learnings.push(l);
      return l;
    }),
  patchLearning: (id: string, patch: Partial<Learning>) =>
    respond(() => {
      const l = get().learnings.find((x) => x.id === id);
      if (!l) throw notFound("Learning");
      Object.assign(l, patch, { updated_at: nowIso() });
      l.stats.vessels_total = audienceCount(l.audience.mode, l.audience.vessel_ids, get().vessels.length);
      return l;
    }),
  publishLearning: (id: string) =>
    mock.patchLearning(id, { status: "published", published_at: nowIso() }),
  retractLearning: (id: string) => mock.patchLearning(id, { status: "retracted" }),

  // ---- fleet ----
  listVessels: () => respond(() => get().vessels),
  fleetOverview: () =>
    respond<FleetOverview>(() => {
      const d = get();
      const now = Date.now();
      const open = d.tickets.filter((t) => t.shore_status === "NEW" || t.shore_status === "IN_REVIEW");
      const bySev = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 } as Record<Severity, number>;
      open.forEach((t) => bySev[t.severity]++);
      const pub = d.learnings.filter((l) => l.status === "published");
      const opened = pub.reduce((s, l) => s + l.stats.opened, 0);
      const ack = pub.reduce((s, l) => s + l.stats.acknowledged, 0);
      const hazards = new Map<string, number>();
      d.tickets.forEach((t) => hazards.set(t.hazard_type, (hazards.get(t.hazard_type) ?? 0) + 1));
      const trend = Array.from({ length: 30 }, (_, i) => {
        const day = new Date(now - (29 - i) * 86400_000);
        const ds = dayStr(day);
        return { date: ds, reports: d.tickets.filter((t) => t.received_at.slice(0, 10) === ds).length, checkins: 30 + ((i * 13) % 17) };
      });
      const lastSync = d.vessels.reduce((m, v) => (v.last_sync_at > m ? v.last_sync_at : m), "");
      return {
        open_by_severity: bySev,
        new_last_24h: d.tickets.filter((t) => now - new Date(t.received_at).getTime() < 86400_000).length,
        median_accept_hours: 5.4,
        learning_ack_rate: opened ? ack / opened : 0,
        per_vessel: d.vessels.map((v) => {
          const ts = d.tickets.filter((t) => t.vessel.id === v.id);
          const c = (s: number) => ts.filter((t) => t.severity === s).length;
          return { vessel: v.name.replace(/^(MV|MT) /, ""), s1: c(1), s2: c(2), s3: c(3), s4: c(4), s5: c(5) };
        }),
        top_hazards: [...hazards.entries()].map(([hazard_type, count]) => ({ hazard_type: hazard_type as Ticket["hazard_type"], count })).sort((a, b) => b.count - a.count).slice(0, 6),
        trend,
        wellbeing: d.vessels.map((v, i) => {
          const n = v.crew_count > 5 ? 8 + i * 2 : 3;
          const show = canShowWellbeing(n);
          return { vessel_id: v.id, vessel: v.name, n, mood: show ? +(3.2 + ((i * 0.37) % 1.4)).toFixed(1) : null, fatigue: show ? +(2.1 + ((i * 0.53) % 1.6)).toFixed(1) : null, mood_trend: (["up", "flat", "down"] as const)[i % 3], fatigue_trend: (["down", "up", "flat"] as const)[i % 3] };
        }),
        last_ship_sync_at: lastSync,
      };
    }),
  clusters: () =>
    respond<HazardCluster[]>(() => {
      const d = get();
      const crane = d.tickets.filter((t) => t.hazard_type === "crane_lifting" && /hydraul|तेल/i.test(t.title_en + t.description_original));
      const slips = d.tickets.filter((t) => t.hazard_type === "slip_trip_fall");
      const enclosed = d.tickets.filter((t) => t.hazard_type === "enclosed_space");
      const mk = (id: string, label: string, ts: Ticket[], q: string): HazardCluster => ({ id, label, hazard_type: ts[0]?.hazard_type ?? "other", vessel_count: new Set(ts.map((t) => t.vessel.id)).size, ticket_count: ts.length, ticket_ids: ts.map((t) => t.id), q });
      return [mk("c1", "Crane hydraulic leaks", crane, "hydraulic"), mk("c2", "Oil and wet surfaces underfoot", slips, ""), mk("c3", "Gas testing before entry", enclosed, "")].filter((c) => c.ticket_count > 0);
    }),

  // ---- dev panel ----
  simulateNewTickets: (count = 2) =>
    respond(() => {
      const d = get();
      const now = Date.now();
      const created: Ticket[] = [];
      for (let i = 0; i < count; i++) {
        const tpl = NEW_TICKET_TEMPLATES[i % NEW_TICKET_TEMPLATES.length];
        const [t] = seedTickets(now, d.vessels).slice(0, 1);
        const n = ++d.seq;
        const nt: Ticket = {
          ...t,
          id: `t${n}`,
          ticket_no: `BCN-000${tpl[0]}-${n}`,
          vessel: { id: d.vessels[tpl[0] - 1].id, name: d.vessels[tpl[0] - 1].name, type: d.vessels[tpl[0] - 1].type },
          title_en: tpl[1],
          description_en: tpl[2],
          description_original: tpl[2],
          original_language: "English",
          hazard_type: tpl[3],
          ism_category: tpl[4],
          severity: tpl[5],
          shore_status: "NEW",
          onboard_status: "SUBMITTED",
          rank_band: tpl[9],
          location_on_board: tpl[10],
          immediate_action: tpl[11],
          photos: [],
          onboard_actions: [],
          assigned_to: undefined,
          received_at: new Date(now).toISOString(),
          occurred_at: new Date(now - 30 * 60_000).toISOString(),
          updated_at: new Date(now + 1).toISOString(),
        };
        d.tickets.push(nt);
        d.analyses[nt.id] = seedAnalysis(nt, d.tickets, now);
        created.push(nt);
      }
      d.vessels[0].last_sync_at = nowIso();
      return created;
    }),
  simulateReporterReply: () =>
    respond(() => {
      const d = get();
      const lastShore = [...d.messages].reverse().find((m) => m.sender === "shore");
      const ticketId = lastShore?.ticket_id ?? d.tickets[0].id;
      const m: Message = { id: uid("m"), ticket_id: ticketId, sender: "reporter", body: "Thank you for the reply. The crew has been briefed today.", created_at: nowIso(), delivered_at: nowIso() };
      d.messages.push(m);
      const t = d.tickets.find((x) => x.id === ticketId);
      if (t) t.updated_at = nowIso();
      return m;
    }),
  simulateShipSync: () =>
    respond(() => {
      const d = get();
      d.vessels.forEach((v) => (v.last_sync_at = nowIso()));
      d.messages.forEach((m) => (m.delivered_at ??= nowIso()));
      return true;
    }),
  reset: () => {
    db = fresh();
    save();
  },
};
