import { USE_MOCK } from "../config";
import { request } from "../client";
import { mock } from "../mock/db";
import type { Vessel } from "../types";

// GET /vessels
export async function listVessels(): Promise<Vessel[]> {
  if (USE_MOCK) return mock.listVessels();
  const res = await request<Vessel[] | { items: Vessel[]; vessels: Vessel[] }>("GET", "/vessels");
  return Array.isArray(res) ? res : (res as any)?.items ?? (res as any)?.vessels ?? [];
}
