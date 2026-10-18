import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as learnApi from "@/api/endpoints/learnings";
import * as fleetApi from "@/api/endpoints/fleet";
import * as vesselApi from "@/api/endpoints/vessels";
import type { Learning, LearningInput, MediaItem } from "@/api/types";
import { qk } from "./query-keys";

const onError = (e: Error) => toast.error(e.message);

// ---- Learnings ----
export const useLearnings = () => useQuery({ queryKey: qk.learnings.all, queryFn: learnApi.listLearnings });
export const useLearning = (id: string) => useQuery({ queryKey: qk.learnings.detail(id), queryFn: () => learnApi.getLearning(id) });
export const useDraftLearning = () => useMutation({ mutationFn: (ticketId?: string) => learnApi.draftLearning(ticketId), onError });
export const useUploadLearningMedia = () => useMutation({
  mutationFn: (v: { file: File; meta: Omit<MediaItem, "id" | "url"> }) => learnApi.uploadLearningMedia("pending", v.file, v.meta),
});

export function useSaveLearning() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id?: string; input: LearningInput }) => (v.id ? learnApi.updateLearning(v.id, v.input) : learnApi.createLearning(v.input)),
    onSuccess: (l) => {
      qc.setQueryData(qk.learnings.detail(l.id), l);
      qc.invalidateQueries({ queryKey: qk.learnings.all });
    },
    onError,
  });
}
function useLearningAction(fn: (id: string) => Promise<Learning>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (l) => {
      qc.setQueryData(qk.learnings.detail(l.id), l);
      qc.invalidateQueries({ queryKey: qk.learnings.all });
    },
    onError,
  });
}
export const usePublishLearning = () => useLearningAction(learnApi.publishLearning);
export const useRetractLearning = () => useLearningAction(learnApi.retractLearning);

// ---- Fleet ----
export const useFleetOverview = () => useQuery({ queryKey: qk.fleet.overview, queryFn: fleetApi.getFleetOverview, refetchInterval: 30_000 });
export const useHazardClusters = () => useQuery({ queryKey: qk.fleet.clusters, queryFn: fleetApi.getHazardClusters });
export const useVessels = () => useQuery({ queryKey: qk.vessels, queryFn: vesselApi.listVessels, staleTime: 60_000 });
