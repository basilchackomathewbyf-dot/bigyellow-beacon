import { USE_MOCK } from "../config";
import { request } from "../client";
import { mock } from "../mock/db";
import type { Learning, LearningDraft, LearningInput, MediaItem } from "../types";

// GET /learnings
export async function listLearnings(): Promise<Learning[]> {
  if (USE_MOCK) return mock.listLearnings();
  const res = await request<Learning[] | { items: Learning[]; learnings: Learning[] }>("GET", "/learnings");
  return Array.isArray(res) ? res : (res as any)?.items ?? (res as any)?.learnings ?? [];
}

// GET /learnings/{id}
export function getLearning(id: string): Promise<Learning> {
  return USE_MOCK ? mock.getLearning(id) : request("GET", `/learnings/${id}`);
}

// POST /learnings/draft
export function draftLearning(ticket_id?: string): Promise<LearningDraft> {
  return USE_MOCK ? mock.draftLearning(ticket_id) : request("POST", "/learnings/draft", { body: { ticket_id } });
}

// POST /learnings
export function createLearning(input: LearningInput): Promise<Learning> {
  return USE_MOCK ? mock.createLearning(input) : request("POST", "/learnings", { body: input });
}

// PATCH /learnings/{id}
export function updateLearning(id: string, patch: Partial<Learning>): Promise<Learning> {
  return USE_MOCK ? mock.patchLearning(id, patch) : request("PATCH", `/learnings/${id}`, { body: patch });
}

// POST /learnings/{id}/media (multipart)
export async function uploadLearningMedia(id: string, file: File, meta: Omit<MediaItem, "id" | "url">): Promise<MediaItem> {
  if (USE_MOCK) {
    const url = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Could not read media"));
      reader.onerror = () => reject(new Error("Could not read media"));
      reader.readAsDataURL(file);
    });
    return { ...meta, id: crypto.randomUUID(), url };
  }
  const form = new FormData();
  form.append("file", file);
  form.append("meta", JSON.stringify(meta));
  return request("POST", `/learnings/${id}/media`, { form });
}

// POST /learnings/{id}/publish
export function publishLearning(id: string): Promise<Learning> {
  return USE_MOCK ? mock.publishLearning(id) : request("POST", `/learnings/${id}/publish`);
}

// POST /learnings/{id}/retract
export function retractLearning(id: string): Promise<Learning> {
  return USE_MOCK ? mock.retractLearning(id) : request("POST", `/learnings/${id}/retract`);
}
