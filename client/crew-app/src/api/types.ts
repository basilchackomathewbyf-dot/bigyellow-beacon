export type Role = "crew" | "master";
export type Language = "en" | "hi";

export interface User {
  id: string;
  name: string;
  rank: string;
  rank_band: "officer" | "rating" | "Officer" | "Rating";
  role: Role;
  language: Language;
  vessel: string;
  checkin_reminder_at?: string;
}

export type HazardType =
  | "slip_trip_fall" | "mooring" | "crane_lifting" | "enclosed_space" | "fire"
  | "machinery" | "electrical" | "chemical" | "other";
export type IsmCategory = "unsafe_act" | "unsafe_condition" | "equipment_failure" | "procedure_gap";
export type OnboardStatus = "SUBMITTED" | "ACKNOWLEDGED" | "ACTION_IN_PROGRESS" | "RESOLVED_ON_BOARD";
export type ShoreStatus = "QUEUED" | "NEW" | "IN_REVIEW" | "REJECTED" | "CLOSED";

export interface TicketAction {
  id: string;
  text: string;
  responsible_rank: string;
  due_at: string;
  photo_url?: string;
  resolved: boolean;
  created_at: string;
}

export interface Ticket {
  id: string;
  ticket_no: string;
  title_en: string;
  description_en: string;
  description_original: string;
  original_language: string;
  location_on_board: string;
  hazard_type: HazardType;
  ism_category: IsmCategory;
  severity: 1 | 2 | 3 | 4 | 5;
  immediate_action: string;
  photos: string[];
  audio_url?: string;
  share_name_with_master: boolean;
  reporter_name?: string;
  reporter_id?: string;
  onboard_status: OnboardStatus;
  shore_status: ShoreStatus;
  reject_reason?: string;
  actions: TicketAction[];
  created_at: string;
}

export interface Message {
  id: string;
  ticket_id: string;
  sender: "reporter" | "master" | "shore";
  body: string;
  created_at: string;
}

export interface ReportFields {
  title_en: string;
  description_en: string;
  location_on_board: string;
  hazard_type: HazardType;
  ism_category: IsmCategory;
  severity: 1 | 2 | 3 | 4 | 5;
  immediate_action: string;
}

export interface StructureResult {
  original_language: string;
  transcript_original: string;
  fields: ReportFields;
  clarifying_question?: string;
  confidence: number;
}

export interface DraftInput {
  audio?: Blob;
  photos?: Blob[];
  text?: string;
  duration?: number;
}

export interface AnchorCard {
  id: string;
  date: string;
  type: "motivation" | "safety" | "news";
  title: string;
  body: string;
  source_name?: string;
  source_url?: string;
  image_url?: string;
  helpful: boolean;
  saved: boolean;
  viewed?: boolean;
}

export interface Learning {
  id: string;
  title: string;
  context: string;
  situation: string;
  do_points: string[];
  dont_points: string[];
  media: { kind: "image" | "gif" | "video"; url: string };
  check_question: { q: string; options: string[]; answer_index: number };
  priority: "normal" | "urgent";
  acked: boolean;
  created_at: string;
}

export interface LearningStat {
  learning_id: string;
  title: string;
  acked: number;
  total: number;
}

export type CheckinTag = "rest" | "workload" | "home" | "family" | "health" | "team";

export interface CheckinEntry {
  date: string;
  mood: 1 | 2 | 3 | 4 | 5;
  fatigue: 1 | 2 | 3 | 4 | 5;
  workload: 1 | 2 | 3 | 4 | 5;
  sleep_hours: number;
  tags: CheckinTag[];
}

export interface CheckinStartInput {
  mode: "quick" | "chat";
  mood: 1 | 2 | 3 | 4 | 5;
  sleep_hours?: number;
  fatigue?: 1 | 2 | 3 | 4 | 5;
  tags?: CheckinTag[];
}

export interface CheckinStartResult { id: string; done: boolean; prompt?: string }
export interface CheckinTurnResult {
  reply: string;
  done: boolean;
  scores?: { mood: number; fatigue: number };
  rail_hit?: boolean;
  safety_rail_triggered?: boolean;
  offer_welfare_check?: boolean;
  clinician_approved_message?: string;
  prompt?: string;
}

export interface CheckinHistory {
  entries: CheckinEntry[];
  streak: number;
  top_tags: { tag: CheckinTag; count: number }[];
  insight: string;
}

export interface InboxItem {
  id: string;
  kind: "shore_reply" | "status_change" | "learning" | "master_reply";
  title: string;
  body: string;
  link?: { to: string; id?: string };
  read: boolean;
  created_at: string;
}

export interface SyncStatus {
  link: "UP" | "DOWN";
  last_push_at: string;
  last_pull_at: string;
  outbox_pending: number;
}

export interface MorningBrief {
  generated_at: string;
  headline: string;
  rest_hours_risk: { level: "low" | "medium" | "high"; note: string };
  mood_trend: { n: number; points: { date: string; mood: number }[] } | null;
  open_hazards: { ticket_no: string; title: string; severity: number }[];
  recommended_action: string;
  fleet_context: string;
}

export interface WelfareRequest {
  id: string;
  name: string;
  created_at: string;
  status: "pending" | "acknowledged" | "contacted";
}

export interface PairedDevice { id: string; crew_name: string; rank: string; paired_at: string }
export interface PairingCode { code: string; qr_payload: string }

export interface PairDevicePayload {
  pairing_code: string;
  crew_id?: string;
  department?: string;
  crew_name?: string;
  pin?: string;
}

export interface PairDeviceResponse {
  device_token: string;
  device_id?: string;
  vessel_id: string;
  crew_id?: string;
  crew_name?: string;
  department?: string;
  expires_at: string;
  token?: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
