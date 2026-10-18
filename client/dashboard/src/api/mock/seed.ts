import type {
  Analysis,
  HazardType,
  IsmCategory,
  Learning,
  Message,
  OnboardStatus,
  RankBand,
  Severity,
  ShoreStatus,
  Ticket,
  Vessel,
} from "../types";
import craneLeak from "@/assets/photo-crane-leak.jpg";
import mooring from "@/assets/photo-mooring.jpg";
import stairs from "@/assets/photo-stairs.jpg";

const H = 3600_000;
const D = 24 * H;
export const iso = (msAgo: number, now: number) => new Date(now - msAgo).toISOString();
export const dayStr = (d: Date) => d.toISOString().slice(0, 10);

export const CORPUS = [
  {
    source: "MAIB",
    title: "Hydraulic hose failure on deck crane during cargo operations",
    url: "https://www.gov.uk/maib-reports",
    why_relevant: "Same failure mode: weeping fitting progressed to burst hose under load.",
  },
  {
    source: "MAIB",
    title: "Snap-back injury to AB during mooring operations",
    url: "https://www.gov.uk/maib-reports",
    why_relevant: "Worn mooring line used past retirement criteria; crew standing in snap-back zone.",
  },
  {
    source: "TSB",
    title: "Fatal fall on engine room ladder with oil contamination",
    url: "https://www.tsb.gc.ca",
    why_relevant: "Oil on stair treads not cleaned before watch handover.",
  },
  {
    source: "MAIB",
    title: "Enclosed space entry without atmosphere testing in cargo hold",
    url: "https://www.gov.uk/maib-reports",
    why_relevant: "Permit system bypassed under time pressure at discharge port.",
  },
];

export function seedVessels(now: number): Vessel[] {
  return [
    { id: "v1", name: "MV Coral Horizon", type: "Bulk carrier", imo: "9712345", flag: "Marshall Islands", last_sync_at: iso(4 * 60_000, now), crew_count: 21 },
    { id: "v2", name: "MV Blue Meridian", type: "Bulk carrier", imo: "9712357", flag: "Marshall Islands", last_sync_at: iso(38 * 60_000, now), crew_count: 20 },
    { id: "v3", name: "MT Sea Lantern", type: "Tanker", imo: "9654321", flag: "Liberia", last_sync_at: iso(2.2 * H, now), crew_count: 24 },
    { id: "v4", name: "MV Pacific Dawn", type: "Bulk carrier", imo: "9712369", flag: "Panama", last_sync_at: iso(1.1 * H, now), crew_count: 19 },
    { id: "v5", name: "MT Northern Tide", type: "Tanker", imo: "9660012", flag: "Singapore", last_sync_at: iso(5.5 * H, now), crew_count: 23 },
    { id: "v6", name: "MV Harbor Star", type: "Container", imo: "9801177", flag: "Malta", last_sync_at: iso(20 * 60_000, now), crew_count: 4 },
  ];
}

type Row = [
  vessel: number,
  title: string,
  desc: string,
  hazard: HazardType,
  ism: IsmCategory,
  sev: Severity,
  shore: ShoreStatus,
  onboard: OnboardStatus,
  hoursAgo: number,
  rank: RankBand,
  location: string,
  immediate: string,
  photos?: string[],
];

