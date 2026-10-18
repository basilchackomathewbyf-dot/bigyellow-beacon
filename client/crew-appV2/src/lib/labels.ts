import type { HazardType, IsmCategory, OnboardStatus, ShoreStatus, CheckinTag } from "@/api/types";

export const HAZARDS: Record<HazardType, string> = {
  slip_trip_fall: "Slip, trip or fall", mooring: "Mooring", crane_lifting: "Crane / lifting", enclosed_space: "Enclosed space",
  fire: "Fire", machinery: "Machinery", electrical: "Electrical", chemical: "Chemical", other: "Other",
};
export const ISM: Record<IsmCategory, string> = {
  unsafe_act: "Unsafe act", unsafe_condition: "Unsafe condition", equipment_failure: "Equipment failure", procedure_gap: "Procedure gap",
};
export const ONBOARD: Record<OnboardStatus, string> = {
  SUBMITTED: "New", ACKNOWLEDGED: "Acknowledged", ACTION_IN_PROGRESS: "Action in progress", RESOLVED_ON_BOARD: "Resolved on board",
};
export const SHORE: Record<ShoreStatus, string> = {
  QUEUED: "Waiting to send", NEW: "Received", IN_REVIEW: "In review", REJECTED: "Not taken forward", CLOSED: "Closed",
};
export const SEVERITY = ["", "Minor", "Low", "Moderate", "Serious", "Critical"];
export const TAGS: CheckinTag[] = ["rest", "workload", "home", "family", "health", "team"];
export const RANKS = ["Master", "Chief Officer", "2nd Officer", "3rd Officer", "Chief Engineer", "2nd Engineer", "3rd Engineer", "Bosun", "AB Seaman", "Oiler", "Cook"];
export const MOODS = ["", "😞", "🙁", "😐", "🙂", "😄"];
export const MOOD_LABEL = ["", "Very low", "Low", "Okay", "Good", "Great"];

export const timeAgo = (iso: string) => {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
};
