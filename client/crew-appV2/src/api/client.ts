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
  const res = await fetch(`${API_BASE_URL}${path}`, { method, headers, body: payload });
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