const ROWS: Row[] = [
  [1, "Hydraulic oil leaking from No.2 crane slewing hose", "During cargo ops a steady drip of hydraulic oil was noticed at the slewing motor hose fitting of crane No.2. Oil pooled on deck around the pedestal. Operator continued lifting for 20 minutes before stopping.", "crane_lifting", "equipment_failure", 4, "NEW", "ACTION_IN_PROGRESS", 3, "Rating", "Main deck, crane No.2 pedestal", "Crane stopped, area cordoned, absorbent applied.", [craneLeak]],
  [2, "Crane No.3 hydraulic hose weeping at luffing cylinder", "Small leak at luffing cylinder hose. Fitting looks corroded. Reported to bosun, crane still in use with monitoring.", "crane_lifting", "equipment_failure", 3, "NEW", "ACKNOWLEDGED", 9, "Officer", "Main deck, crane No.3", "Drip tray placed, hourly checks."],
  [4, "क्रेन नंबर 1 की हाइड्रोलिक पाइप से तेल रिसाव", "Oil leaking from hydraulic pipe of crane No.1 while lifting hatch cover. Deck became slippery and one AB almost slipped near pedestal.", "crane_lifting", "equipment_failure", 4, "IN_REVIEW", "ACTION_IN_PROGRESS", 30, "Rating", "Main deck, crane No.1", "Crane isolated. Oil cleaned. Spare hose requested."],
  [3, "Gas detector found out of calibration before tank entry", "Portable 4-gas meter showed calibration expired 2 weeks ago, noticed during pre-entry checks for cargo tank 3P.", "enclosed_space", "procedure_gap", 5, "NEW", "SUBMITTED", 1.5, "Officer", "Cargo tank 3P", "Entry postponed, spare calibrated meter used."],
  [1, "Mooring line chafed through outer strands", "Aft spring line found with outer strands chafed through at fairlead. Line had been in service beyond its recorded retirement date.", "mooring", "unsafe_condition", 4, "IN_REVIEW", "ACTION_IN_PROGRESS", 50, "Rating", "Aft mooring deck", "Line replaced with spare.", [mooring]],
  [5, "Oil on engine room stairs after purifier overflow", "Purifier overflow left oil on the stairs from upper platform. Oiler slipped two steps but held the handrail.", "slip_trip_fall", "unsafe_condition", 3, "NEW", "RESOLVED_ON_BOARD", 6, "Rating", "Engine room, upper platform stairs", "Stairs cleaned, purifier alarm tested.", [stairs]],
  [6, "Lashing rod dropped from container bay 18", "A lashing rod slipped from a stevedore's hands and fell from tier 3, landing 1 m from a crew member.", "crane_lifting", "unsafe_act", 4, "NEW", "ACKNOWLEDGED", 12, "Cadet", "Bay 18, deck", "Ops stopped, stevedore foreman informed."],
  [2, "Missing guard on workshop grinder", "Bench grinder in workshop found without eye shield. Used by fitter without goggles.", "machinery", "unsafe_condition", 2, "CLOSED", "RESOLVED_ON_BOARD", 200, "Officer", "Engine workshop", "Shield refitted, toolbox talk held."],
  [3, "Chemical splash during sampling", "During cargo sampling a small splash reached the forearm of the pumpman; gloves were short-cuff.", "chemical", "unsafe_act", 3, "IN_REVIEW", "RESOLVED_ON_BOARD", 72, "Rating", "Manifold area", "Eyewash used as precaution, long-cuff gloves issued."],
  [4, "Electrical panel left open in steering gear room", "Panel door found open with live terminals exposed after maintenance.", "electrical", "unsafe_condition", 3, "NEW", "SUBMITTED", 20, "Crew", "Steering gear room", "Panel closed and locked."],
  [5, "Galley deep fryer overheated", "Thermostat stuck, oil started smoking. Cook switched off at mains.", "fire", "equipment_failure", 4, "CLOSED", "RESOLVED_ON_BOARD", 310, "Crew", "Galley", "Fryer tagged out, thermostat replaced."],
  [6, "Trip hazard from loose deck cable", "Temporary reefer cable laid across walkway without cover.", "slip_trip_fall", "unsafe_condition", 2, "REJECTED", "RESOLVED_ON_BOARD", 400, "Rating", "Port walkway", "Cable rerouted."],
  [1, "Hatch cover moved with person nearby", "Hatch cover opened while AB was still inside the danger zone checking cleats.", "machinery", "unsafe_act", 5, "IN_REVIEW", "ACTION_IN_PROGRESS", 40, "Officer", "Hold No.4 hatch", "Ops stopped, communication procedure reviewed."],
  [2, "Pilot ladder side rope worn", "Side rope of pilot ladder shows wear near the 5th step.", "other", "unsafe_condition", 3, "CLOSED", "RESOLVED_ON_BOARD", 500, "Officer", "Starboard pilot station", "Ladder replaced from stores."],
  [3, "Fire door wedged open in accommodation", "A-deck fire door was wedged with a chock for ventilation.", "fire", "unsafe_act", 3, "REJECTED", "RESOLVED_ON_BOARD", 260, "Crew", "A-deck corridor", "Wedge removed."],
  [4, "Forklift reversing alarm not working", "Engine room forklift reverse alarm inoperative.", "machinery", "equipment_failure", 2, "CLOSED", "RESOLVED_ON_BOARD", 600, "Rating", "Engine store", "Alarm repaired."],
  [5, "Inert gas pressure drop during discharge", "IG pressure dropped below 100 mmWG briefly during discharge.", "enclosed_space", "equipment_failure", 4, "CLOSED", "RESOLVED_ON_BOARD", 450, "Officer", "Cargo control room", "Discharge rate reduced."],
  [6, "Slippery gangway in rain", "Gangway treads slippery; no safety net rigged.", "slip_trip_fall", "unsafe_condition", 3, "IN_REVIEW", "ACKNOWLEDGED", 90, "Cadet", "Gangway", "Net rigged, anti-slip mats added."],
  [1, "Welding without fire watch", "Hot work near hold No.2 without assigned fire watch.", "fire", "procedure_gap", 4, "CLOSED", "RESOLVED_ON_BOARD", 380, "Officer", "Main deck, hold No.2", "Work stopped, permit reissued."],
  [2, "Heaving line monkey fist weighted", "Shore linesman threw heaving line with weighted monkey fist.", "mooring", "unsafe_act", 2, "REJECTED", "RESOLVED_ON_BOARD", 520, "Rating", "Forecastle", "Port informed."],
  [3, "Ballast pump coupling guard missing", "Coupling guard removed and not refitted after overhaul.", "machinery", "unsafe_condition", 3, "NEW", "SUBMITTED", 28, "Rating", "Pump room", "Area barricaded."],
  [4, "Accommodation ladder winch brake slipping", "Brake slipped 30 cm when lowering ladder.", "machinery", "equipment_failure", 4, "CLOSED", "RESOLVED_ON_BOARD", 650, "Officer", "Port side", "Brake lining replaced."],
  [5, "Battery room ventilation fan stopped", "Fan found stopped; hydrogen smell noticed.", "electrical", "equipment_failure", 3, "IN_REVIEW", "ACTION_IN_PROGRESS", 110, "Officer", "Battery room", "Door opened, fan repaired."],
  [6, "Stack collapse risk from damaged twistlock", "Damaged twistlock found at bay 22 tier 4.", "other", "equipment_failure", 2, "NEW", "SUBMITTED", 16, "Crew", "Bay 22", "Reported to chief officer."],
  [1, "Paint locker CO2 seal broken", "CO2 system seal on paint locker found broken.", "fire", "unsafe_condition", 1, "CLOSED", "RESOLVED_ON_BOARD", 700, "Rating", "Paint locker", "Checked & resealed."],
];

