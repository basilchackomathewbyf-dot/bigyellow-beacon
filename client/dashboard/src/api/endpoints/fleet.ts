import { USE_MOCK } from "../config";
import { request } from "../client";
import { mock } from "../mock/db";
import type { FleetOverview, HazardCluster } from "../types";

// GET /fleet/overview
export function getFleetOverview(): Promise<FleetOverview> {
  return USE_MOCK ? mock.fleetOverview() : request("GET", "/fleet/overview");
}

// GET /fleet/clusters
export async function getHazardClusters(): Promise<HazardCluster[]> {
  if (USE_MOCK) return mock.clusters();
  const res = await request<HazardCluster[] | { clusters: HazardCluster[] }>("GET", "/fleet/clusters");
  return Array.isArray(res) ? res : res.clusters ?? [];
}
