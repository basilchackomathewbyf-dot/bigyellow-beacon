// Pure business rules shared by mock handlers and the UI. Unit tested.
import type { MediaItem, RejectReason, ShoreStatus } from "@/api/types";

export const TRANSITIONS: Record<"accept" | "reject" | "close", ShoreStatus[]> = {
  accept: ["NEW"],
  reject: ["NEW"],
  close: ["IN_REVIEW"],
};
export function canTransition(action: keyof typeof TRANSITIONS, from: ShoreStatus) {
  return TRANSITIONS[action].includes(from);
}
export const REJECT_REASONS: RejectReason[] = ["duplicate", "not_near_miss", "insufficient_info", "out_of_scope"];
export function validateReject(reason: string | undefined, note: string) {
  return !!reason && REJECT_REASONS.includes(reason as RejectReason) && note.trim().length > 0;
}

// ---- Media ----
export const MB = 1024 * 1024;
export const IMAGE_MAX_BYTES = 5 * MB;
export const VIDEO_MAX_BYTES = 20 * MB;
export const VIDEO_MAX_SECONDS = 6;
export const MAX_EXTRA_IMAGES = 2;
export const SHIP_BUDGET_BYTES = 2 * MB;

export type MediaCheck =
  | { ok: true; kind: MediaItem["kind"]; note?: "resize" | "gif_to_video" }
  | { ok: false; error: string };

export function classifyFile(file: { type: string; size: number }, durationS?: number): MediaCheck {
  const t = file.type;
  if (t === "image/gif") return { ok: true, kind: "gif", note: "gif_to_video" };
  if (["image/jpeg", "image/png", "image/webp"].includes(t)) {
    if (file.size > IMAGE_MAX_BYTES) return { ok: false, error: "Image is larger than 5 MB." };
    return { ok: true, kind: "image", note: "resize" };
  }
  if (t.startsWith("video/")) {
    if (file.size > VIDEO_MAX_BYTES) return { ok: false, error: "Video is larger than 20 MB." };
    if (durationS !== undefined && durationS > VIDEO_MAX_SECONDS)
      return { ok: false, error: `Video is ${durationS.toFixed(1)} s. Maximum is 6 seconds.` };
    return { ok: true, kind: "video" };
  }
  return { ok: false, error: "Use JPG, PNG, WebP, GIF or a short video." };
}

/** One primary item (any kind) plus up to 2 extra images. */
export function canAddMedia(existing: Pick<MediaItem, "kind">[], kind: MediaItem["kind"]) {
  if (existing.length === 0) return true;
  if (kind !== "image") return false;
  return existing.length - 1 < MAX_EXTRA_IMAGES;
}

/** Rough post-compression estimate of what ships will download. */
export function estimateDeliveryBytes(items: Pick<MediaItem, "kind" | "bytes" | "duration_s">[]) {
  return items.reduce((sum, m) => {
    if (m.kind === "image") return sum + Math.min(m.bytes, 350_000);
    if (m.kind === "gif") return sum + Math.round(m.bytes * 0.25);
    return sum + Math.round((m.duration_s ?? 6) * 120_000);
  }, 0);
}

// ---- Wellbeing privacy threshold (k-anonymity) ----
export const WELLBEING_MIN_N = 5;
export function canShowWellbeing(n: number) {
  return n >= WELLBEING_MIN_N;
}

export function audienceCount(mode: "same_vessel" | "selected" | "all", selected: string[], total: number) {
  if (mode === "all") return total;
  if (mode === "same_vessel") return 1;
  return selected.length;
}

// ---- Review flow steps (ticket detail tracker) ----
export const FLOW_STEPS = ["received", "review", "decide", "reply", "close"] as const;
export type FlowStep = (typeof FLOW_STEPS)[number];
/** Index of the step the reviewer should do next. Equals FLOW_STEPS.length when done. */
export function currentFlowStep(status: ShoreStatus, hasShoreReply: boolean): number {
  if (status === "CLOSED" || status === "REJECTED") return FLOW_STEPS.length;
  if (status === "NEW") return 1;
  return hasShoreReply ? 4 : 3;
}
