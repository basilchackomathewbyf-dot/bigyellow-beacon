import type {
  AnchorCard, CheckinEntry, CheckinTag, InboxItem, Learning, Message, PairedDevice, Ticket, User, WelfareRequest,
} from "../types";

const DAY = 86_400_000;
const iso = (msAgo: number) => new Date(Date.now() - msAgo).toISOString();
const dateKey = (d: Date) => d.toISOString().slice(0, 10);

export const VESSEL = "MV Coral Horizon";

export const CREW: User[] = [
  { id: "u-master", name: "Capt. Kundan", rank: "Master", rank_band: "officer", role: "master", language: "en", vessel: VESSEL },
  { id: "01a14acb-e04c-79f8-aa4e-0395dcf068d0", name: "Amarjeet", rank: "AB Seaman", rank_band: "rating", role: "crew", language: "en", vessel: VESSEL },
  { id: "u-crew", name: "Amarjeet", rank: "AB Seaman", rank_band: "rating", role: "crew", language: "en", vessel: VESSEL },
  { id: "u-3", name: "Jose Santos", rank: "Bosun", rank_band: "rating", role: "crew", language: "en", vessel: VESSEL },
  { id: "u-4", name: "Olena Kovalenko", rank: "2nd Officer", rank_band: "officer", role: "crew", language: "en", vessel: VESSEL },
  { id: "u-5", name: "Mark Dela Cruz", rank: "Oiler", rank_band: "rating", role: "crew", language: "en", vessel: VESSEL },
  { id: "u-6", name: "Priya Sharma", rank: "3rd Engineer", rank_band: "officer", role: "crew", language: "en", vessel: VESSEL },
  { id: "u-7", name: "Taras Melnyk", rank: "Chief Engineer", rank_band: "officer", role: "crew", language: "en", vessel: VESSEL },
  { id: "u-8", name: "Ramon Bautista", rank: "Cook", rank_band: "rating", role: "crew", language: "en", vessel: VESSEL },
];

export function seedTickets(): Ticket[] {
  const base = (n: number, t: Partial<Ticket>): Ticket => ({
    id: `t-${n}`, ticket_no: `BCN-0007-0${String(n + 35).padStart(2, "0")}`,
    title_en: "", description_en: "", description_original: "", original_language: "en",
    location_on_board: "", hazard_type: "other", ism_category: "unsafe_condition", severity: 2,
    immediate_action: "", photos: [], share_name_with_master: false,
    onboard_status: "SUBMITTED", shore_status: "QUEUED", actions: [], created_at: iso(n * 9 * 3600_000),
    ...t,
  });
  return [
    base(7, {
      title_en: "Slipped on hydraulic leak near deck crane 2",
      description_en: "While walking past deck crane 2 I slipped on hydraulic oil leaking from the slewing unit. I did not fall fully. The area is not marked.",
      description_original: "डेक क्रेन 2 के पास से गुजरते समय मैं स्लूइंग यूनिट से रिस रहे हाइड्रोलिक तेल पर फिसल गया। मैं पूरी तरह नहीं गिरा। जगह पर कोई निशान नहीं है।",
      original_language: "hi", location_on_board: "Main deck, crane 2", hazard_type: "slip_trip_fall",
      ism_category: "unsafe_condition", severity: 3, immediate_action: "Put sawdust on the oil and told the bosun.",
      reporter_id: "u-crew", onboard_status: "ACTION_IN_PROGRESS", shore_status: "IN_REVIEW",
      share_name_with_master: true, reporter_name: "Amarjeet",
      photos: ["https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?w=800&q=60"],
      actions: [{ id: "a1", text: "Isolate crane 2 and replace slewing seal", responsible_rank: "Chief Engineer", due_at: iso(-DAY), resolved: false, created_at: iso(3 * 3600_000) }],
      created_at: iso(20 * 3600_000),
    }),
    base(1, { title_en: "Mooring line chafed at fairlead", description_en: "Aft mooring line shows heavy chafe at the port fairlead.", description_original: "Aft mooring line shows heavy chafe at the port fairlead.", location_on_board: "Poop deck, port", hazard_type: "mooring", ism_category: "equipment_failure", severity: 4, immediate_action: "Doubled up the line.", reporter_id: "u-crew", onboard_status: "SUBMITTED", shore_status: "QUEUED" }),
    base(2, { title_en: "Enclosed space entry without gas test", description_en: "Saw a fitter about to enter the ballast tank before the gas test was done.", description_original: "Saw a fitter about to enter the ballast tank before the gas test was done.", location_on_board: "No. 3 ballast tank", hazard_type: "enclosed_space", ism_category: "unsafe_act", severity: 5, immediate_action: "Stopped him and called the duty officer.", onboard_status: "ACKNOWLEDGED", shore_status: "NEW" }),
    base(3, { title_en: "Loose handrail on accommodation ladder", description_en: "Handrail moves when you lean on it.", description_original: "Ang hawakan ay gumagalaw kapag sumandal ka.", original_language: "tl", location_on_board: "Accommodation ladder, starboard", hazard_type: "slip_trip_fall", ism_category: "equipment_failure", severity: 2, immediate_action: "Tied a warning tag.", reporter_id: "u-crew", onboard_status: "RESOLVED_ON_BOARD", shore_status: "CLOSED",
      actions: [{ id: "a2", text: "Re-welded the bracket", responsible_rank: "Bosun", due_at: iso(2 * DAY), resolved: true, created_at: iso(2 * DAY) }] }),
    base(4, { title_en: "Oily rags near hot exhaust", description_en: "Rags left on the exhaust lagging in the engine room.", description_original: "Ганчір'я залишено на ізоляції вихлопу в машинному відділенні.", original_language: "uk", location_on_board: "Engine room, aux genset 2", hazard_type: "fire", ism_category: "unsafe_act", severity: 4, immediate_action: "Removed them to the oily waste bin.", onboard_status: "RESOLVED_ON_BOARD", shore_status: "REJECTED", reject_reason: "Duplicate of BCN-0007-031, merged there." }),
    base(5, { title_en: "Missing guard on lathe", description_en: "Chuck guard removed and not refitted.", description_original: "Chuck guard removed and not refitted.", location_on_board: "Engine workshop", hazard_type: "machinery", ism_category: "procedure_gap", severity: 3, immediate_action: "Put a do-not-use sign.", onboard_status: "ACKNOWLEDGED", shore_status: "IN_REVIEW" }),
    base(6, { title_en: "Frayed cable on galley mixer", description_en: "Power cable insulation is cracked near the plug.", description_original: "Power cable insulation is cracked near the plug.", location_on_board: "Galley", hazard_type: "electrical", ism_category: "equipment_failure", severity: 2, immediate_action: "Unplugged it.", onboard_status: "SUBMITTED", shore_status: "NEW" }),
  ];
}

