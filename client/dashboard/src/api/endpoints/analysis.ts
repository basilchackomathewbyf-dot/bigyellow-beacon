import { USE_MOCK } from "../config";
import { request } from "../client";
import { mock } from "../mock/db";
import type { Analysis } from "../types";

// GET /tickets/{id}/analysis
export function getAnalysis(ticketId: string): Promise<Analysis> {
  return USE_MOCK ? mock.getAnalysis(ticketId) : request("GET", `/tickets/${ticketId}/analysis`);
}

// POST /tickets/{id}/analysis
export function rerunAnalysis(ticketId: string): Promise<Analysis> {
  return USE_MOCK ? mock.rerunAnalysis(ticketId) : request("POST", `/tickets/${ticketId}/analysis`);
}
