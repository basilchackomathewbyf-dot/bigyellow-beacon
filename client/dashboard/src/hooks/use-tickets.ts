import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import * as api from "@/api/endpoints/tickets";
import * as analysisApi from "@/api/endpoints/analysis";
import * as msgApi from "@/api/endpoints/messages";
import { POLL_INTERVAL_MS } from "@/api/config";
import type { IsmCategory, RejectReason, Severity, Ticket, TicketFilters } from "@/api/types";
import { qk } from "./query-keys";

export function useTickets(f: TicketFilters = {}, enabled = true) {
  return useQuery({ queryKey: qk.tickets.list(f), queryFn: () => api.listTickets(f), enabled });
}
export function useTicket(id: string) {
  return useQuery({ queryKey: qk.tickets.detail(id), queryFn: () => api.getTicket(id), enabled: !!id });
}
export function useSimilarTickets(id: string) {
  return useQuery({ queryKey: qk.tickets.similar(id), queryFn: () => api.getSimilarTickets(id) });
}

/** Polls `updated_since` every 10s and toasts when new tickets arrive from ships. */
export function useNewTicketWatcher(enabled: boolean) {
  const qc = useQueryClient();
  const { t } = useTranslation();
  const since = useRef<string>(new Date().toISOString());
  const seen = useRef(new Set<string>());
  const q = useQuery({
    queryKey: ["tickets", "poll"],
    queryFn: () => api.listTickets({ updated_since: since.current }),
    refetchInterval: POLL_INTERVAL_MS,
    enabled,
  });
  useEffect(() => {
    const rows = q.data;
    if (!rows?.length) return;
    since.current = rows.reduce((m, r) => (r.updated_at > m ? r.updated_at : m), since.current);
    const fresh = rows.filter((r) => r.shore_status === "NEW" && !seen.current.has(r.id) && Date.now() - new Date(r.received_at).getTime() < 120_000);
    rows.forEach((r) => seen.current.add(r.id));
    qc.invalidateQueries({ queryKey: qk.tickets.all, predicate: (x) => x.queryKey[1] !== "poll" });
    if (fresh.length) {
      const byVessel = new Map<string, number>();
      fresh.forEach((r) => byVessel.set(r.vessel.name, (byVessel.get(r.vessel.name) ?? 0) + 1));
      byVessel.forEach((count, vessel) => toast.info(t("tickets.newToast", { count, vessel })));
    }
  }, [q.data, qc, t]);
}

function useTicketMutation<V>(fn: (v: V) => Promise<Ticket>, successKey: string) {
  const qc = useQueryClient();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: fn,
    onSuccess: (ticket) => {
      qc.setQueryData(qk.tickets.detail(ticket.id), ticket);
      qc.invalidateQueries({ queryKey: qk.tickets.all });
      qc.invalidateQueries({ queryKey: qk.fleet.overview });
      toast.success(t(successKey, { no: ticket.ticket_no }));
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export const useAcceptTicket = () => useTicketMutation((id: string) => api.acceptTicket(id), "tickets.toast.accepted");
export const useRejectTicket = () =>
  useTicketMutation((v: { id: string; reason: RejectReason; note: string }) => api.rejectTicket(v.id, v.reason, v.note), "tickets.toast.rejected");
export const useCloseTicket = () =>
  useTicketMutation((v: { id: string; note: string }) => api.closeTicket(v.id, v.note), "tickets.toast.closed");
export const useApplySuggestion = () =>
  useTicketMutation((v: { id: string; severity?: Severity; ism_category?: IsmCategory }) => api.updateTicketFields(v.id, v), "analysis.applied");

export function useAnalysis(ticketId: string) {
  return useQuery({ queryKey: qk.analysis(ticketId), queryFn: () => analysisApi.getAnalysis(ticketId) });
}
export function useRerunAnalysis(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => analysisApi.rerunAnalysis(ticketId),
    onMutate: () => qc.setQueryData(qk.analysis(ticketId), undefined),
    onSettled: () => qc.invalidateQueries({ queryKey: qk.analysis(ticketId) }),
  });
}

export function useMessages(ticketId: string) {
  return useQuery({ queryKey: qk.messages(ticketId), queryFn: () => msgApi.listMessages(ticketId), refetchInterval: POLL_INTERVAL_MS });
}
export function useSendMessage(ticketId: string, senderName: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => msgApi.sendMessage(ticketId, body),
    onMutate: async (body) => {
      await qc.cancelQueries({ queryKey: qk.messages(ticketId) });
      const prev = qc.getQueryData(qk.messages(ticketId));
      qc.setQueryData(qk.messages(ticketId), (old: Awaited<ReturnType<typeof msgApi.listMessages>> = []) => [
        ...old,
        { id: `tmp-${Date.now()}`, ticket_id: ticketId, sender: "shore" as const, shore_user_name: senderName, body, created_at: new Date().toISOString() },
      ]);
      return { prev };
    },
    onError: (e: Error, _v, ctx) => {
      qc.setQueryData(qk.messages(ticketId), ctx?.prev);
      toast.error(e.message);
    },
    onSuccess: (message) => {
      qc.setQueryData(qk.messages(ticketId), (old: Awaited<ReturnType<typeof msgApi.listMessages>> = []) => [
        ...old.filter((m) => !m.id.startsWith("tmp-")), message,
      ]);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: qk.messages(ticketId) }),
  });
}
