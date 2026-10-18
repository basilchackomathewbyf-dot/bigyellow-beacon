import { ApiError } from "../types";
import { getDb } from "./db";

/** Simulate a tiny latency and the edge server being unreachable. */
export async function latency<T>(fn: () => T): Promise<T> {
  await new Promise((r) => setTimeout(r, 20 + Math.random() * 40));
  if (!getDb().edgeReachable) throw new ApiError(0, "Ship server unreachable");
  return structuredClone(fn());
}

export const id = (p: string) => `${p}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
export const nowIso = () => new Date().toISOString();
export const todayKey = () => new Date().toISOString().slice(0, 10);