const HINDI = "क्रेन नंबर 1 की हाइड्रोलिक पाइप से तेल रिसाव हो रहा था जब हम हैच कवर उठा रहे थे। डेक फिसलन भरा हो गया और एक एबी पेडस्टल के पास लगभग फिसल गया।";

export function seedTickets(now: number, vessels: Vessel[]): Ticket[] {
  const counters: Record<number, number> = {};
  return ROWS.map((r, i) => {
    const [vi, title, desc, hazard, ism, sev, shore, onboard, hoursAgo, rank, location, immediate, photos] = r;
    const v = vessels[vi - 1];
    counters[vi] = (counters[vi] ?? 40) + 1;
    const isHindi = i === 2;
    const received = now - hoursAgo * H;
    return {
      id: `t${i + 1}`,
      ticket_no: `BCN-000${vi}-0${counters[vi]}`,
      vessel: { id: v.id, name: v.name, type: v.type },
      rank_band: rank,
      title_en: isHindi ? "Hydraulic oil leaking from crane No.1 pipe" : title,
      description_en: desc,
      description_original: isHindi ? HINDI : desc,
      original_language: isHindi ? "Hindi" : "English",
      location_on_board: location,
      hazard_type: hazard,
      ism_category: ism,
      severity: sev,
      immediate_action: immediate,
      photos: photos ?? [],
      onboard_status: onboard,
      shore_status: shore,
      onboard_actions:
        onboard === "SUBMITTED"
          ? []
          : [
              { text: "Acknowledged and discussed at toolbox meeting", responsible_rank: "Master", due_at: new Date(received + 6 * H).toISOString(), created_at: new Date(received + 1 * H).toISOString() },
              ...(onboard !== "ACKNOWLEDGED"
                ? [{ text: immediate, responsible_rank: "Chief Officer", due_at: new Date(received + 24 * H).toISOString(), created_at: new Date(received + 2 * H).toISOString() }]
                : []),
            ],
      assigned_to: shore === "IN_REVIEW" || shore === "CLOSED" ? "Anita Rao" : undefined,
      reject_reason: shore === "REJECTED" ? (i % 2 ? "out_of_scope" : "duplicate") : undefined,
      reject_note: shore === "REJECTED" ? "Handled under vessel's routine maintenance system." : undefined,
      similar_count: hazard === "crane_lifting" && i < 3 ? 2 : (i * 7) % 3,
      occurred_at: new Date(received - 2 * H).toISOString(),
      received_at: new Date(received).toISOString(),
      updated_at: new Date(received).toISOString(),
    };
  });
}

