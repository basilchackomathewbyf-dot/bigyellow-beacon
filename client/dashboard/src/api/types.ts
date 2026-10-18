// Domain types shared by the API layer, hooks and UI.
// NOTE: there is intentionally no reporter identity anywhere in these types.

export type Role = "reviewer" | "admin";
export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
}
export interface LoginResponse {
  token: string;
  user: User;
}

export type VesselType = "Bulk carrier" | "Tanker" | "Container";
export interface Vessel {
  id: string;
  name: string;
  type: VesselType;
  imo: string;
  flag: string;
  last_sync_at: string;
  crew_count: number;
}
export type VesselRef = Pick<Vessel, "id" | "name" | "type">;

export type RankBand = "Officer" | "Rating" | "Cadet" | "Crew";
export type HazardType =
  | "slip_trip_fall"
  | "mooring"
  | "crane_lifting"
  | "enclosed_space"
  | "fire"
  | "machinery"
  | "electrical"
  | "chemical"
  | "other";
export type IsmCategory = "unsafe_act" | "unsafe_condition" | "equipment_failure" | "procedure_gap";
export type Severity = 1 | 2 | 3 | 4 | 5;
export type OnboardStatus = "SUBMITTED" | "ACKNOWLEDGED" | "ACTION_IN_PROGRESS" | "RESOLVED_ON_BOARD";
export type ShoreStatus = "NEW" | "IN_REVIEW" | "REJECTED" | "CLOSED";
export type RejectReason = "duplicate" | "not_near_miss" | "insufficient_info" | "out_of_scope";

export interface OnboardAction {
  text: string;
  responsible_rank: string;
  due_at: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  ticket_no: string;
  vessel: VesselRef;
  rank_band: RankBand;
  title_en: string;
  description_en: string;
  description_original: string;
  original_language: string;
  location_on_board: string;
  hazard_type: HazardType;
  ism_category: IsmCategory;
  severity: Severity;
  immediate_action: string;
  photos: string[];
  onboard_status: OnboardStatus;
  shore_status: ShoreStatus;
  onboard_actions: OnboardAction[];
  assigned_to?: string;
  reject_reason?: RejectReason;
  reject_note?: string;
  resolution_note?: string;
  similar_count: number;
  occurred_at: string;
  received_at: string;
  updated_at: string;
}

export interface TicketFilters {
  status?: ShoreStatus;
  vessel_id?: string[];
  severity?: Severity[];
  hazard_type?: HazardType[];
  ism_category?: IsmCategory[];
  from?: string;
  to?: string;
  q?: string;
  updated_since?: string;
}

export interface Analysis {
  ticket_id: string;
  model: string;
  created_at: string;
  summary: string[];
  contributing_factors: string[];
  ism_check: { current: IsmCategory; suggested: IsmCategory; reason: string };
  severity_check: { current: Severity; suggested: Severity; reason: string };
  similar_tickets: { ticket_id: string; ticket_no: string; vessel: string; title: string; score: number }[];
  corpus_matches: { source: string; title: string; url: string; why_relevant: string }[];
  recommendations: { type: "corrective" | "preventive"; text: string }[];
  suggest_learning: boolean;
}

export type MessageSender = "reporter" | "master" | "shore";
export interface Message {
  id: string;
  ticket_id: string;
  sender: MessageSender;
  shore_user_name?: string;
  body: string;
  created_at: string;
  delivered_at?: string;
}

export type MediaKind = "image" | "gif" | "video";
export interface MediaItem {
  id: string;
  kind: MediaKind;
  url: string;
  duration_s?: number;
  bytes: number;
  primary?: boolean;
}
export type AudienceMode = "same_vessel" | "selected" | "all";
export interface Audience {
  mode: AudienceMode;
  vessel_ids: string[];
}
export type LearningStatus = "draft" | "published" | "retracted";
export interface LearningStats {
  vessels_delivered: number;
  vessels_total: number;
  opened: number;
  acknowledged: number;
  check_correct: number;
}
export interface Learning {
  id: string;
  source_ticket_id?: string;
  title: string;
  context: string;
  situation: string;
  do_points: string[];
  dont_points: string[];
  check_question: { q: string; options: string[]; answer_index: number };
  tags: { tool?: string; area?: string; situation?: string };
  media: MediaItem[];
  audience: Audience;
  rank_filter: "all" | "officers" | "ratings";
  priority: "normal" | "urgent";
  status: LearningStatus;
  ai_drafted_fields: string[];
  stats: LearningStats;
  published_at?: string;
  updated_at: string;
}
export type LearningInput = Omit<Learning, "id" | "status" | "stats" | "published_at" | "updated_at">;
export type LearningDraft = Pick<
  Learning,
  "title" | "context" | "situation" | "do_points" | "dont_points" | "check_question" | "tags"
> & { ai_drafted_fields: string[] };

export interface FleetOverview {
  open_by_severity: Record<Severity, number>;
  new_last_24h: number;
  median_accept_hours: number;
  learning_ack_rate: number;
  per_vessel: { vessel: string; s1: number; s2: number; s3: number; s4: number; s5: number }[];
  top_hazards: { hazard_type: HazardType; count: number }[];
  trend: { date: string; reports: number; checkins: number }[];
  wellbeing: {
    vessel_id: string;
    vessel: string;
    n: number;
    mood: number | null;
    fatigue: number | null;
    mood_trend: "up" | "down" | "flat";
    fatigue_trend: "up" | "down" | "flat";
  }[];
  last_ship_sync_at: string;
}
export interface HazardCluster {
  id: string;
  label: string;
  hazard_type: HazardType;
  vessel_count: number;
  ticket_count: number;
  ticket_ids: string[];
  q: string;
}
