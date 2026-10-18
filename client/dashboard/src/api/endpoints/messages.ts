import { USE_MOCK } from "../config";
import { request } from "../client";
import { mock } from "../mock/db";
import type { Message } from "../types";

// GET /tickets/{id}/messages
export function listMessages(ticketId: string): Promise<Message[]> {
  return USE_MOCK ? mock.listMessages(ticketId) : request("GET", `/tickets/${ticketId}/messages`);
}

// POST /tickets/{id}/messages
export function sendMessage(ticketId: string, body: string): Promise<Message> {
  return USE_MOCK ? mock.sendMessage(ticketId, body) : request("POST", `/tickets/${ticketId}/messages`, { body: { body } });
}
