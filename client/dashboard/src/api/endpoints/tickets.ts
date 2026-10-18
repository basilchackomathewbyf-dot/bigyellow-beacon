import { USE_MOCK } from "../config";
import { request } from "../client";
import { mock } from "../mock/db";
import type { IsmCategory, RejectReason, Severity, Ticket, TicketFilters } from "../types";

// GET /tickets?status=&vessel_id=&severity=&hazard_type=&from=&to=&q=&updated_since=
export async function listTickets(f: TicketFilters = {}): Promise<Ticket[]> {
  if (USE_MOCK) return mock.listTickets(f);
  const res = await request<Ticket[] | { items: Ticket[]; total?: number }>("GET", "/tickets", {
    query: { ...f } as any,
  });
  return Array.isArray(res) ? res : res.items ?? [];
}

// GET /tickets/{id}
export function getTicket(id: string): Promise<Ticket> {
  return USE_MOCK ? mock.getTicket(id) : request("GET", `/tickets/${id}`);
}

// POST /tickets/{id}/accept
export function acceptTicket(id: string): Promise<Ticket> {
  return USE_MOCK ? mock.accept(id) : request("POST", `/tickets/${id}/accept`);
}

// POST /tickets/{id}/reject
export function rejectTicket(id: string, reason: RejectReason, note: string): Promise<Ticket> {
  return USE_MOCK ? mock.reject(id, reason, note) : request("POST", `/tickets/${id}/reject`, { body: { reason, note } });
}

// POST /tickets/{id}/close
export function closeTicket(id: string, resolution_note: string): Promise<Ticket> {
  return USE_MOCK ? mock.close(id, resolution_note) : request("POST", `/tickets/${id}/close`, { body: { resolution_note } });
}

// PATCH /tickets/{id}  (apply an AI suggestion after an explicit click)
export function updateTicketFields(id: string, patch: { severity?: Severity; ism_category?: IsmCategory }): Promise<Ticket> {
  return USE_MOCK ? mock.updateFields(id, patch) : request("PATCH", `/tickets/${id}`, { body: patch });
}

// GET /tickets/{id}/similar
export async function getSimilarTickets(id: string): Promise<Ticket[]> {
  if (USE_MOCK) return mock.similar(id);
  const res = await request<Ticket[] | { items: Ticket[] }>("GET", `/tickets/${id}/similar`);
  return Array.isArray(res) ? res : res.items ?? [];
}