export function seedMessages(): Message[] {
  return [
    { id: "m1", ticket_id: "t-7", sender: "master", body: "Thank you. Crane 2 is isolated until the seal is changed.", created_at: iso(5 * 3600_000) },
    { id: "m2", ticket_id: "t-7", sender: "shore", body: "Thanks for reporting. We are checking if other vessels have the same crane model issue.", created_at: iso(2 * 3600_000) },
    { id: "m3", ticket_id: "t-3", sender: "shore", body: "Good catch. Closed after the repair photo.", created_at: iso(DAY) },
    { id: "m4", ticket_id: "t-4", sender: "shore", body: "Merged with an earlier report. Thank you for the extra detail.", created_at: iso(DAY * 1.5) },
  ];
}

const anchors: Omit<AnchorCard, "id" | "date" | "helpful" | "saved">[] = [
  { type: "motivation", title: "Small steps still move the ship", body: "You don't need a perfect day. One honest effort on watch is enough. Rest when you can." },
  { type: "safety", title: "Three points of contact", body: "On ladders, keep two hands and a foot, or two feet and a hand, on the ladder. Carry tools in a bag, not in your hand." },
  { type: "news", title: "IMO adopts new guidance on seafarer fatigue", body: "Updated guidelines ask companies to plan watch schedules around real rest, not just paper hours.", source_name: "IMO News", source_url: "https://www.imo.org" },
  { type: "motivation", title: "Call home, even briefly", body: "Two minutes of voice can carry a long way. If the link is up tonight, use it." },
  { type: "safety", title: "Mooring snap-back zones", body: "Snap-back zones can move as lines shift. Stand clear of the bight, always." },
  { type: "news", title: "Port of Singapore expands crew welfare centre", body: "A new seafarer centre opens near Pasir Panjang with free Wi-Fi and counselling.", source_name: "Splash247", source_url: "https://splash247.com" },
  { type: "motivation", title: "Your crew is your harbour", body: "Ask a shipmate how they're really doing today. Then listen." },
  { type: "safety", title: "Test before you touch", body: "Lock out, tag out, try out. A dead circuit is only dead when you've proved it." },
  { type: "news", title: "Fleet milestone: 200 days without LTI", body: "The fleet reached 200 days without a lost-time injury. Every report counts.", source_name: "Fleet bulletin" },
  { type: "motivation", title: "Sleep is safety equipment", body: "Six hours or more makes your reactions faster than any coffee." },
  { type: "safety", title: "Hot work permits", body: "Fire watch stays 30 minutes after hot work ends. Sparks travel further than you think." },
  { type: "news", title: "New MLC amendments take effect", body: "Shore leave access and repatriation rules get clearer under the new amendments.", source_name: "ILO", source_url: "https://www.ilo.org" },
  { type: "motivation", title: "Learn one new thing", body: "Ask the engineer about one system you don't know. Curiosity keeps watches lively." },
  { type: "safety", title: "Enclosed space: never alone", body: "No entry without a permit, a gas test and an attendant at the entrance." },
];

