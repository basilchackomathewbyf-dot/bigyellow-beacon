// Dev-panel simulations. Mutate mock state and emit live events.
import { events } from "../events";
import type { Learning, Ticket } from "../types";
import { getDb, resetDb } from "./db";
import { id, nowIso } from "./util";

export function simulateNearMiss() {
  const db = getDb();
  const t: Ticket = {
    id: id("t"), ticket_no: `BCN-0007-${String(db.ticketSeq++).padStart(3, "0")}`,
    title_en: "Unsecured drum rolling on poop deck", description_en: "A chemical drum came loose in the swell.",
    description_original: "Isang drum ng kemikal ang kumawala sa alon.", original_language: "tl",
    location_on_board: "Poop deck, starboard", hazard_type: "chemical", ism_category: "unsafe_condition",
    severity: 4, immediate_action: "Lashed it to the rail.", photos: [], share_name_with_master: true,
    reporter_name: "Jose Santos", reporter_id: "u-3", onboard_status: "SUBMITTED",
    shore_status: db.sync.link === "UP" ? "NEW" : "QUEUED", actions: [], created_at: nowIso(),
  };
  db.tickets.unshift(t);
  events.emit("ticket.new", t);
}

export function simulateShoreReply() {
  const db = getDb();
  const t = db.tickets.find((x) => x.reporter_id === "u-crew") ?? db.tickets[0];
  const m = { id: id("m"), ticket_id: t.id, sender: "shore" as const, body: "Shore safety team here — thank you. We've shared this as a fleet learning.", created_at: nowIso() };
  db.messages.push(m);
  t.shore_status = "IN_REVIEW";
  const item = { id: id("i"), kind: "shore_reply" as const, title: `Shore replied on ${t.ticket_no}`, body: m.body, link: { to: "/reports/$id", id: t.id }, read: false, created_at: nowIso() };
  db.inbox.unshift(item);
  events.emit("message.new", m);
  events.emit("inbox.new", item);
}

export function simulateUrgentLearning() {
  const db = getDb();
  const l: Learning = {
    id: id("l"), title: "Gangway nets after rigging", priority: "urgent", acked: false, created_at: nowIso(),
    context: "A visitor nearly fell between ship and quay last week.", situation: "The safety net was not refitted after the gangway was moved.",
    do_points: ["Refit the net every time the gangway moves", "Check lighting at night"], dont_points: ["Leave the gangway unattended"],
    media: { kind: "image", url: "https://images.unsplash.com/photo-1572883454114-1cf0031ede2a?w=1000&q=60" },
    check_question: { q: "When must the gangway net be refitted?", options: ["Once a voyage", "Every time the gangway moves"], answer_index: 1 },
  };
  db.learnings.unshift(l);
  const item = { id: id("i"), kind: "learning" as const, title: "New urgent learning", body: l.title, link: { to: "/learn/$id", id: l.id }, read: false, created_at: nowIso() };
  db.inbox.unshift(item);
  events.emit("learning.new", l);
  events.emit("inbox.new", item);
}

export function simulateWelfare() {
  const w = { id: id("w"), name: "Olena Kovalenko", created_at: nowIso(), status: "pending" as const };
  getDb().welfare.push(w);
  events.emit("welfare.request", w);
}

export function toggleLink() {
  const s = getDb().sync;
  s.link = s.link === "UP" ? "DOWN" : "UP";
  if (s.link === "UP") s.last_pull_at = s.last_push_at = nowIso();
  events.emit("sync.status", { ...s });
}

export function toggleEdge() {
  const db = getDb();
  db.edgeReachable = !db.edgeReachable;
  events.emit("sync.status", { ...db.sync });
  return db.edgeReachable;
}

export const isEdgeReachable = () => getDb().edgeReachable;
export const resetDemo = resetDb;
