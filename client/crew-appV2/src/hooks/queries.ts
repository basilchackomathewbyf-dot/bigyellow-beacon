// TanStack Query hooks. Components use only these — never mock data directly.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as reports from "@/api/endpoints/reports";
import * as master from "@/api/endpoints/master";
import * as checkins from "@/api/endpoints/checkins";
import * as content from "@/api/endpoints/content";
import * as auth from "@/api/endpoints/auth";
import type { CheckinStartInput, DraftInput, OnboardStatus, ReportFields, Language } from "@/api/types";
import { sendOrQueue } from "@/lib/outbox";

export const qk = {
  mine: ["reports", "mine"] as const,
  ticket: (id: string) => ["ticket", id] as const,
  messages: (id: string) => ["messages", id] as const,
  master: (f?: object) => ["master", "tickets", f ?? {}] as const,
  brief: ["master", "brief"] as const,
  stats: ["master", "stats"] as const,
  welfare: ["master", "welfare"] as const,
  devices: ["master", "devices"] as const,
  checkinToday: ["checkin", "today"] as const,
  history: (r: string) => ["checkin", "history", r] as const,
  anchorToday: ["anchor", "today"] as const,
  anchorList: (saved?: boolean) => ["anchor", "list", !!saved] as const,
  learnings: ["learnings"] as const,
  inbox: ["inbox"] as const,
  sync: ["sync"] as const,
};

/* Reports */
export const useMyReports = () => useQuery({ queryKey: qk.mine, queryFn: reports.myReports });
export const useTicket = (id: string) => useQuery({ queryKey: qk.ticket(id), queryFn: () => reports.getTicket(id) });
export const useMessages = (id: string) => useQuery({ queryKey: qk.messages(id), queryFn: () => reports.ticketMessages(id) });
export const useCreateDraft = () => useMutation({ mutationFn: (i: DraftInput) => reports.createDraft(i) });
export const useStructure = () => useMutation({ mutationFn: (id: string) => reports.structureDraft(id) });
export const useAnswerDraft = () => useMutation({ mutationFn: (v: { id: string; answer: string }) => reports.answerDraft(v.id, v.answer) });
export function useSubmitReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { draft_id: string; fields: ReportFields; share: boolean }) => reports.submitReport(v.draft_id, v.fields, v.share),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["reports"] }); qc.invalidateQueries({ queryKey: ["master"] }); },
  });
}
export function usePostMessage(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => sendOrQueue("message", { ticketId, body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.messages(ticketId) }),
  });
}

/* Master */
export const useMasterTickets = (f: { onboard_status?: OnboardStatus; severity?: number } = {}) =>
  useQuery({ queryKey: qk.master(f), queryFn: () => master.masterTickets(f) });
function useInvalidateTickets() {
  const qc = useQueryClient();
  return () => { qc.invalidateQueries({ queryKey: ["master"] }); qc.invalidateQueries({ queryKey: ["reports"] }); qc.invalidateQueries({ queryKey: ["ticket"] }); };
}
export function useAckTicket() { const inv = useInvalidateTickets(); return useMutation({ mutationFn: master.ackTicket, onSuccess: inv }); }
export function useAddAction() {
  const inv = useInvalidateTickets();
  return useMutation({ mutationFn: (v: { id: string; text: string; responsible_rank: string; due_at: string; resolve?: boolean; photo?: Blob }) => master.addAction(v.id, v), onSuccess: inv });
}
export const useBrief = () => useQuery({ queryKey: qk.brief, queryFn: master.getBrief });
export function useRegenerateBrief() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: master.regenerateBrief, onSuccess: (b) => qc.setQueryData(qk.brief, b) });
}
export const useLearningStats = () => useQuery({ queryKey: qk.stats, queryFn: master.learningStats });
export const useWelfare = () => useQuery({ queryKey: qk.welfare, queryFn: master.welfareList });
export function useWelfareAck() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { id: string; status: "acknowledged" | "contacted" }) => master.welfareAck(v.id, v.status), onSuccess: () => qc.invalidateQueries({ queryKey: qk.welfare }) });
}
export const useDevices = () => useQuery({ queryKey: qk.devices, queryFn: master.pairedDevices });
export function useRevokeDevice() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: master.revokeDevice, onSuccess: () => qc.invalidateQueries({ queryKey: qk.devices }) });
}