const FACTORS: Record<HazardType, string[]> = {
  crane_lifting: ["Hose fittings beyond PMS replacement interval", "Leak normalised during cargo time pressure", "No drip-tray or spill kit staged at pedestal"],
  mooring: ["Line retirement records not cross-checked", "Fairlead roller seized causing chafe", "Crew positioned in snap-back zone"],
  slip_trip_fall: ["Housekeeping not part of watch handover", "Spill not reported immediately", "Poor lighting on stairway"],
  enclosed_space: ["Calibration tracking manual and unreviewed", "Pre-entry checklist lacks calibration date field", "Schedule pressure at port"],
  fire: ["Hot-work permit steps skipped", "Routine maintenance not scheduled", "Familiarity reduced vigilance"],
  machinery: ["Guards not refitted after overhaul", "Communication between operator and deck team", "Maintenance sign-off incomplete"],
  electrical: ["LOTO not applied after maintenance", "Panel locks missing", "Inspection rounds skipped"],
  chemical: ["Incorrect PPE selected for cargo", "MSDS not reviewed before sampling", "Sampling point position awkward"],
  other: ["Equipment condition checks not formalised", "Spare availability", "Reporting culture"],
};

export function seedAnalysis(t: Ticket, all: Ticket[], now: number): Analysis {
  const similar = all
    .filter((o) => o.id !== t.id && o.hazard_type === t.hazard_type)
    .slice(0, 3)
    .map((o, i) => ({ ticket_id: o.id, ticket_no: o.ticket_no, vessel: o.vessel.name, title: o.title_en, score: +(0.92 - i * 0.11).toFixed(2) }));
  const corpus =
    t.hazard_type === "crane_lifting"
      ? [CORPUS[0]]
      : t.hazard_type === "mooring"
        ? [CORPUS[1]]
        : t.hazard_type === "slip_trip_fall"
          ? [CORPUS[2]]
          : t.hazard_type === "enclosed_space"
            ? [CORPUS[3]]
            : [];
  const suggestedSev = (t.hazard_type === "crane_lifting" && t.severity < 5 ? Math.min(5, t.severity + 1) : t.severity) as Severity;
  const suggestedIsm: IsmCategory = t.hazard_type === "crane_lifting" && t.ism_category !== "equipment_failure" ? "equipment_failure" : t.ism_category;
  return {
    ticket_id: t.id,
    model: "Gemini 2.5 Pro",
    created_at: new Date(new Date(t.received_at).getTime() + 5 * 60_000 > now ? now : new Date(t.received_at).getTime() + 5 * 60_000).toISOString(),
    summary: [
      `${t.title_en} on ${t.vessel.name}.`,
      `Reported by a ${t.rank_band.toLowerCase()}; immediate action: ${t.immediate_action.toLowerCase()}`,
      /hydraul/i.test(t.title_en) ? "Pattern matches 2 other crane hydraulic reports on sister vessels in 30 days." : "No recurring pattern detected fleet-wide in the last 30 days.",
    ],
    contributing_factors: FACTORS[t.hazard_type],
    ism_check: {
      current: t.ism_category,
      suggested: suggestedIsm,
      reason: suggestedIsm === t.ism_category ? "Category is consistent with the described events." : "Root cause is component degradation rather than crew behaviour.",
    },
    severity_check: {
      current: t.severity,
      suggested: suggestedSev,
      reason: suggestedSev === t.severity ? "Severity is consistent with potential outcome." : "Burst hose under load can cause dropped load and high-pressure injection injury.",
    },
    similar_tickets: similar,
    corpus_matches: corpus,
    recommendations: [
      { type: "corrective", text: t.immediate_action },
      { type: "corrective", text: "Verify condition of equivalent equipment on board within 48 h." },
      { type: "preventive", text: "Add item to PMS with shortened inspection interval." },
      { type: "preventive", text: "Share learning fleet-wide via a 60-second microlearning." },
    ],
    suggest_learning: t.severity >= 3,
  };
}