export function seedAnchors(): AnchorCard[] {
  return anchors.map((a, i) => ({
    ...a,
    id: `an-${i}`,
    date: dateKey(new Date(Date.now() - i * DAY)),
    helpful: false,
    saved: i === 4,
  }));
}

export function seedLearnings(): Learning[] {
  return [
    {
      id: "l1", title: "Hydraulic leaks on deck cranes", priority: "urgent", acked: false, created_at: iso(6 * 3600_000),
      context: "Two vessels in the fleet had slips near deck cranes this month.",
      situation: "A slewing unit seal failed and oil spread across the walkway. It wasn't marked and a crew member slipped.",
      do_points: ["Mark and barricade any leak at once", "Use absorbent, not water", "Report the leak in Beacon"],
      dont_points: ["Walk through oil to save time", "Run the crane until it's inspected"],
      media: { kind: "image", url: "https://images.unsplash.com/photo-1605745341112-85968b19335b?w=1000&q=60" },
      check_question: { q: "What do you do first when you see a hydraulic leak on deck?", options: ["Hose it overboard", "Mark and barricade the area", "Keep working and report later"], answer_index: 1 },
    },
    {
      id: "l2", title: "Mooring line snap-back", priority: "normal", acked: false, created_at: iso(3 * DAY),
      context: "Snap-back is still the top cause of serious mooring injuries.",
      situation: "During berthing a line parted and whipped across the deck.",
      do_points: ["Stay out of the bight", "Watch line tension", "Communicate clearly with the winch operator"],
      dont_points: ["Stand in painted zones only — zones change", "Step over lines under tension"],
      media: { kind: "image", url: "https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=1000&q=60" },
      check_question: { q: "Painted snap-back zones show every danger area.", options: ["True", "False"], answer_index: 1 },
    },
    {
      id: "l3", title: "Fatigue on night watch", priority: "normal", acked: true, created_at: iso(7 * DAY),
      context: "Most near-misses on our fleet happen between 02:00 and 05:00.",
      situation: "A watchkeeper missed a radar target after a short sleep.",
      do_points: ["Speak up if you've slept under 6 hours", "Walk and talk to stay alert"],
      dont_points: ["Rely on caffeine alone", "Sit in a dark, warm wheelhouse corner"],
      media: { kind: "image", url: "https://images.unsplash.com/photo-1500375592092-40eb2168fd21?w=1000&q=60" },
      check_question: { q: "When are near-misses most common on our fleet?", options: ["08:00–11:00", "14:00–17:00", "02:00–05:00"], answer_index: 2 },
    },
  ];
}

const TAGS: CheckinTag[] = ["rest", "workload", "home", "family", "health", "team"];
/** 90 days of realistic history (today left empty). */
export function seedCheckins(): CheckinEntry[] {
  const out: CheckinEntry[] = [];
  for (let i = 90; i >= 1; i--) {
    if (Math.random() < 0.12) continue;
    const sleep = Math.round((5 + Math.random() * 3.5) * 2) / 2;
    const wave = Math.sin(i / 9);
    const moodRaw = 3 + wave * 0.8 + (sleep - 6.5) * 0.6 + (Math.random() - 0.5);
    const mood = Math.max(1, Math.min(5, Math.round(moodRaw))) as CheckinEntry["mood"];
    const fatigue = Math.max(1, Math.min(5, Math.round(6 - mood + (Math.random() - 0.5)))) as CheckinEntry["fatigue"];
    const tags = TAGS.filter(() => Math.random() < 0.22);
    out.push({ date: dateKey(new Date(Date.now() - i * DAY)), mood, fatigue, workload: Math.ceil(Math.random() * 5) as CheckinEntry["workload"], sleep_hours: sleep, tags });
  }
  return out;
}

export function seedInbox(): InboxItem[] {
  return [
    { id: "i1", kind: "shore_reply", title: "Shore replied on BCN-0007-042", body: "We are checking if other vessels have the same crane model issue.", link: { to: "/reports/$id", id: "t-7" }, read: false, created_at: iso(2 * 3600_000) },
    { id: "i2", kind: "learning", title: "New urgent learning", body: "Hydraulic leaks on deck cranes", link: { to: "/learn/$id", id: "l1" }, read: false, created_at: iso(6 * 3600_000) },
    { id: "i3", kind: "status_change", title: "BCN-0007-038 resolved on board", body: "Handrail bracket re-welded.", link: { to: "/reports/$id", id: "t-3" }, read: true, created_at: iso(2 * DAY) },
  ];
}

export function seedWelfare(): WelfareRequest[] {
  return [{ id: "w1", name: "Mark Dela Cruz", created_at: iso(30 * 3600_000), status: "contacted" }];
}

export function seedDevices(): PairedDevice[] {
  return CREW.map((c, i) => ({ id: `d-${i}`, crew_name: c.name, rank: c.rank, paired_at: iso((20 - i) * DAY) }));
}