export const useCrewList = () => useQuery({ queryKey: ["master", "crew"], queryFn: master.getCrewList });
export function useCreateCrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: master.createCrewMember,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["master", "crew"] }),
  });
}
export function useDeleteCrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: master.deleteCrewMember,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["master", "crew"] }),
  });
}

/* Check-ins */
export const useCheckinToday = () => useQuery({ queryKey: qk.checkinToday, queryFn: checkins.todayDone });
export const useHistory = (r: "7d" | "30d" | "90d") => useQuery({ queryKey: qk.history(r), queryFn: () => checkins.history(r) });
function useInvalidateCheckin() { const qc = useQueryClient(); return () => qc.invalidateQueries({ queryKey: ["checkin"] }); }
export function useQuickCheckin() {
  const inv = useInvalidateCheckin();
  return useMutation({ mutationFn: (i: CheckinStartInput) => sendOrQueue("checkin_quick", i), onSuccess: inv });
}
export const useStartChat = () => useMutation({ mutationFn: (i: CheckinStartInput) => checkins.startCheckin(i) });
export function useChatTurn() {
  const inv = useInvalidateCheckin();
  return useMutation({ mutationFn: (v: { id: string; text: string }) => checkins.checkinTurn(v.id, v.text), onSuccess: (r) => { if (r.done) inv(); } });
}
export const useWelfareRequest = () => useMutation({ mutationFn: (id: string) => checkins.welfareRequest(id) });
export function useDeleteHistory() { const inv = useInvalidateCheckin(); return useMutation({ mutationFn: checkins.deleteHistory, onSuccess: inv }); }

/* Anchor / learnings / inbox / sync */
export const useAnchorToday = () => useQuery({ queryKey: qk.anchorToday, queryFn: content.anchorToday });
export const useAnchorList = (saved?: boolean) => useQuery({ queryKey: qk.anchorList(saved), queryFn: () => content.anchorList({ days: 14, saved }) });
export function useAnchorReact() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { id: string; r: { helpful?: boolean; saved?: boolean; viewed?: boolean } }) => sendOrQueue("anchor_react", v), onSuccess: () => qc.invalidateQueries({ queryKey: ["anchor"] }) });
}
export const useLearnings = () => useQuery({ queryKey: qk.learnings, queryFn: content.learnings });
export function useLearningAck() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { id: string; body: { opened?: boolean; acked?: boolean; check_answer?: number } }) => sendOrQueue("learning_ack", v), onSuccess: () => qc.invalidateQueries({ queryKey: qk.learnings }) });
}
export const useInbox = () => useQuery({ queryKey: qk.inbox, queryFn: content.inbox });
export function useInboxRead() { const qc = useQueryClient(); return useMutation({ mutationFn: content.inboxRead, onSuccess: () => qc.invalidateQueries({ queryKey: qk.inbox }) }); }
export const useSyncStatus = () => useQuery({ queryKey: qk.sync, queryFn: content.syncStatus, refetchInterval: 15_000, retry: false });
export function useSyncNow() { const qc = useQueryClient(); return useMutation({ mutationFn: content.syncNow, onSuccess: () => qc.invalidateQueries() }); }
export const useUpdatePrefs = () => useMutation({ mutationFn: (p: { language?: Language }) => auth.updatePreferences(p) });
export const useTranscribe = () => useMutation({ mutationFn: (v: { id: string; audio: Blob }) => checkins.transcribeTurn(v.id, v.audio) });
