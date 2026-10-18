import { API_BASE_URL } from "./config";
import { ApiError } from "./types";

const KEY = "beacon.session";
let token: string | null = null;
try {
  if (typeof window !== "undefined") {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      token = (JSON.parse(raw) as { token?: string }).token ?? null;
    }
  }
} catch {}

export const setAuthToken = (t: string | null) => { token = t; };
export const getAuthToken = () => token;

const uuid = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export function buildUrl(path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const base = API_BASE_URL.replace(/\/+$/, "");
  const full = `${base}${cleanPath}`;
  if (full.startsWith("http://") || full.startsWith("https://")) {
    return full;
  }
  const origin =
    typeof window !== "undefined"
      ? window.location.origin
      : (typeof process !== "undefined" && process.env?.INTERNAL_ORIGIN) || "http://127.0.0.1";
  return new URL(full, origin).toString();
}

/** Thin fetch wrapper used when USE_MOCK is false. */
export async function api<T>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (method !== "GET") headers["Idempotency-Key"] = uuid();
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(buildUrl(path), { method, headers, body: payload });
  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const parsed = JSON.parse(text);
      message = parsed.error || (typeof parsed.detail === "string" ? parsed.detail : (parsed.detail ? JSON.stringify(parsed.detail) : text));
    } catch {}
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