export function seedMessages(tickets: Ticket[], now: number): Message[] {
  const m: Message[] = [];
  for (const t of tickets.slice(0, 8)) {
    const r = new Date(t.received_at).getTime();
    m.push({ id: `m-${t.id}-1`, ticket_id: t.id, sender: "master", body: "Received. We have discussed this at the morning toolbox meeting.", created_at: new Date(r + H).toISOString(), delivered_at: new Date(r + H).toISOString() });
    if (t.shore_status !== "NEW") {
      m.push({ id: `m-${t.id}-2`, ticket_id: t.id, sender: "shore", shore_user_name: "Anita Rao", body: "Thank you for reporting this. We are reviewing and will share findings across the fleet.", created_at: new Date(r + 4 * H).toISOString(), delivered_at: new Date(Math.min(now, r + 6 * H)).toISOString() });
      m.push({ id: `m-${t.id}-3`, ticket_id: t.id, sender: "reporter", body: "Thanks. The spare hose arrived at last port but no one fitted it yet.", created_at: new Date(Math.min(now, r + 7 * H)).toISOString(), delivered_at: new Date(Math.min(now, r + 7 * H)).toISOString() });
    }
  }
  return m;
}

export function seedLearnings(now: number): Learning[] {
  const base = {
    tags: { tool: "Hydraulic crane", area: "Main deck", situation: "Cargo ops" },
    rank_filter: "all" as const,
    ai_drafted_fields: [],
    check_question: { q: "A hose fitting is weeping during ops. What do you do first?", options: ["Keep lifting and monitor", "Stop the crane and report", "Wipe it and continue"], answer_index: 1 },
    do_points: ["Stop the crane at first sign of a leak", "Place drip tray and absorbent", "Report to OOW immediately"],
    dont_points: ["Don't keep lifting 'to finish the hatch'", "Don't touch a pressurised hose", "Don't walk through oil on deck"],
  };
  return [
    { ...base, id: "l1", source_ticket_id: "t3", title: "A small leak is a big warning", context: "Three sister vessels reported crane hydraulic leaks in 30 days.", situation: "Oil dripping at a hose fitting while lifting a hatch cover.", media: [{ id: "md1", kind: "image", url: craneLeak, bytes: 420_000, primary: true }], audience: { mode: "all", vessel_ids: [] }, priority: "urgent", status: "published", stats: { vessels_delivered: 4, vessels_total: 6, opened: 61, acknowledged: 48, check_correct: 44 }, published_at: iso(2 * D, now), updated_at: iso(2 * D, now) },
    { ...base, id: "l2", source_ticket_id: "t5", title: "Know when to retire a mooring line", context: "Lines in service beyond retirement criteria.", situation: "Outer strands chafed at fairlead.", tags: { tool: "Mooring line", area: "Aft deck", situation: "Mooring" }, media: [{ id: "md2", kind: "image", url: mooring, bytes: 380_000, primary: true }], audience: { mode: "selected", vessel_ids: ["v1", "v2", "v4"] }, priority: "normal", status: "published", stats: { vessels_delivered: 3, vessels_total: 3, opened: 52, acknowledged: 30, check_correct: 27 }, published_at: iso(6 * D, now), updated_at: iso(6 * D, now) },
    { ...base, id: "l3", source_ticket_id: "t6", title: "Clean the spill before the handover", context: "Oil on stairs after purifier overflow.", situation: "Oiler slipped on stairs.", tags: { tool: "Purifier", area: "Engine room", situation: "Watchkeeping" }, media: [], audience: { mode: "same_vessel", vessel_ids: ["v5"] }, priority: "normal", status: "draft", stats: { vessels_delivered: 0, vessels_total: 1, opened: 0, acknowledged: 0, check_correct: 0 }, updated_at: iso(5 * H, now) },
    { ...base, id: "l4", title: "Hot work needs a fire watch, always", context: "Welding without fire watch.", situation: "Hot work near hold.", tags: { tool: "Welding set", area: "Main deck", situation: "Hot work" }, media: [], audience: { mode: "all", vessel_ids: [] }, priority: "normal", status: "retracted", stats: { vessels_delivered: 6, vessels_total: 6, opened: 80, acknowledged: 41, check_correct: 39 }, published_at: iso(15 * D, now), updated_at: iso(10 * D, now) },
  ];
}


export const NEW_TICKET_TEMPLATES: Row[] = [
  [1, "Crane No.4 hydraulic hose bulging", "Visible bulge on hydraulic hose near the jib.", "crane_lifting", "equipment_failure", 4, "NEW", "SUBMITTED", 0, "Rating", "Main deck, crane No.4", "Crane stopped."],
  [1, "Loose handrail on poop deck ladder", "Handrail moves when weight applied.", "slip_trip_fall", "unsafe_condition", 2, "NEW", "SUBMITTED", 0, "Cadet", "Poop deck", "Taped off."],
];
export type TicketRow = Row;
