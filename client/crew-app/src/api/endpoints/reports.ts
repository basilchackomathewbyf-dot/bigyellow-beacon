import { USE_MOCK } from "../config";
import { api } from "../client";
import { events } from "../events";
import { ApiError, type DraftInput, type HazardType, type Message, type ReportFields, type StructureResult, type Ticket } from "../types";
import { getDb } from "../mock/db";
import { id, latency, nowIso } from "../mock/util";

// POST /api/v1/reports/drafts (multipart: audio?, photos[]?, text?, duration?)
export async function createDraft(input: DraftInput): Promise<{ draft_id: string }> {
  if (!USE_MOCK) {
    const fd = new FormData();
    if (input.audio) fd.append("audio", input.audio, "voice.webm");
    if (input.duration !== undefined && input.duration !== null) fd.append("duration", String(input.duration));
    input.photos?.forEach((p, i) => fd.append("photos[]", p, `photo-${i}.jpg`));
    if (input.text) fd.append("text", input.text);
    return api("POST", "/api/v1/reports/drafts", fd);
  }
  // Object URLs are created outside the clone so blobs survive.
  const audio_url = input.audio ? URL.createObjectURL(input.audio) : undefined;
  const photo_urls = (input.photos ?? []).map((p) => URL.createObjectURL(p));
  return latency(() => {
    const draft_id = id("dr");
    getDb().drafts[draft_id] = { id: draft_id, text: input.text, audio_url, photo_urls };
    return { draft_id };
  });
}

const guessHazard = (t: string): HazardType => {
  const s = t.toLowerCase();
  if (/(slip|trip|fall|oil|wet)/.test(s)) return "slip_trip_fall";
  if (/(moor|rope|line)/.test(s)) return "mooring";
  if (/(crane|lift|sling)/.test(s)) return "crane_lifting";
  if (/(tank|enclosed|void)/.test(s)) return "enclosed_space";
  if (/(fire|smoke|hot)/.test(s)) return "fire";
  if (/(cable|electric|wire|shock)/.test(s)) return "electrical";
  if (/(chemical|acid|fume)/.test(s)) return "chemical";
  if (/(engine|pump|machine)/.test(s)) return "machinery";
  return "other";
};

// POST /reports/drafts/{id}/structure
export async function structureDraft(draftId: string): Promise<StructureResult> {
  if (!USE_MOCK) return api("POST", `/reports/drafts/${draftId}/structure`);
  await new Promise((r) => setTimeout(r, 400));
  return latency(() => {
    const d = getDb().drafts[draftId];
    if (!d) throw new ApiError(404, "Draft not found");
    const text = d.text?.trim() || (d.audio_url
      ? "Slipped on hydraulic oil near deck crane 2. No injury. Area not marked."
      : "Hazard seen on board (from photo).");
    const hazard = guessHazard(text);
    const res: StructureResult = {
      original_language: d.text ? "en" : d.audio_url ? "hi" : "en",
      transcript_original: d.audio_url && !d.text ? "डेक क्रेन 2 के पास हाइड्रोलिक तेल पर फिसल गया। कोई चोट नहीं।" : text,
      fields: {
        title_en: text.split(/[.!?]/)[0].slice(0, 70) || "Near-miss on board",
        description_en: text,
        location_on_board: /crane 2/i.test(text) ? "Main deck, crane 2" : "",
        hazard_type: hazard,
        ism_category: "unsafe_condition",
        severity: 3,
        immediate_action: "",
      },
      clarifying_question: /crane|deck/i.test(text) ? undefined : "Where on board did this happen?",
      confidence: 0.78,
    };
    if (!res.fields.location_on_board) res.clarifying_question = "Where on board did this happen?";
    d.structure = res;
    return res;
  });
}

// POST /reports/drafts/{id}/answer
export async function answerDraft(draftId: string, answer: string): Promise<ReportFields> {
  if (!USE_MOCK) return api("POST", `/reports/drafts/${draftId}/answer`, { answer });
  return latency(() => {
    const d = getDb().drafts[draftId];
    if (!d?.structure) throw new ApiError(404, "Draft not found");
    d.structure.fields.location_on_board = answer;
    d.structure.clarifying_question = undefined;
    return d.structure.fields;
  });
}

// POST /reports
export async function submitReport(draft_id: string, fields: ReportFields, share_name_with_master: boolean): Promise<Ticket> {
  if (!USE_MOCK) return api("POST", "/reports", { draft_id, fields, share_name_with_master });
  const t = await latency(() => {
    const db = getDb();
    const d = db.drafts[draft_id];
    const ticket: Ticket = {
      id: id("t"),
      ticket_no: `BCN-0007-${String(db.ticketSeq++).padStart(3, "0")}`,
      ...fields,
      description_original: d?.structure?.transcript_original ?? fields.description_en,
      original_language: d?.structure?.original_language ?? "en",
      photos: d?.photo_urls ?? [],
      audio_url: d?.audio_url,
      share_name_with_master,
      reporter_name: share_name_with_master ? db.user?.name : undefined,
      reporter_id: db.user?.id,
      onboard_status: "SUBMITTED",
      shore_status: db.sync.link === "UP" ? "NEW" : "QUEUED",
      actions: [],
      created_at: nowIso(),
    };
    db.tickets.unshift(ticket);
    return ticket;
  });
  events.emit("ticket.new", t);
  return t;
}

// GET /reports/mine
export async function myReports(): Promise<Ticket[]> {
  if (!USE_MOCK) return api("GET", "/reports/mine");
  return latency(() => getDb().tickets.filter((t) => t.reporter_id === getDb().user?.id));
}

/** GET /tickets/{id} (helper used by detail views) */
export async function getTicket(ticketId: string): Promise<Ticket> {
  if (!USE_MOCK) return api("GET", `/tickets/${ticketId}`);
  return latency(() => {
    const t = getDb().tickets.find((x) => x.id === ticketId);
    if (!t) throw new ApiError(404, "Not found");
    return t;
  });
}

// GET /tickets/{id}/messages
export async function ticketMessages(ticketId: string): Promise<Message[]> {
  if (!USE_MOCK) return api("GET", `/tickets/${ticketId}/messages`);
  return latency(() => getDb().messages.filter((m) => m.ticket_id === ticketId));
}

// POST /tickets/{id}/messages
export async function postMessage(ticketId: string, body: string): Promise<Message> {
  if (!USE_MOCK) return api("POST", `/tickets/${ticketId}/messages`, { body });
  const m = await latency(() => {
    const db = getDb();
    const msg: Message = { id: id("m"), ticket_id: ticketId, sender: db.user?.role === "master" ? "master" : "reporter", body, created_at: nowIso() };
    db.messages.push(msg);
    return msg;
  });
  events.emit("message.new", m);
  return m;
}
