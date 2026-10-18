export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "https://shore-api.example.run.app/api/v1";

export const USE_MOCK: boolean = (import.meta.env.VITE_USE_MOCK ?? "true") === "true";

export const POLL_INTERVAL_MS = 10_000;
export const TOKEN_KEY = "beacon.token";
export const USER_KEY = "beacon.user";
